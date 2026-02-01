# CreditNexus x402 Demo

Two complementary implementations of x402 payment-protected tools for CreditNexus.

## Overview

This directory contains two approaches to x402 integration:

1. **Server** - Server-side payment enforcement (FastMCP)
2. **Autonomous** - Client-side autonomous agent (LangChain.js)

Both implementations can work independently or together.

---

## 1. Server (Payment-Protected MCP)

**Location**: `server/`
**Stack**: Python, FastMCP
**Approach**: Server-side payment enforcement

### What It Does

MCP server that protects CreditNexus tools with x402 payments. Uses a hybrid approach:
- CreditNexus allowlist checking (custom logic)
- Official x402 facilitator for verify/settle

### Quick Start

```bash
cd server
pip install -r requirements.txt
python server.py
```

Server runs on `localhost:4023`

### Tools Available

- `run_prediction` - Stock prediction (6¢ via Aptos USDC)

### Use Case

IDE integrations (Cursor, Claude Desktop) where the server enforces payment requirements.

**Payment Flow**:
```
Client → 402 Response → User Signs → Retry with Payment → Result
```

See `server/README.md` for details.

---

## 2. Autonomous (Agent with x402 Client)

**Location**: `autonomous/`
**Stack**: Node.js, LangChain.js
**Approach**: Client-side autonomous payment handling

### What It Does

LangChain.js agent that consumes x402-protected MCP tools. Handles payments automatically:
- Agent has its own Aptos + EVM wallets
- Agent reasons about when to pay
- Agent handles 402 → pay → retry flow autonomously

### Quick Start

```bash
cd autonomous
npm install
node src/run-agent.js "Run a 30-day prediction for AAPL"
```

### Tools Available

- `run_prediction` - Stock prediction (6¢ via Aptos)
- `run_backtest` - Trading strategy backtest (6¢ via Aptos)
- `open_bank_account` - Plaid bank account ($3.65 via Base)

### Use Case

Autonomous workflows where the agent manages its own payments without human intervention.

**Payment Flow**:
```
Agent calls tool → Gets 402 → Builds payment → Verifies → Settles → Retries → Uses result
```

See `autonomous/README.md` for details.

---

## Integration: Agent + Server

The autonomous agent can call the MCP server for enhanced protection:

```env
# In autonomous/.env
MCP_SERVER_URL=http://localhost:4023
```

**Combined Flow**:
```
Autonomous Agent
    ↓ calls
MCP Server (with allowlist)
    ↓ enforces payment
x402 Facilitator
    ↓ verifies/settles
CreditNexus Backend
```

**Plaid KYC from MCP server** – The MCP server exposes HTTP endpoints **GET /plaid/link-token** and **POST /plaid/exchange** (no x402 payment). The **onboarding** site can proxy these so users optionally connect a bank (Plaid) during onboarding; link token and exchange are served from the MCP server and backed by CreditNexus (X-API-Key). Set **MCP_SERVER_URL** on the onboarding server to enable the “Connect bank with Plaid” step.

**Benefits**:
- Agent gets autonomous payment handling
- Server provides allowlist management
- Optional Plaid KYC in onboarding, served from MCP
- Best of both approaches

---

## Architecture Comparison

| Aspect | Server | Autonomous |
|--------|--------|------------|
| **Language** | Python | Node.js |
| **Framework** | FastMCP | LangChain.js |
| **Payment Logic** | Server returns 402 | Client handles 402 |
| **Wallets** | User's external wallet | Agent's managed wallets |
| **Tools** | 1 tool (prediction) | 3 tools + local tools |
| **Allowlist** | ✅ Yes (server-side) | ❌ No |
| **x402 Integration** | Hybrid (allowlist + facilitator) | Pure facilitator |
| **Target Use Case** | IDE integrations | Autonomous workflows |

---

## One-command launch (PM2)

From the **project root** you can run the full flow: start CreditNexus backend, wait 1 minute, log in as admin, create an API key (saved to `server/.env`), start the MCP server, then run the demo agent with **human input on the terminal** (interactive prompt).

**Setup**

1. Copy `demo_mcp/.env.example` to `demo_mcp/.env` (or set in project root `.env`):
   - `ADMIN_EMAIL` – administrator email for CreditNexus
   - `ADMIN_PASSWORD` – administrator password
   - Optional: `CREDITNEXUS_URL` (default `http://localhost:8000`)

2. Ensure CreditNexus has an **instance admin** user with that email/password: the user must have `role=admin` and `is_instance_admin=True`. If you get "Instance admin access required" when creating the API key, run once from the project root:
   ```bash
   python scripts/dev/set_instance_admin.py demo@creditnexus.app
   ```
   (Use the same email as `ADMIN_EMAIL`.) Also set `MCP_DEMO_USER_ID` in CreditNexus config for API-key-authenticated requests.

**Run**

```bash
# From repo root
npm run demo-mcp:launch
```

This will:

1. Start CreditNexus backend (PM2 `backend-dev`), logs → `demo_mcp/logs/`
2. Wait 1 minute
3. Log in as administrator and create an API key; save it to `demo_mcp/server/.env` as `CREDITNEXUS_SERVICE_KEY`
4. Start the MCP server (PM2 `mcp-server`), logs → `demo_mcp/logs/`
5. Start the **onboarding site** (PM2 `onboarding`), logs → `demo_mcp/logs/`, at **http://localhost:4024** — use the flow at http://localhost:4024/flow.html to whitelist your agent (wallet, banking/KYC, allowlist, env snippet).
6. If agent dependencies are missing, the launcher runs `npm install` in `demo_mcp/autonomous`, then opens an interactive prompt: type a message and press Enter to run the agent; type `exit` to quit (backend, MCP server, and onboarding site keep running under PM2).

PM2 processes are started using `demo_mcp/ecosystem.config.cjs` so all logs are written under `demo_mcp/logs/` (e.g. `backend-dev-out.log`, `mcp-server-out.log`, `onboarding-out.log`). Open **http://localhost:4024/flow.html** to complete the whitelisting flow (connect wallet, banking/KYC, register allowlist, get env snippet) before or while using the agent.

---

## Deployment

### Option 1: Both Independent

```bash
# Terminal 1: MCP Server
cd server && python server.py

# Terminal 2: Autonomous Agent (optional)
cd autonomous && node src/run-agent.js
```

### Option 2: Agent Using Server

```bash
# Terminal 1: MCP Server
cd server && python server.py

# Terminal 2: Autonomous Agent (configured to use server)
cd autonomous
# Edit .env: MCP_SERVER_URL=http://localhost:4023
node src/run-agent.js
```

---

## x402 Protocol v2

Both implementations use x402 Protocol v2:

**Payment Requirements Format**:
```json
{
  "scheme": "x402",
  "network": "aptos:2",
  "amount": "60000",
  "asset": "0x69091fbab5f7d635ee7ac5098cf0c1efbe31d68fec0f2cd565e8d168daf52832",
  "payTo": "0x...",
  "resource": "/mcp/prediction/AAPL",
  "description": "Stock prediction for AAPL"
}
```

**Payment Payload Format** (Aptos):
```json
{
  "transaction": [/* BCS bytes */],
  "senderAuthenticator": [/* signature bytes */]
}
```

---

## Crediting agent wallets (sandbox / testnets)

For **Aptos** (run_prediction, run_backtest):

- **Testnet** (demo default): No programmatic faucet. Fund the agent at [Aptos testnet faucet](https://aptos.dev/network/faucet) (sign in, enter agent address, request APT). USDC for x402 from Circle/testnet if needed.
- **Devnet** (automated testing): Set `APTOS_FAUCET_NETWORK=devnet` and run `node src/credit-aptos-agent.js` from `demo_mcp/autonomous` (or `npm run credit:aptos` with that env). Uses [Aptos faucet API](https://aptos.dev/build/apis/faucet-api).

**Full testing script** (create Aptos wallet if missing, then credit on devnet or print testnet instructions):

```bash
# From repo root
node demo_mcp/scripts/credit-agent-wallets.mjs
# With devnet crediting:
APTOS_FAUCET_NETWORK=devnet node demo_mcp/scripts/credit-agent-wallets.mjs
```

Reference: [Canteen – Aptos x402](https://canteenapp-aptos-x402.notion.site/) for hydration and crediting patterns.

**EVM** (open_bank_account): Fund Base Sepolia and whitelist the agent at the onboarding flow; no programmatic crediting in this repo.

---

## Configuration

Environment variables and config files for the demo. Copy `server/.env.example` to `server/.env` and `autonomous/.env.example` to `autonomous/.env` as needed.

### Launcher (project root or `demo_mcp/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `ADMIN_EMAIL` | CreditNexus admin email (for API key creation) | — |
| `ADMIN_PASSWORD` | CreditNexus admin password | — |
| `CREDITNEXUS_URL` | CreditNexus backend base URL | `http://localhost:8000` |

### MCP Server (`server/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `CREDITNEXUS_API_URL` | CreditNexus backend URL (Plaid, API key auth) | `http://localhost:8000` |
| `CREDITNEXUS_SERVICE_KEY` | API key from CreditNexus admin (POST /api/admin/generate-api-key) | — |
| `X402_FACILITATOR_URL` | x402 facilitator (Aptos: prediction/backtest) | — |
| `X402_EVM_FACILITATOR_URL` | x402 facilitator for EVM (open_bank_account); falls back to `X402_FACILITATOR_URL` | same as above |
| `AGENT_ALLOWLIST` | Comma-separated agent addresses (overridden by onboarding file when set) | — |
| `PAY_TO_ALLOWLIST` | Comma-separated payTo addresses | — |
| `ONBOARDING_ALLOWLIST_FILE` | Path to allowlist JSON (e.g. `onboarding/allowlist.json`); when set, server re-reads on each request so whitelist updates without restart | — |
| `APTOS_NETWORK` | Aptos network id (e.g. `aptos:2` testnet) | `aptos:2` |
| `APTOS_USDC_ASSET` | Aptos USDC asset type (testnet resource address) | (testnet default) |
| `APTOS_PAYTO_ADDRESS` | Aptos payTo address for x402 | — |
| `BASE_SEPOLIA_NETWORK` | EVM network id (e.g. `eip155:84532`) | `eip155:84532` |
| `BASE_SEPOLIA_USDC` | Base Sepolia USDC contract | (default) |
| `BASE_SEPOLIA_PAYTO` | EVM payTo address for open_bank_account | — |
| `MCP_PRICE_PREDICTION_USD` | Price per run_prediction (USD) | `0.06` |
| `MCP_PRICE_BACKTEST_USD` | Price per run_backtest (USD) | `0.06` |
| `MCP_PRICE_BANKING_USD` | Price for open_bank_account (USD) | `3.65` |
| `MCP_PRICE_SCORE_USD` | Price per score query (USD) | `0.01` |
| `PORT` | MCP server port | `4023` |
| `MAX_TIMEOUT_SECONDS` | x402 payment timeout | `60` |
| `ONRAMP_URL` | Shown in 402 response for user funding | `https://faucet.circle.com` |

### Onboarding (`onboarding/`)

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Onboarding HTTP port | `4024` |
| `MCP_SERVER_URL` | MCP server base URL (for Plaid proxy and config) | `http://localhost:4023` |
| `CREDITNEXUS_APP_URL` | CreditNexus app link shown in UI | `http://localhost:8000` |
| `ONBOARDING_ALLOWLIST_FILE` | Path to allowlist JSON written on register | `onboarding/allowlist.json` |
| `ONBOARDING_SUBMISSIONS_FILE` | Path to submissions JSON (banking application) | `onboarding/submissions.json` |
| `ONBOARDING_HYDRO_ENV_FILE` | If set, write env snippet to this path on register (for `source` in shell) | — |
| `ONBOARDING_SILENT_STARTUP` | If set, skip startup banner in logs | — |

### Autonomous Agent (`autonomous/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVER_URL` | MCP server base URL | `http://localhost:4023` |
| `X402_FACILITATOR_URL` | x402 facilitator (Aptos) | e.g. `https://x402-navy.vercel.app/facilitator` |
| `X402_EVM_FACILITATOR_URL` | x402 facilitator for EVM; defaults to `X402_FACILITATOR_URL` | same as above |
| `LLM_BASE_URL` | OpenAI-compatible API base (e.g. Hugging Face router) | — |
| `HUGGINGFACE_API_KEY` or `HF_TOKEN` | Hugging Face token for inference | — |
| `LLM_MODEL` | Model name (e.g. `meta-llama/Llama-3.2-3B-Instruct`) | — |
| `APTOS_WALLET_PATH` | Path to Aptos wallet JSON | `~/.aptos-agent-wallet.json` |
| `EVM_WALLET_PATH` | Path to EVM wallet JSON | `~/.evm-wallet.json` |
| `EVM_PRIVATE_KEY` | If set, use this key instead of wallet file (e.g. MetaMask export); whitelist that address | — |
| `APTOS_FAUCET_NETWORK` | `devnet` = programmatic faucet in credit_aptos_wallet; `testnet` = instructions only | `testnet` |
| `BASE_SEPOLIA_RPC` | Base Sepolia RPC URL for EVM | `https://sepolia.base.org` |

### PM2 / ecosystem

Processes are defined in `demo_mcp/ecosystem.config.cjs`. Logs go to `demo_mcp/logs/`. Key env in ecosystem:

- **backend-dev**: CreditNexus backend (project root).
- **mcp-server**: `server/` cwd, `uv run python server/server.py` (or equivalent), `CREDITNEXUS_API_URL`, `ONBOARDING_ALLOWLIST_FILE` typically set.
- **onboarding**: `onboarding/` cwd, Python server, `PORT=4024`, `MCP_SERVER_URL`, optional `ONBOARDING_HYDRO_ENV_FILE`, `PYTHONIOENCODING=utf-8`.

### Development networks & funding your own wallets

Use these places to run on **development networks** and to **fund your own agent wallets**.

| What | Where | Key variables / actions |
|------|--------|--------------------------|
| **Networks used by MCP tools** (prediction, backtest, open_bank_account) | `server/.env` | `APTOS_NETWORK=aptos:2` (testnet), `BASE_SEPOLIA_NETWORK=eip155:84532`. Change only if your facilitator and payTo use another network (e.g. devnet). |
| **Agent wallet files** | `autonomous/.env` | `APTOS_WALLET_PATH`, `EVM_WALLET_PATH` (multi-wallet: `~/.aptos-agent-wallets.json`, `~/.evm-wallets.json`). Or set `EVM_PRIVATE_KEY` to use an existing key; whitelist that address at flow.html. Agent can have multiple Aptos and multiple EVM wallets (testnet/mainnet). |
| **Aptos: programmatic funding (devnet)** | `autonomous/.env` or shell | `APTOS_FAUCET_NETWORK=devnet`. Then run from `autonomous/`: `npm run credit:aptos` or `node src/credit-aptos-agent.js`. The agent can also use the `credit_aptos_wallet` tool when this is set. |
| **Aptos: testnet funding (manual)** | — | No env needed. Fund at [Aptos testnet faucet](https://aptos.dev/network/faucet); or run `node src/credit-aptos-agent.js` (or agent tool `credit_aptos_wallet`) for instructions. **If tokens are sent but don’t arrive**, see [Troubleshooting: Tokens sent but not arriving](#tokens-sent-but-not-arriving-at-agent-addresses) below. |
| **Aptos: register agent address (testnet)** | `autonomous/` | On Aptos, an account must exist on-chain before it can receive. If the faucet says “sent” but the agent balance stays zero, run `node src/register-aptos-agent.js [agent_address]` once. Use a sender with APT: set `REGISTER_SENDER_PRIVATE_KEY` in env, or run from the agent wallet if it already has APT. |
| **EVM: funding (manual)** | — | No programmatic faucet in this repo. Fund Base Sepolia at a faucet (e.g. [Alchemy Base Sepolia](https://www.alchemy.com/faucets/base-sepolia)). Use agent tool `fund_evm_wallet` for address and link. Whitelist the EVM address at http://localhost:4024/flow.html. |
| **Full wallet setup + crediting script** | From repo root | `node demo_mcp/scripts/credit-agent-wallets.mjs` (creates Aptos wallet if missing, then credits or prints instructions). With devnet: `APTOS_FAUCET_NETWORK=devnet node demo_mcp/scripts/credit-agent-wallets.mjs`. |
| **Local x402 facilitator** (optional) | `facilitator/env.example` → `facilitator/.env` | Copy `facilitator/env.example` to `facilitator/.env`. Set `APTOS_NETWORK`, `APTOS_FULLNODE_URL`, `EVM_RELAYER_PRIVATE_KEY`, `BASE_SEPOLIA_RPC`. Then point `server/.env` and `autonomous/.env` at your facilitator URL instead of the public one. |

**Summary**

- **Development networks**: MCP server uses **Aptos testnet** and **Base Sepolia** by default; configure in `server/.env` (`APTOS_*`, `BASE_SEPOLIA_*`). Agent wallet paths and optional `EVM_PRIVATE_KEY` are in `autonomous/.env`.
- **Funding your own wallets**: Set `APTOS_FAUCET_NETWORK=devnet` in `autonomous/.env` (or in the shell when running scripts) to use the **programmatic Aptos devnet faucet**. For testnet, use the [Aptos testnet faucet](https://aptos.dev/network/faucet) and the agent’s `credit_aptos_wallet` / `node src/credit-aptos-agent.js` for instructions. For EVM, use a Base Sepolia faucet and the agent’s `fund_evm_wallet` tool for the address and link. Always whitelist agent addresses at http://localhost:4024/flow.html (EVM and Aptos rows; you can add multiple of each and optionally tag testnet/mainnet).

---

## Troubleshooting

### Tokens sent but not arriving at agent addresses

**Aptos testnet**

- On Aptos, an **account must exist on-chain** before it can receive tokens. The first transfer to an address (e.g. from the [testnet faucet](https://aptos.dev/network/faucet)) usually creates the account; sometimes the faucet or network requires the account to exist first.
- **Fix**: Register the agent address once so it can receive:
  1. From `demo_mcp/autonomous/`: run `node src/register-aptos-agent.js [agent_address]` (omit address to use the default agent wallet).
  2. Use a **sender that already has APT** on the same network: set `REGISTER_SENDER_PRIVATE_KEY` in env (hex private key), or run the script when the agent wallet already has a small amount of APT.
  3. After registration, fund via the faucet or any transfer; tokens should arrive.
- **Also check**: (1) **Network** – faucet and agent must use the same network (testnet vs mainnet vs devnet). (2) **Address format** – use the full address (0x + 64 hex chars) when pasting into the faucet.

**Facilitator / validator**

- The x402 facilitator **validates** payment payloads: it checks that the transaction recipient matches the server’s **payTo** and (in CreditNexus mode) that **payTo** is in **PAY_TO_ALLOWLIST**. Addresses are normalized to 64-char hex before comparison, so short vs long form should not cause `pay_to_mismatch`.
- If payments fail with `pay_to_not_allowed`: set **PAY_TO_ALLOWLIST** (or **APTOS_PAYTO_ADDRESS** in the MCP server) and ensure the facilitator’s **FACILITATOR_MODE=creditnexus** and **PAY_TO_ALLOWLIST** include the intended payTo address.

---

## Prerequisites

### Server
- Python 3.10+
- CreditNexus backend running (localhost:8000)
- x402 facilitator: use **public** (e.g. https://x402-navy.vercel.app/facilitator or https://facilitator.x402.org) for full demo including open_bank_account; or local Aptos facilitator + X402_EVM_FACILITATOR_URL=public for EVM.

### Autonomous
- Node.js 18+
- Aptos wallet (for prediction/backtest)
- EVM wallet (for open_bank_account)
- x402 facilitator: **public** for full demo (open_bank_account uses public facilitator); optional X402_EVM_FACILITATOR_URL when using local Aptos facilitator.
- Hugging Face API token (for LLM)

---

## References

- [x402 Protocol Spec](https://github.com/coinbase/x402)
- [x402 Facilitator](https://facilitator.x402.org)
- [MCP Specification](https://modelcontextprotocol.io)
- [LangChain.js MCP](https://js.langchain.com/docs/integrations/toolkits/mcp_toolbox)

---

## License

MIT
