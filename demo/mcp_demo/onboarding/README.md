# CreditNexus Onboarding Website

Multi-user onboarding flow for MCP setup, wallet linking, and agent registration.

## Features

- ✅ Wallet connection (MetaMask)
- ✅ Funding links (Circle faucet)
- ✅ MCP config snippet generation
- ✅ Agent registration (allowlist)
- 🚧 Plaid bank linking (optional)

## Quick Start

```bash
# Install
npm install

# Configure
cp .env.local.example .env.local
# Edit .env.local

# Run
npm run dev
# Visit http://localhost:3000
```

## User Flow

1. **Connect Wallet** - MetaMask connection
2. **Fund Wallet** - Links to Circle faucet for USDC
3. **Register Agent** - Add wallet to verifier allowlist
4. **Get Snippet** - Personalized MCP config for Cursor/Claude

## Implementation Status

- [x] Landing page with wallet connect
- [x] Snippet generation page
- [ ] MetaMask integration (wagmi)
- [ ] Agent registration API call
- [ ] Plaid Link integration (optional)
- [ ] Wallet balance checking
- [ ] Multi-wallet support (Petra for Aptos)

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- TailwindCSS
- wagmi/viem (Ethereum wallet)
- Aptos wallet adapter (TODO)
