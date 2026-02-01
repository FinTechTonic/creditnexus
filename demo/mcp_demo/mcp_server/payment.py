"""
Payment Wrapper - Hybrid Approach
Combines CreditNexus-specific allowlist logic with official x402 facilitator

This module:
1. Checks CreditNexus allowlists (our custom logic)
2. Forwards to official x402 facilitator for verification/settlement
3. Uses x402 protocol v2 format
"""

import httpx
import os
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv

load_dotenv()

# Official x402 facilitator
X402_FACILITATOR_URL = os.getenv("X402_FACILITATOR_URL", "https://facilitator.x402.org")

# CreditNexus-specific allowlists
AGENT_ALLOWLIST = set(filter(None, os.getenv("AGENT_ALLOWLIST", "").split(",")))
PAY_TO_ALLOWLIST = set(filter(None, os.getenv("PAY_TO_ALLOWLIST", "").split(",")))

# Aptos configuration
APTOS_NETWORK = os.getenv("APTOS_NETWORK", "aptos:2")
APTOS_USDC_ASSET = os.getenv("APTOS_USDC_ASSET")
APTOS_PAYTO_ADDRESS = os.getenv("APTOS_PAYTO_ADDRESS")
MAX_TIMEOUT_SECONDS = int(os.getenv("MAX_TIMEOUT_SECONDS", "60"))


def normalize_address(address: str) -> str:
    """Normalize Aptos address for comparison"""
    return address.lower().removeprefix("0x")


def check_allowlist(address: str, is_agent: bool = True) -> Tuple[bool, Optional[str]]:
    """
    CreditNexus-specific allowlist checking.
    This is OUR custom business logic, not part of x402.

    Args:
        address: Wallet address to check
        is_agent: True for agent requests, False for CreditNexus direct requests

    Returns:
        (is_allowed, error_reason)
    """
    if not address:
        return False, "missing_address"

    # Normalize address
    address_normalized = normalize_address(address)

    # Choose allowlist
    allowlist = AGENT_ALLOWLIST if is_agent else PAY_TO_ALLOWLIST
    allowlist_normalized = {normalize_address(addr) for addr in allowlist if addr}

    # Check
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
    description: str = "CreditNexus API Access"
) -> dict:
    """
    Build x402 v2 PaymentRequirements object for Aptos testnet.

    Args:
        amount_usd: Amount in USD (e.g., 0.06)
        resource: Resource being paid for (e.g., "/mcp/prediction/AAPL")
        description: Human-readable description

    Returns:
        x402 v2 PaymentRequirements dict
    """
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
            "sponsored": False  # User pays gas fees
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

    # Step 1: Extract payer from payload
    # In x402 v2, the payer is determined from the transaction signature
    # For now, we need to extract from the payload structure
    try:
        # The payer will be verified by the facilitator from the transaction signature
        # We'll check allowlist after getting the facilitator response
        pass
    except Exception as e:
        return {
            "isValid": False,
            "invalidReason": f"invalid_payload_structure: {str(e)}"
        }

    # Step 2: Forward to official x402 facilitator for verification
    # This handles:
    # - Signature verification
    # - Amount checking
    # - Asset verification
    # - Network validation
    # - Transaction simulation
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{X402_FACILITATOR_URL}/verify",
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

            # Step 3: Check allowlist if payment is valid
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

    # Forward to official x402 facilitator for settlement
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{X402_FACILITATOR_URL}/settle",
                json={
                    "x402Version": 2,
                    "paymentPayload": payment_payload,
                    "paymentRequirements": payment_requirements
                },
                timeout=60.0  # Settlement can take longer
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "errorReason": f"settlement_failed: HTTP {response.status_code} - {response.text}",
                    "network": APTOS_NETWORK
                }

            result = response.json()

            # Add payer from verification if not in result
            if verification.get("payer") and "payer" not in result:
                result["payer"] = verification["payer"]

            return result

    except httpx.TimeoutException:
        return {
            "success": False,
            "errorReason": "settlement_timeout: Request timed out",
            "network": APTOS_NETWORK
        }
    except httpx.RequestError as e:
        return {
            "success": False,
            "errorReason": f"settlement_connection_error: {str(e)}",
            "network": APTOS_NETWORK
        }
    except Exception as e:
        return {
            "success": False,
            "errorReason": f"settlement_error: {str(e)}",
            "network": APTOS_NETWORK
        }
