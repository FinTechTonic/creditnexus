# .nexus File Transfer E2E – Testing Plan

## 1. Overview

**Feature**: End-to-end .nexus file transfer from **Client A → Server → Client B**.

**Scope**:
- Client A (sender): generates a .nexus file via `POST /api/nexus/generate`.
- Server: persists send event, returns .nexus bytes.
- Client B (receiver): uploads the .nexus file via `POST /api/nexus/upload`.
- Server: parses .nexus, creates receive event, returns workflow data.

**Test location**: `tests/compatibility/test_nexus_file_transfer_e2e.py`

---

## 2. Prerequisites

| Requirement | Notes |
|-------------|--------|
| **PM2 dev stack** | `npm run dev:pm2` (backend on 8000, frontend on 5000) |
| **Python 3.10+** | `uv run` or project venv |
| **Backend base URL** | Default `http://127.0.0.1:8000`; override via `BASE_URL` |
| **Demo user** | `demo@creditnexus.app` / `DemoPassword123!` (created by server or `scripts/dev/create_demo_user.py`) |
| **Optional second user** | `auditor@creditnexus.app` / `Auditor123!` (from `scripts/dev/seed_demo_users.py`) for two-client flow |
| **LINK_ENCRYPTION_KEY** | Optional; if unset, server uses an in-memory key (works for single run; set in `.env` for consistency across restarts) |
| **Database** | PostgreSQL or SQLite; `SharingEvent` (and `WorkflowDelegation` if used) must exist (Alembic migrations) |

---

## 3. PM2 and Run Order

### 3.1 Start the stack

```bash
# From project root
npm install
npm run dev:pm2
```

- Ensures `logs/pm2/` and starts `backend-dev` (8000) and `frontend-dev` (5000).
- Backend: `scripts/run_dev.py` → Uvicorn.
- Frontend: Vite in `client/`; `/api` proxied to `http://127.0.0.1:8000`.

### 3.2 Wait for backend

The E2E script polls `GET /api/health` until 200 or `NEXUS_E2E_HEALTH_TIMEOUT` (default 60s).

### 3.3 Run the E2E test

```bash
uv run python tests/compatibility/test_nexus_file_transfer_e2e.py
# or
pytest tests/compatibility/test_nexus_file_transfer_e2e.py -v
# or
npm run test:nexus-e2e
```

**PM2 is not used to run the test itself**; the test is an HTTP client. PM2 is only for running the server (and optionally the frontend).

---

## 4. Test Flows

### 4.1 Same-user (self-transfer)

1. Login as `SENDER_EMAIL` → JWT.
2. `POST /api/nexus/generate` (workflow_type=verification, deal_id=null, include_files=true).
3. Receive .nexus bytes.
4. `POST /api/nexus/upload` with multipart `file` = .nexus bytes.
5. Assert `status == "success"` and `workflow_id` present.

**Purpose**: Validates generate → upload round-trip and server-side parse/send-receive events.

### 4.2 Two-client (Client A → Server → Client B)

1. Login as `SENDER_EMAIL` → JWT (Client A).
2. `POST /api/nexus/generate` → .nexus bytes.
3. Login as `RECEIVER_EMAIL` → JWT (Client B); if this fails, fallback to sender JWT.
4. `POST /api/nexus/upload` with .nexus bytes as Client B.
5. Assert `status == "success"`.

**Purpose**: Validates transfer between two distinct users via the server.

---

## 5. Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `BASE_URL` | `http://127.0.0.1:8000` | Backend base (no trailing slash) |
| `NEXUS_E2E_SENDER_EMAIL` | `demo@creditnexus.app` | Sender login |
| `NEXUS_E2E_SENDER_PASSWORD` | `DemoPassword123!` | Sender password |
| `NEXUS_E2E_RECEIVER_EMAIL` | `auditor@creditnexus.app` | Receiver (two-client) |
| `NEXUS_E2E_RECEIVER_PASSWORD` | `Auditor123!` | Receiver password |
| `NEXUS_E2E_HEALTH_TIMEOUT` | `60` | Seconds to wait for `/api/health` |
| `NEXUS_E2E_HTTP_TIMEOUT` | `30.0` | Timeout for HTTP calls |

---

## 6. Success and Failure

- **Exit 0**: At least same-user flow passed (two-client may be skipped or failed if receiver missing).
- **Exit 1**: Same-user flow failed.
- **Exit 2**: Backend not healthy within `NEXUS_E2E_HEALTH_TIMEOUT`.

---

## 7. Optional: Run Script (scripts/dev)

A wrapper can:

1. Start PM2 if not already running (`npm run dev:pm2`).
2. Wait for `GET /api/health` 200.
3. Run `uv run python tests/compatibility/test_nexus_file_transfer_e2e.py`.
4. Optionally leave PM2 running or stop it.

Implemented wrappers:

- **PowerShell** (from project root): `.\scripts\dev\run_nexus_e2e.ps1`
- **Bash** (from project root): `./scripts/dev/run_nexus_e2e.sh`

Both start the PM2 stack if needed, wait for `/api/health`, then run the E2E script.

---

## 8. Logs and Debugging

- **PM2**: `npx pm2 logs backend-dev` or `logs/pm2/backend-dev-out.log`, `backend-dev-error.log`.
- **E2E script**: Prints `[nexus-e2e]` to stdout and `[nexus-e2e] ERROR:` to stderr.
- **Common issues**:
  - Nexus routes not mounted: ensure `server.py` includes `nexus_router` (`app.include_router(nexus_router)`).
  - 401 on /api/nexus/*: wrong credentials or missing `Authorization: Bearer <token>`.
  - 404 on /api/nexus/*: base URL wrong (e.g. frontend 5000 without `/api` proxy to 8000); use `BASE_URL=http://127.0.0.1:8000`. Also ensure `server.py` includes `app.include_router(nexus_router)` and restart backend (`npm run dev:pm2:restart`).
  - 405 on /api/nexus/generate: the path may be matched by another route or the running backend was started before `nexus_router` was added. Restart: `npm run dev:pm2:restart`.
  - **`cannot import name 'PermissionKey' from 'app.db.models'`** (or `SharingEvent`): the `PermissionKey`, `PermissionKeyType`, and `SharingEvent` models must exist in `app/db/models.py`. These are used by `nexus_routes` and `permission_key_service` / `sharing_event_service`. Ensure `alembic upgrade head` has been run so `permission_keys` and `sharing_events` tables exist.
  - **Backend not healthy / connection refused**: the backend can take 10–30s to finish lifespan (DB init, policy engine, demo user, etc.). If PM2 was just started, wait a bit before running the E2E, or rely on the health timeout (default 60s). If the backend keeps exiting, check `logs/pm2/backend-dev-error*.log` for import or startup errors (e.g. missing `PermissionKey`/`SharingEvent` causing a crash loop).
  - Parse/decrypt errors on upload: `LINK_ENCRYPTION_KEY` changed between generate and upload, or .nexus corrupted; for single process, in-memory key is usually sufficient.

---

## 9. References

- `.nexus` format: `docs/specifications/nexus-file-format.md`
- PM2 dev: `docs/guides/pm2-dev-setup.md`, `.cursor/rules/pm2-dev-and-logging.mdc`
- Nexus API: `app/api/nexus_routes.py` (`/api/nexus/generate`, `/api/nexus/upload`)
- Generator/parser: `app/utils/nexus_file_generator.py`, `app/utils/nexus_file_parser.py`
