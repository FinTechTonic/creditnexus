# CreditNexus MCP Server - x402 Hybrid

Payment-protected tools using **official x402 facilitator** + **CreditNexus allowlist**.

## Quick Start

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure .env (add your wallet address)
# 3. Start CreditNexus backend
# 4. Run server
python server.py
```

## Architecture

- ✅ CreditNexus allowlist checking (our custom logic)
- ✅ x402 facilitator for verify/settle (official protocol)
- ✅ CreditNexus backend for services (stock prediction)

See full README in docs for details.
