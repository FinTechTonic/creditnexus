"""Nexus file parser for CreditNexus-to-CreditNexus sharing."""

import zipfile
import json
import base64
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from io import BytesIO
import logging

from app.utils.link_payload import LinkPayloadGenerator

logger = logging.getLogger(__name__)


class NexusFileParser:
    """Parse .nexus files and extract workflow data."""

    def __init__(self):
        """Initialize nexus file parser."""
        self.link_generator = LinkPayloadGenerator()

    def parse_nexus_file(self, nexus_bytes: bytes) -> Dict[str, Any]:
        """Parse .nexus file and extract all data.

        Args:
            nexus_bytes: .nexus file as bytes

        Returns:
            Dictionary with workflow data, files, permissions, etc.

        Raises:
            ValueError: If file is invalid, expired, or checksum mismatch
        """
        with zipfile.ZipFile(BytesIO(nexus_bytes), 'r') as nexus_zip:
            # 1. Read and decrypt metadata
            try:
                metadata_encrypted = nexus_zip.read('META-INF/metadata.json').decode('utf-8')
                metadata = self._decrypt_metadata(metadata_encrypted)
            except KeyError:
                raise ValueError("Missing META-INF/metadata.json in .nexus file")
            except Exception as e:
                raise ValueError(f"Failed to decrypt metadata: {e}")

            # 2. Read manifest
            try:
                manifest_json = nexus_zip.read('META-INF/manifest.json').decode('utf-8')
                manifest = json.loads(manifest_json)
            except KeyError:
                raise ValueError("Missing META-INF/manifest.json in .nexus file")
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid manifest JSON: {e}")

            # 3. Extract embedded files
            embedded_files = {}
            for file_info in manifest.get('files', []):
                if file_info.get('embedded'):
                    file_path = file_info['path']
                    try:
                        file_content = nexus_zip.read(file_path)

                        # Verify checksum
                        expected_checksum = file_info.get('checksum', '').replace('sha256:', '')
                        if expected_checksum:
                            actual_checksum = hashlib.sha256(file_content).hexdigest()
                            if expected_checksum != actual_checksum:
                                raise ValueError(
                                    f"Checksum mismatch for {file_info['filename']}: "
                                    f"expected {expected_checksum[:16]}..., got {actual_checksum[:16]}..."
                                )

                        embedded_files[file_info['filename']] = {
                            "content": file_content,
                            "size": file_info['size'],
                            "category": file_info.get('category', 'legal'),
                            "checksum": file_info.get('checksum'),
                        }
                    except KeyError:
                        logger.warning(f"Embedded file {file_path} not found in ZIP")
                    except ValueError as e:
                        # Re-raise checksum errors
                        raise

            # 4. Read large file references
            large_file_references = []
            try:
                references_json = nexus_zip.read('references/large_files.json').decode('utf-8')
                large_file_references = json.loads(references_json)
            except KeyError:
                pass  # No large file references
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid large_files.json: {e}")

            # 5. Read permissions (if available)
            permissions = None
            try:
                permissions_encrypted = nexus_zip.read('META-INF/permissions.json').decode('utf-8')
                permissions = self._decrypt_permissions(permissions_encrypted)
            except KeyError:
                pass  # No permissions
            except Exception as e:
                logger.warning(f"Failed to decrypt permissions: {e}")

            # 6. Read whitelist config (if available)
            whitelist_config = None
            try:
                whitelist_json = nexus_zip.read('META-INF/whitelist.json').decode('utf-8')
                whitelist_config = json.loads(whitelist_json)
            except KeyError:
                pass  # No whitelist config
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid whitelist.json: {e}")

            # 7. Check expiration
            expires_at_str = metadata.get('expires_at')
            if expires_at_str:
                try:
                    expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                    if datetime.utcnow() > expires_at.replace(tzinfo=None):
                        raise ValueError(f"Nexus file has expired (expired at {expires_at_str})")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse expiration date: {e}")

            # 8. Check download TTL (if applicable)
            download_ttl_str = metadata.get('download_ttl')
            if download_ttl_str:
                try:
                    download_ttl = datetime.fromisoformat(download_ttl_str.replace('Z', '+00:00'))
                    if datetime.utcnow() > download_ttl.replace(tzinfo=None):
                        raise ValueError(f"Download TTL has expired (expired at {download_ttl_str})")
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Failed to parse download TTL: {e}")

            logger.info(
                f"Parsed .nexus file for workflow {metadata.get('workflow_id')}: "
                f"{len(embedded_files)} embedded files, {len(large_file_references)} references"
            )

            return {
                "metadata": metadata,
                "manifest": manifest,
                "embedded_files": embedded_files,
                "large_file_references": large_file_references,
                "permissions": permissions,
                "whitelist_config": whitelist_config,
            }

    def _decrypt_metadata(self, encrypted_metadata: str) -> Dict[str, Any]:
        """Decrypt metadata."""
        # Add padding if needed
        padding = 4 - len(encrypted_metadata) % 4
        if padding != 4:
            encrypted_metadata += "=" * padding

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_metadata)
            decrypted = self.link_generator.cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to decrypt metadata: {e}")

    def _decrypt_permissions(self, encrypted_permissions: str) -> Dict[str, Any]:
        """Decrypt permission keys."""
        # Add padding if needed
        padding = 4 - len(encrypted_permissions) % 4
        if padding != 4:
            encrypted_permissions += "=" * padding

        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_permissions)
            decrypted = self.link_generator.cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to decrypt permissions: {e}")
