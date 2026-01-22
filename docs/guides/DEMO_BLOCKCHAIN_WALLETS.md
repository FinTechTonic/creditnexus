# Demo Blockchain Wallets & Subscriptions Configuration

This document describes how to configure blockchain wallet addresses and subscriptions for demo users.

## Overview

When seeding demo users, you can now:
1. Assign blockchain wallet addresses from your local Hardhat node to demo users
2. Automatically create subscriptions for demo users based on their roles
3. Automatically create credit balances for demo users

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Comma-separated list of wallet accounts from Hardhat node
# Format: "address:private_key" pairs (private key is required for signing transactions)
# These will be assigned to demo users in order
# Example:
DEMO_BLOCKCHAIN_ACCOUNTS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266:0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80,0x70997970C51812dc3A010C7d01b50e0d17dc79C8:0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d,0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC:0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a

# RPC URL for blockchain node (default: local Hardhat node)
DEMO_BLOCKCHAIN_RPC_URL=http://127.0.0.1:8545
```

### Getting Wallet Addresses and Private Keys from Hardhat

When you run `npm run node` in the `contracts` directory, Hardhat will display a list of accounts with their addresses and private keys. Copy both the address and private key for each account you want to use.

**IMPORTANT**: Private keys are required for demo users to sign blockchain transactions. Without private keys, wallets can only receive/view transactions but cannot sign.

Example output from Hardhat:
```
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
Private Key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

Account #1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000 ETH)
Private Key: 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d

Account #2: 0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC (10000 ETH)
Private Key: 0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a
...
```

Format each account as `address:private_key` in the environment variable.

## Subscription Tiers

Demo users are automatically assigned subscription tiers based on their roles:

- **PREMIUM** (Yearly subscription, 10,000 credits):
  - ADMIN
  - BANKER
  - LAW_OFFICER

- **PRO** (Monthly subscription, 5,000 credits):
  - ANALYST
  - ACCOUNTANT
  - REVIEWER

- **FREE** (Pay-as-you-go, 1,000 credits):
  - APPLICANT
  - Other roles

## Usage

1. Start your Hardhat node:
   ```bash
   cd contracts
   npm run node
   ```

2. Copy wallet addresses and private keys from the Hardhat output and add them to `.env`:
   ```bash
   # Format: address:private_key pairs, comma-separated
   DEMO_BLOCKCHAIN_ACCOUNTS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266:0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80,0x70997970C51812dc3A010C7d01b50e0d17dc79C8:0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d,...
   ```

3. Seed demo users via API or script:
   ```bash
   # The wallet assignment and subscription/credit creation happens automatically
   # when you seed users via the demo data API
   ```

## Implementation Details

### Wallet Assignment

- Wallets are assigned to demo users in the order they appear in `DEMO_BLOCKCHAIN_ACCOUNTS`
- Format: `address:private_key` pairs (private key is required for signing transactions)
- Only users without existing wallet addresses will be assigned new wallets
- Wallet addresses are encrypted in the database (using `EncryptedString`)
- Private keys are stored securely in `profile_data` (using `EncryptedJSON`)
- If only address is provided (no private key), wallet can receive/view but cannot sign transactions

### Subscription Creation

- Subscriptions are created with `is_active=True`
- Premium and Pro subscriptions have `auto_renew=True`
- Free subscriptions have `auto_renew=False`
- Subscriptions are linked to users via `user_id`

### Credit Balance Creation

- Credit balances are created with initial credits based on subscription tier
- `lifetime_earned` is set to the initial credit amount
- `lifetime_spent` starts at 0
- Credits are stored in the `universal` credit type

## Notes

- If `DEMO_BLOCKCHAIN_ACCOUNTS` is not set, wallet assignment is skipped (no error)
- If there are more users than wallet addresses, only the first N users get wallets
- Existing wallets are not overwritten
- Subscriptions and credits are created/updated on every user seed (idempotent)
