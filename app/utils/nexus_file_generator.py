"""Nexus file generator for CreditNexus-to-CreditNexus sharing."""

import zipfile
import json
import hashlib
import base64
import uuid
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from app.utils.link_payload import LinkPayloadGenerator
from app.services.file_storage_service import FileStorageService

logger = logging.getLogger(__name__)


class NexusFileGenerator:
    """Generate .nexus files for CreditNexus sharing."""

    MAX_EMBEDDED_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self):
        """Initialize nexus file generator."""
        self.link_generator = LinkPayloadGenerator()
        self.file_storage = FileStorageService()

    def generate_nexus_file(
        self,
        workflow_type: str,
        workflow_id: str,
        deal_id: Optional[int] = None,
        deal_data: Optional[Dict[str, Any]] = None,
        cdm_payload: Optional[Dict[str, Any]] = None,
        workflow_metadata: Optional[Dict[str, Any]] = None,
        file_references: Optional[List[Dict[str, Any]]] = None,
        whitelist_config: Optional[Dict[str, Any]] = None,
        sender_info: Optional[Dict[str, Any]] = None,
        receiver_info: Optional[Dict[str, Any]] = None,
        permission_keys: Optional[Dict[str, Any]] = None,
        expires_in_hours: int = 72,
        download_ttl_hours: Optional[int] = None,
        include_files: bool = True,
        max_embedded_size: int = MAX_EMBEDDED_SIZE,
    ) -> bytes:
        """Generate .nexus file as ZIP archive.

        Args:
            workflow_type: Workflow type
            workflow_id: Workflow UUID
            deal_id: Optional deal ID
            deal_data: Optional deal data
            cdm_payload: Optional CDM payload
            workflow_metadata: Optional workflow metadata
            file_references: Optional file references
            whitelist_config: Optional whitelist config
            sender_info: Optional sender info
            receiver_info: Optional receiver info
            permission_keys: Optional permission keys (wallet, app, whitelist)
            expires_in_hours: Link expiration
            download_ttl_hours: Optional download TTL (separate from link expiration)
            include_files: Whether to embed files
            max_embedded_size: Maximum size for embedded files

        Returns:
            .nexus file as bytes
        """
        # Use BytesIO to avoid Windows file-lock issues with tempfile.NamedTemporaryFile
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as nexus_zip:
            # 1. Generate encrypted metadata
            metadata = self._build_metadata(
                workflow_type, workflow_id, deal_id, deal_data,
                cdm_payload, workflow_metadata, sender_info,
                receiver_info, expires_in_hours, download_ttl_hours
            )
            encrypted_metadata = self._encrypt_metadata(metadata)
            nexus_zip.writestr('META-INF/metadata.json', encrypted_metadata)

            # 2. Process files (embed small, reference large)
            files_manifest = []
            large_file_references = []

            if include_files and file_references:
                for file_ref in file_references:
                    file_size = file_ref.get('size', 0)
                    filename = file_ref.get('filename', 'unknown')

                    if file_size <= max_embedded_size:
                        # Embed file
                        file_content = self._get_file_content(file_ref)
                        if file_content:
                            file_path = f"files/{filename}"
                            nexus_zip.writestr(file_path, file_content)

                            files_manifest.append({
                                "path": file_path,
                                "filename": filename,
                                "size": file_size,
                                "category": file_ref.get('category', 'legal'),
                                "checksum": self._compute_checksum(file_content),
                                "embedded": True
                            })
                    else:
                        # Reference large file
                        large_file_references.append({
                            "filename": filename,
                            "size": file_size,
                            "download_url": file_ref.get('download_url'),
                            "download_ttl": self._calculate_download_ttl(download_ttl_hours),
                            "checksum": file_ref.get('checksum'),
                            "embedded": False
                        })

            # 3. Write manifest
            manifest = self._build_manifest(
                workflow_type, workflow_id, sender_info,
                files_manifest, large_file_references
            )
            nexus_zip.writestr('META-INF/manifest.json', json.dumps(manifest, indent=2))

            # 4. Write large file references
            if large_file_references:
                nexus_zip.writestr(
                    'references/large_files.json',
                    json.dumps(large_file_references, indent=2)
                )

            # 5. Write permissions (encrypted)
            if permission_keys:
                encrypted_permissions = self._encrypt_permissions(permission_keys)
                nexus_zip.writestr('META-INF/permissions.json', encrypted_permissions)

            # 6. Write whitelist config (if provided)
            if whitelist_config:
                nexus_zip.writestr(
                    'META-INF/whitelist.json',
                    json.dumps(whitelist_config, indent=2)
                )

        nexus_bytes = buffer.getvalue()
        logger.info(f"Generated .nexus file for workflow {workflow_id} ({len(nexus_bytes)} bytes)")
        return nexus_bytes

    def _build_metadata(
        self,
        workflow_type: str,
        workflow_id: str,
        deal_id: Optional[int],
        deal_data: Optional[Dict[str, Any]],
        cdm_payload: Optional[Dict[str, Any]],
        workflow_metadata: Optional[Dict[str, Any]],
        sender_info: Optional[Dict[str, Any]],
        receiver_info: Optional[Dict[str, Any]],
        expires_in_hours: int,
        download_ttl_hours: Optional[int],
    ) -> Dict[str, Any]:
        """Build metadata dictionary."""
        expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()
        download_ttl = None
        if download_ttl_hours:
            download_ttl = (datetime.utcnow() + timedelta(hours=download_ttl_hours)).isoformat()

        return {
            "version": "3.0",
            "workflow_type": workflow_type,
            "workflow_id": workflow_id,
            "deal_id": deal_id,
            "deal_data": deal_data or {},
            "cdm_payload": cdm_payload or {},
            "workflow_metadata": workflow_metadata or {},
            "sender_info": sender_info or {},
            "receiver_info": receiver_info or {},
            "expires_at": expires_at,
            "download_ttl": download_ttl,
            "created_at": datetime.utcnow().isoformat(),
        }

    def _encrypt_metadata(self, metadata: Dict[str, Any]) -> str:
        """Encrypt metadata using Fernet."""
        json_data = json.dumps(metadata, sort_keys=True, separators=(",", ":"))
        encrypted = self.link_generator.cipher.encrypt(json_data.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")

    def _get_file_content(self, file_ref: Dict[str, Any]) -> Optional[bytes]:
        """Get file content from reference."""
        # Try to get from file storage
        if 'document_id' in file_ref:
            # Get from database
            from app.db.models import Document, DocumentVersion
            from app.db import SessionLocal

            db = SessionLocal()
            try:
                doc = db.query(Document).filter(Document.id == file_ref['document_id']).first()
                if doc:
                    latest_version = (
                        db.query(DocumentVersion)
                        .filter(DocumentVersion.document_id == doc.id)
                        .order_by(DocumentVersion.version_number.desc())
                        .first()
                    )
                    if latest_version and latest_version.source_filename:
                        # Get file from storage
                        deal_id_str = None
                        if doc.deal_id:
                            from app.db.models import Deal
                            deal = db.query(Deal).filter(Deal.id == doc.deal_id).first()
                            if deal:
                                deal_id_str = deal.deal_id

                        file_path = self.file_storage.get_document_path(
                            user_id=doc.uploaded_by or 1,
                            deal_id=deal_id_str,
                            document_id=doc.id
                        )
                        if file_path and Path(file_path).exists():
                            # Read and decrypt if needed
                            try:
                                return self.file_storage.read_encrypted_file(file_path)
                            except Exception as e:
                                logger.warning(f"Failed to read encrypted file {file_path}: {e}")
                                # Fallback: read as plain file
                                return Path(file_path).read_bytes()
            finally:
                db.close()

        # Try to download from URL
        if 'download_url' in file_ref:
            try:
                import httpx
                response = httpx.get(file_ref['download_url'], timeout=30.0)
                response.raise_for_status()
                return response.content
            except Exception as e:
                logger.error(f"Failed to download file from URL: {e}")

        # Try direct file path
        if 'file_path' in file_ref:
            file_path = Path(file_ref['file_path'])
            if file_path.exists():
                try:
                    return self.file_storage.read_encrypted_file(str(file_path))
                except Exception as e:
                    logger.warning(f"Failed to read encrypted file {file_path}: {e}")
                    return file_path.read_bytes()

        return None

    def _compute_checksum(self, content: bytes) -> str:
        """Compute SHA-256 checksum."""
        return f"sha256:{hashlib.sha256(content).hexdigest()}"

    def _calculate_download_ttl(self, download_ttl_hours: Optional[int]) -> Optional[str]:
        """Calculate download TTL timestamp."""
        if download_ttl_hours:
            return (datetime.utcnow() + timedelta(hours=download_ttl_hours)).isoformat()
        return None

    def _encrypt_permissions(self, permissions: Dict[str, Any]) -> str:
        """Encrypt permission keys."""
        json_data = json.dumps(permissions, sort_keys=True, separators=(",", ":"))
        encrypted = self.link_generator.cipher.encrypt(json_data.encode("utf-8"))
        return base64.urlsafe_b64encode(encrypted).decode("utf-8")

    def _build_manifest(
        self,
        workflow_type: str,
        workflow_id: str,
        sender_info: Optional[Dict[str, Any]],
        files_manifest: List[Dict[str, Any]],
        large_file_references: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Build file manifest."""
        return {
            "version": "1.0",
            "format": "nexus",
            "created_at": datetime.utcnow().isoformat(),
            "created_by": sender_info or {},
            "workflow_type": workflow_type,
            "workflow_id": workflow_id,
            "files": files_manifest,
            "references": large_file_references,
            "metadata_encryption": {
                "algorithm": "fernet",
                "key_id": "shared-key"
            }
        }
