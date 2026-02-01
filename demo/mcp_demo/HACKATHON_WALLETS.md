# Hackathon Test Wallets

Pre-funded wallets provided by hackathon hosts for testing.

## Wallet 3 (PRIMARY - Used in configs)

```
Address: 0x924c2e983753bb29b45ae9b4036d48861f204da096b36af710c95d1742b05ad4
Public Key: 0xCDBC869A311F921BE1F32A242C8FC911A2E035E751E9233B99B94A7E6D8D9E20
Private Key: 0xCCCE62852DA00DA8318C97084F4CB7D6E063C214039A93528EBC3BF7E8B4248B
```

**Funded with:**
- ~20 USDC on Aptos Testnet
- ~1 APT on Aptos Testnet

**Used for:**
- Verifier signing/settlement
- Payment receiver (payTo)
- Agent allowlist (testing)

## Wallet 4 (BACKUP)

```
Address: 0xf1697d22257fd39653319eb3a2ee23fca2ca99b26f7fc79090249fbfbc401e03
Public Key: 0x14ECDCD65EB90D09CAED23B6E677DEF93F0077F527B8E6AF6C1710D380473D86
Private Key: 0x208325A1C287DEA4A671E4615F61E2ABE3D83274547E7DA1996729ECBC7305BE
```

**Funded with:**
- ~20 USDC on Aptos Testnet
- ~1 APT on Aptos Testnet

**Used for:**
- Alternative payer for testing
- Multi-wallet scenarios

## Quick Check Balance

```bash
# Check Wallet 3 balance
curl https://fullnode.testnet.aptoslabs.com/v1/accounts/0x924c2e983753bb29b45ae9b4036d48861f204da096b36af710c95d1742b05ad4/resources

# Or use Aptos Explorer
# https://explorer.aptoslabs.com/account/0x924c2e983753bb29b45ae9b4036d48861f204da096b36af710c95d1742b05ad4?network=testnet
```

## Refill if Needed

If wallets run low:
- **USDC**: https://faucet.circle.com (select Aptos Testnet)
- **APT**: https://aptos.dev/network/faucet

## Security Note

⚠️ These are **testnet wallets** for the hackathon only. Do NOT use these keys on mainnet or store real funds.

## Configuration

These wallets are already configured in:
- `demo/mcp_demo/verifier/.env` (Wallet 3 as verifier)
- `demo/mcp_demo/mcp_server/.env` (Wallet 3 as payTo receiver)
- Both wallets in `AGENT_ALLOWLIST` for testing
