"""Encrypted link payload generator for self-contained workflow links."""

import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.workflow_types import (
    WorkflowType,
    WorkflowTypeMetadata,
    get_workflow_metadata,
    validate_workflow_type,
    get_custom_workflow_metadata,
)

logger = logging.getLogger(__name__)


class LinkPayloadGenerator:
    """Generate encrypted self-contained workflow link payloads.

    Supports multiple workflow types (verification, notarization, document review, etc.)
    with unified v3.0 payload format, while maintaining backward compatibility with
    v2.0 verification links and v1.0 payment links.
    """

    def __init__(self):
        """Initialize payload generator with encryption key."""
        self.cipher = self._get_or_generate_key()

    def _get_or_generate_key(self):
        """Get encryption key from settings or generate one."""
        # Try to get from settings
        key_obj = getattr(settings, "LINK_ENCRYPTION_KEY", None)

        if key_obj:
            try:
                # Handle SecretStr type from pydantic-settings
                if hasattr(key_obj, "get_secret_value"):
                    key_str = key_obj.get_secret_value()
                else:
                    key_str = str(key_obj)

                if key_str and key_str.strip():
                    return Fernet(key_str.encode())
            except Exception as e:
                logger.warning(f"Invalid LINK_ENCRYPTION_KEY, generating new one: {e}")

        # Generate new key
        key = Fernet.generate_key()
        logger.warning("Using auto-generated encryption key (not persistent across restarts)")
        return Fernet(key)

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

    def generate_payment_link_payload(
        self,
        payment_id: str,
        payment_type: str,
        amount: float,
        currency: str,
        payer_info: Optional[Dict[str, Any]] = None,
        receiver_info: Optional[Dict[str, Any]] = None,
        notarization_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        pool_id: Optional[int] = None,
        tranche_id: Optional[int] = None,
        facilitator_url: Optional[str] = None,
        expires_in_hours: int = 24,
    ) -> str:
        """Generate encrypted payment link payload for x402 payment flows.

        Args:
            payment_id: Unique payment identifier
            payment_type: Type of payment (notarization_fee, tranche_purchase, etc.)
            amount: Payment amount
            currency: Payment currency (USD, USDC, etc.)
            payer_info: Optional payer metadata (wallet address, user_id, etc.)
            receiver_info: Optional receiver metadata (wallet address, contract address, etc.)
            notarization_id: Optional notarization record ID
            deal_id: Optional deal ID
            pool_id: Optional securitization pool ID
            tranche_id: Optional tranche ID
            facilitator_url: Optional x402 facilitator URL
            expires_in_hours: Link expiration time

        Returns:
            Base64url-encoded encrypted payload
        """
        expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()

        payload = {
            "payment_id": payment_id,
            "payment_type": payment_type,
            "amount": amount,
            "currency": currency,
            "payer_info": payer_info or {},
            "receiver_info": receiver_info or {},
            "notarization_id": notarization_id,
            "deal_id": deal_id,
            "pool_id": pool_id,
            "tranche_id": tranche_id,
            "facilitator_url": facilitator_url,
            "expires_at": expires_at,
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        # Serialize to JSON
        json_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        # Encrypt
        encrypted = self.cipher.encrypt(json_payload.encode("utf-8"))

        # Base64url encode (URL-safe)
        encoded = base64.urlsafe_b64encode(encrypted).decode("utf-8").rstrip("=")

        logger.info(f"Generated encrypted payment link payload for payment {payment_id}")
        return encoded

    def generate_workflow_link_payload(
        self,
        workflow_type: Union[WorkflowType, str],
        workflow_id: str,
        deal_id: Optional[int] = None,
        deal_data: Optional[Dict[str, Any]] = None,
        cdm_payload: Optional[Dict[str, Any]] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
        file_references: Optional[List[Dict[str, Any]]] = None,
        whitelist_config: Optional[Dict[str, Any]] = None,
        sender_info: Optional[Dict[str, Any]] = None,
        receiver_info: Optional[Dict[str, Any]] = None,
        fdc3_context: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
    ) -> str:
        """Generate encrypted workflow link payload (v3.0 format).

        Unified method for generating links for all workflow types with enhanced
        metadata, whitelist configuration, and FDC3 context support.

        Args:
            workflow_type: Workflow type (WorkflowType enum or string)
            workflow_id: Unique workflow identifier (UUID)
            deal_id: Optional deal database ID
            deal_data: Optional deal information
            cdm_payload: Optional full CDM event payload
            workflow_metadata: Optional workflow-specific metadata (instructions, deadline, etc.)
            file_references: Optional list of document metadata to include
            whitelist_config: Optional whitelist configuration to include in link
            sender_info: Optional sender metadata (user_id, email, name, organization)
            receiver_info: Optional receiver metadata (user_id, email, name, required_role)
            fdc3_context: Optional FDC3 context for desktop app integration
            callback_url: Optional URL for state synchronization callbacks
            expires_in_hours: Optional expiration time (uses default from workflow type if None)

        Returns:
            Base64url-encoded encrypted payload
        """
        # Normalize workflow type
        if isinstance(workflow_type, str):
            try:
                workflow_type_enum = WorkflowType(workflow_type)
            except ValueError:
                # Check if it's a custom workflow type
                custom_metadata = get_custom_workflow_metadata(workflow_type)
                if not custom_metadata:
                    raise ValueError(f"Invalid workflow type: {workflow_type}")
                workflow_type_enum = WorkflowType.CUSTOM
        else:
            workflow_type_enum = workflow_type

        # Get workflow metadata for defaults
        metadata = get_workflow_metadata(workflow_type_enum)
        if not metadata:
            # Try custom workflow
            if isinstance(workflow_type, str):
                metadata = get_custom_workflow_metadata(workflow_type)
            if not metadata:
                raise ValueError(f"Workflow type {workflow_type} not found in registry")

        # Use default expiration if not provided
        if expires_in_hours is None:
            expires_in_hours = metadata.default_expires_in_hours

        expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()

        # Build workflow_metadata with defaults
        if workflow_metadata is None:
            workflow_metadata = {}

        # Merge with defaults from workflow type
        final_workflow_metadata = {
            "title": workflow_metadata.get("title", metadata.title),
            "description": workflow_metadata.get("description", metadata.description),
            "instructions": workflow_metadata.get("instructions", []),
            "deadline": workflow_metadata.get("deadline", expires_at),
            "priority": workflow_metadata.get("priority", "medium"),
            "required_actions": workflow_metadata.get(
                "required_actions", metadata.required_actions
            ),
            "allowed_actions": workflow_metadata.get("allowed_actions", metadata.allowed_actions),
            **{
                k: v
                for k, v in workflow_metadata.items()
                if k
                not in [
                    "title",
                    "description",
                    "instructions",
                    "deadline",
                    "priority",
                    "required_actions",
                    "allowed_actions",
                ]
            },
        }

        # Build payload (v3.0 format)
        payload = {
            "version": "3.0",
            "workflow_type": workflow_type_enum.value
            if isinstance(workflow_type_enum, WorkflowType)
            else workflow_type,
            "workflow_id": workflow_id,
            "workflow_metadata": final_workflow_metadata,
            "deal_id": deal_id,
            "deal_data": deal_data or {},
            "cdm_payload": cdm_payload or {},
            "file_references": file_references or [],
            "whitelist_config": whitelist_config,
            "sender_info": sender_info or {},
            "receiver_info": receiver_info or {},
            "fdc3_context": fdc3_context,
            "expires_at": expires_at,
            "created_at": datetime.utcnow().isoformat(),
            "callback_url": callback_url,
        }

        # Serialize to JSON
        json_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"))

        # Encrypt
        encrypted = self.cipher.encrypt(json_payload.encode("utf-8"))

        # Base64url encode (URL-safe)
        encoded = base64.urlsafe_b64encode(encrypted).decode("utf-8").rstrip("=")

        logger.info(
            f"Generated encrypted workflow link payload (v3.0) for {workflow_type_enum.value} workflow {workflow_id}"
        )
        return encoded

    def parse_workflow_link_payload(self, payload: str) -> Optional[Dict[str, Any]]:
        """Parse and decrypt workflow link payload (supports v3.0, v2.0, and v1.0).

        Automatically detects payload version and parses accordingly.
        Maintains backward compatibility with legacy verification and payment links.

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
                workflow_id = (
                    data.get("workflow_id") or data.get("verification_id") or data.get("payment_id")
                )
                logger.warning(f"Link payload expired: {workflow_id}")
                return None

            # Normalize v2.0 verification links to v3.0 format
            version = data.get("version", "1.0")
            if version == "2.0" and "verification_id" in data:
                # Convert v2.0 verification link to v3.0 format
                data = {
                    "version": "3.0",
                    "workflow_type": "verification",
                    "workflow_id": data["verification_id"],
                    "workflow_metadata": {
                        "title": "Deal Verification",
                        "description": "Verify deal documents and CDM compliance",
                        "required_actions": ["accept", "decline"],
                        "allowed_actions": ["view", "download", "comment"],
                    },
                    "deal_id": data.get("deal_id", 0),
                    "deal_data": data.get("deal_data", {}),
                    "cdm_payload": data.get("cdm_payload", {}),
                    "file_references": data.get("file_references", []),
                    "sender_info": {},
                    "receiver_info": data.get("verifier_info", {}),
                    "expires_at": data["expires_at"],
                    "created_at": data.get("created_at", datetime.utcnow().isoformat()),
                }

            # Validate workflow type if v3.0
            if version == "3.0":
                workflow_type = data.get("workflow_type")
                if workflow_type and not validate_workflow_type(workflow_type):
                    logger.warning(f"Unknown workflow type in payload: {workflow_type}")
                    # Don't fail, but log warning

            return data

        except Exception as e:
            logger.error(f"Failed to parse workflow link payload: {e}")
            return None

    def parse_payment_link_payload(self, payload: str) -> Optional[Dict[str, Any]]:
        """Parse and decrypt payment link payload.

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
                logger.warning(f"Payment link payload expired: {data.get('payment_id')}")
                return None

            return data

        except Exception as e:
            logger.error(f"Failed to parse payment link payload: {e}")
            return None

    def generate_deal_flow_link_payload(
        self,
        workflow_id: str,
        deal_id: int,
        deal_data: Dict[str, Any],
        flow_type: str = "approval",  # "approval", "review", "closure"
        cdm_payload: Optional[Dict[str, Any]] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
        file_references: Optional[List[Dict[str, Any]]] = None,
        whitelist_config: Optional[Dict[str, Any]] = None,
        sender_info: Optional[Dict[str, Any]] = None,
        receiver_info: Optional[Dict[str, Any]] = None,
        expires_in_hours: Optional[int] = None,
    ) -> str:
        """Generate encrypted link payload for deal flow workflows (approval, review, closure).

        Args:
            workflow_id: Unique workflow identifier
            deal_id: Deal database ID
            deal_data: Deal information
            flow_type: Type of deal flow ("approval", "review", "closure")
            cdm_payload: Optional full CDM event payload
            workflow_metadata: Optional workflow-specific metadata
            file_references: Optional list of document metadata
            whitelist_config: Optional whitelist configuration
            sender_info: Optional sender metadata
            receiver_info: Optional receiver metadata
            expires_in_hours: Optional expiration time

        Returns:
            Base64url-encoded encrypted payload
        """
        # Map flow_type to WorkflowType
        workflow_type_map = {
            "approval": WorkflowType.DEAL_APPROVAL,
            "review": WorkflowType.DEAL_REVIEW,
            "closure": WorkflowType.DEAL_APPROVAL,  # Use approval workflow for closure
        }

        workflow_type = workflow_type_map.get(flow_type, WorkflowType.DEAL_APPROVAL)

        # Build default workflow metadata if not provided
        if workflow_metadata is None:
            workflow_metadata = {}

        if flow_type == "approval":
            workflow_metadata.setdefault("title", "Deal Approval Request")
            workflow_metadata.setdefault(
                "description", "Please review and approve this deal proposal"
            )
            workflow_metadata.setdefault("required_actions", ["approve", "reject"])
        elif flow_type == "review":
            workflow_metadata.setdefault("title", "Deal Review Request")
            workflow_metadata.setdefault(
                "description", "Please review this deal and provide feedback"
            )
            workflow_metadata.setdefault("required_actions", ["submit_review"])
        else:  # closure
            workflow_metadata.setdefault("title", "Deal Closure Request")
            workflow_metadata.setdefault("description", "Please review and approve deal closure")
            workflow_metadata.setdefault("required_actions", ["approve", "reject"])

        return self.generate_workflow_link_payload(
            workflow_type=workflow_type,
            workflow_id=workflow_id,
            deal_id=deal_id,
            deal_data=deal_data,
            cdm_payload=cdm_payload,
            workflow_metadata=workflow_metadata,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            receiver_info=receiver_info,
            expires_in_hours=expires_in_hours,
        )

    def generate_document_workflow_link_payload(
        self,
        workflow_id: str,
        document_id: int,
        document_version: Optional[int] = None,
        deal_id: Optional[int] = None,
        deal_data: Optional[Dict[str, Any]] = None,
        review_type: str = "general",  # "legal", "financial", "compliance", "general"
        workflow_metadata: Optional[Dict[str, Any]] = None,
        file_references: Optional[List[Dict[str, Any]]] = None,
        whitelist_config: Optional[Dict[str, Any]] = None,
        sender_info: Optional[Dict[str, Any]] = None,
        receiver_info: Optional[Dict[str, Any]] = None,
        expires_in_hours: Optional[int] = None,
    ) -> str:
        """Generate encrypted link payload for document workflow (review, approval, signature).

        Args:
            workflow_id: Unique workflow identifier
            document_id: Document database ID
            document_version: Optional document version number
            deal_id: Optional deal database ID
            deal_data: Optional deal information
            review_type: Type of review ("legal", "financial", "compliance", "general")
            workflow_metadata: Optional workflow-specific metadata
            file_references: Optional list of document metadata
            whitelist_config: Optional whitelist configuration
            sender_info: Optional sender metadata
            receiver_info: Optional receiver metadata
            expires_in_hours: Optional expiration time

        Returns:
            Base64url-encoded encrypted payload
        """
        # Build default workflow metadata if not provided
        if workflow_metadata is None:
            workflow_metadata = {}

        workflow_metadata.setdefault("title", f"Document Review - {review_type.title()}")
        workflow_metadata.setdefault(
            "description", f"Please review this document ({review_type} review)"
        )
        workflow_metadata.setdefault("required_actions", ["approve", "reject", "request_changes"])
        workflow_metadata.setdefault("document_id", document_id)
        if document_version:
            workflow_metadata.setdefault("document_version", document_version)
        workflow_metadata.setdefault("review_type", review_type)

        return self.generate_workflow_link_payload(
            workflow_type=WorkflowType.DOCUMENT_REVIEW,
            workflow_id=workflow_id,
            deal_id=deal_id,
            deal_data=deal_data,
            workflow_metadata=workflow_metadata,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            receiver_info=receiver_info,
            expires_in_hours=expires_in_hours,
        )

    def generate_custom_workflow_link_payload(
        self,
        workflow_id: str,
        custom_workflow_type: str,
        workflow_metadata: Dict[str, Any],
        deal_id: Optional[int] = None,
        deal_data: Optional[Dict[str, Any]] = None,
        cdm_payload: Optional[Dict[str, Any]] = None,
        file_references: Optional[List[Dict[str, Any]]] = None,
        whitelist_config: Optional[Dict[str, Any]] = None,
        sender_info: Optional[Dict[str, Any]] = None,
        receiver_info: Optional[Dict[str, Any]] = None,
        expires_in_hours: int = 72,
    ) -> str:
        """Generate encrypted link payload for custom workflow types.

        Args:
            workflow_id: Unique workflow identifier
            custom_workflow_type: Custom workflow type identifier
            workflow_metadata: Workflow-specific metadata (must include title, description, required_actions)
            deal_id: Optional deal database ID
            deal_data: Optional deal information
            cdm_payload: Optional full CDM event payload
            file_references: Optional list of document metadata
            whitelist_config: Optional whitelist configuration
            sender_info: Optional sender metadata
            receiver_info: Optional receiver metadata
            expires_in_hours: Expiration time in hours

        Returns:
            Base64url-encoded encrypted payload
        """
        # Validate custom workflow type
        if not validate_workflow_type(custom_workflow_type):
            # Try to register it if it doesn't exist
            from app.core.workflow_types import register_custom_workflow_type

            if not register_custom_workflow_type(
                workflow_type=custom_workflow_type,
                title=workflow_metadata.get("title", "Custom Workflow"),
                description=workflow_metadata.get("description", ""),
                required_actions=workflow_metadata.get("required_actions", []),
                allowed_actions=workflow_metadata.get(
                    "allowed_actions", ["view", "download", "comment"]
                ),
            ):
                logger.warning(
                    f"Custom workflow type {custom_workflow_type} registration failed or already exists"
                )

        return self.generate_workflow_link_payload(
            workflow_type=custom_workflow_type,
            workflow_id=workflow_id,
            deal_id=deal_id,
            deal_data=deal_data,
            cdm_payload=cdm_payload,
            workflow_metadata=workflow_metadata,
            file_references=file_references,
            whitelist_config=whitelist_config,
            sender_info=sender_info,
            receiver_info=receiver_info,
            expires_in_hours=expires_in_hours,
        )
