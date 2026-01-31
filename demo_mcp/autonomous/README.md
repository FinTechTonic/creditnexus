# Autonomous Agent – x402 MCP + LangChain.js

Standalone agent that uses an **x402-enabled MCP server** (predict tickers, backtest trading strategy, open bank account). Handles **x402 payment flow** (402 → pay → retry) with **Aptos** (prediction/backtest) and **Ethereum/Base** (open bank account). LLM: **Hugging Face inference** via OpenAI-compatible endpoint. Runs with PM2 from the CreditNexus repo root.

## Overview

- **Agent**: LangChain.js ReAct agent with MCP tools (run_prediction, run_backtest, open_bank_account) and local tools (balance_aptos, balance_evm, get_wallet_addresses).
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
| `X402_FACILITATOR_URL` | Facilitator base URL (verify/settle) |
| `LLM_BASE_URL` | Hugging Face OpenAI-compatible base URL (default https://router.huggingface.co/v1) |
| `HUGGINGFACE_API_KEY` or `HF_TOKEN` | Hugging Face API key |
| `LLM_MODEL` | Model ID (e.g. meta-llama/Llama-3.2-3B-Instruct) |
| `APTOS_WALLET_PATH` | Path to Aptos wallet JSON (default ~/.aptos-agent-wallet.json) |
| `EVM_WALLET_PATH` | Path to EVM wallet (default ~/.evm-wallet.json) |
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
2. **x402 facilitator** (verify/settle)  
3. **MCP server** (x402-enabled tools)  
4. **Agent** (this repo): `node src/run-agent.js` or PM2

## Commands (EVM wallet)

| Command | Description |
|---------|-------------|
| `node src/setup.js` | Generate EVM wallet |
| `node src/setup-aptos.js` | Generate Aptos wallet |
| `node src/balance.js <chain>` | EVM balance |
| `node src/run-agent.js [message]` | Run agent |

## References

- [X402 Hackathon Plan](../../dev/X402_HACKATHON_PLAN_AGENTS_MCP_VERIFIER.md)
- [Canteen App – Aptos x402](https://canteenapp-aptos-x402.notion.site/?p=2d098ea5579180f9853fed98f0a12e6f&pm=c)
- [LangChain.js MCP](https://js.langchain.com/docs/integrations/toolkits/mcp_toolbox)
- [Hugging Face Inference – OpenAI-compatible](https://huggingface.co/docs/api-inference/en/index)
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md)

## License

MIT
