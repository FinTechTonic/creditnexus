"""
Payment Wrapper - Hybrid Approach
Combines CreditNexus-specific allowlist logic with official x402 facilitator

This module:
1. Checks CreditNexus allowlists (our custom logic)
2. Forwards to official x402 facilitator for verification/settlement
3. Uses x402 protocol v2 format
"""

import httpx
import logging
from typing import Dict, Tuple, Optional

from demo_mcp.server.config import (
    X402_FACILITATOR_URL,
    X402_EVM_FACILITATOR_URL,
    get_agent_allowlist,
    get_pay_to_allowlist,
    APTOS_NETWORK,
    APTOS_USDC_ASSET,
    APTOS_PAYTO_ADDRESS,
    BASE_SEPOLIA_NETWORK,
    BASE_SEPOLIA_USDC,
    BASE_SEPOLIA_PAYTO,
    MAX_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


def normalize_address(address: str) -> str:
    """Normalize Aptos address for comparison"""
    return address.lower().removeprefix("0x")


def check_allowlist(address: str, is_agent: bool = True) -> Tuple[bool, Optional[str]]:
    """
    CreditNexus-specific allowlist checking.
    This is OUR custom business logic, not part of x402.
    When ONBOARDING_ALLOWLIST_FILE is set, get_*_allowlist() re-reads the file
    on every call so whitelisting is visible without MCP restart.

    Args:
        address: Wallet address to check
        is_agent: True for agent requests, False for CreditNexus direct requests

    Returns:
        (is_allowed, error_reason)
    """
    if not address:
        return False, "missing_address"

    address_normalized = normalize_address(address)
    # Always use getters so allowlist is refreshed from file when configured
    allowlist = get_agent_allowlist() if is_agent else get_pay_to_allowlist()
    allowlist_normalized = {normalize_address(addr) for addr in allowlist if addr}

    if address_normalized not in allowlist_normalized:
        list_type = "agent" if is_agent else "payTo"
        return False, f"not_allowlisted: {address} not in {list_type} allowlist"

    return True, None


def usd_to_atomic(usd_amount: float) -> str:
    """Convert USD to USDC atomic units (6 decimals)"""
    atomic = int(usd_amount * 1_000_000)
    return str(atomic)


def build_payment_requirements(
    amount_usd: float,
    resource: str,
    description: str = "CreditNexus API Access",
    network: str = "aptos"
) -> dict:
    """
    Build x402 v2 PaymentRequirements object for Aptos or EVM networks.

    Args:
        amount_usd: Amount in USD (e.g., 0.06 or 3.65)
        resource: Resource being paid for (e.g., "/mcp/prediction/AAPL")
        description: Human-readable description
        network: "aptos" or "evm"

    Returns:
        x402 v2 PaymentRequirements dict
    """
    if network == "evm":
        return {
            "scheme": "exact",
            "network": BASE_SEPOLIA_NETWORK,
            "amount": usd_to_atomic(amount_usd),
            "asset": BASE_SEPOLIA_USDC,
            "payTo": BASE_SEPOLIA_PAYTO,
            "maxTimeoutSeconds": MAX_TIMEOUT_SECONDS,
            "extra": {
                "resource": resource,
                "description": description,
                "sponsored": False
            }
        }
    else:
        return {
            "scheme": "exact",
            "network": APTOS_NETWORK,
            "amount": usd_to_atomic(amount_usd),
            "asset": APTOS_USDC_ASSET,
            "payTo": APTOS_PAYTO_ADDRESS,
            "maxTimeoutSeconds": MAX_TIMEOUT_SECONDS,
            "extra": {
                "resource": resource,
                "description": description,
                "sponsored": False
            }
        }


async def verify_payment(
    payment_payload: dict,
    payment_requirements: dict
) -> dict:
    """
    Verify payment with hybrid approach:
    1. Check CreditNexus allowlist (our logic)
    2. Forward to official x402 facilitator (their logic)

    Args:
        payment_payload: x402 v2 PaymentPayload from user
        payment_requirements: x402 v2 PaymentRequirements we expect

    Returns:
        x402 v2 VerifyResponse:
        {
            "isValid": bool,
            "payer": str,
            "invalidReason": str (if invalid)
        }
    """

    network = payment_requirements.get("network", "")
    facilitator_url = (X402_EVM_FACILITATOR_URL if network.startswith("eip155:") else X402_FACILITATOR_URL)
    if not facilitator_url:
        return {
            "isValid": False,
            "payer": "",
            "invalidReason": "facilitator_not_configured",
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{facilitator_url.rstrip('/')}/verify",
                json={
                    "x402Version": 2,
                    "paymentPayload": payment_payload,
                    "paymentRequirements": payment_requirements
                },
                timeout=30.0
            )

            if response.status_code != 200:
                return {
                    "isValid": False,
                    "invalidReason": f"facilitator_error: HTTP {response.status_code} - {response.text}"
                }

            result = response.json()

            # Check allowlist if payment is valid
            if result.get("isValid"):
                payer = result.get("payer")
                is_allowed, error = check_allowlist(payer, is_agent=True)
                if not is_allowed:
                    return {
                        "isValid": False,
                        "payer": payer,
                        "invalidReason": error
                    }

            return result

    except httpx.TimeoutException:
        return {
            "isValid": False,
            "invalidReason": "facilitator_timeout: Request timed out"
        }
    except httpx.RequestError as e:
        return {
            "isValid": False,
            "invalidReason": f"facilitator_connection_error: {str(e)}"
        }
    except Exception as e:
        return {
            "isValid": False,
            "invalidReason": f"verification_error: {str(e)}"
        }


async def settle_payment(
    payment_payload: dict,
    payment_requirements: dict,
    verification: dict
) -> dict:
    """
    Settle payment on-chain using official x402 facilitator.
    We just forward to x402 - no custom logic here.

    Args:
        payment_payload: x402 v2 PaymentPayload from user
        payment_requirements: x402 v2 PaymentRequirements
        verification: Result from verify_payment

    Returns:
        x402 v2 SettleResponse:
        {
            "success": bool,
            "transaction": str,  # Transaction hash
            "network": str,
            "payer": str,
            "errorReason": str (if failed)
        }
    """

    if not verification.get("isValid"):
        return {
            "success": False,
            "errorReason": "cannot_settle_invalid_payment"
        }

    network = payment_requirements.get("network", APTOS_NETWORK)
    facilitator_url = (X402_EVM_FACILITATOR_URL if (network or "").startswith("eip155:") else X402_FACILITATOR_URL)
    if not facilitator_url:
        return {
            "success": False,
            "errorReason": "facilitator_not_configured",
            "network": network
        }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{facilitator_url.rstrip('/')}/settle",
                json={
                    "x402Version": 2,
                    "paymentPayload": payment_payload,
                    "paymentRequirements": payment_requirements,
                    "verification": verification,
                },
                timeout=60.0
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "errorReason": f"settlement_failed: HTTP {response.status_code} - {response.text}",
                    "network": network
                }

            result = response.json()

            if verification.get("payer") and "payer" not in result:
                result["payer"] = verification["payer"]

            return result

    except httpx.TimeoutException:
        return {
            "success": False,
            "errorReason": "settlement_timeout: Request timed out",
            "network": network
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "errorReason": f"settlement_connection_error: {str(e)}",
            "network": network
        }
    except Exception as e:
        return {
            "success": False,
            "errorReason": f"settlement_error: {str(e)}",
            "network": network
        }
