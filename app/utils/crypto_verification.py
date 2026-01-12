"""Cryptographic signature verification utilities for Ethereum wallets."""

import logging
from typing import Optional
from eth_account import Account
from eth_account.messages import encode_defunct

logger = logging.getLogger(__name__)


def verify_ethereum_signature(message: str, signature: str, wallet_address: str) -> bool:
    """Verify Ethereum signature using eth_account.

    Args:
        message: The original message that was signed
        signature: The signature string (hex)
        wallet_address: The expected wallet address

    Returns:
        True if signature is valid for the wallet address, False otherwise
    """
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)

        is_valid = recovered_address.lower() == wallet_address.lower()

        if is_valid:
            logger.debug(f"Signature verified for wallet: {wallet_address}")
        else:
            logger.warning(
                f"Signature verification failed: expected {wallet_address}, got {recovered_address}"
            )

        return is_valid

    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def generate_signing_message(
    nonce: str, timestamp: str, deal_id: Optional[int] = None, verification_id: Optional[str] = None
) -> str:
    """Generate a structured message for signing.

    Args:
        nonce: Unique nonce for this signing request
        timestamp: ISO 8601 timestamp
        deal_id: Optional deal ID
        verification_id: Optional verification ID

    Returns:
        Formatted message to sign
    """
    message = f"""CreditNexus Notarization

Nonce: {nonce}
Timestamp: {timestamp}"""

    if deal_id:
        message += f"\nDeal ID: {deal_id}"

    if verification_id:
        message += f"\nVerification ID: {verification_id}"

    message += "\n\nBy signing this message, you confirm your agreement to the terms and conditions of this notarization."

    return message


def validate_wallet_address(wallet_address: str) -> bool:
    """Validate Ethereum wallet address format.

    Args:
        wallet_address: Wallet address to validate

    Returns:
        True if valid format, False otherwise
    """
    try:
        from eth_utils import is_checksum_address

        return is_checksum_address(wallet_address)
    except Exception:
        return False


def normalize_wallet_address(wallet_address: str) -> str:
    """Normalize wallet address to checksum format.

    Args:
        wallet_address: Wallet address to normalize

    Returns:
        Checksum-normalized address
    """
    try:
        from eth_utils import to_checksum_address

        return to_checksum_address(wallet_address)
    except Exception:
        return wallet_address.lower()


def recover_signer_address(message: str, signature: str) -> Optional[str]:
    """Recover the signer's address from a signature.

    Args:
        message: The original message
        signature: The signature

    Returns:
        Recovered wallet address or None if recovery fails
    """
    try:
        message_hash = encode_defunct(text=message)
        recovered_address = Account.recover_message(message_hash, signature=signature)
        return recovered_address
    except Exception as e:
        logger.error(f"Failed to recover signer address: {e}")
        return None


def generate_nonce() -> str:
    """Generate a unique nonce for signing requests.

    Returns:
        Unique nonce string
    """
    import secrets
    import time

    timestamp = str(int(time.time()))
    random_part = secrets.token_hex(8)
    return f"{timestamp}-{random_part}"


def compute_payload_hash(payload: dict) -> str:
    """Compute hash of CDM payload for notarization.

    Args:
        payload: CDM payload dictionary

    Returns:
        Hex-encoded SHA256 hash
    """
    import json
    import hashlib

    payload_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    hash_obj = hashlib.sha256(payload_str.encode("utf-8"))
    return f"0x{hash_obj.hexdigest()}"
