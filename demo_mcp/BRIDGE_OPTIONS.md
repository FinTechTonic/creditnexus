# Bridge Options (Aptos ↔ EVM)

This doc outlines options for moving value between **Aptos** and **EVM** (e.g. Base Sepolia). The CreditNexus x402 demo currently uses **two separate wallets** (Aptos for prediction/backtest, EVM for open_bank_account); no bridge is implemented.

---

## Current Demo Setup

| Use case            | Network      | Wallet / asset        |
|---------------------|-------------|------------------------|
| run_prediction      | Aptos Testnet | Agent Aptos wallet, USDC (fungible asset) |
| run_backtest        | Aptos Testnet | Agent Aptos wallet, USDC |
| open_bank_account   | Base Sepolia  | Agent EVM wallet, USDC (EIP-3009) |

So the agent holds:

1. **Aptos wallet** – funds for prediction/backtest (Aptos USDC).
2. **EVM wallet** – funds for open_bank_account (Base Sepolia USDC).

No automatic transfer between the two; each side must be funded independently (e.g. Aptos faucet + Base Sepolia faucet / onramp).

---

## Why a Bridge?

- **Single onramp**: User funds once (e.g. EVM) and moves part to Aptos (or vice versa).
- **Unified balance**: One “balance” notion across chains (requires app-level aggregation + bridge).
- **Cost / UX**: Prefer one chain for onramp and bridge to the other if needed.

---

## Bridge Options (High Level)

### 1. Third-party bridges (no in-repo implementation)

- **LayerZero, Wormhole, Celer, etc.**  
  Use existing Aptos ↔ EVM bridges. User connects wallet(s), locks on source chain, receives on destination chain.  
  - Pros: Battle-tested, no custom security.  
  - Cons: Fees, delay, and trust in the bridge protocol.

- **Centralized exchange (CEX)**  
  Deposit on one chain, withdraw on the other.  
  - Pros: Simple for users who already use CEX.  
  - Cons: KYC, custody, not programmable in-demo.

### 2. Custodial / demo-only “bridge”

- **Internal ledger**: Demo backend credits “Aptos balance” when user deposits on EVM (or the reverse), and debits when they “withdraw” to the other chain. Settlement happens off-chain or via a single relayer.  
  - Pros: Fast, no public bridge dependency.  
  - Cons: Custodial, demo-only, not trustless.

### 3. Native x402 / facilitator flow (current)

- **No bridge**: Two wallets, two funding paths. Optional **wallet check** (e.g. `ENABLE_WALLET_CHECK` + `onramp_url`) tells the user to top up on the same chain when balance is low.  
  - Pros: Simple, non-custodial, matches current facilitator.  
  - Cons: User must fund both chains if they use both tools.

---

## Recommendation for This Demo

- **Keep the current two-wallet, no-bridge design** for the open-source demo.
- **Document** faucets/onramps per chain (Aptos testnet, Base Sepolia) and the optional **wallet check** + **onramp_url** so clients can guide users to top up when `insufficient_funds` is returned.
- **If** you later add a “bridge” experience, prefer:
  - **Option 1** (third-party bridge) for a non-custodial, production-like path; or  
  - **Option 2** only for a clearly labeled demo/playground with a custodial disclaimer.

---

## References

- [Aptos Docs – Interoperability](https://aptos.dev/concepts/guides/interoperability)
- [LayerZero](https://layerzero.network/), [Wormhole](https://wormhole.com/) (Aptos ↔ EVM)
- x402 facilitator: **wallet check** and **onramp_url** in `demo_mcp/facilitator` (Aptos + EVM when `ENABLE_WALLET_CHECK=true`)
