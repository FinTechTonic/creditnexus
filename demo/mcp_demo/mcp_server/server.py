"""
CreditNexus MCP Server - Hybrid x402 Approach
Payment-protected tools using official x402 facilitator + CreditNexus allowlist
"""

from fastmcp import FastMCP
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP(
    "creditnexus-x402",
    description="Payment-protected tools for CreditNexus using x402 protocol v2"
)

# Import and register tools
from tools.prediction import register_tools as register_prediction_tools

# Register all tools
register_prediction_tools(mcp)


if __name__ == "__main__":
    # Run MCP server
    # FastMCP handles stdio or HTTP transport automatically
    port = int(os.getenv("PORT", 4023))

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║  CreditNexus MCP Server (x402 Hybrid)                    ║
╠═══════════════════════════════════════════════════════════╣
║  Protocol: x402 v2                                        ║
║  Network:  Aptos Testnet (aptos:2)                       ║
║  Port:     {port}                                            ║
╠═══════════════════════════════════════════════════════════╣
║  Tools Available:                                         ║
║  • run_prediction (0.06 USD)                              ║
╠═══════════════════════════════════════════════════════════╣
║  Payment Flow:                                            ║
║  1. Tool called without payment → 402 Response            ║
║  2. Client signs transaction                              ║
║  3. Tool called with payment_payload                      ║
║  4. CreditNexus checks allowlist                          ║
║  5. x402 facilitator verifies & settles                   ║
║  6. CreditNexus backend processes request                 ║
║  7. Result returned with payment receipt                  ║
╚═══════════════════════════════════════════════════════════╝
    """)

    mcp.run()
