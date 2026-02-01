# Getting Started - x402 Hackathon

Step-by-step guide to start the hackathon implementation.

---

## Hour 0-2: Foundation & Research

### Step 1: Set Up Aptos Testnet Wallet

```bash
# Install Aptos CLI
curl -fsSL "https://aptos.dev/scripts/install_cli.py" | python3

# Initialize wallet
aptos init --network testnet

# Save your address and private key!
```

### Step 2: Fund with USDC

Visit https://faucet.circle.com
- Select "Aptos Testnet"
- Enter your address
- Request USDC

### Step 3: Configure Environment

```bash
cd demo/mcp_demo/verifier
uv sync
cp .env.example .env
# Edit .env with your Aptos private key
```

### Step 4: Start Building!

Now you're ready to implement the verifier following the plan in `dev/X402_HACKATHON_IMPLEMENTATION_PLAN.md`
