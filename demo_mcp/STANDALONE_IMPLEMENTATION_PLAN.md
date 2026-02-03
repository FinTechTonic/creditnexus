# Standalone demo_mcp Implementation Plan

**Goal:** Make `demo_mcp/` completely standalone so it can run in production on Replit without the main CreditNexus repo. Vendor required backend behavior into demo_mcp; deploy MCP + onboarding as a single Replit application with the **Replit website = onboarding site** (demo_mcp/onboarding/). The **autonomous** agent (demo_mcp/autonomous/) is **published in parallel** with a **capability + adapter** layout: capability (MCP client + x402, platform-agnostic) and adapters (OpenClaw SKILL.md, OpenAI openapi.yaml, Anthropic tools.json) so “publish once, run everywhere.” ETC support deferred.

**Scope:** Use the **folder** `demo_mcp/` as the standalone unit (no separate repository). The same folder works in two modes: (1) **Monorepo** – run from CreditNexus root with `PYTHONPATH=<repo_root>`; (2) **Standalone** – run from `demo_mcp/` as project root (e.g. Replit root = contents of demo_mcp). Dual-mode is achieved via path bootstrap in `server/server.py` and try/except imports (`server` first, then `demo_mcp.server`) so one codebase serves both.

**ETC:** ETC token support (Project 5) is deferred; not included in the task breakdown below.

---

## 0. Stubbed vs vendored dependencies (investigation summary)

| Dependency | Main app usage | Standalone approach | Vendor? |
|------------|----------------|---------------------|---------|
| **Stock prediction (daily)** | `StockPredictionService.predict_daily` → `ChronosModelManager.run_inference` → **Modal** `chronos_modal/app.py::chronos_inference` or local `chronos.ChronosPipeline` | **Stub only.** No Modal, no Chronos, no torch. Return exact response shape from `server/vendored/stock_stub.py` (stdlib only). | No |
| **Backtest** | `run_backtest_from_data_source` → `get_historical_data` (market data) + `run_backtest` (OHLCV + strategies) in `app/stock_prediction_core/backtesting.py` | **Stub only.** No market data, no pandas/numpy. Return exact response shape from `server/vendored/stock_stub.py` (stdlib only). | No |
| **Plaid (link-token, exchange, agent-score)** | `app/services/plaid_service.py` (create_link_token, exchange_public_token) + DB `UserImplementationConnection` / `VerifiedImplementation` | **Vendored.** `server/vendored/plaid_local.py` + `server/vendored/db.py` (SQLite). Use `plaid-python`; no Modal. | Yes (plaid-python + SQLite) |

- **Modal / Chronos:** Not vendored. Main app uses `chronos_modal/app.py` (Modal) and `ChronosModelManager` (Modal or local Chronos). Standalone uses **stub only** so there is no dependency on Modal, chronos-bolt, or torch.
- **Exact response shapes** (for stubs) are defined in Section 12 under Project 2 and Project 3 line-level todos.

---

## 1. Current Dependencies on Main Repo

### 1.1 Python path and imports

- **MCP server** (`server/server.py`) sets `project_root = Path(__file__).parent.parent.parent` (CreditNexus repo root) and uses `from demo_mcp.server.config`, `from demo_mcp.server.services`, `from demo_mcp.server.tools`.
- **Implication:** When running standalone, the project root must be the `demo_mcp` directory; there is no parent `creditnexus` package. All `demo_mcp.server.*` imports must become `server.*` when running in standalone mode.

### 1.2 HTTP dependencies on CreditNexus backend

The MCP server’s `server/services/backend.py` calls these CreditNexus APIs:

| API | Purpose | Used by |
|-----|---------|--------|
| `GET /api/stock-prediction/daily` | Daily prediction (symbol, horizon) | run_prediction |
| `POST /api/stock-prediction/backtest` | Backtest (symbol, start, end, strategy) | run_backtest |
| `GET /api/banking/link-token` | Plaid Link token | Plaid KYC (onboarding + open_bank_account) |
| `POST /api/banking/connect` | Plaid exchange + store (optional agent_wallet) | Plaid KYC |
| `GET /api/agent-score?wallet=0x...` | Plaid-derived borrower score by agent wallet | get_borrower_score, get_agent_reputation_score |

- **Implication:** For full standalone, these five surfaces must be implemented inside demo_mcp (vendored or stubbed) so no live CreditNexus backend is required.

### 1.3 Launcher and ecosystem

- **`scripts/launch-demo-mcp.mjs`** and **`ecosystem.config.cjs`** start:
  1. CreditNexus backend (repo root, `uv run scripts/run_dev.py`)
  2. MCP server (repo root, `uv run demo_mcp/server/server.py`, `PYTHONPATH=projectRoot`)
  3. Onboarding (repo root, `uv run demo_mcp/onboarding/server.py`)
- The launcher also logs in to CreditNexus and creates an API key for the MCP server.
- **Implication:** Standalone run must not start the main backend; instead it starts only MCP + onboarding (and, if desired, a single process that serves vendored backend APIs).

### 1.4 Onboarding

- **`onboarding/server.py`** does not import from `app`. It proxies Plaid to `MCP_SERVER_URL` and reads/writes local JSON (allowlist, submissions). It only needs `MCP_SERVER_URL` and optional `CREDITNEXUS_APP_URL` (for UI link).
- **Implication:** Onboarding is already standalone-capable; only the MCP server and “backend” need to be made self-contained.

---

## 2. Standalone Architecture

### 2.1 Recommended layout (Replit root = demo_mcp)

- **Single “backend” surface:** Implement the five APIs above inside the MCP server process (same HTTP server as FastMCP). The MCP server then calls `CREDITNEXUS_API_URL` pointing to itself (e.g. `http://127.0.0.1:4023`).
- **Three processes on Replit (vendored together):**
  1. **x402 facilitator** (port 4022): `demo_mcp/facilitator/` — Node.js service; verify + settle for Aptos and EVM. MCP server and agents depend on it for 402 payment flow. Set `APTOS_PRIVATE_KEY` (fee payer) in Replit Secrets; optional `PAY_TO_ALLOWLIST`, `FACILITATOR_MODE=creditnexus`. Started first by `run_standalone.py`.
  2. **MCP server** (port 4023): FastMCP + vendored routes for `/api/stock-prediction/daily`, `/api/stock-prediction/backtest`, `/api/banking/link-token`, `/api/banking/connect`, `/api/agent-score`. `X402_FACILITATOR_URL=http://127.0.0.1:4022` (or Replit public URL for facilitator so external agents can pay).
  3. **Onboarding** (port 8080): Existing FastAPI app; primary web port so Replit URL serves onboarding; `MCP_SERVER_URL=http://127.0.0.1:4023`.
- **No separate CreditNexus backend process.** Facilitator is vendored and deployed alongside MCP and onboarding so they depend on each other in one deploy.

### 2.2 Import and path strategy (folder demo_mcp, dual-mode)

- **Same folder** `demo_mcp/` is used in both monorepo and standalone; no separate repository.
- **Path bootstrap** in `server/server.py`: detect whether the parent of `demo_mcp` exists as a directory containing `demo_mcp` (monorepo) or not (standalone). Insert **creditnexus root** into `sys.path` in monorepo so `demo_mcp.server` resolves; insert **demo_mcp root** in standalone so `server` resolves.
- **Dual imports** in every server file: `try: from server.X import ... except ImportError: from demo_mcp.server.X import ...`. Try `server` first (standalone), then `demo_mcp.server` (monorepo). One codebase works in both contexts.
- **Standalone run:** Use `demo_mcp` as project root (e.g. Replit root = contents of demo_mcp); run `python run_standalone.py` or `python server/server.py` with `PYTHONPATH=.` (demo_mcp). **Monorepo run:** Use CreditNexus root; run `uv run demo_mcp/server/server.py` with `PYTHONPATH=<repo_root>`; launcher can set STANDALONE=0 and start backend, or STANDALONE=1 and skip backend (vendored APIs only).

---

## 2.3 Three-layer model (capability / adapter / distribution)

Standalone demo_mcp is optimized around three layers, not platforms:

| Layer | Role | In demo_mcp |
|-------|------|-------------|
| **1. Capability** | What the skill actually does; portable, canonical; knows nothing about OpenAI, Claw, Anthropic. | **MCP server** (HTTP API): payment-protected tools (run_prediction, run_backtest, open_bank_account, scores). **Autonomous agent** (Node CLI/package): `demo_mcp/autonomous/` — agent that calls MCP, handles x402, runs locally or as package. |
| **2. Adapter** | Thin wrappers per platform: how to call the capability + how to describe it to that agent system. | **OpenClaw/Moltbot:** SKILL.md (human-readable, ClawHub). **OpenAI:** openapi.yaml (GPTs, Assistants). **Anthropic:** tools.json (Claude). **Local:** manifest.json or README. Live under `autonomous/adapters/` (or equivalent) so one repo can be ingested by every platform. |
| **3. Distribution** | Where people find it. | **GitHub** = canonical source (tag releases, version). **Replit** = **onboarding site** as the **default web** (demo_mcp/onboarding/) — the Replit URL serves the onboarding flow (landing + flow.html), not the MCP or agent UI. **Autonomous** = published in parallel (same repo or subtree) with capability + adapters so OpenClaw, OpenAI, Claude, local agents can consume it. |

- **Replit website = onboarding:** The Replit deployment’s **default web** (main URL) must serve **demo_mcp/onboarding/** (landing + flow.html). MCP runs on a secondary port (4023); clients and adapters point at the MCP URL. Users who open the Replit app see the onboarding site first.
- **Autonomous published in parallel:** The `demo_mcp/autonomous/` repository (or folder) is published alongside the Replit site: capability (agent + tools) + adapters (SKILL.md, openapi.yaml, tools.json). GitHub remains the source of truth; Replit is where users onboard; adapters let each platform consume the same capability.

---

## 3. Vendored Backend Behavior

### 3.1 Prediction and backtest (stub)

- **Scope:** No Chronos, no PostgreSQL, no market data.
- **Vendor:** New module e.g. `server/vendored/stock_stub.py`.
  - **GET /api/stock-prediction/daily?symbol=...&horizon=...**  
    Return a deterministic or random stub, e.g. `{"forecast": [...], "model_id": "standalone-stub"}` with a small list of floats (e.g. 30 values for 30-day horizon). Match the shape the MCP tool and agent expect.
  - **POST /api/stock-prediction/backtest**  
    Body: `symbol`, optional `start`, `end`, `strategy` (main app also has `timeframe`, `initial_capital`; MCP backend sends only symbol/start/end/strategy). Return stub with **exact** main-app shape: `total_return`, `sharpe_ratio`, `max_drawdown`, `win_rate`, `n_trades`, `equity_curve`, `trades`, `metadata` (see `app/api/stock_prediction_routes.py` L169–177, `app/stock_prediction_core/backtesting.py` BacktestResult).
- **Auth:** Optional `X-API-Key` (same as current); if `CREDITNEXUS_SERVICE_KEY` is set, require it for these routes when called by the MCP server (self-calls can use that key).

### 3.2 Plaid (vendored)

- **Scope:** Only link-token creation and public-token exchange; store connection in SQLite with optional `agent_wallet`.
- **Vendor:** New module e.g. `server/vendored/plaid_stub.py` (or `plaid_local.py`) and a small SQLite schema.
- **Dependencies:** Add `plaid-python` (and Python-dotenv if not already) to `server/requirements.txt`.
- **Schema (SQLite):**
  - Table `implementations`: `id`, `name` (e.g. `plaid`), `is_active`.
  - Table `plaid_connections`: `id`, `implementation_id`, `user_id` (string, e.g. `mcp-demo`), `connection_data` (JSON: `access_token`, `item_id`, optional `agent_wallet`), `is_active`, `created_at`.
- **Logic to vendor (from main app’s plaid_service):**
  - `create_link_token(user_id: str)` → call Plaid `link_token_create`; return `{"link_token": "..."}` or `{"error": "..."}`. Use env `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` (sandbox/development/production).
  - `exchange_public_token(public_token: str, agent_wallet: Optional[str] = None)` → call Plaid `item_public_token_exchange`; insert row into `plaid_connections` with `connection_data = { "access_token", "item_id", "agent_wallet" }`; return `{"status": "connected", "connection_id": id}` or error.
- **API surface:**
  - **GET /api/banking/link-token**  
    No body; optional `X-API-Key`. Call vendored `create_link_token("mcp-demo")`; return JSON.
  - **POST /api/banking/connect**  
    Body: `public_token`, optional `agent_wallet`. Call vendored `exchange_public_token(...)`; return JSON.
- **Plaid secrets:** In Replit, set `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` (and optionally `CREDITNEXUS_SERVICE_KEY` for self-calls). If Plaid is not configured, return 503 or `{"error": "Plaid not configured"}` for link-token and connect.

### 3.3 Agent score (vendored)

- **Scope:** Return a Plaid-derived score for an agent wallet when a Plaid connection exists for that wallet.
- **Vendor:** In the same SQLite + vendored Plaid module, implement `get_plaid_connection_by_agent_wallet(agent_wallet: str)` (query `plaid_connections` where `connection_data->agent_wallet` matches).
- **GET /api/agent-score?wallet=0x...**  
  Query by wallet; if a connection exists, return `{"plaid_score": 50}` (or a constant); else 404 or `{"plaid_score": null}`. Optional `X-API-Key` for consistency with main app.

### 3.4 Where to mount vendored routes

- **Option (recommended):** Add these routes to the **same FastMCP app** in `server/server.py` via `@mcp.custom_route(...)` (or equivalent) so one process serves:
  - MCP transport (e.g. `/mcp`)
  - Existing `/plaid/link-token`, `/plaid/exchange`
  - New `/api/stock-prediction/daily`, `/api/stock-prediction/backtest`, `/api/banking/link-token`, `/api/banking/connect`, `/api/agent-score`
- Set `CREDITNEXUS_API_URL=http://127.0.0.1:4023` (and same host in production with Replit’s public URL if needed for server-side self-calls) so `backend.py` continues to use httpx to “CreditNexus” which is now this server.

---

## 4. Configuration and Env

### 4.1 Standalone mode flag

- **STANDALONE=1** (or **REPLIT=1**): Use vendored backend; default `CREDITNEXUS_API_URL` to `http://127.0.0.1:4023`. Optionally skip API key creation step in launcher.
- **Server config** (`server/config/settings.py`): If `CREDITNEXUS_API_URL` is empty and standalone mode is set, default to `http://127.0.0.1:4023`.

### 4.2 Replit secrets / env

- **Required for full demo (with vendored facilitator):**  
  **`APTOS_PRIVATE_KEY`** (hex with `0x`) — fee payer for facilitator `/settle` on Aptos. Set in Replit Secrets.  
  `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` (if using Plaid).
- **Optional:**  
  `X402_FACILITATOR_URL` — when facilitator is vendored, run_standalone sets it to `http://127.0.0.1:4022` for MCP; on Replit set to the **public** facilitator URL (port 4022) so external agents can pay.  
  `X402_EVM_FACILITATOR_URL`, `CREDITNEXUS_SERVICE_KEY`, `ONBOARDING_ALLOWLIST_FILE`, `AGENT_ALLOWLIST`, `PAY_TO_ALLOWLIST`, `FACILITATOR_MODE=creditnexus`, Aptos/EVM network and asset config.  
  For EVM (open_bank_account): `EVM_RELAYER_PRIVATE_KEY`, `BASE_SEPOLIA_RPC` in facilitator env.
- **SQLite path:** e.g. `server/data/standalone.sqlite` or `REPLIT_VAR`; ensure directory exists and is writable.

---

## 5. ETC Token Support (Ethereum Classic)

- **ETC:** chainId **61**, native symbol ETC. “Accept ETC” here means the **agent** (and optionally facilitator) can use ETC as a payment or display option.
- **Autonomous agent** (`autonomous/src/lib/chains.js`): Add an **`etc`** entry (chainId 61, name "Ethereum Classic", nativeToken ETC, explorer, rpcs). Then `getChain("etc")` and other helpers work for ETC.
- **Facilitator:** Current `facilitator/src/evm.ts` supports Base Sepolia (84532) and Base (8453). Adding ETC (61) would require:
  - ETC chain config in viem (or equivalent), and
  - A USDC or accepted token contract on ETC if x402 payments on ETC are required.
- **Recommendation:**  
  - **Phase 1:** Add ETC to the **agent’s** `chains.js` so the agent can reason about ETC and show ETC addresses/explorers.  
  - **Phase 2 (optional):** If x402 facilitator supports ETC and there is a stablecoin on ETC, add ETC to the facilitator’s EVM config and expose it in MCP/facilitator env (e.g. `ETC_NETWORK`, `ETC_PAYTO`). Document in README that ETC is supported for display/agent use; payment support depends on facilitator and token availability.

---

## 6. Replit Deployment

### 6.1 Replit default web = onboarding site

- The **Replit website** (the URL users see when they open the Replit app) must be the **onboarding site** (`demo_mcp/onboarding/`): landing page (index.html) and onboarding flow (flow.html). MCP is a backend service on a secondary port; it is not the default web.
- **Port assignment:** Start **onboarding** on the **primary (web) port** (e.g. `8080` or `5000` — use Replit’s expected web port or env `ONBOARDING_PORT`). Start **MCP** on a secondary port (e.g. `4023`). Replit’s “web” preview / default URL should point at the onboarding port so `https://<repl>.replit.app` → onboarding site.
- **Single entrypoint:** `run_standalone.py` (or equivalent) starts (1) onboarding server on **primary port first** (so Replit binds web to it), (2) MCP server on secondary port. Both stay alive; onboarding is the public face.

### 6.2 Run command (one main process + optional second)

- **Single entrypoint that spawns two processes:** e.g. `python run_standalone.py` which starts (1) **onboarding** on `ONBOARDING_PORT` (default `8080` or Replit web port), (2) **MCP** on `MCP_PORT` (default `4023`). Order: start onboarding first so the primary port is the web site. Keep both alive (subprocess.Popen, then wait or signal handling).
- **Two run targets:** If Replit supports multiple run targets, configure “Web” = onboarding (primary port), “MCP” = server (4023). Expose both; default URL = onboarding.

### 6.3 Build (if any)

- **MCP server:** `pip install -r server/requirements.txt` (include `plaid-python` and any new deps). No front-end build for MCP.
- **Onboarding:** Static files only; no build. Python deps: `pip install -r onboarding/requirements.txt`.
- **Optional:** Single `requirements.txt` at demo_mcp root that merges server + onboarding + vendored deps for one `pip install` before run.

### 6.4 .replit and replit.nix (in demo_mcp)

- **Create `demo_mcp/.replit`:**
  - **run:** e.g. `python run_standalone.py` or `node scripts/start-standalone.mjs` (see below).
  - **Modules:** e.g. `python-3.11`, `nodejs-20` if the starter script is Node.
- **Create `demo_mcp/replit.nix` (or use Replit’s default):** Ensure Python 3.10+, Node 18+ if needed, and any system libs required by Plaid/SQLite.

### 6.5 Start script (example)

- **`run_standalone.py`** at demo_mcp root:
  - Set `os.environ.setdefault("STANDALONE", "1")`, `os.environ.setdefault("CREDITNEXUS_API_URL", "http://127.0.0.1:4023")`.
  - **Primary (web) port = onboarding:** Read `ONBOARDING_PORT` (default `8080` or `5000` so Replit treats it as web). Spawn **onboarding first**: `python onboarding/server.py` with `PORT=<ONBOARDING_PORT>`, `MCP_SERVER_URL=http://127.0.0.1:4023` (or Replit public MCP URL in prod), `cwd=Path(__file__).parent`.
  - **Secondary port = MCP:** Spawn MCP: `python server/server.py` with `PORT=4023`, `PYTHONPATH=.` (demo_mcp root).
  - Wait on both (e.g. `process.wait()` or signal handling). Replit’s default web URL should point at ONBOARDING_PORT so the site is the onboarding app.

---

## 7. File and Code Change Checklist

### 7.1 Import and path (standalone)

- [ ] **server/server.py:**  
  - When running standalone (e.g. `STANDALONE=1` or path detection), set `project_root = Path(__file__).resolve().parent.parent` and `sys.path.insert(0, str(project_root))`.  
  - Use a single import style: either always `from server.*` when a top-level package `server` is present (standalone), or keep `from demo_mcp.server.*` and ensure standalone run adds the parent of `demo_mcp` to path (so “demo_mcp” is the package name). Recommended: **standalone-only codebase** uses `server` and `onboarding` as top-level packages; no `demo_mcp` in path.
- [ ] **server/config/**, **server/services/**, **server/tools/**: Replace `from demo_mcp.server.*` with `from server.*` (or use a small compat layer that tries `server` then `demo_mcp.server`).
- [ ] **server/config/__init__.py:** Export same symbols; ensure it’s loadable as `server.config`.

### 7.2 Vendored backend

- [ ] **server/vendored/__init__.py** (optional).
- [ ] **server/vendored/stock_stub.py:** Stub implementations for daily prediction and backtest; callable from HTTP handlers.
- [ ] **server/vendored/plaid_local.py:** Plaid client (link_token, exchange), SQLite helpers for implementations + plaid_connections, `get_plaid_connection_by_agent_wallet`.
- [ ] **server/vendored/db.py** (or inline): SQLite engine/session; create tables on first use (implementations, plaid_connections).
- [ ] **server/server.py:** Register custom routes for `/api/stock-prediction/daily`, `/api/stock-prediction/backtest`, `/api/banking/link-token`, `/api/banking/connect`, `/api/agent-score`. Implement them by calling vendored modules. Optionally refactor existing `/plaid/link-token` and `/plaid/exchange` to use the same vendored Plaid + DB so one code path.
- [ ] **server/requirements.txt:** Add `plaid-python`, and any other deps for vendored code.

### 7.3 Config and env

- [ ] **server/config/settings.py:** In standalone mode, default `CREDITNEXUS_API_URL` to `http://127.0.0.1:4023`. Add `STANDALONE` or `REPLIT` env read. Add SQLite path env (e.g. `STANDALONE_DB_PATH`).
- [ ] **.env.example** (demo_mcp and server): Document `STANDALONE`, `PLAID_*`, `CREDITNEXUS_API_URL`, `X402_FACILITATOR_URL`, Replit-specific vars.

### 7.4 ETC (agent)

- [ ] **autonomous/src/lib/chains.js:** Add `etc: { chainId: 61, name: "Ethereum Classic", nativeToken: { symbol: "ETC", decimals: 18 }, explorer, rpcs }`. Update `getSupportedChains()` and any docs.

### 7.5 Replit and run

- [ ] **demo_mcp/.replit:** run command, modules, ports (4023, 4024).
- [ ] **demo_mcp/run_standalone.py** or **demo_mcp/scripts/start-standalone.mjs:** Start MCP server + onboarding; env defaults for standalone.
- [ ] **demo_mcp/README.md** (or **STANDALONE_DEPLOY.md**): Steps to deploy on Replit, env vars, and note that agent skills are published separately.

### 7.6 Launcher (monorepo)

- [ ] **scripts/launch-demo-mcp.mjs:** When `STANDALONE=1` (or no backend desired), skip starting CreditNexus backend and API key creation; only start MCP server and onboarding with correct cwd and PYTHONPATH so they work from repo root (optional, for dev in monorepo).

---

## 8. Agent Skills Published Separately

- The plan does not bundle agent skills (e.g. Clawdhub, custom tools) into the Replit app. They remain published and configured separately (e.g. Cursor/IDE MCP config pointing at the deployed MCP URL). Document in README that the Replit deployment exposes the MCP endpoint and onboarding URL; users add the MCP server to their client and use published skills as needed.

---

## 9. Testing and Follow-up

- [ ] **Run MCP server alone** with `CREDITNEXUS_API_URL` pointing at vendored routes (self); run prediction and backtest tools; confirm 402 → pay → result flow.
- [ ] **Run onboarding** with `MCP_SERVER_URL` pointing at MCP; complete allowlist + Plaid (if configured); confirm env snippet and allowlist file update.
- [ ] **Run autonomous agent** against standalone MCP (and optional facilitator); confirm prediction/backtest/banking tool flows.
- [ ] **Replit:** Deploy from a repo that contains only demo_mcp (or run from subdir); set secrets; open onboarding and MCP URLs; smoke-test tools and onboarding.
- [ ] **ETC:** After adding ETC to chains.js, run agent with a task that references ETC (e.g. “show ETC explorer”) to confirm chain resolution.

---

## 10. Summary

| Area | Action |
|------|--------|
| **Standalone root** | Replit project = demo_mcp directory; use `server` / `onboarding` as top-level packages; PYTHONPATH = demo_mcp root. |
| **Backend** | **Stub** prediction/backtest (no Modal/Chronos); **vendor** Plaid + agent-score (plaid-python + SQLite) in MCP server; serve `/api/*` from same process; point CREDITNEXUS_API_URL at self when STANDALONE. |
| **Plaid** | SQLite + plaid-python; link-token and exchange; store agent_wallet in connection_data; agent-score reads from SQLite. |
| **Imports** | Dual-mode try/except: `server` first, then `demo_mcp.server`. |
| **Replit** | **Replit website = onboarding site** (demo_mcp/onboarding/). Start onboarding on **primary (web) port** first (e.g. 8080), MCP on secondary (4023). Replit URL → onboarding; MCP URL for clients/adapters. |
| **Three layers** | **Capability:** MCP server (HTTP API) + autonomous agent (Node, src/). **Adapter:** openclaw/SKILL.md, openai/openapi.yaml, anthropic/tools.json under autonomous/adapters/. **Distribution:** GitHub = canonical; Replit = onboarding site; autonomous published in parallel. |
| **ETC** | Deferred; not in task breakdown. |
| **Agent skills** | Autonomous (capability + adapters) published in parallel; document MCP URL and onboarding URL; “How to use on OpenClaw / OpenAI / Claude / local” in autonomous/README and adapters/. |

This yields a single, deployable Replit app: MCP + onboarding, no dependency on the main CreditNexus repo or running backend, with optional ETC support in the agent and a path to ETC in the facilitator if needed later.

---

## 11. Follow-up Issues to Watch

- **Allowlist path:** When running on Replit, `ONBOARDING_ALLOWLIST_FILE` must point to a path writable in the Replit filesystem (e.g. `./onboarding/allowlist.json`). Ensure the MCP server can read the same path (e.g. absolute path or shared volume).
- **MCP_SERVER_URL in production:** On Replit, the onboarding site and clients need the **public** MCP URL (e.g. `https://<repl>.replit.app` or Replit’s assigned URL for the MCP port). Set `MCP_SERVER_URL` to that public URL so the onboarding flow and Cursor/IDE can reach the MCP.
- **CORS:** MCP server already uses CORS middleware for onboarding (different origin). In production, consider restricting `allow_origins` to the onboarding and Replit domains if needed.
- **Plaid redirect URI:** If using Plaid Link with redirect, register Replit’s onboarding URL (e.g. `https://<repl>.replit.app`) in the Plaid dashboard as an allowed redirect URI.
- **SQLite persistence:** On Replit, ensure the SQLite file path is under a persistent directory (e.g. Replit’s persistent storage) so Plaid connections and agent-score data survive restarts.
- **Facilitator URL:** Use the same public x402 facilitator (e.g. `https://x402-navy.vercel.app/facilitator` or `https://facilitator.x402.org`) or deploy the facilitator (e.g. `facilitator/`) separately and set `X402_FACILITATOR_URL` / `X402_EVM_FACILITATOR_URL` accordingly.
- **API key for self-calls:** If the MCP server calls its own `/api/*` routes with `X-API-Key`, set `CREDITNEXUS_SERVICE_KEY` to a fixed secret in Replit secrets so backend.py can send it; no need for CreditNexus admin login.

---

## 12. Projects, Activities, and Task Breakdown

Structured work for standalone demo_mcp using the **folder** `demo_mcp/` (no separate repo). Each **Project** groups **Activities**; each Activity has **file-level tasks** and **line-level subtasks** tied to the current code.

---

### Project 1: Import and path compatibility (dual-mode)

**Objective:** One codebase runs from monorepo (CreditNexus root) or standalone (demo_mcp root) via path bootstrap and try/except imports.

#### Activity 1.1: Path bootstrap in MCP server entrypoint

| File | Task | Line-level subtasks |
|------|------|---------------------|
| `demo_mcp/server/server.py` | Detect run context and set `sys.path` so both `server` (standalone) and `demo_mcp.server` (monorepo) resolve. | **L11–L14:** Replace `project_root = Path(__file__).parent.parent.parent` and single `sys.path.insert`. New logic: `_root = Path(__file__).resolve().parent.parent` (demo_mcp directory). If `_root.parent` and `(_root.parent / "demo_mcp").is_dir()` and `(_root.parent / "demo_mcp").resolve() == _root.resolve()`: monorepo — insert `str(_root.parent)` (creditnexus) so `demo_mcp.server` works. Else: standalone — insert `str(_root)` so `server` works. Keep `env_path = Path(__file__).parent / '.env'` and `load_dotenv(env_path)` unchanged. |

#### Activity 1.2: Compatible imports in server package

Use try/except in every file that imports from `demo_mcp.server`: try `from server.X` then `from demo_mcp.server.X`. Order: try `server` first (standalone), except `ImportError` then `demo_mcp.server` (monorepo).

| File | Task | Line-level subtasks |
|------|------|---------------------|
| `demo_mcp/server/server.py` | Dual imports for config, services, tools. | **L35–L36:** Replace `from demo_mcp.server.config import PORT` and `from demo_mcp.server.services import ...` with: `try: from server.config import PORT\nexcept ImportError: from demo_mcp.server.config import PORT`; same pattern for services (create_plaid_link_token, exchange_plaid_public_token). **L46:** Replace `from demo_mcp.server.tools import register_all_tools` with try/except (server.tools then demo_mcp.server.tools). |
| `demo_mcp/server/config/__init__.py` | Dual import from settings. | **L5–L26:** Replace `from demo_mcp.server.config.settings import (` with `try:\n    from server.config.settings import (\n...\n)\nexcept ImportError:\n    from demo_mcp.server.config.settings import (\n...\n)`. Keep same symbol list and `__all__`. |
| `demo_mcp/server/services/__init__.py` | Dual imports from backend and payment. | **L5–L16:** Replace `from demo_mcp.server.services.backend import (...)` and `from demo_mcp.server.services.payment import (...)` with try/except: try `from server.services.backend import ...` and `from server.services.payment import ...`, except `from demo_mcp.server.services.backend import ...` and `from demo_mcp.server.services.payment import ...`. |
| `demo_mcp/server/services/backend.py` | Dual import for config. | **L10:** Replace `from demo_mcp.server.config import CREDITNEXUS_URL, SERVICE_KEY` with try/except (server.config then demo_mcp.server.config). |
| `demo_mcp/server/services/payment.py` | Dual import for config. | **L15–L27:** Replace single `from demo_mcp.server.config import (...)` with try/except (server.config then demo_mcp.server.config); same symbol list. |
| `demo_mcp/server/tools/__init__.py` | Dual imports for all tool modules. | **L8–L11:** Replace each `from demo_mcp.server.tools.X import register_tools as register_X_tools` with try/except (server.tools.X then demo_mcp.server.tools.X). |
| `demo_mcp/server/tools/prediction.py` | Dual imports for config and services. | **L9–L10:** try `from server.config import ...` and `from server.services import ...`, except `from demo_mcp.server.config import ...` and `from demo_mcp.server.services import ...`. |
| `demo_mcp/server/tools/backtest.py` | Dual imports for config and services. | **L9–L10:** Same pattern as prediction.py (server then demo_mcp.server). |
| `demo_mcp/server/tools/banking.py` | Dual imports for config and services. | **L9–L10:** Same pattern as prediction.py. |
| `demo_mcp/server/tools/scores.py` | Dual imports for config and services. | **L10–L17:** try server.config and server.services (including get_borrower_score_for_agent), except demo_mcp.server.*. |

---

### Project 2: Stub prediction/backtest (no Modal/Chronos)

**Objective:** Implement stub APIs for `/api/stock-prediction/daily` and `/api/stock-prediction/backtest` so `backend.py` can call self when standalone. **Do not vendor Modal or Chronos;** stub only, stdlib-only.

#### Activity 2.1: Stock stub module

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 2.1.1 | `demo_mcp/server/vendored/__init__.py` | Create: `"""Vendored standalone backend (stubs + Plaid local)."""` or empty. |
| 2.1.2 | `demo_mcp/server/vendored/stock_stub.py` | Create: stub_daily, stub_backtest with exact response shapes below. |

**Line-level todos – `server/vendored/stock_stub.py`**

| # | Line / block | Todo |
|---|----------------|------|
| 2.1.2.1 | Top | Imports: `from typing import Optional`; no third-party deps. |
| 2.1.2.2 | `stub_daily(symbol: str, horizon: int = 30) -> dict` | Return shape **exactly** as main app daily API: `{"forecast": list[float], "model_id": str}`. `forecast`: length `horizon`, e.g. deterministic floats from `hash(symbol + str(horizon)) % 1000 / 1000.0` or small linear trend so agent/tool get valid-looking numbers. `model_id`: `"standalone-stub"`. Optional keys for compatibility: `"symbol"`, `"error"` (None when ok). Reference: `app/services/stock_prediction_service.py` L246–256, `chronos_modal/app.py` L42 return. |
| 2.1.2.3 | `stub_backtest(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None, strategy: Optional[str] = "chronos") -> dict` | Return shape **exactly** as main app backtest API: `total_return` (float), `sharpe_ratio` (float), `max_drawdown` (float), `win_rate` (float), `n_trades` (int), `equity_curve` (list of float), `trades` (list of dicts, e.g. `[{"side":"buy","price":...,"shares":...}]`), `metadata` (dict, e.g. `{"strategy": strategy, "symbol": symbol}`). Stub values: e.g. total_return=0.02, sharpe_ratio=0.5, max_drawdown=-0.05, win_rate=0.55, n_trades=10, equity_curve=[100_000.0, 102_000.0], trades=[], metadata={}. Reference: `app/api/stock_prediction_routes.py` L169–177, `app/stock_prediction_core/backtesting.py` BacktestResult (L25–33) and return (L169–177). |

#### Activity 2.2: Mount stub routes on MCP server

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 2.2.1 | `demo_mcp/server/server.py` | Register GET `/api/stock-prediction/daily` and POST `/api/stock-prediction/backtest`; optional X-API-Key; try/except import for vendored stock_stub. |

**Line-level todos – `server/server.py`**

| # | Location | Todo |
|---|----------|------|
| 2.2.1.1 | After L50 (after `register_all_tools(mcp)`) | Add try/except import: `try: from server.vendored.stock_stub import stub_daily, stub_backtest except ImportError: from demo_mcp.server.vendored.stock_stub import stub_daily, stub_backtest`. |
| 2.2.1.2 | New route GET `/api/stock-prediction/daily` | Parse query params `symbol` (required), `horizon` (default 30). If SERVICE_KEY set, require `X-API-Key` header and return 401 when missing. Call `stub_daily(symbol, horizon)`; return `JSONResponse(result)`. |
| 2.2.1.3 | New route POST `/api/stock-prediction/backtest` | Parse JSON body: `symbol` (required), `start`, `end`, `strategy` (optional). If SERVICE_KEY set, require X-API-Key. Call `stub_backtest(symbol, start_date=body.get("start"), end_date=body.get("end"), strategy=body.get("strategy"))`; return `JSONResponse(result)`. |

---

### Project 3: Vendored Plaid and SQLite

**Objective:** Implement `/api/banking/link-token`, `/api/banking/connect`, and `/api/agent-score` using **vendored** Plaid (plaid-python) and SQLite. No Modal.

#### Activity 3.1: SQLite schema and session

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 3.1.1 | `demo_mcp/server/vendored/db.py` | Create: SQLite engine/session, init_db(), tables implementations + plaid_connections. |
| 3.1.2 | `demo_mcp/server/config/settings.py` | Add STANDALONE, STANDALONE_DB_PATH, CREDITNEXUS_URL default when standalone; Path import. |
| 3.1.3 | `demo_mcp/server/config/__init__.py` | Export STANDALONE, STANDALONE_DB_PATH. |

**Line-level todos – `server/vendored/db.py`**

| # | Line / block | Todo |
|---|----------------|------|
| 3.1.1.1 | Top | Imports: `sqlite3`, `json`, `os`, `pathlib.Path`; read db path from env `STANDALONE_DB_PATH` or default `Path(__file__).resolve().parent.parent / "data" / "standalone.sqlite"`; ensure parent dir exists (`mkdir(parents=True, exist_ok=True)`). |
| 3.1.1.2 | `init_db()` | Create table `implementations`: `id` INTEGER PRIMARY KEY AUTOINCREMENT, `name` TEXT NOT NULL, `is_active` INTEGER DEFAULT 1. Create table `plaid_connections`: `id` INTEGER PRIMARY KEY AUTOINCREMENT, `implementation_id` INTEGER NOT NULL REFERENCES implementations(id), `user_id` TEXT NOT NULL, `connection_data` TEXT NOT NULL (JSON string), `is_active` INTEGER DEFAULT 1, `created_at` TEXT (ISO). Call `init_db()` on first use (e.g. in get_connection() or module load). |
| 3.1.1.3 | `get_connection() -> sqlite3.Connection` | Return `sqlite3.connect(db_path)`; enable `row_factory = sqlite3.Row` for dict-like rows. |
| 3.1.1.4 | Helper to run queries | Optional: context manager or function to execute and commit (e.g. insert plaid_connection, select by agent_wallet). |

**Line-level todos – `server/config/settings.py`**

| # | Location | Todo |
|---|----------|------|
| 3.1.2.1 | Top | Add `from pathlib import Path` if not present. |
| 3.1.2.2 | After L76 (ONRAMP_URL) | Add `STANDALONE = os.getenv("STANDALONE", "").strip().lower() in ("1", "true", "yes")`. Add `STANDALONE_DB_PATH = os.getenv("STANDALONE_DB_PATH") or str(Path(__file__).resolve().parent.parent / "data" / "standalone.sqlite")`. |
| 3.1.2.3 | L10–L11 (CREDITNEXUS_URL) | After current assignment, add: `if STANDALONE and (not CREDITNEXUS_URL or CREDITNEXUS_URL == "http://localhost:8000"): CREDITNEXUS_URL = "http://127.0.0.1:4023"` (or use PORT from env). Ensure PORT is read before this if using dynamic port. |

#### Activity 3.2: Plaid local module (vendored plaid-python)

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 3.2.1 | `demo_mcp/server/vendored/plaid_local.py` | Create: create_link_token, exchange_public_token, get_plaid_connection_by_agent_wallet, ensure_plaid_implementation. |
| 3.2.2 | `demo_mcp/server/requirements.txt` | Add `plaid-python>=11.0.0` (match main app plaid API). |

**Line-level todos – `server/vendored/plaid_local.py`**

| # | Line / block | Todo |
|---|----------------|------|
| 3.2.1.1 | Top | Imports: `os`, `json`, `logging`, `typing.Optional`; import vendored `db` (init_db, get_connection). Lazy-init Plaid client from env PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV (sandbox/development/production). Reference: `app/services/plaid_service.py` L33–71, L74–108, L147–165. |
| 3.2.1.2 | `create_link_token(user_id: str) -> dict` | Return `{"link_token": str}` or `{"error": str}`. Use plaid `link_token_create` with products=[transactions], country_codes=[US], client_name="CreditNexus MCP", user=LinkTokenCreateRequestUser(client_user_id=user_id). |
| 3.2.1.3 | `ensure_plaid_implementation()` | Query implementations for name="plaid"; if missing, insert one row; return impl id. Use vendored db.get_connection() and init_db(). |
| 3.2.1.4 | `exchange_public_token(public_token: str, agent_wallet: Optional[str] = None) -> dict` | Call plaid `item_public_token_exchange`; get access_token, item_id. Build connection_data = {"access_token": ..., "item_id": ...}; if agent_wallet: connection_data["agent_wallet"] = agent_wallet.strip(). Insert into plaid_connections (implementation_id from ensure_plaid_implementation(), user_id="mcp-demo", connection_data=json.dumps(connection_data), is_active=1, created_at=iso). Return `{"status": "connected", "connection_id": last_row_id}` or `{"error": str}`. |
| 3.2.1.5 | `get_plaid_connection_by_agent_wallet(agent_wallet: str)` | Query plaid_connections join implementations where name="plaid" and is_active=1; for each row parse connection_data JSON; if connection_data.get("agent_wallet", "").strip().lower() == agent_wallet.strip().lower(): return row (or dict). Return None if not found. |

#### Activity 3.3: Wire backend to vendored Plaid/stubs when STANDALONE

**Note:** Vendored stub_daily, stub_backtest, and plaid_local functions are **sync**. When STANDALONE, backend.py (async) calls them directly; blocking is acceptable for these short-lived operations. Optionally wrap in `asyncio.to_thread()` or `run_in_executor` if desired.

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 3.3.1 | `demo_mcp/server/services/backend.py` | After config import, read STANDALONE. In each of call_prediction, call_backtest, create_plaid_link_token, exchange_plaid_public_token, get_borrower_score_for_agent: if STANDALONE, call vendored stub/plaid_local and return; else keep current httpx logic. |
| 3.3.2 | `demo_mcp/server/server.py` | Register GET /api/banking/link-token, POST /api/banking/connect, GET /api/agent-score; refactor /plaid/link-token and /plaid/exchange to call same backend helpers. |

**Line-level todos – `server/services/backend.py`**

| # | Location | Todo |
|---|----------|------|
| 3.3.1.1 | After L11 (config import) | Import STANDALONE: add to config import or get from config. |
| 3.3.1.2 | `call_prediction` (L15–L46) | At start: `if STANDALONE: try: from server.vendored.stock_stub import stub_daily except ImportError: from demo_mcp.server.vendored.stock_stub import stub_daily; return stub_daily(symbol, horizon)` (sync; wrap in asyncio if needed or make stub_daily sync and await run_in_executor). Else: existing httpx GET. |
| 3.3.1.3 | `call_backtest` (L49–L90) | At start: if STANDALONE, import stub_backtest (try/except), return stub_backtest(symbol, start_date, end_date, strategy). Else: existing POST. |
| 3.3.1.4 | `create_plaid_link_token` (L118–L142) | At start: if STANDALONE, import plaid_local.create_link_token (try/except), call create_link_token(user_id or "mcp-demo") (sync), return result. Else: existing GET. |
| 3.3.1.5 | `exchange_plaid_public_token` (L145–L179) | At start: if STANDALONE, import plaid_local.exchange_public_token, call exchange_public_token(public_token, agent_wallet), return result. Else: existing POST. |
| 3.3.1.6 | `get_borrower_score_for_agent` (L93–L115) | At start: if STANDALONE, import plaid_local.get_plaid_connection_by_agent_wallet; conn = get_plaid_connection_by_agent_wallet(agent_address); return 50 if conn else None. Else: existing GET. |

**Line-level todos – `server/server.py` (API routes)**

| # | Location | Todo |
|---|----------|------|
| 3.3.2.1 | After stub routes (Activity 2.2) | Add GET /api/banking/link-token: optional X-API-Key; await create_plaid_link_token(); return JSONResponse(result). |
| 3.3.2.2 | Same block | Add POST /api/banking/connect: parse body public_token, agent_wallet; await exchange_plaid_public_token(public_token, agent_wallet); return JSONResponse(result). |
| 3.3.2.3 | Same block | Add GET /api/agent-score: query param wallet; score = await get_borrower_score_for_agent(wallet); if score is None return JSONResponse({"detail": "No Plaid connection for this agent wallet"}, status_code=404); else return JSONResponse({"plaid_score": score}). |
| 3.3.2.4 | Existing /plaid/link-token (L55–L71) | Keep calling create_plaid_link_token (backend already branches on STANDALONE). No change if backend is used. |
| 3.3.2.5 | Existing /plaid/exchange (L74–L103) | Keep calling exchange_plaid_public_token (backend already branches on STANDALONE). No change. |

---

### Project 4: Replit and standalone run (Replit web = onboarding site)

**Objective:** Single entrypoint from demo_mcp root; **Replit default web = onboarding site** (demo_mcp/onboarding/); MCP on secondary port.

#### Activity 4.1: Standalone start script (onboarding = primary port)

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 4.1.1 | `demo_mcp/run_standalone.py` | Create: start **onboarding first** on primary (web) port; then MCP on secondary port. |
| 4.1.2 | `demo_mcp/.replit` | Create: run command; **primary (web) port = onboarding port** so Replit URL → onboarding site. |
| 4.1.3 | `demo_mcp/replit.nix` | Optional: Python 3.11, plaid-python. |

**Line-level todos – `run_standalone.py`**

| # | Location | Todo |
|---|----------|------|
| 4.1.1.1 | Env defaults | Set `STANDALONE=1`, `CREDITNEXUS_API_URL=http://127.0.0.1:4023`. Read `ONBOARDING_PORT` (default `8080` or `5000` so Replit treats it as web). Read `MCP_PORT` (default `4023`). |
| 4.1.1.2 | Start order | **Start onboarding first** (so primary port binds to web): spawn `python onboarding/server.py` with `PORT=<ONBOARDING_PORT>`, `MCP_SERVER_URL=http://127.0.0.1:<MCP_PORT>`, `cwd=Path(__file__).parent`. |
| 4.1.1.3 | Then MCP | Spawn `python server/server.py` with `PORT=<MCP_PORT>`, `PYTHONPATH=str(Path(__file__).parent)`, `cwd=Path(__file__).parent`. |
| 4.1.1.4 | Wait / signals | Keep both process refs; wait on both or handle SIGTERM. |

**Line-level todos – `.replit`**

| # | Location | Todo |
|---|----------|------|
| 4.1.2.1 | run | `run = "python run_standalone.py"` (or `uv run run_standalone.py`). |
| 4.1.2.2 | ports | Expose **onboarding port** (e.g. 8080) as the **default web** port so Replit URL serves onboarding. Expose MCP port (4023) for API/MCP clients. In Replit, set the "web" port to ONBOARDING_PORT so the main URL is the onboarding site. |

#### Activity 4.2: Launcher and ecosystem (monorepo mode)

| File | Task | Line-level subtasks |
|------|------|---------------------|
| `demo_mcp/scripts/launch-demo-mcp.mjs` | Support STANDALONE=1: skip backend and API key. | **main():** If `process.env.STANDALONE === "1"`: skip steps [1/7]–[4/7]; set CREDITNEXUS_API_URL to http://127.0.0.1:4023; start only mcp-server and onboarding (cwd=demoMcpRoot, PYTHONPATH=demoMcpRoot). |
| `demo_mcp/ecosystem.config.cjs` | Optional: standalone app entries. | Document or add mcp-standalone; standalone run uses run_standalone.py with onboarding on primary port. |

---

### Project 5: ETC token support (deferred)

**Objective:** Agent support for ETC (Ethereum Classic, chainId 61) is **deferred**. No file-level or line-level tasks in this plan. When implemented: add `etc` to `autonomous/src/lib/chains.js` (chainId 61, name, nativeToken, explorer, rpcs).

---

### Project 6: Documentation and env examples

**Objective:** README and .env.example document standalone deployment and env vars.

#### Activity 6.1: Docs and env

| File | Task | Line-level subtasks |
|------|------|---------------------|
| `demo_mcp/README.md` | Add standalone deployment section. | **New subsection:** "Standalone deployment (Replit)". Steps: clone or copy demo_mcp as project root; set STANDALONE=1, PLAID_* (if using Plaid), X402_FACILITATOR_URL; optionally CREDITNEXUS_SERVICE_KEY for self-calls; run `python run_standalone.py` (or Replit run). Ports 4023 (MCP), 4024 (onboarding). Agent skills published separately; add MCP URL to client config. |
| `demo_mcp/.env.example` | Document standalone vars. | Add `STANDALONE=0`, `STANDALONE_DB_PATH=`, `PLAID_CLIENT_ID=`, `PLAID_SECRET=`, `PLAID_ENV=sandbox`. |
| `demo_mcp/server/.env.example` | Same. | Add same vars; note CREDITNEXUS_API_URL defaults to http://127.0.0.1:4023 when STANDALONE=1. |

---

### Project 8: Capability and adapter layout (autonomous)

**Objective:** Structure `demo_mcp/autonomous/` as **capability** (portable, platform-agnostic) + **adapters** (thin wrappers per platform). Publish in parallel to the Replit onboarding site so OpenClaw, OpenAI, Claude, and local agents can consume the same capability.

#### Activity 8.1: Adapter directory layout

**File-level tasks**

| # | File / path | Action |
|---|-------------|--------|
| 8.1.1 | `demo_mcp/autonomous/adapters/` | Create directory. |
| 8.1.2 | `demo_mcp/autonomous/adapters/openclaw/` | Create; move or copy SKILL for OpenClaw/Moltbot. |
| 8.1.3 | `demo_mcp/autonomous/adapters/openai/` | Create; add OpenAPI spec for MCP tools (GPTs, Assistants). |
| 8.1.4 | `demo_mcp/autonomous/adapters/anthropic/` | Create; add tools.json for Claude. |
| 8.1.5 | `demo_mcp/autonomous/adapters/local/` | Optional; manifest.json or README for local/OSS agents. |

**Line-level todos – adapters**

| # | Path | Todo |
|---|------|------|
| 8.1.2.1 | `autonomous/adapters/openclaw/SKILL.md` | **OpenClaw/Moltbot adapter.** Copy or move `autonomous/SKILL-clawdhub.md` to `adapters/openclaw/SKILL.md`. Ensure frontmatter (name, description, metadata) and body describe: how to install (clone/npm), how to run the agent (node src/run-agent.js), MCP_SERVER_URL and x402 flow. No platform-specific logic in capability; adapter only describes how to call it. Reference: existing SKILL-clawdhub.md; ClawHub discoverability. |
| 8.1.3.1 | `autonomous/adapters/openai/openapi.yaml` | **OpenAI adapter.** Add OpenAPI 3.x spec that describes the MCP server’s HTTP API (or the tools exposed to agents): run_prediction, run_backtest, open_bank_account, get_agent_reputation_score, get_borrower_score. Include paths, request/response schemas, and 402 payment requirement where applicable. Enables Custom GPTs and Assistants API to call the capability. |
| 8.1.4.1 | `autonomous/adapters/anthropic/tools.json` | **Anthropic adapter.** Add JSON schema for Claude tools: same tool set (run_prediction, run_backtest, open_bank_account, scores). Format: Claude tool-definition format (name, description, input_schema). Enables Claude to call the capability. |
| 8.1.5.1 | `autonomous/adapters/local/README.md` | Optional: short instructions for local/OSS agents (LM Studio, AutoGen, CrewAI): GitHub repo, npm install, MCP_SERVER_URL, env snippet. |

#### Activity 8.2: Capability stays platform-agnostic

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 8.2.1 | `demo_mcp/autonomous/README.md` | Update: state that **core** (src/) is the capability layer (no OpenAI/Claw/Anthropic in code); **adapters/** describe how each platform calls it. Add subsection “How to use on OpenClaw / OpenAI / Claude / local” with links to adapters. |
| 8.2.2 | `demo_mcp/autonomous/package.json` | Ensure name and description are capability-focused (e.g. “x402 MCP agent”); no platform-specific keywords required. |

**Line-level todos**

| # | Location | Todo |
|---|----------|------|
| 8.2.1.1 | `autonomous/README.md` | **New subsection:** “Capability + adapters”. Explain: capability = MCP client + x402 flow + local tools (src/); adapters = openclaw/SKILL.md, openai/openapi.yaml, anthropic/tools.json. “How to use on OpenClaw” → link to adapters/openclaw/SKILL.md. “How to use on OpenAI” → link to adapters/openai/openapi.yaml + README. “How to use on Claude” → link to adapters/anthropic/tools.json. “Local / OSS” → link to adapters/local/README.md if present. |
| 8.2.1.2 | `autonomous/README.md` | **Existing:** Keep install, config, run (node src/run-agent.js); add one line: “For platform-specific setup (OpenClaw, OpenAI, Claude), see adapters/.” |

---

### Project 9: Distribution and publish

**Objective:** **GitHub** = canonical source; **Replit** = onboarding site (default web); **autonomous** = published in parallel with capability + adapters. “Publish once, run everywhere” via one repo and multiple adapters.

#### Activity 9.1: GitHub as canonical source

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 9.1.1 | `demo_mcp/README.md` | Add “Distribution” subsection: GitHub = source of truth; tag releases; version everything. Replit = where users **onboard** (default web = onboarding site). Autonomous = published in parallel (same repo: demo_mcp/autonomous/ with adapters/). |
| 9.1.2 | Versioning | Document: tag releases (e.g. v1.0.0) at demo_mcp or repo root; CHANGELOG or version in package.json (autonomous), server (optional). |

**Line-level todos**

| # | Location | Todo |
|---|----------|------|
| 9.1.1.1 | `demo_mcp/README.md` | **New subsection:** “Distribution (three layers)”. (1) **Capability:** MCP server (server/) + autonomous agent (autonomous/src/). (2) **Adapters:** autonomous/adapters/ (OpenClaw SKILL.md, OpenAI openapi.yaml, Anthropic tools.json). (3) **Where to find it:** GitHub = canonical; Replit = onboarding site (main URL → demo_mcp/onboarding/); ClawHub / docs / template repos for discoverability. |
| 9.1.1.2 | `demo_mcp/README.md` | **Standalone deployment (Replit):** State that the **Replit website** is the **onboarding site** (landing + flow.html). MCP runs on a secondary port; add MCP URL to client/IDE config. Agent skills (autonomous + adapters) are published in parallel; use adapters for each platform. |

#### Activity 9.2: Replit = onboarding site (documentation)

**File-level tasks**

| # | File | Action |
|---|------|--------|
| 9.2.1 | `demo_mcp/README.md` | In “Standalone deployment (Replit)”, explicitly: “The Replit default web URL serves the **onboarding site** (demo_mcp/onboarding/). MCP is available on port 4023 for clients and adapters.” |
| 9.2.2 | `demo_mcp/onboarding/README.md` | Add one line: “This app is the **default web** experience when demo_mcp is deployed on Replit (landing + onboarding flow).” |

**Line-level todos**

| # | Location | Todo |
|---|----------|------|
| 9.2.1.1 | `demo_mcp/README.md` | In Replit deployment steps: “Set Replit web port to onboarding port (e.g. 8080). Opening the Replit URL shows the onboarding site; use the MCP URL (port 4023) in Cursor, Claude Desktop, or adapter configs.” |
| 9.2.2.1 | `demo_mcp/onboarding/README.md` | **New line** (after first paragraph or in “Overview”): “When demo_mcp is deployed on Replit, this onboarding site is the **default web** (main URL).” |

---

### Project 7: Testing and validation

**Objective:** Verify dual-mode and standalone behavior.

#### Activity 7.1: Manual test matrix

| Activity | Task | Subtasks |
|----------|------|----------|
| Monorepo mode | Run from CreditNexus root. | Start backend; run launch-demo-mcp.mjs (STANDALONE unset). Confirm MCP and onboarding start; tools call CreditNexus backend; Plaid and agent-score work if backend configured. |
| Standalone mode | Run from demo_mcp root. | Set STANDALONE=1; run `python run_standalone.py` from demo_mcp. Confirm **onboarding** starts on primary port (e.g. 8080) and **MCP** on 4023; run_prediction and run_backtest return stub data after 402→pay→result; Plaid link/exchange and agent-score use vendored SQLite when PLAID_* set. |
| Replit | Deploy demo_mcp as root. | Set secrets; run; **open Replit URL → onboarding site** (landing + flow.html); open MCP URL (port 4023) for clients; smoke-test one tool and allowlist flow. |
| Adapters | OpenClaw / OpenAI / Claude. | After Project 8: verify adapters/openclaw/SKILL.md, adapters/openai/openapi.yaml, adapters/anthropic/tools.json exist; README “How to use on…” points to adapters. |
| Distribution | GitHub + Replit. | After Project 9: README states GitHub = canonical, Replit = onboarding site; tag release (optional). |

---

### Summary: File-level task list

| Path | Action |
|------|--------|
| `demo_mcp/server/server.py` | Modify: path bootstrap (L11–14), dual imports (L35–36, L46), register /api/* and optionally refactor /plaid (after L50). |
| `demo_mcp/server/config/settings.py` | Modify: STANDALONE, STANDALONE_DB_PATH, CREDITNEXUS_URL default when standalone (L10–11, after L76). |
| `demo_mcp/server/config/__init__.py` | Modify: dual import from settings; export new symbols if any. |
| `demo_mcp/server/services/__init__.py` | Modify: dual imports backend + payment. |
| `demo_mcp/server/services/backend.py` | Modify: dual config import; when STANDALONE use vendored stubs/Plaid/agent-score. |
| `demo_mcp/server/services/payment.py` | Modify: dual config import. |
| `demo_mcp/server/tools/__init__.py` | Modify: dual imports for prediction, backtest, banking, scores. |
| `demo_mcp/server/tools/prediction.py` | Modify: dual imports config + services. |
| `demo_mcp/server/tools/backtest.py` | Modify: dual imports. |
| `demo_mcp/server/tools/banking.py` | Modify: dual imports. |
| `demo_mcp/server/tools/scores.py` | Modify: dual imports. |
| `demo_mcp/server/vendored/__init__.py` | Create. |
| `demo_mcp/server/vendored/stock_stub.py` | Create: stub_daily, stub_backtest. |
| `demo_mcp/server/vendored/db.py` | Create: SQLite schema, init_db, get_session. |
| `demo_mcp/server/vendored/plaid_local.py` | Create: create_link_token, exchange_public_token, get_plaid_connection_by_agent_wallet. |
| `demo_mcp/server/requirements.txt` | Modify: add plaid-python. |
| `demo_mcp/run_standalone.py` | Create: env defaults; **start onboarding first** on primary (web) port, then MCP on secondary port. |
| `demo_mcp/.replit` | Create: run; **primary (web) port = onboarding** so Replit URL → onboarding site. |
| `demo_mcp/replit.nix` | Create (optional). |
| `demo_mcp/scripts/launch-demo-mcp.mjs` | Modify: STANDALONE=1 skips backend, wait, login, API key; start MCP + onboarding from demo_mcp. |
| `demo_mcp/README.md` | Modify: Standalone deployment (Replit); **Replit web = onboarding site**; Distribution (three layers); GitHub canonical, Replit = onboarding, autonomous published in parallel. |
| `demo_mcp/.env.example` | Modify: STANDALONE, STANDALONE_DB_PATH, PLAID_*, ONBOARDING_PORT (optional). |
| `demo_mcp/server/.env.example` | Modify: same + CREDITNEXUS_API_URL note for standalone. |
| `demo_mcp/autonomous/adapters/openclaw/SKILL.md` | Create: move or copy from autonomous/SKILL-clawdhub.md; OpenClaw/Moltbot adapter. |
| `demo_mcp/autonomous/adapters/openai/openapi.yaml` | Create: OpenAPI spec for MCP tools (run_prediction, run_backtest, open_bank_account, scores). |
| `demo_mcp/autonomous/adapters/anthropic/tools.json` | Create: Claude tools schema (same tool set). |
| `demo_mcp/autonomous/adapters/local/README.md` | Create (optional): instructions for local/OSS agents. |
| `demo_mcp/autonomous/README.md` | Modify: Capability + adapters subsection; “How to use on OpenClaw / OpenAI / Claude / local” with links to adapters/. |
| `demo_mcp/onboarding/README.md` | Modify: state that this app is the **default web** when demo_mcp is deployed on Replit. |
