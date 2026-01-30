# Brokerage Funding (Plaid + Alpaca ACH)

This guide describes how to link a bank for brokerage funding and perform deposits (fund) and withdrawals (withdraw) using Plaid Auth and the Alpaca Broker API.

## Overview

- **Link bank for funding**: User completes Plaid Link (Auth product). Backend exchanges `public_token` → `access_token`, creates a Plaid **processor token** (processor=`alpaca`), and sends it to Alpaca to create an **ACH relationship**. The relationship is stored in `brokerage_ach_relationships` so we can initiate transfers.
- **Fund**: User enters an amount; backend uses the stored ACH `relationship_id` and calls Alpaca **Create Transfer** with `direction: INCOMING`.
- **Withdraw**: User enters an amount and selects a linked bank; backend uses `relationship_id` and calls Alpaca **Create Transfer** with `direction: OUTGOING`.

## Configuration

- **Plaid**: `PLAID_ENABLED`, `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV` (sandbox/development/production). Auth product is used for funding link; processor token is created via `/processor/token/create`.
- **Alpaca Broker**: `ALPACA_BROKER_BASE_URL`, `ALPACA_BROKER_API_KEY`, `ALPACA_BROKER_API_SECRET`. Used for ACH relationships and transfers.
- **Optional**: `BROKERAGE_MAX_SINGLE_TRANSFER` to cap a single fund/withdraw amount.

See `.env.example` for all variables.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/brokerage/funding-link-token` | Plaid Link token for linking a bank (Auth only). |
| GET | `/api/brokerage/ach-relationships` | List linked banks (ACH relationships) for the current user. |
| POST | `/api/brokerage/link-bank-for-funding` | Link a bank: body `{ public_token, plaid_account_id, nickname? }`. |
| POST | `/api/brokerage/fund` | Fund brokerage: body `{ amount, relationship_id? }`. |
| POST | `/api/brokerage/withdraw` | Withdraw to bank: body `{ amount, relationship_id }`. |

All endpoints require authentication and org unlock (402 if not unlocked).

## Frontend

Link Accounts (Settings or Link accounts) shows a **Bank accounts for funding** section when the brokerage account status is ACTIVE: list linked banks, **Link bank for funding** (Plaid Link), **Deposit to brokerage**, and **Withdraw to bank** forms.

## References

- [Plaid: Add Alpaca to your app](https://plaid.com/docs/auth/partnerships/alpaca/)
- [Plaid API: Processor Token Create](https://plaid.com/docs/api/processors/#processortokencreate)
- [Alpaca: ACH Relationships](https://docs.alpaca.markets/reference/createachrelationshipforaccount)
- [Alpaca: Create Transfer](https://docs.alpaca.markets/reference/createtransferforaccount)
- Implementation plan: `dev/PLAID_ALPACA_FUNDING_WITHDRAWAL_PLAN.md`
