# Aptos Payment Verification Research

## Quick Facts

### Aptos Transaction Structure
- **Encoding**: BCS (Binary Canonical Serialization)
- **Signature**: Ed25519
- **USDC Transfer Function**: `0x1::primary_fungible_store::transfer`
- **USDC Asset**: `0x69091fbab5f7d635ee7ac5098cf0c1efbe31d68fec0f2cd565e8d168daf52832`

### What We Need to Verify
1. **Transaction is properly signed** (Ed25519 signature)
2. **Sender address** matches expected payer
3. **Receiver address** matches payTo requirement
4. **Amount** >= required amount
5. **Asset/coin type** matches USDC
6. **Sender is allowlisted** (agent or payTo allowlist)

## Implementation Approach

### Option 1: Use Aptos Python SDK ✅ (Recommended)
```python
from aptos_sdk.account import Account
from aptos_sdk.client import RestClient
from aptos_sdk.transactions import EntryFunction, TransactionPayload
```

**Pros:**
- Official SDK, well-maintained
- Handles BCS encoding/decoding
- Built-in signature verification
- Transaction submission helpers

**Cons:**
- Might be overkill for our needs
- Need to learn SDK API

### Option 2: Direct REST API + Manual Parsing
```python
import httpx
# Manually decode BCS, verify signatures
```

**Pros:**
- Minimal dependencies
- Full control over logic

**Cons:**
- Complex BCS decoding
- Need to implement crypto primitives
- Error-prone

### Decision: Start with Option 1, fallback to Option 2 if SDK is too complex

## Simplified Approach for Hackathon

For the MVP, we'll use a **hybrid approach**:

1. **Accept transaction as JSON** (not raw BCS) - easier for testing
2. **Use Aptos REST API** to simulate transactions
3. **Verify signature using Python cryptography** library
4. **Submit using REST API** for settlement

This avoids complex BCS parsing while still being functional for the demo.

## Payment Payload Format (Simplified)

```json
{
  "signature": "0x...",  // Ed25519 signature hex
  "transaction": {
    "sender": "0x...",
    "receiver": "0x...",
    "amount": "60000",  // in atomic units (60000 = 0.06 USDC if 6 decimals)
    "asset": "0x69091fbab5f7d635ee7ac5098cf0c1efbe31d68fec0f2cd565e8d168daf52832",
    "sequence_number": 4,
    "gas_unit_price": "100",
    "max_gas_amount": "1000"
  },
  "network": "aptos:2"
}
```

## Verification Steps

```python
async def verify_aptos_payment(payload, requirements):
    # 1. Parse transaction from payload
    tx = payload["transaction"]

    # 2. Verify amounts match
    required_amount = usd_to_atomic(requirements["amount"])
    if tx["amount"] < required_amount:
        return {invalid: "insufficient_amount"}

    # 3. Verify receiver matches payTo
    if tx["receiver"] != requirements["payTo"]:
        return {invalid: "invalid_receiver"}

    # 4. Verify asset is USDC
    if tx["asset"] != APTOS_USDC_ASSET:
        return {invalid: "invalid_asset"}

    # 5. Verify signature
    if not verify_ed25519_signature(tx, payload["signature"]):
        return {invalid: "invalid_signature"}

    # 6. Check allowlist
    if tx["sender"] not in AGENT_ALLOWLIST:
        return {invalid: "not_allowlisted"}

    return {valid: True, payer: tx["sender"]}
```

## Settlement Steps

```python
async def settle_aptos_payment(payload):
    # Submit to Aptos RPC
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{APTOS_RPC_URL}/transactions",
            json=payload["transaction"]
        )
        tx_hash = response.json()["hash"]
        return {success: True, transaction: tx_hash}
```

## Testing Strategy

1. **Mock transactions** - Create fake but valid-looking transactions
2. **Test each validation step** - Amount, receiver, asset, signature
3. **Test allowlist** - Valid and invalid addresses
4. **Integration test** - Full verify → settle flow (when wallets funded)

## Resources

- Aptos Python SDK: https://github.com/aptos-labs/aptos-python-sdk
- Aptos REST API: https://fullnode.testnet.aptoslabs.com/v1/spec
- BCS in Python: https://github.com/aptos-labs/aptos-python-sdk/tree/main/aptos_sdk/bcs
- Ed25519 in Python: `from cryptography.hazmat.primitives.asymmetric import ed25519`
