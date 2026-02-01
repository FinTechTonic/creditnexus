# CreditNexus MCP Server - x402 Hybrid

Payment-protected tools using **official x402 facilitator** + **CreditNexus allowlist**.

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure .env
cp .env.example .env
# Edit .env with your wallet addresses

# 3. Start CreditNexus backend (in another terminal)
cd /path/to/creditnexus
uvicorn app.main:app --port 8000

# 4. Run MCP server
python server.py
```

Server runs on `localhost:4023`

---

## Tools Available

| Tool | Description | Cost | Network |
|------|-------------|------|---------|
| **run_prediction** | Stock prediction for a ticker | $0.06 | Aptos Testnet |
| **run_backtest** | Trading strategy backtest | $0.06 | Aptos Testnet |
| **open_bank_account** | Plaid Link for bank account | $3.65 | Base Sepolia |
| **get_agent_reputation_score** | Query agent reputation (100 for allowlisted/KYC); 200 with score or 403 | $0.01 | Aptos Testnet |
| **get_borrower_score** | Query borrower score: "100" or "100+{plaid_score}" when bank linked; 200 or 403 | $0.01 | Aptos Testnet |

---

## Architecture

**Hybrid Approach**:
1. ✅ CreditNexus allowlist checking (our custom logic)
2. ✅ Official x402 facilitator for verify/settle
3. ✅ CreditNexus backend for services

**Flow**:
```
Client → 402 Response → Sign Tx → Verify (facilitator) → Settle → Backend → Result
```

**Networks Supported**:
- Aptos Testnet (`aptos:2`) for prediction/backtest
- Base Sepolia (`eip155:84532`) for banking

---

## Payment Flow

### Example: run_prediction

1. **Client calls tool without payment**:
   ```json
   {
     "symbol": "AAPL",
     "horizon": 30
   }
   ```

2. **Server returns 402**:
   ```json
   {
     "status": 402,
     "paymentRequirements": {
       "network": "aptos:2",
       "amount": "60000",
       "asset": "0x69091...",
       "payTo": "0x74ea3..."
     }
   }
   ```

3. **Client signs Aptos transaction** (6¢ USDC transfer)

4. **Client retries with payment_payload**:
   ```json
   {
     "symbol": "AAPL",
     "horizon": 30,
     "payment_payload": {
       "transaction": [...],
       "senderAuthenticator": [...]
     }
   }
   ```

5. **Server verifies allowlist → x402 facilitator → settles → calls backend**

6. **Server returns result + receipt**:
   ```json
   {
     "status": 200,
     "result": { "predictions": [...] },
     "paymentReceipt": {
       "transaction": "0xabc...",
       "network": "aptos:2",
       "payer": "0x74ea3...",
       "settled": true
     }
   }
   ```

---

## Configuration

### .env Variables

```bash
# x402 Facilitator
X402_FACILITATOR_URL=https://facilitator.x402.org

# Allowlists
AGENT_ALLOWLIST=0x...  # Comma-separated
PAY_TO_ALLOWLIST=0x...

# Aptos (for prediction/backtest)
APTOS_NETWORK=aptos:2
APTOS_USDC_ASSET=0x69091fbab5f7d635ee7ac5098cf0c1efbe31d68fec0f2cd565e8d168daf52832
APTOS_PAYTO_ADDRESS=0x...

# Base Sepolia (for banking)
BASE_SEPOLIA_NETWORK=eip155:84532
BASE_SEPOLIA_USDC=0x036CbD53842c5426634e7929541eC2318f3dCF7e
BASE_SEPOLIA_PAYTO=0x...

# Backend
CREDITNEXUS_API_URL=http://localhost:8000
CREDITNEXUS_SERVICE_KEY=

# Pricing
MCP_PRICE_PREDICTION_USD=0.06
MCP_PRICE_BACKTEST_USD=0.06
MCP_PRICE_BANKING_USD=3.65
```

---

## Tool Details

### run_prediction

```python
async def run_prediction(
    symbol: str,              # Stock symbol (e.g., "AAPL")
    horizon: int = 30,        # Days to predict
    payment_payload: dict = None
) -> dict
```

**Backend**: `GET /api/stock-prediction/daily`

**Example**:
```python
result = await run_prediction("AAPL", horizon=30, payment_payload=signed_tx)
```

---

### run_backtest

```python
async def run_backtest(
    symbol: str,              # Stock symbol
    start_date: str = None,   # YYYY-MM-DD
    end_date: str = None,     # YYYY-MM-DD
    strategy: str = "chronos", # Strategy name
    payment_payload: dict = None
) -> dict
```

**Backend**: `POST /api/stock-prediction/backtest`

**Example**:
```python
result = await run_backtest("TSLA", strategy="chronos", payment_payload=signed_tx)
```

---

### open_bank_account

```python
async def open_bank_account(
    user_id: str = None,      # Optional user ID
    payment_payload: dict = None
) -> dict
```

**Backend**: `POST /api/banking/plaid/link/token/create`

**Returns**: Plaid link_token for bank account connection

**Example**:
```python
result = await open_bank_account(payment_payload=signed_evm_tx)
# result.link_token → Use with Plaid Link
```

---

## Integration with Autonomous Agent

The autonomous agent in `demo_mcp/autonomous/` is designed to call this server:

```env
# In autonomous/.env
MCP_SERVER_URL=http://localhost:4023
```

The agent will:
1. Call tools
2. Receive 402 responses
3. Build payments (Aptos or EVM)
4. Verify and settle via x402 facilitator
5. Retry with payment_payload
6. Use results

---

## Testing

```bash
# Start server
python server.py

# Server will show:
# ╔═══════════════════════════════════════════════════════════╗
# ║  CreditNexus MCP Server (x402 Hybrid)                    ║
# ║  Tools: run_prediction, run_backtest, open_bank_account  ║
# ╚═══════════════════════════════════════════════════════════╝
```

---

## References

- [x402 Protocol](https://github.com/coinbase/x402)
- [x402 Facilitator](https://facilitator.x402.org)
- [MCP Specification](https://modelcontextprotocol.io)
- [CreditNexus Documentation](../../README.md)

---

## License

MIT
