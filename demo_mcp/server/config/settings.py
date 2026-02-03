"""
Environment configuration and settings for CreditNexus MCP Server
All environment variables are loaded here centrally
"""

import json
import os
from pathlib import Path

# CreditNexus Backend (default so Plaid/link-token never gets empty URL)
CREDITNEXUS_URL = os.getenv("CREDITNEXUS_API_URL") or os.getenv("CREDITNEXUS_URL") or "http://localhost:8000"
SERVICE_KEY = os.getenv("CREDITNEXUS_SERVICE_KEY")

# Standalone mode: use vendored stubs/Plaid; default CREDITNEXUS_URL to self (MCP server port)
STANDALONE = os.getenv("STANDALONE", "").strip().lower() in ("1", "true", "yes")
STANDALONE_DB_PATH = os.getenv("STANDALONE_DB_PATH") or str(
    Path(__file__).resolve().parent.parent / "data" / "standalone.sqlite"
)
if STANDALONE and (not CREDITNEXUS_URL or CREDITNEXUS_URL == "http://localhost:8000"):
    _port = os.getenv("PORT", "4023")
    CREDITNEXUS_URL = f"http://127.0.0.1:{_port}"

# x402 Facilitator (Aptos; can be local or public)
X402_FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL")
# EVM facilitator (open_bank_account); use public when Aptos is local
X402_EVM_FACILITATOR_URL = os.getenv("X402_EVM_FACILITATOR_URL") or X402_FACILITATOR_URL

# CreditNexus Allowlists (env + optional file from onboarding API)
def _load_allowlists():
    agents = set(filter(None, os.getenv("AGENT_ALLOWLIST", "").split(",")))
    pay_to = set(filter(None, os.getenv("PAY_TO_ALLOWLIST", "").split(",")))
    allowlist_file = os.getenv("ONBOARDING_ALLOWLIST_FILE")
    if allowlist_file and os.path.isfile(allowlist_file):
        try:
            with open(allowlist_file, encoding="utf-8") as f:
                data = json.load(f)
            agents.update((a or "").strip() for a in (data.get("agents") or []) if (a or "").strip())
            pay_to.update((p or "").strip() for p in (data.get("pay_to") or []) if (p or "").strip())
        except (OSError, json.JSONDecodeError):
            pass
    return agents, pay_to


_agent_set, _pay_to_set = _load_allowlists()
AGENT_ALLOWLIST = _agent_set
PAY_TO_ALLOWLIST = _pay_to_set

# When ONBOARDING_ALLOWLIST_FILE is set, re-read from file on each call so onboarding
# registrations are picked up without MCP server restart.
def get_agent_allowlist():
    if os.getenv("ONBOARDING_ALLOWLIST_FILE") and os.path.isfile(os.getenv("ONBOARDING_ALLOWLIST_FILE", "")):
        agents, pay_to = _load_allowlists()
        return agents
    return AGENT_ALLOWLIST


def get_pay_to_allowlist():
    if os.getenv("ONBOARDING_ALLOWLIST_FILE") and os.path.isfile(os.getenv("ONBOARDING_ALLOWLIST_FILE", "")):
        agents, pay_to = _load_allowlists()
        return pay_to
    return PAY_TO_ALLOWLIST

# Aptos Configuration – defaults so 402 response always has network/asset/payTo
APTOS_NETWORK = os.getenv("APTOS_NETWORK") or "aptos:2"
APTOS_USDC_ASSET = os.getenv("APTOS_USDC_ASSET") or "0x69091fbab5f7d635ee7ac5098cf0c1efbe31d68fec0f2cd565e8d168daf52832"
APTOS_PAYTO_ADDRESS = os.getenv("APTOS_PAYTO_ADDRESS") or ""

# EVM Configuration (Base Sepolia) – defaults so 402 response always has network/asset/payTo
BASE_SEPOLIA_NETWORK = os.getenv("BASE_SEPOLIA_NETWORK") or "eip155:84532"
BASE_SEPOLIA_USDC = os.getenv("BASE_SEPOLIA_USDC") or "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
BASE_SEPOLIA_PAYTO = os.getenv("BASE_SEPOLIA_PAYTO") or ""

# Payment Settings
MAX_TIMEOUT_SECONDS = int(os.getenv("MAX_TIMEOUT_SECONDS", "60"))

# Pricing (USD) – defaults so banking 402 has non-zero amount
PRICE_PREDICTION_USD = float(os.getenv("MCP_PRICE_PREDICTION_USD", "0.06"))
PRICE_BACKTEST_USD = float(os.getenv("MCP_PRICE_BACKTEST_USD", "0.06"))
PRICE_BANKING_USD = float(os.getenv("MCP_PRICE_BANKING_USD", "3.65"))
PRICE_SCORE_USD = float(os.getenv("MCP_PRICE_SCORE_USD", "0.01"))

# Server
PORT = int(os.getenv("PORT", "4023"))

# Onramp
ONRAMP_URL = os.getenv("ONRAMP_URL")

# Re-export for config consumers (STANDALONE set above)
__all__ = [
    "CREDITNEXUS_URL", "SERVICE_KEY", "STANDALONE", "STANDALONE_DB_PATH",
    "X402_FACILITATOR_URL", "X402_EVM_FACILITATOR_URL",
    "AGENT_ALLOWLIST", "PAY_TO_ALLOWLIST", "get_agent_allowlist", "get_pay_to_allowlist",
    "APTOS_NETWORK", "APTOS_USDC_ASSET", "APTOS_PAYTO_ADDRESS",
    "BASE_SEPOLIA_NETWORK", "BASE_SEPOLIA_USDC", "BASE_SEPOLIA_PAYTO",
    "MAX_TIMEOUT_SECONDS", "PRICE_PREDICTION_USD", "PRICE_BACKTEST_USD", "PRICE_BANKING_USD", "PRICE_SCORE_USD",
    "PORT", "ONRAMP_URL",
]
