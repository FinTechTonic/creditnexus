# PM2 Development Setup

This guide describes how to run CreditNexus development processes with **PM2** and collect logs in a project folder for easy access.

## Implementation plan (summary)

| Deliverable | Location |
|-------------|----------|
| PM2 ecosystem | `ecosystem.config.cjs` (backend-dev, frontend-dev, `logs/pm2/`) |
| NPM scripts | `dev:pm2`, `dev:pm2:stop`, `dev:pm2:restart`, `dev:pm2:logs`, `dev:pm2:status` |
| Log directory | `logs/pm2/` (ignored via `logs/` in `.gitignore`) |
| Documentation | This file; conceptual notes in `dev/pm2.md` |
| Dependencies | `pm2` in `devDependencies`; use `npx pm2` in scripts |

---

## 1. Purpose

- **Run dev processes**: Backend (FastAPI) and frontend (Vite) under PM2.
- **Centralize logs**: All stdout/stderr go to `logs/pm2/` in the project root.
- **Mirror prod behavior**: One command to start, stop, and inspect; logs persist across restarts and terminal disconnects.

---

## 2. Prerequisites

- **Node.js** 18+ (for `npm` and PM2).
- **PM2**: either
  - `npm install` in project root (uses `pm2` from `devDependencies` and `npx pm2` in scripts), or
  - `npm install -g pm2` and use `pm2` directly instead of `npx pm2`.
- **Python** 3.10+ and project deps (e.g. `uv sync` or `pip install -e .`).
- **.env** at project root (see [Installation](/getting-started/installation)).

---

## 3. Project Layout

| Item | Path |
|------|------|
| PM2 config | `ecosystem.config.cjs` |
| Log directory | `logs/pm2/` |
| Backend stdout | `logs/pm2/backend-dev-out.log` |
| Backend stderr | `logs/pm2/backend-dev-error.log` |
| Frontend stdout | `logs/pm2/frontend-dev-out.log` |
| Frontend stderr | `logs/pm2/frontend-dev-error.log` |

`logs/` is in `.gitignore`; log files are local only.

---

## 4. Processes and Ports

| App name | Process | Port | Notes |
|----------|---------|------|-------|
| `backend-dev` | `python scripts/run_dev.py` (Uvicorn) | 8000 | Hot reload via Uvicorn |
| `frontend-dev` | `npm run dev` (Vite) in `client/` | 5000 | Proxies `/api` → `http://127.0.0.1:8000` |

- **Backend**: <http://127.0.0.1:8000>, docs at <http://127.0.0.1:8000/docs>.
- **Frontend**: <http://localhost:5000> (or <http://0.0.0.0:5000>).

---

## 5. Commands

### 5.1 NPM scripts (recommended)

Run from **project root**:

| Script | Description |
|--------|-------------|
| `npm run dev:pm2` | Ensure `logs/pm2` exists and start both apps from `ecosystem.config.cjs` |
| `npm run dev:pm2:stop` | Delete `backend-dev` and `frontend-dev` from PM2 |
| `npm run dev:pm2:restart` | Restart both apps |
| `npm run dev:pm2:logs` | Live tail of all PM2 logs |
| `npm run dev:pm2:status` | Show status of PM2 processes |

### 5.2 PM2 commands

If PM2 is only in `devDependencies`, use `npx pm2` instead of `pm2`.

| Command | Description |
|---------|-------------|
| `pm2 start ecosystem.config.cjs` | Start all apps in the ecosystem file |
| `pm2 start ecosystem.config.cjs --only backend-dev` | Start only backend |
| `pm2 start ecosystem.config.cjs --only frontend-dev` | Start only frontend |
| `pm2 status` | List apps, PID, status, restarts, CPU/mem |
| `pm2 logs` | Tail all logs (stdout + stderr) |
| `pm2 logs backend-dev` | Tail only backend |
| `pm2 logs frontend-dev` | Tail only frontend |
| `pm2 logs --lines 200` | Show last 200 lines |
| `pm2 info backend-dev` | Detailed info for one app |
| `pm2 restart backend-dev` | Restart one app |
| `pm2 restart ecosystem.config.cjs` | Restart both |
| `pm2 stop backend-dev` | Stop (keep in PM2) |
| `pm2 delete backend-dev` | Remove from PM2 |
| `pm2 delete backend-dev frontend-dev` | Remove both (or use `npm run dev:pm2:stop`) |
| `pm2 flush` | Truncate all PM2 log files (does not change `logs/pm2/` paths if set in config) |
| `pm2 save` | Save process list (for `pm2 resurrect` after reboot) |
| `pm2 startup` | Generate command to run PM2 on OS boot |

---

## 6. Ecosystem Config Keys

Relevant keys in `ecosystem.config.cjs`:

| Key | Purpose |
|-----|---------|
| `name` | PM2 app name (`backend-dev`, `frontend-dev`) |
| `script` | Executable (`python`, `npm`) |
| `args` | Arguments (`scripts/run_dev.py`, `run dev`) |
| `cwd` | Working directory (project root or `client`) |
| `interpreter` | `none` so PM2 does not use Node to run Python/npm |
| `env` | `NODE_ENV: 'development'` etc. |
| `out_file` | Stdout log path (`logs/pm2/<name>-out.log`) |
| `error_file` | Stderr log path (`logs/pm2/<name>-error.log`) |
| `log_date_format` | Timestamp in logs (`YYYY-MM-DD HH:mm:ss.SSS`) |
| `merge_logs` | `false` = separate out/error files |
| `watch` | `false`; Uvicorn/Vite handle hot reload |
| `autorestart` | Restart on exit |
| `max_restarts` | Max restarts in a short time |
| `min_uptime` | Minimum uptime to consider a start “successful” |

---

## 7. Quick Start

```bash
# From project root
npm install -g pm2
npm run dev:pm2
```

Then open:

- Frontend: http://localhost:5000  
- API docs: http://127.0.0.1:8000/docs  

View logs:

```bash
npm run dev:pm2:logs
# or
pm2 logs backend-dev
pm2 logs frontend-dev
```

Stop:

```bash
npm run dev:pm2:stop
```

---

## 8. Customization

### 8.1 Python / `uv`

If you use `uv` and want PM2 to run the project interpreter:

- Change `backend-dev` in `ecosystem.config.cjs` to:
  - `script: 'uv'`
  - `args: 'run python scripts/run_dev.py'`

### 8.2 Python executable

If `python` is not on `PATH` or you use `python3` / `py`:

- Set `script` to the full path or `python3` / `py`, and adjust `args` if needed.

### 8.3 Backend path

- The backend entry is `scripts/run_dev.py`. To use a different script (e.g. `uv run python scripts/run_dev.py`), set `script` and `args` in the `backend-dev` app accordingly.

### 8.4 Log directory

- Edit `logsDir` in `ecosystem.config.cjs` and the `out_file` / `error_file` paths to point to another folder (e.g. `dev/pm2-logs`).

---

## 9. PM2 vs Hot Reload

- **PM2**: process lifecycle, restarts, log aggregation.
- **Hot reload**: Uvicorn (`--reload`) and Vite handle code changes.

We keep `watch: false` in the ecosystem so only Uvicorn and Vite do file watching.

---

## 10. Boot Persistence (Optional)

On a server or VM you can have PM2 restore apps after reboot:

```bash
pm2 startup   # run the command it prints (e.g. sudo env PATH=... pm2 startup systemd -u user --hp /home/user)
pm2 save
```

On laptops this is usually optional.

---

## 11. File Reference

- **Ecosystem**: `ecosystem.config.cjs` (project root)
- **Backend entry**: `scripts/run_dev.py` → `server:app` (Uvicorn)
- **Frontend**: `client/` with `npm run dev` (Vite)
- **Conceptual notes**: `dev/pm2.md`

---

## 12. Troubleshooting

| Issue | What to try |
|-------|-------------|
| `python` not found | Use full path, `python3`, or `uv` (see §8). |
| `logs/pm2` missing | `npm run dev:pm2` creates it; or `mkdir -p logs/pm2` (Unix) / `mkdir logs\pm2` (Windows). |
| Port 8000 or 5000 in use | Stop the other process or change `run_dev.py` / `client/vite.config.ts` and the ecosystem. |
| Backend exits immediately | Check `logs/pm2/backend-dev-error.log` and `.env` (e.g. `DATABASE_URL`). |
| Frontend exits | Check `logs/pm2/frontend-dev-error.log` and `client/node_modules` (`npm install` in `client/`). |
| PM2 not in PATH | Use `npx pm2` (after `npm install`) or install globally: `npm install -g pm2`. |
