"""Encrypted link payload generator for self-contained verification links."""

import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from cryptography.fernet import Fernet

from app.core.config import settings

logger = logging.getLogger(__name__)


class LinkPayloadGenerator:
    """Generate encrypted self-contained verification link payloads."""

    def __init__(self):
        """Initialize payload generator with encryption key."""
        self._get_or_generate_key()

    def _get_or_generate_key(self):
        """Get encryption key from settings or generate one."""
        # Try to get from settings
        key_str = getattr(settings, "LINK_ENCRYPTION_KEY", None)

        if key_str:
            try:
                return Fernet(key_str.encode())
            except Exception as e:
                logger.warning(f"Invalid LINK_ENCRYPTION_KEY, generating new one: {e}")

        # Generate new key
        key = Fernet.generate_key()
        logger.warning("Using auto-generated encryption key (not persistent across restarts)")
        return key

    def generate_verification_link_payload(
        self,
        verification_id: str,
        deal_id: int,
        deal_data: Dict[str, Any],
        cdm_payload: Dict[str, Any],
        verifier_info: Optional[Dict[str, Any]] = None,
        file_references: Optional[List[Dict[str, Any]]] = None,
        expires_in_hours: int = 72,
    ) -> str:
        """Generate encrypted verification link payload.

        Args:
            verification_id: Verification UUID
            deal_id: Deal database ID
            deal_data: Deal information
            cdm_payload: Full CDM event payload
            verifier_info: Optional verifier metadata
            file_references: List of document metadata to include
            expires_in_hours: Link expiration time

        Returns:
            Base64url-encoded encrypted payload
        """
        expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()

        payload = {
            "verification_id": verification_id,
            "deal_id": deal_id,
            "deal_data": deal_data,
            "cdm_payload": cdm_payload,
            "verifier_info": verifier_info or {},
            "file_references": file_references or [],
            "expires_at": expires_at,
            "created_at": datetime.utcnow().isoformat(),
            "version": "2.0",
        }

        # Serialize to JSON
        json_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        # Encrypt
        encrypted = self.cipher.encrypt(json_payload.encode("utf-8"))

        # Base64url encode (URL-safe)
        encoded = base64.urlsafe_b64encode(encrypted).decode("utf-8").rstrip("=")

        logger.info(f"Generated encrypted link payload for verification {verification_id}")
        return encoded

    def parse_verification_link_payload(self, payload: str) -> Optional[Dict[str, Any]]:
        """Parse and decrypt verification link payload.

        Args:
            payload: Base64url-encoded encrypted payload

        Returns:
            Parsed payload dictionary or None if invalid/expired
        """
        try:
            # Add padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += "=" * padding

            # Base64url decode
            encrypted = base64.urlsafe_b64decode(payload)

            # Decrypt
            decrypted = self.cipher.decrypt(encrypted)

            # Deserialize JSON
            data = json.loads(decrypted.decode("utf-8"))

            # Check expiration
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() > expires_at:
                logger.warning(f"Link payload expired: {data.get('verification_id')}")
                return None

            return data

        except Exception as e:
            logger.error(f"Failed to parse link payload: {e}")
            return None
