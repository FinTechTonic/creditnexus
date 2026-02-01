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

**Benefits**:
- Agent gets autonomous payment handling
- Server provides allowlist management
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

## Prerequisites

### Server
- Python 3.10+
- CreditNexus backend running (localhost:8000)
- x402 facilitator (https://facilitator.x402.org)

### Autonomous
- Node.js 18+
- Aptos wallet (for prediction/backtest)
- EVM wallet (for open_bank_account)
- x402 facilitator
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
