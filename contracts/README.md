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

See `dev/SMART_CONTRACT_DEVELOPMENT_SETUP.md` for detailed deployment instructions and `dev/SECURITIZATION_WORKFLOW_IMPLEMENTATION_PLAN.md` for integration details.
