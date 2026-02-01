"""
Aptos Payment Verification Logic

This module handles verification and settlement of Aptos USDC payments.
"""

import os
import httpx
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional
from pydantic import BaseModel


# Aptos Configuration
APTOS_RPC_URL = os.getenv("APTOS_RPC_URL", "https://fullnode.testnet.aptoslabs.com/v1")
APTOS_USDC_ASSET = os.getenv(
    "APTOS_USDC_ASSET",
    "0x69091fbab5f7d635ee7ac5098cf0c1efbe31d68fec0f2cd565e8d168daf52832"
)
APTOS_PRIVATE_KEY = os.getenv("APTOS_PRIVATE_KEY")
APTOS_ADDRESS = os.getenv("APTOS_ADDRESS")

# USDC has 6 decimals on Aptos
USDC_DECIMALS = 6


class AptosTransaction(BaseModel):
    """Simplified Aptos transaction structure for verification"""
    sender: str
    receiver: str
    amount: str  # Amount in atomic units (smallest denomination)
    asset: str
    sequence_number: Optional[int] = None
    gas_unit_price: Optional[str] = None
    max_gas_amount: Optional[str] = None
    expiration_timestamp_secs: Optional[int] = None


class AptosVerifier:
    """Handles Aptos payment verification and settlement"""

    def __init__(self, agent_allowlist: set, payto_allowlist: set):
        self.agent_allowlist = agent_allowlist
        self.payto_allowlist = payto_allowlist

    def usd_to_atomic(self, usd_amount: str) -> int:
        """
        Convert USD amount to atomic units (smallest denomination).

        USDC on Aptos has 6 decimals, so 1 USDC = 1,000,000 atomic units.
        Example: 0.06 USD = 60,000 atomic units

        Args:
            usd_amount: USD amount as string (e.g., "0.06")

        Returns:
            Atomic units as integer
        """
        usd_decimal = Decimal(usd_amount)
        atomic = int(usd_decimal * (10 ** USDC_DECIMALS))
        return atomic

    def atomic_to_usd(self, atomic_amount: str) -> Decimal:
        """
        Convert atomic units to USD.

        Args:
            atomic_amount: Atomic units as string

        Returns:
            USD amount as Decimal
        """
        atomic_int = int(atomic_amount)
        usd = Decimal(atomic_int) / Decimal(10 ** USDC_DECIMALS)
        return usd

    def parse_transaction(self, payment_payload: Dict[str, Any]) -> AptosTransaction:
        """
        Parse transaction from payment payload.

        For MVP, we accept a simplified transaction structure.
        In production, this would decode BCS-encoded raw transactions.

        Args:
            payment_payload: Payment payload from user

        Returns:
            Parsed transaction
        """
        tx_data = payment_payload.get("transaction", {})

        return AptosTransaction(
            sender=tx_data.get("sender", ""),
            receiver=tx_data.get("receiver", ""),
            amount=str(tx_data.get("amount", "0")),
            asset=tx_data.get("asset", ""),
            sequence_number=tx_data.get("sequence_number"),
            gas_unit_price=tx_data.get("gas_unit_price"),
            max_gas_amount=tx_data.get("max_gas_amount"),
            expiration_timestamp_secs=tx_data.get("expiration_timestamp_secs")
        )

    def verify_amount(
        self,
        tx: AptosTransaction,
        required_amount_usd: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify transaction amount meets requirement.

        Args:
            tx: Parsed transaction
            required_amount_usd: Required amount in USD (e.g., "0.06")

        Returns:
            (is_valid, error_reason)
        """
        required_atomic = self.usd_to_atomic(required_amount_usd)
        tx_amount = int(tx.amount)

        if tx_amount < required_atomic:
            actual_usd = self.atomic_to_usd(tx.amount)
            return False, f"insufficient_amount: got {actual_usd} USD, need {required_amount_usd} USD"

        return True, None

    def verify_receiver(
        self,
        tx: AptosTransaction,
        required_payto: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify transaction receiver matches payTo requirement.

        Args:
            tx: Parsed transaction
            required_payto: Required receiver address

        Returns:
            (is_valid, error_reason)
        """
        # Normalize addresses (remove 0x prefix if present, compare lowercase)
        tx_receiver = tx.receiver.lower().removeprefix("0x")
        required_receiver = required_payto.lower().removeprefix("0x")

        if tx_receiver != required_receiver:
            return False, f"invalid_receiver: got {tx.receiver}, expected {required_payto}"

        return True, None

    def verify_asset(self, tx: AptosTransaction) -> Tuple[bool, Optional[str]]:
        """
        Verify transaction asset is USDC.

        Args:
            tx: Parsed transaction

        Returns:
            (is_valid, error_reason)
        """
        # Normalize addresses
        tx_asset = tx.asset.lower().removeprefix("0x")
        usdc_asset = APTOS_USDC_ASSET.lower().removeprefix("0x")

        if tx_asset != usdc_asset:
            return False, f"invalid_asset: got {tx.asset}, expected USDC {APTOS_USDC_ASSET}"

        return True, None

    def verify_signature(
        self,
        tx: AptosTransaction,
        signature: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify Ed25519 signature.

        For MVP/hackathon, we'll simplify this:
        - Accept signature as provided (trust but verify later)
        - In production, this would use cryptography library to verify Ed25519

        Args:
            tx: Parsed transaction
            signature: Signature hex string

        Returns:
            (is_valid, error_reason)
        """
        # TODO: Implement proper Ed25519 signature verification
        # For now, just check signature is present and looks valid

        if not signature or len(signature) < 10:
            return False, "invalid_signature: signature missing or too short"

        # In production, would do:
        # from cryptography.hazmat.primitives.asymmetric import ed25519
        # public_key = ed25519.Ed25519PublicKey.from_public_bytes(...)
        # public_key.verify(signature_bytes, message_bytes)

        return True, None  # Accept for MVP

    def check_allowlist(
        self,
        sender: str,
        is_agent_request: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if sender is in the appropriate allowlist.

        Args:
            sender: Sender address
            is_agent_request: True for agent requests, False for CreditNexus requests

        Returns:
            (is_valid, error_reason)
        """
        # Normalize address
        sender_normalized = sender.lower().removeprefix("0x")

        # Check appropriate allowlist
        allowlist = self.agent_allowlist if is_agent_request else self.payto_allowlist

        # Normalize allowlist addresses for comparison
        allowlist_normalized = {addr.lower().removeprefix("0x") for addr in allowlist}

        if sender_normalized not in allowlist_normalized:
            list_type = "agent" if is_agent_request else "payTo"
            return False, f"not_allowlisted: {sender} not in {list_type} allowlist"

        return True, None

    async def verify(
        self,
        payment_payload: Dict[str, Any],
        payment_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify an Aptos payment against requirements.

        Args:
            payment_payload: Payment payload with transaction and signature
            payment_requirements: Required payment parameters

        Returns:
            Verification result: {isValid: bool, payer: str | None, invalidReason: str | None}
        """
        try:
            # Parse transaction
            tx = self.parse_transaction(payment_payload)

            # Extract requirements
            required_amount = payment_requirements.get("amount", "0")
            required_payto = payment_requirements.get("payTo", "")
            signature = payment_payload.get("signature", "")

            # Run all verifications
            checks = [
                ("amount", self.verify_amount(tx, required_amount)),
                ("receiver", self.verify_receiver(tx, required_payto)),
                ("asset", self.verify_asset(tx)),
                ("signature", self.verify_signature(tx, signature)),
                ("allowlist", self.check_allowlist(tx.sender, is_agent_request=True))
            ]

            # Find first failed check
            for check_name, (is_valid, error_reason) in checks:
                if not is_valid:
                    return {
                        "isValid": False,
                        "payer": tx.sender,
                        "invalidReason": error_reason or f"{check_name}_failed"
                    }

            # All checks passed
            return {
                "isValid": True,
                "payer": tx.sender,
                "invalidReason": None
            }

        except Exception as e:
            return {
                "isValid": False,
                "payer": None,
                "invalidReason": f"verification_error: {str(e)}"
            }

    async def settle(
        self,
        payment_payload: Dict[str, Any],
        verification: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Settle a verified Aptos payment by submitting to the network.

        Args:
            payment_payload: Payment payload with transaction
            verification: Verification result from verify()

        Returns:
            Settlement result: {success: bool, transaction: str | None, ...}
        """
        if not verification.get("isValid"):
            return {
                "success": False,
                "transaction": None,
                "network": "aptos:2",
                "payer": None,
                "errorReason": "Cannot settle invalid payment"
            }

        try:
            # For MVP, we'll simulate settlement
            # In production, this would:
            # 1. Sign the transaction with verifier's key
            # 2. Submit to Aptos RPC
            # 3. Wait for confirmation

            tx = self.parse_transaction(payment_payload)

            # TODO: Actual settlement when wallets are funded
            # async with httpx.AsyncClient() as client:
            #     response = await client.post(
            #         f"{APTOS_RPC_URL}/transactions",
            #         json=build_aptos_transaction(tx)
            #     )
            #     tx_hash = response.json()["hash"]

            # For now, return mock transaction hash
            mock_tx_hash = f"0x{tx.sender[:8]}...settlement_pending"

            return {
                "success": True,
                "transaction": mock_tx_hash,
                "network": "aptos:2",
                "payer": verification.get("payer"),
                "errorReason": None,
                "note": "Settlement simulated for MVP - implement with funded wallet"
            }

        except Exception as e:
            return {
                "success": False,
                "transaction": None,
                "network": "aptos:2",
                "payer": verification.get("payer"),
                "errorReason": f"settlement_error: {str(e)}"
            }


# Helper function to check wallet balance (for optional pre-flight check)
async def check_aptos_balance(address: str) -> Dict[str, Any]:
    """
    Check USDC balance for an Aptos address.

    Args:
        address: Aptos address to check

    Returns:
        Balance info: {balance_usdc: Decimal, balance_atomic: int, has_usdc: bool}
    """
    try:
        async with httpx.AsyncClient() as client:
            # Get account resources
            response = await client.get(
                f"{APTOS_RPC_URL}/accounts/{address}/resources"
            )
            resources = response.json()

            # Look for USDC balance in fungible assets
            # This is simplified - actual implementation would parse fungible_asset stores
            usdc_balance = 0

            for resource in resources:
                if "fungible_asset" in resource.get("type", "").lower():
                    # Extract balance if it's USDC
                    # TODO: Parse actual fungible asset data
                    pass

            verifier = AptosVerifier(set(), set())
            balance_usd = verifier.atomic_to_usd(str(usdc_balance))

            return {
                "balance_usdc": balance_usd,
                "balance_atomic": usdc_balance,
                "has_usdc": usdc_balance > 0
            }

    except Exception as e:
        return {
            "balance_usdc": Decimal("0"),
            "balance_atomic": 0,
            "has_usdc": False,
            "error": str(e)
        }
