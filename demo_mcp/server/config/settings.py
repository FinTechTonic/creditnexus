"""
Environment configuration and settings for CreditNexus MCP Server
All environment variables are loaded here centrally
"""

import os

# CreditNexus Backend
CREDITNEXUS_URL = os.getenv("CREDITNEXUS_API_URL")
SERVICE_KEY = os.getenv("CREDITNEXUS_SERVICE_KEY")

# x402 Facilitator (Official)
X402_FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL")

# CreditNexus Allowlists
AGENT_ALLOWLIST = set(filter(None, os.getenv("AGENT_ALLOWLIST", "").split(",")))
PAY_TO_ALLOWLIST = set(filter(None, os.getenv("PAY_TO_ALLOWLIST", "").split(",")))

# Aptos Configuration
APTOS_NETWORK = os.getenv("APTOS_NETWORK")
APTOS_USDC_ASSET = os.getenv("APTOS_USDC_ASSET")
APTOS_PAYTO_ADDRESS = os.getenv("APTOS_PAYTO_ADDRESS")

# EVM Configuration (Base Sepolia)
BASE_SEPOLIA_NETWORK = os.getenv("BASE_SEPOLIA_NETWORK")
BASE_SEPOLIA_USDC = os.getenv("BASE_SEPOLIA_USDC")
BASE_SEPOLIA_PAYTO = os.getenv("BASE_SEPOLIA_PAYTO")

# Payment Settings
MAX_TIMEOUT_SECONDS = int(os.getenv("MAX_TIMEOUT_SECONDS", "60"))

# Pricing (USD)
PRICE_PREDICTION_USD = float(os.getenv("MCP_PRICE_PREDICTION_USD", "0"))
PRICE_BACKTEST_USD = float(os.getenv("MCP_PRICE_BACKTEST_USD", "0"))
PRICE_BANKING_USD = float(os.getenv("MCP_PRICE_BANKING_USD", "0"))

# Server
PORT = int(os.getenv("PORT", "4023"))

# Onramp
ONRAMP_URL = os.getenv("ONRAMP_URL")
