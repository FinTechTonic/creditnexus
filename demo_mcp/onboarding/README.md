# CreditNexus Demo Onboarding (Standalone Site)

Standalone onboarding site for the CreditNexus x402 demo. **Open-source community** with an affinity for developer tools and serving customers with innovative, agentic products. Used by people to **whitelist their agents**: connect wallet (prefilled editable agent address), provide banking application and MCP information, optionally complete KYC/Plaid via the CreditNexus app, and register for the allowlist. Copy is optimized for a futuristic innovation tone, whitepaper-style explanations of social (onboarding) implications, and an optimistic steward of a compliant, reputation-based economy. No auth (demo only).

## What it does

- **Site** – Landing at `/` and onboarding flow at `/flow.html`:
  1. **Wallet** – Connect MetaMask; agent address is prefilled but editable so folks can add any wallet they want.
  2. **Banking & KYC** – Collect information required for the banking application (full name, email, optional address). Explains that bank linking (Plaid) and KYC can be completed in the CreditNexus app or when calling the **open_bank_account** MCP tool.
  3. **Whitelist** – Register agent address(es): you can add multiple EVM and multiple Aptos addresses and optionally tag each as testnet or mainnet (pay-to is not required for the demo). Submit and get env + MCP snippets.
  4. **Open bank account** – Explains open_bank_account (pay small fee to open US bank account), KYC, and **borrower score** (100 or 100+Plaid when linked). MCP tools **get_agent_reputation_score** and **get_borrower_score** sell access to scores via x402 (200 with score or 403).
  5. **Done** – Copy snippets; reputation and borrower scores become queryable by the ecosystem.

- **API**
  - **POST /register** – At least one of **agent_address** (EVM) or **aptos_agent_address** (Aptos) required; or use **agent_addresses** / **aptos_agent_addresses** (lists of `{ address, network? }` with optional `"testnet"`/`"mainnet"`). Optional **pay_to_address**; optional **banking_application**. Persisted to `allowlist.json` (agents flat list + agent_wallets.evm/aptos with network); banking info to `submissions.json`.
  - **GET /config** – Returns `creditnexus_app_url` (for Plaid/KYC link) and `api_base`. Set `CREDITNEXUS_APP_URL` in server env so the flow can link to the CreditNexus app.
  - **GET /allowlist**, **GET /snippet**, **GET /health** – Unchanged.

## Quick start

```bash
cd demo_mcp/onboarding
pip install -r requirements.txt
python server.py
```

Runs on **port 4024** by default (`PORT=4024`). Set **MCP_SERVER_URL** (e.g. `http://localhost:4023`) to enable the optional “Connect bank with Plaid” step (Plaid KYC served from the MCP server). Open:

- **http://localhost:4024/** – Landing page  
- **http://localhost:4024/flow.html** – Onboarding flow (wallet → banking/KYC info [optional Plaid] → whitelist → open bank → done)

## Structure

```
demo_mcp/onboarding/
  server.py          # Serves static site + API
  allowlist.json     # Persisted allowlist (agents, pay_to)
  submissions.json   # Optional banking application submissions (last 100)
  requirements.txt
  static/
    index.html       # Landing (value prop, how it works, whitelist explanation)
    flow.html        # 5-step flow
    css/site.css
    js/app.js
```

## API

### POST /register

At least one EVM or Aptos address is required. You can send **agent_address** (single EVM), **aptos_agent_address** (single Aptos), and/or **agent_addresses** / **aptos_agent_addresses** (lists of `{ "address": "0x...", "network": "testnet"|"mainnet"|null }`). **pay_to_address** is optional. **banking_application** is optional (full_name, email, address) and stored for submission.

**Body (JSON):**

```json
{
  "agent_address": "0x...",
  "aptos_agent_address": "0x...",
  "agent_addresses": [{"address": "0x...", "network": "testnet"}],
  "aptos_agent_addresses": [{"address": "0x...", "network": "mainnet"}],
  "pay_to_address": "0x...",
  "banking_application": { "full_name": "Jane Doe", "email": "jane@example.com", "address": "Optional" }
}
```

**Response:** `agent_allowlist`, `pay_to_allowlist`, `agent_wallets` (evm/aptos with network), `env_snippet`, `mcp_snippet`.

### GET /config

Returns `{ "creditnexus_app_url": "...", "api_base": "" }`. Set `CREDITNEXUS_APP_URL` in server env so the flow can link to the CreditNexus app for Plaid/KYC.

### GET /snippet, GET /allowlist, GET /health

Same as before.

## MCP server integration

- Paste **env_snippet** into `demo_mcp/server/.env` as `AGENT_ALLOWLIST` and `PAY_TO_ALLOWLIST`.
- Or set `ONBOARDING_ALLOWLIST_FILE` to the path of `allowlist.json`; the server loads and merges with env.

## Config

| Env | Default | Description |
|-----|---------|-------------|
| `PORT` | 4024 | Onboarding site port |
| `ONBOARDING_ALLOWLIST_FILE` | `./allowlist.json` | Path to allowlist JSON file |
| `ONBOARDING_SUBMISSIONS_FILE` | `./submissions.json` | Path to submissions file (banking_application) |
| `MCP_SERVER_URL` | http://localhost:4023 | Base URL used in `mcp_snippet` |
| `CREDITNEXUS_APP_URL` | (empty) | URL of CreditNexus app for Plaid/KYC link (e.g. http://localhost:5173) |

**Client (CreditNexus app):** Set `VITE_ONBOARDING_SITE_URL` (e.g. `http://localhost:4024`) so the login page “x402 Demo: Get onboarded” link points to this standalone site.

## Allowlist file format

`allowlist.json`:

```json
{
  "agents": ["0x...", "0x..."],
  "agent_wallets": { "evm": [{"address": "0x...", "network": "testnet"}], "aptos": [{"address": "0x...", "network": null}] },
  "pay_to": ["0x..."]
}
```

Addresses are normalized (lowercase, optional `0x`). Duplicates are merged.
