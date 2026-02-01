# x402 Payment Verifier/Facilitator

Standalone payment verification and settlement service for Aptos and Ethereum/Base networks.

## Features

- ✅ Payment verification (Aptos + EVM)
- ✅ Payment settlement (on-chain submission)
- ✅ Agent allowlist management
- ✅ PayTo allowlist enforcement
- 🚧 Wallet balance checking (optional)

## Quick Start

```bash
# Install (using uv)
uv sync

# Configure
cp .env.example .env
# Edit .env with your private keys and config

# Run
uv run python main.py
# Server will start at http://localhost:4022
```

## API Endpoints

### POST /verify
Verify a payment payload against requirements.

**Request:**
```json
{
  "payment_payload": {
    "signature": "0x...",
    "transaction": "0x...",
    "network": "aptos:2"
  },
  "payment_requirements": {
    "amount": "0.06",
    "currency": "USD",
    "network": "aptos:2",
    "asset": "0x...",
    "payTo": "0x...",
    "resource": "/mcp/prediction"
  }
}
```

**Response:**
```json
{
  "isValid": true,
  "payer": "0x...",
  "invalidReason": null
}
```

### POST /settle
Submit verified transaction on-chain.

**Response:**
```json
{
  "success": true,
  "transaction": "0x...",
  "network": "aptos:2",
  "payer": "0x..."
}
```

### POST /allowlist/agent/add
Add agent to allowlist (admin only).

### GET /health
Health check.

## Networks Supported

- Aptos Testnet (`aptos:2`)
- Base Sepolia (`eip155:84532`)

## Implementation Status

- [ ] Aptos verification
- [ ] Aptos settlement
- [ ] EVM verification
- [ ] EVM settlement
- [ ] Allowlist enforcement
- [ ] Wallet balance checking
