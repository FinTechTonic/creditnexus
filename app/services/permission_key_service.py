"""Permission key service for managing permission keys."""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import uuid
import hashlib
import json
import base64
import logging

from app.db.models import PermissionKey, PermissionKeyType
from app.utils.link_payload import LinkPayloadGenerator

logger = logging.getLogger(__name__)


class PermissionKeyService:
    """Service for managing permission keys."""

    def __init__(self, db: Session):
        """Initialize permission key service."""
        self.db = db
        self.link_generator = LinkPayloadGenerator()

    def create_wallet_key(
        self,
        wallet_address: str,
        permissions: List[str],
        deal_id: Optional[int] = None,
        document_id: Optional[int] = None,
        workflow_id: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
        download_ttl_hours: Optional[int] = None,
        created_by: int = 1,
    ) -> PermissionKey:
        """Create wallet-based permission key.

        Args:
            wallet_address: Ethereum wallet address
            permissions: List of permissions (view, download, sign, edit)
            deal_id: Optional deal ID
            document_id: Optional document ID
            workflow_id: Optional workflow ID
            expires_in_hours: Optional expiration
            download_ttl_hours: Optional download TTL
            created_by: Creator user ID

        Returns:
            Created PermissionKey
        """
        key_id = str(uuid.uuid4())

        # Generate key data
        key_data = {
            "wallet_address": wallet_address.lower(),
            "permissions": permissions,
            "deal_id": deal_id,
            "document_id": document_id,
            "workflow_id": workflow_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Encrypt key data
        encrypted_key = self._encrypt_key_data(key_data)

        # Compute key hash for lookup
        key_hash = hashlib.sha256(encrypted_key.encode("utf-8")).hexdigest()

        # Calculate expiration
        expires_at = None
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        download_ttl = None
        if download_ttl_hours:
            download_ttl = datetime.utcnow() + timedelta(hours=download_ttl_hours)

        permission_key = PermissionKey(
            key_id=key_id,
            key_type=PermissionKeyType.WALLET.value,
            encrypted_key=encrypted_key,  # Will be encrypted by EncryptedJSON
            key_hash=key_hash,
            permissions=permissions,
            deal_id=deal_id,
            document_id=document_id,
            workflow_id=workflow_id,
            wallet_address=wallet_address.lower(),
            expires_at=expires_at,
            download_ttl=download_ttl,
            created_by=created_by,
        )

        self.db.add(permission_key)
        self.db.commit()
        self.db.refresh(permission_key)

        logger.info(f"Created wallet permission key {key_id} for wallet {wallet_address[:10]}...")
        return permission_key

    def create_application_key(
        self,
        application_key_id: str,
        permissions: List[str],
        organization_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        expires_in_hours: Optional[int] = None,
        download_ttl_hours: Optional[int] = None,
        created_by: int = 1,
    ) -> PermissionKey:
        """Create application-based permission key.

        Args:
            application_key_id: Application key identifier
            permissions: List of permissions
            organization_id: Optional organization ID
            deal_id: Optional deal ID
            expires_in_hours: Optional expiration
            download_ttl_hours: Optional download TTL
            created_by: Creator user ID

        Returns:
            Created PermissionKey
        """
        key_id = str(uuid.uuid4())

        key_data = {
            "application_key_id": application_key_id,
            "permissions": permissions,
            "organization_id": organization_id,
            "deal_id": deal_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        encrypted_key = self._encrypt_key_data(key_data)
        key_hash = hashlib.sha256(encrypted_key.encode("utf-8")).hexdigest()

        expires_at = None
        if expires_in_hours:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

        download_ttl = None
        if download_ttl_hours:
            download_ttl = datetime.utcnow() + timedelta(hours=download_ttl_hours)

        permission_key = PermissionKey(
            key_id=key_id,
            key_type=PermissionKeyType.APPLICATION.value,
            encrypted_key=encrypted_key,
            key_hash=key_hash,
            permissions=permissions,
            organization_id=organization_id,
            deal_id=deal_id,
            application_key_id=application_key_id,
            expires_at=expires_at,
            download_ttl=download_ttl,
            created_by=created_by,
        )

        self.db.add(permission_key)
        self.db.commit()
        self.db.refresh(permission_key)

        logger.info(f"Created application permission key {key_id} for app key {application_key_id[:10]}...")
        return permission_key

    def verify_permission_key(
        self,
        key_hash: str,
        wallet_address: Optional[str] = None,
        application_key_id: Optional[str] = None,
        required_permission: str = "view",
    ) -> Optional[PermissionKey]:
        """Verify permission key and check if it grants required permission.

        Args:
            key_hash: Key hash for lookup
            wallet_address: Optional wallet address (for wallet keys)
            application_key_id: Optional application key ID (for application keys)
            required_permission: Required permission (view, download, sign, edit)

        Returns:
            PermissionKey if valid, None otherwise
        """
        permission_key = (
            self.db.query(PermissionKey)
            .filter(PermissionKey.key_hash == key_hash)
            .first()
        )

        if not permission_key:
            logger.warning(f"Permission key not found for hash {key_hash[:16]}...")
            return None

        # Check expiration
        if permission_key.expires_at and datetime.utcnow() > permission_key.expires_at:
            logger.warning(f"Permission key {permission_key.key_id} has expired")
            return None

        # Check download TTL (if applicable)
        if required_permission == "download" and permission_key.download_ttl:
            if datetime.utcnow() > permission_key.download_ttl:
                logger.warning(f"Permission key {permission_key.key_id} download TTL has expired")
                return None

        # Verify key type matches
        if permission_key.key_type == PermissionKeyType.WALLET.value:
            if not wallet_address or permission_key.wallet_address != wallet_address.lower():
                logger.warning(f"Wallet address mismatch for key {permission_key.key_id}")
                return None
        elif permission_key.key_type == PermissionKeyType.APPLICATION.value:
            if not application_key_id or permission_key.application_key_id != application_key_id:
                logger.warning(f"Application key ID mismatch for key {permission_key.key_id}")
                return None

        # Check permissions
        if required_permission not in permission_key.permissions:
            logger.warning(
                f"Permission key {permission_key.key_id} does not grant {required_permission} permission"
            )
            return None

        # Update usage tracking
        permission_key.usage_count += 1
        permission_key.last_used_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Verified permission key {permission_key.key_id} for {required_permission} permission")
        return permission_key

    def _encrypt_key_data(self, key_data: Dict[str, Any]) -> str:
        """Encrypt key data using Fernet."""
        json_data = json.dumps(key_data, sort_keys=True, separators=(",", ":"))
        encrypted = self.link_generator.cipher.encrypt(json_data.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")
