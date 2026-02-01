# CreditNexus x402 MCP Hackathon Deliverable

**Status:** In Development
**Deadline:** 24 hours from 2026-01-31
**Goal:** Payment-protected MCP tools with x402 verification (Aptos + Ethereum)

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Aptos CLI (optional)
- Funded testnet wallets (Aptos + Base Sepolia)

### Installation

```bash
# 1. Install all components
cd demo/mcp_demo

# Verifier (using uv)
cd verifier
uv sync
cp .env.example .env
# Edit .env with your Aptos private key

# MCP Server (using uv)
cd ../mcp_server
uv sync
cp .env.example .env
# Edit .env

# Onboarding
cd ../onboarding
npm install
cp .env.local.example .env.local
# Edit .env.local
```

### Running

```bash
# Terminal 1: Verifier
cd verifier
uv run python main.py

# Terminal 2: MCP Server
cd mcp_server
uv run python server.py

# Terminal 3: Onboarding
cd onboarding
npm run dev

# Terminal 4: CreditNexus (optional demo backend)
cd ../..
uv run python scripts/run_dev.py
```

---

## Components

### 1. x402 Verifier
**Port:** 4022
**Purpose:** Verify and settle Aptos payments

Endpoints:
- `POST /verify` - Verify payment payload
- `POST /settle` - Submit transaction on-chain
- `POST /allowlist/add` - Add agent to allowlist
- `GET /health` - Health check

### 2. MCP Server
**Port:** 4023 (or stdio)
**Purpose:** Payment-protected tools calling CreditNexus

Tools:
- `run_prediction` - Stock prediction (6¢, Aptos)
- `run_backtest` - Backtest (6¢, Aptos) [optional]

### 3. Onboarding Website
**Port:** 3000
**Purpose:** User onboarding and MCP snippet generation

Flow:
1. Connect wallet (MetaMask)
2. Fund wallet (faucet links)
3. Register agent
4. Get MCP config snippet

---

## Demo Flow

1. **Onboard**: Visit http://localhost:3000 → connect wallet → get snippet
2. **Setup MCP**: Paste snippet into `~/.cursor/mcp.json`
3. **Use Tool**: In Cursor, call `run_prediction` → receive 402 → pay → result

---

## Architecture

```
User (Cursor/Claude)
    ↓ MCP protocol
MCP Server
    ↓ 402 + payment
x402 Verifier
    ↓ verify & settle
Aptos Testnet
```

---

## Next Steps

See `../dev/X402_HACKATHON_IMPLEMENTATION_PLAN.md` for full timeline.

**Immediate:** Start with Hour 0-2 (Foundation & Research)
