# Standalone Aptos x402 Facilitator

HTTP service that implements **verify** and **settle** for the x402 protocol on the **Aptos** blockchain. Lives under **demo_mcp/** for the CreditNexus x402 demo. Aptos has no public x402 facilitator (CDP, PayAI support Base, Solana, Polygon—not Aptos). This service fills that gap for our system and can be used by any resource server.

## Overview

- **Verify**: Confirms the client’s payment payload meets the server’s payment requirements (amount, payTo, scheme, network). For Aptos: deserialize BCS payload, validate `0x1::primary_fungible_store::transfer`, simulate.
- **Settle**: Submits the validated payment to Aptos (fee payer sponsors gas), waits for confirmation, returns transaction hash.
- **No custody**: The facilitator does not hold funds; it only verifies and submits client-signed transactions (and pays gas as fee payer).

## Prerequisites

- Node.js 18+
- **APTOS_PRIVATE_KEY**: Hex private key (with `0x`) for the fee payer account. Required for `/settle`. The fee payer pays gas; the client’s transaction moves the payment amount to `payTo`.

## Setup

```bash
cp env.example .env
# Edit .env: set APTOS_PRIVATE_KEY (required for settle)
```

## Running

```bash
npm install
npm run build
npm start
# Or for development:
npm run dev
```

Default port: **4022**. Health: `GET http://localhost:4022/health`.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/verify` | Verify payment payload against payment requirements. Body: `paymentPayload`, `paymentRequirements`. Response: `isValid`, `payer`, `invalidReason?`. |
| POST | `/settle` | Settle after verify. Body: `paymentPayload`, `verification`, optional `paymentRequirements`. Response: `success`, `transaction?`, `network?`, `payer?`, `errorReason?`. |
| GET | `/supported` | Supported kinds (aptos:2, aptos:1) and signers (fee payer address). |
| GET | `/health` | Health check. Returns `{ status: "ok" }`. |

Optional: set `USE_FACILITATOR_PREFIX=true` to mount routes under `/facilitator` (e.g. `/facilitator/verify`, `/facilitator/settle`).

## Payload format (Aptos)

Client sends a payment payload with:

- `scheme`: `"exact"`
- `network`: `"aptos:2"` (testnet) or `"aptos:1"` (mainnet)
- `payload`: `{ transaction: number[] (BCS), senderAuthenticator: number[] (BCS) }`

The transaction must be a signed RawTransaction calling `0x1::primary_fungible_store::transfer` with the correct recipient (`payTo`), amount, and asset. The facilitator adds a fee payer and submits.

## CreditNexus mode (PayTo allowlist)

Set `FACILITATOR_MODE=creditnexus` and `PAY_TO_ALLOWLIST` to a comma-separated list of Aptos addresses. Only those `payTo` values are accepted for verify/settle. Omit or leave empty for community mode (any payTo).

## Integration

- **CreditNexus**: Set `X402_APTOS_FACILITATOR_URL` (or `X402_FACILITATOR_URL`) to this service base URL (e.g. `http://localhost:4022`). Use network `aptos:2` in payment requirements for testnet.
- **demo_mcp/autonomous agent**: Set `X402_FACILITATOR_URL` to this service; the agent’s x402 client will POST to `/verify` and `/settle`.

## References

- [x402 Facilitator](https://x402.gitbook.io/x402/core-concepts/facilitator)
- [Aptos Sponsoring Transactions](https://aptos.dev/build/sdks/ts-sdk/building-transactions/sponsoring-transactions)
- [aptos-labs/x402](https://github.com/aptos-labs/x402), [x402-minimal-facilitator-aptos](https://github.com/aashidham/x402-minimal-facilitator-aptos)
- Plan: `dev/STANDALONE_APTOS_X402_FACILITATOR_PLAN.md`
