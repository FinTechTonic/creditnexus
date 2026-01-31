# Securitization Smart Contracts

This directory contains the Solidity smart contracts for the CreditNexus securitization workflow.

## Contracts

### 1. SecuritizationNotarization.sol
- **Purpose**: On-chain notarization of securitization pools
- **Features**:
  - Multi-signer notarization support
  - Signature verification using Ethereum message signing
  - Completion tracking

### 2. SecuritizationToken.sol
- **Purpose**: ERC-721 NFT representing tranche ownership
- **Features**:
  - Minting of tranche position NFTs
  - Payment distribution to token holders
  - Integration with USDC (Base network)
  - Tranche position tracking

### 3. SecuritizationPaymentRouter.sol
- **Purpose**: Payment distribution router for securitization pools
- **Features**:
  - Payment waterfall processing (Senior → Mezzanine → Equity)
  - Integration with x402 payment protocol
  - Payment schedule management

## Dependencies

- OpenZeppelin Contracts v5.0+:
  - `@openzeppelin/contracts/token/ERC721/ERC721.sol`
  - `@openzeppelin/contracts/token/ERC721/extensions/ERC721Enumerable.sol`
  - `@openzeppelin/contracts/access/Ownable.sol`
  - `@openzeppelin/contracts/token/ERC20/IERC20.sol`

## Network

- **Target Network**: Base (L2)
- **USDC Address**: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

## Directory Structure

```
contracts/
├── contracts/              # Source files (.sol)
│   ├── SecuritizationNotarization.sol
│   ├── SecuritizationToken.sol
│   └── SecuritizationPaymentRouter.sol
├── scripts/                # Deployment scripts
│   └── deploy.js
├── artifacts/              # Compiled contracts (generated)
├── cache/                  # Build cache (generated)
├── hardhat.config.js       # Hardhat configuration
└── package.json            # Dependencies
```

## Compilation

To compile these contracts:

```bash
cd contracts
npm install
npm run compile
```

This will:
1. Install dependencies (Hardhat, OpenZeppelin Contracts)
2. Compile all contracts in `contracts/` directory
3. Generate artifacts in `artifacts/` directory

**Note:** Contracts are located in `contracts/contracts/` subdirectory to avoid Hardhat treating `node_modules` as source files.

## Deployment

### Local development (no private key required)

**Option A — One-off in-memory chain**

Runs an ephemeral Hardhat network, deploys, then exits. Uses built-in test accounts; no `.env` or `PRIVATE_KEY`:

```bash
cd contracts
npm run compile
npm run deploy:local
```

**Option B — Persistent local node**

For a long-lived chain (e.g. app or integration tests):

1. **Terminal 1 — start the node:**
   ```bash
   cd contracts
   npm run node
   ```

2. **Terminal 2 — deploy to it:**
   ```bash
   cd contracts
   npm run deploy:localhost
   ```

3. Add the printed addresses to your project-root `.env` and set:
   ```env
   X402_NETWORK_RPC_URL=http://127.0.0.1:8545
   SECURITIZATION_NOTARIZATION_CONTRACT=0x...
   SECURITIZATION_TOKEN_CONTRACT=0x...
   SECURITIZATION_PAYMENT_ROUTER_CONTRACT=0x...
   ```

### Base Sepolia (testnet) or Base (mainnet)

Requires `PRIVATE_KEY` or `BLOCKCHAIN_DEPLOYER_PRIVATE_KEY` in the project-root `.env` (see `hardhat.config.js`). Optional: `contracts/.env` or `BASE_SEPOLIA_RPC_URL` / `BASE_RPC_URL`.

```bash
cd contracts
npm run compile

# Testnet
npm run deploy:base-sepolia

# Mainnet
npm run deploy:base
```

After deployment, add the contract addresses to the project-root `.env` and set `X402_NETWORK_RPC_URL` to the matching RPC (e.g. `https://sepolia.base.org` or `https://mainnet.base.org`).

### Scripts reference

| Script | Description |
|--------|-------------|
| `npm run compile` | Compile contracts |
| `npm run test` | Run Hardhat tests |
| `npm run node` | Start persistent Hardhat node at `http://127.0.0.1:8545` |
| `npm run deploy:local` | Deploy to in-memory Hardhat network (one-off) |
| `npm run deploy:localhost` | Deploy to `http://127.0.0.1:8545` (run `npm run node` first) |
| `npm run deploy:base-sepolia` | Deploy to Base Sepolia (requires `PRIVATE_KEY`) |
| `npm run deploy:base` | Deploy to Base mainnet (requires `PRIVATE_KEY`) |
| `npm run verify` | Verify contracts on BaseScan |

### Contract verification

```bash
npx hardhat verify --network base <CONTRACT_ADDRESS> [CONSTRUCTOR_ARGS]
# Example: npx hardhat verify --network base 0x... 0x[TOKEN_ADDRESS]  # for PaymentRouter
```

## Organisations and local blockchain

For **organisation-specific** routing (e.g. each org pointing to a local or shared Hardhat chain), see the docs guide **Hardhat Local Blockchain for Organisations**: it covers starting the node, deploying, setting project-root `.env`, and optionally adding rows to `organization_blockchain_deployments` so the server routes users by organisation. In-repo: `docs/guides/hardhat-local-blockchain.mdx`.
