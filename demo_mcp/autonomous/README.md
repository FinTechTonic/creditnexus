# Autonomous Agent – x402 MCP + LangChain.js

Standalone agent that uses an **x402-enabled MCP server** (predict tickers, backtest trading strategy, open bank account). Handles **x402 payment flow** (402 → pay → retry) with **Aptos** (prediction/backtest) and **Ethereum/Base** (open bank account). LLM: **Hugging Face inference** via OpenAI-compatible endpoint. Runs with PM2 from the CreditNexus repo root.

## Overview

- **Agent**: LangChain.js ReAct agent with MCP tools (run_prediction, run_backtest, open_bank_account) and local tools (balance_aptos, balance_evm, get_wallet_addresses, create_aptos_wallet, create_evm_wallet, credit_aptos_wallet, fund_evm_wallet). **get_wallet_addresses** returns lists of `{ address, network? }` for Aptos and EVM; the agent can have multiple Aptos and multiple EVM wallets (optionally testnet or mainnet).
- **x402**: On 402 Payment Required, the agent pays via the x402 facilitator (verify → settle) and retries with PAYMENT-SIGNATURE.
- **Chains**: Aptos testnet for prediction/backtest (~6¢); Base Sepolia (or Base) for open_bank_account (~$3.65).

## LLM (Hugging Face)

The agent uses **Hugging Face inference** via an **OpenAI-compatible** API (no OpenAI key required):

- **Router (recommended)**: `LLM_BASE_URL=https://router.huggingface.co/v1`, `HUGGINGFACE_API_KEY` or `HF_TOKEN`, `LLM_MODEL` (e.g. `meta-llama/Llama-3.2-3B-Instruct`).
- **Dedicated endpoint**: Use your Inference Endpoint URL as `LLM_BASE_URL` and its API key.

## Prerequisites

- Node.js 18+
- **Wallets**: Aptos (`node src/setup-aptos.js`) and/or EVM (`node src/setup.js`) for payments.
- **MCP server URL**: x402-enabled MCP server (built separately).
- **Facilitator URL**: x402 verifier (e.g. https://x402-navy.vercel.app/facilitator).
- **Hugging Face token**: For LLM (HUGGINGFACE_API_KEY or HF_TOKEN).

## Install

```bash
cd demo_mcp/autonomous
npm install
```

## Config

Copy `.env.example` to `.env` and set:

| Variable | Description |
|----------|-------------|
| `MCP_SERVER_URL` | x402 MCP server base URL (e.g. http://localhost:4023) |
| `X402_FACILITATOR_URL` | Facilitator base URL for Aptos (verify/settle). For full demo including open_bank_account use public (e.g. https://x402-navy.vercel.app/facilitator). |
| `X402_EVM_FACILITATOR_URL` | Optional. Facilitator for EVM (open_bank_account). Defaults to X402_FACILITATOR_URL. Set to public when using local Aptos facilitator. |
| `LLM_BASE_URL` | Hugging Face OpenAI-compatible base URL (default https://router.huggingface.co/v1) |
| `HUGGINGFACE_API_KEY` or `HF_TOKEN` | Hugging Face API key |
| `LLM_MODEL` | Model ID (e.g. meta-llama/Llama-3.2-3B-Instruct) |
| `APTOS_WALLET_PATH` | Path to Aptos wallet JSON. Multi-wallet: ~/.aptos-agent-wallets.json (wallets array + defaultIndex). |
| `EVM_WALLET_PATH` | Path to EVM wallet. Multi-wallet: ~/.evm-wallets.json (wallets array + defaultIndex). Or set EVM_PRIVATE_KEY for single wallet. |
| `BASE_SEPOLIA_RPC` | Optional; Base Sepolia RPC for open_bank_account |

## Run

```bash
# With a message
node src/run-agent.js "Run a 30-day prediction for AAPL"

# Demo prompt (balance + prediction)
node src/run-agent.js

# Or use npm
npm run agent
```

**PM2** (from CreditNexus repo root):

```bash
pm2 start ecosystem.config.cjs --only agent-autonomous
```

## MCP Tools

| Tool | Description | Cost |
|------|-------------|------|
| `run_prediction` | Stock prediction (symbol, horizon, strategy) | ~6¢ (Aptos) |
| `run_backtest` | Backtest trading strategy | ~6¢ (Aptos) |
| `open_bank_account` | Start Plaid link / open bank account | ~$3.65 (Ethereum/Base) |

## x402 Flow

1. Agent calls MCP tool → server returns **402** with payment requirements.
2. Agent builds payment (Aptos or EVM), calls facilitator **/verify** then **/settle**.
3. Agent retries the same request with **PAYMENT-SIGNATURE** header.
4. Server returns result + request_payload, response_payload, payment_receipt.

## Deployment Order

1. **CreditNexus** (optional demo backend)  
2. **x402 facilitator**: For full demo (including open_bank_account) use **public** facilitator (X402_FACILITATOR_URL). For Aptos-only local demo use local facilitator and set X402_EVM_FACILITATOR_URL to public.  
3. **MCP server** (x402-enabled tools)  
4. **Agent** (this repo): `node src/run-agent.js` or PM2

## Commands (wallets)

| Command | Description |
|---------|-------------|
| `node src/setup.js` | Generate EVM wallet (single; for multi use agent tool create_evm_wallet with network) |
| `node src/setup-aptos.js` | Generate Aptos wallet (single; for multi use create_aptos_wallet with network) |
| `node src/show-agent-addresses.js` | Print all Aptos and EVM addresses (with optional network) for whitelisting at flow.html |
| `npm run credit:aptos` | Credit Aptos agent (devnet: programmatic; testnet: print mint page instructions) |
| `node src/balance.js <chain>` | EVM balance |
| `node src/run-agent.js [message]` | Run agent |

**Crediting Aptos agent**: Testnet has no programmatic faucet—use [Aptos testnet faucet](https://aptos.dev/network/faucet). For automated crediting use devnet: `APTOS_FAUCET_NETWORK=devnet npm run credit:aptos`. See [Canteen – Aptos x402](https://canteenapp-aptos-x402.notion.site/) for reference hydration flows.

## References

- [Implementation Status & Integration](../../dev/demo_mcp/IMPLEMENTATION_STATUS_AND_INTEGRATION.md) — facilitator usage (open_bank_account → public), integrations, launch.
- [X402 Hackathon Plan](../../dev/X402_HACKATHON_PLAN_AGENTS_MCP_VERIFIER.md)
- [Canteen App – Aptos x402](https://canteenapp-aptos-x402.notion.site/) — reference implementations for hydrating and crediting the agent wallet
- [LangChain.js MCP](https://js.langchain.com/docs/integrations/toolkits/mcp_toolbox)
- [Hugging Face Inference – OpenAI-compatible](https://huggingface.co/docs/api-inference/en/index)
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## License

MIT
