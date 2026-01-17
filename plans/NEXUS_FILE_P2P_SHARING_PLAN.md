# .nexus File Format & CreditNexus-to-CreditNexus Sharing Plan

**Status**: Comprehensive Implementation Plan  
**Priority**: P0 (Critical)  
**Estimated Timeline**: 10-12 weeks  
**Last Updated**: 2024-12-XX

---

## Executive Summary

This document provides a **complete plan** for implementing `.nexus` file format for CreditNexus-to-CreditNexus sharing with enhanced connectivity, permission management, blockchain notarization, and offline support. The `.nexus` format will be a self-contained, encrypted file that can be shared peer-to-peer or via traditional channels, with embedded metadata, optional file embedding, permission keys, and blockchain-verified send/receive events.

**Key Features**:
- `.nexus` file format (self-contained encrypted package)
- Client-server-client connectivity with WebRTC/WebSocket fallback
- Permission keys (wallet keys, application keys) for access control
- Whitelist configuration support
- Download TTL (time-to-live) for shared files
- Blockchain notarization for send/receive events
- Offline support (files can be opened without server connection)
- Direct file embedding for small files (<10MB)
- File references with download URLs for large files

---

## Current State Assessment

### ✅ Existing Infrastructure

1. **Link Payload System**: 
   - `LinkPayloadGenerator` with Fernet encryption
   - Base64url encoding for URL-safe payloads
   - Versioned payloads (v3.0, v2.0, v1.0)
   - Workflow metadata, deal data, CDM payload, file references

2. **File Download System**:
   - `download_file_from_url()` utility
   - File storage via `FileStorageService`
   - Document versioning support

3. **Notarization System**:
   - `NotarizationService` with blockchain integration
   - CDM notarization events
   - Multi-signer support

4. **Workflow Delegation**:
   - `WorkflowDelegationService` for link generation
   - State synchronization callbacks
   - Whitelist configuration support

5. **FDC3 Integration**:
   - Desktop app integration
   - Workflow link broadcasting
   - Context sharing

### ❌ Critical Issues Identified

1. **Connection Dependency**:
   - **Issue**: Download URLs require sender's server to be accessible
   - **Impact**: Links fail if sender's server is down or unreachable
   - **Location**: `app/api/remote_routes.py` line 283, `app/utils/file_downloader.py`
   - **Solution**: Embed small files in .nexus, use P2P for large files

2. **Authentication Barriers**:
   - **Issue**: Download URLs may require authentication (JWT tokens)
   - **Impact**: Receiver cannot download files without valid credentials
   - **Location**: File download endpoints require authentication
   - **Solution**: Permission keys in .nexus file unlock access

3. **No Offline Support**:
   - **Issue**: Links require active server connection to parse and download
   - **Impact**: Cannot share files for offline use
   - **Location**: All link processing requires server connection
   - **Solution**: .nexus files are self-contained, can be parsed offline

4. **No Direct File Embedding**:
   - **Issue**: Files are always referenced via URLs, never embedded
   - **Impact**: Large files cannot be shared offline
   - **Location**: `LinkPayloadGenerator` only includes file references
   - **Solution**: Embed files <10MB, reference files >10MB with download TTL

5. **No Permission Keys**:
   - **Issue**: No wallet/application key sharing for permissions
   - **Impact**: Cannot unlock permissions for shared files/deals
   - **Location**: No permission key system exists
   - **Solution**: Permission key system with wallet/app/whitelist keys

6. **No Download TTL**:
   - **Issue**: Links have expiration but no separate download TTL
   - **Impact**: Cannot set different expiration for link vs. file access
   - **Location**: `LinkPayloadGenerator` uses single `expires_in_hours`
   - **Solution**: Separate `download_ttl` field in .nexus metadata

7. **No Blockchain Events for Sharing**:
   - **Issue**: No notarization events for send/receive operations
   - **Impact**: Cannot audit or verify file sharing activities
   - **Location**: No sharing event generation
   - **Solution**: `SharingEvent` model with blockchain notarization

8. **No P2P Connectivity**:
   - **Issue**: All sharing goes through servers, no direct client-to-client
   - **Impact**: Slower, less efficient, requires server availability
   - **Location**: No WebRTC/WebSocket P2P implementation
   - **Solution**: WebRTC with WebSocket fallback for P2P file transfer

9. **No .nexus File Format**:
   - **Issue**: Links are URL-encoded strings, not downloadable files
   - **Impact**: Cannot share via email attachments, USB drives, etc.
   - **Location**: No file format implementation
   - **Solution**: ZIP-based .nexus format with embedded metadata and files

---

## Feasibility Assessment

### ✅ **HIGHLY FEASIBLE**

**Reasons**:
1. **Existing Encryption**: Fernet encryption already implemented
2. **File Format**: Can use ZIP/TAR format with JSON metadata (similar to .epub, .docx)
3. **WebRTC/WebSocket**: Mature libraries available (aiortc, websockets)
4. **Blockchain Integration**: Notarization system already exists
5. **Permission System**: Role-based permissions can be extended

**Challenges**:
1. **File Size Limits**: Large files (>10MB) should use references, not embedding
2. **P2P NAT Traversal**: May require STUN/TURN servers
3. **Key Management**: Secure storage and transmission of permission keys
4. **Format Compatibility**: Need to support both .nexus files and legacy links

**Solutions**:
1. Use hybrid approach: embed small files, reference large files
2. Use WebRTC with STUN/TURN fallback to WebSocket
3. Encrypt permission keys with recipient's public key or shared secret
4. Support both formats with automatic detection

---

## Implementation Plan

### Project 1: .nexus File Format Specification

**Objective**: Define and implement `.nexus` file format as a self-contained encrypted package.

#### Task 1.1: File Format Specification

**File Format**: `.nexus` (ZIP-based, similar to .epub, .docx)

**Structure**:
```
deal_share_2024_001.nexus
├── META-INF/
│   ├── manifest.json          # File manifest with checksums
│   ├── metadata.json          # Encrypted workflow metadata
│   └── permissions.json       # Permission keys (encrypted)
├── files/
│   ├── document_1.pdf          # Embedded files (<10MB)
│   ├── document_2.docx
│   └── ...
├── references/
│   └── large_files.json       # References to large files (>10MB)
└── signature.nexus            # Digital signature (optional)
```

**File**: `docs/specifications/nexus-file-format.md` (NEW)

**Subtasks**:
1. **Define manifest structure**:
   ```json
   {
     "version": "1.0",
     "format": "nexus",
     "created_at": "2024-12-XXT00:00:00Z",
     "created_by": {
       "user_id": 123,
       "email": "sender@example.com",
       "organization": "Bank A"
     },
     "workflow_type": "verification",
     "workflow_id": "uuid-here",
     "files": [
       {
         "path": "files/document_1.pdf",
         "filename": "document_1.pdf",
         "size": 1024000,
         "category": "legal",
         "checksum": "sha256:...",
         "embedded": true
       }
     ],
     "references": [
       {
         "filename": "large_file.pdf",
         "size": 50000000,
         "download_url": "https://...",
         "download_ttl": "2024-12-XXT00:00:00Z",
         "checksum": "sha256:...",
         "embedded": false
       }
     ],
     "metadata_encryption": {
       "algorithm": "fernet",
       "key_id": "key-uuid"
     }
   }
   ```

2. **Define metadata structure** (encrypted):
   ```json
   {
     "workflow_type": "verification",
     "workflow_id": "uuid",
     "deal_id": 123,
     "deal_data": {...},
     "cdm_payload": {...},
     "workflow_metadata": {...},
     "sender_info": {...},
     "receiver_info": {...},
     "whitelist_config": {...},
     "expires_at": "2024-12-XXT00:00:00Z",
     "download_ttl": "2024-12-XXT00:00:00Z",
     "version": "3.0"
   }
   ```

3. **Define permissions structure** (encrypted):
   ```json
   {
     "wallet_keys": [
       {
         "wallet_address": "0x...",
         "permissions": ["view", "download", "sign"],
         "encrypted_key": "fernet-encrypted-key"
       }
     ],
     "application_keys": [
       {
         "key_id": "app-key-uuid",
         "permissions": ["view", "download"],
         "encrypted_key": "fernet-encrypted-key",
         "organization_id": 456
       }
     ],
     "whitelist_keys": [
       {
         "whitelist_id": "whitelist-uuid",
         "permissions": ["view"],
         "encrypted_key": "fernet-encrypted-key"
       }
     ]
   }
   ```

**Code Reference**: See `docs/specifications/nexus-file-format.md` (NEW)

#### Task 1.2: Nexus File Generator

**File**: `app/utils/nexus_file_generator.py` (NEW)

**Lines**: 1-500

**Subtasks**:
1. **Create NexusFileGenerator class**:
   ```python
   import zipfile
   import json
   import hashlib
   import tempfile
   from pathlib import Path
   from typing import Dict, Any, List, Optional
   from cryptography.fernet import Fernet
   from datetime import datetime, timedelta
   
   from app.utils.link_payload import LinkPayloadGenerator
   from app.services.file_storage_service import FileStorageService
   
   class NexusFileGenerator:
       """Generate .nexus files for CreditNexus sharing."""
       
       MAX_EMBEDDED_SIZE = 10 * 1024 * 1024  # 10MB
       
       def __init__(self):
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
           # Create temporary ZIP file
           with tempfile.NamedTemporaryFile(delete=False, suffix='.nexus') as tmp_file:
               with zipfile.ZipFile(tmp_file.name, 'w', zipfile.ZIP_DEFLATED) as nexus_zip:
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
               
               # Read ZIP file as bytes
               with open(tmp_file.name, 'rb') as f:
                   nexus_bytes = f.read()
               
               # Clean up
               Path(tmp_file.name).unlink()
               
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
                           file_path = self.file_storage.get_file_path(
                               user_id=doc.user_id,
                               deal_id=doc.deal_id,
                               filename=latest_version.source_filename,
                               subdirectory=file_ref.get('subdirectory', 'documents')
                           )
                           if file_path and Path(file_path).exists():
                               return Path(file_path).read_bytes()
               finally:
                   db.close()
           
           # Try to download from URL
           if 'download_url' in file_ref:
               import httpx
               try:
                   response = httpx.get(file_ref['download_url'], timeout=30.0)
                   response.raise_for_status()
                   return response.content
               except Exception as e:
                   logger.error(f"Failed to download file from URL: {e}")
           
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
   ```

**Code Reference**: See `app/utils/nexus_file_generator.py` (NEW)

#### Task 1.3: Nexus File Parser

**File**: `app/utils/nexus_file_parser.py` (NEW)

**Lines**: 1-400

**Subtasks**:
1. **Create NexusFileParser class**:
   ```python
   import zipfile
   import json
   import base64
   import hashlib
   from pathlib import Path
   from typing import Dict, Any, List, Optional
   from datetime import datetime
   from io import BytesIO
   
   from app.utils.link_payload import LinkPayloadGenerator
   
   class NexusFileParser:
       """Parse .nexus files and extract workflow data."""
       
       def __init__(self):
           self.link_generator = LinkPayloadGenerator()
       
       def parse_nexus_file(self, nexus_bytes: bytes) -> Dict[str, Any]:
           """Parse .nexus file and extract all data.
           
           Args:
               nexus_bytes: .nexus file as bytes
               
           Returns:
               Dictionary with workflow data, files, permissions, etc.
           """
           with zipfile.ZipFile(BytesIO(nexus_bytes), 'r') as nexus_zip:
               # 1. Read and decrypt metadata
               metadata_encrypted = nexus_zip.read('META-INF/metadata.json').decode('utf-8')
               metadata = self._decrypt_metadata(metadata_encrypted)
               
               # 2. Read manifest
               manifest_json = nexus_zip.read('META-INF/manifest.json').decode('utf-8')
               manifest = json.loads(manifest_json)
               
               # 3. Extract embedded files
               embedded_files = {}
               for file_info in manifest.get('files', []):
                   if file_info.get('embedded'):
                       file_path = file_info['path']
                       file_content = nexus_zip.read(file_path)
                       
                       # Verify checksum
                       expected_checksum = file_info.get('checksum', '').replace('sha256:', '')
                       actual_checksum = hashlib.sha256(file_content).hexdigest()
                       if expected_checksum and expected_checksum != actual_checksum:
                           raise ValueError(f"Checksum mismatch for {file_info['filename']}")
                       
                       embedded_files[file_info['filename']] = {
                           "content": file_content,
                           "size": file_info['size'],
                           "category": file_info.get('category', 'legal'),
                           "checksum": file_info.get('checksum'),
                       }
               
               # 4. Read large file references
               large_file_references = []
               try:
                   references_json = nexus_zip.read('references/large_files.json').decode('utf-8')
                   large_file_references = json.loads(references_json)
               except KeyError:
                   pass  # No large file references
               
               # 5. Read permissions (if available)
               permissions = None
               try:
                   permissions_encrypted = nexus_zip.read('META-INF/permissions.json').decode('utf-8')
                   permissions = self._decrypt_permissions(permissions_encrypted)
               except KeyError:
                   pass  # No permissions
               
               # 6. Read whitelist config (if available)
               whitelist_config = None
               try:
                   whitelist_json = nexus_zip.read('META-INF/whitelist.json').decode('utf-8')
                   whitelist_config = json.loads(whitelist_json)
               except KeyError:
                   pass  # No whitelist config
               
               # 7. Check expiration
               expires_at = datetime.fromisoformat(metadata.get('expires_at'))
               if datetime.utcnow() > expires_at:
                   raise ValueError("Nexus file has expired")
               
               # 8. Check download TTL (if applicable)
               download_ttl = metadata.get('download_ttl')
               if download_ttl:
                   download_ttl_dt = datetime.fromisoformat(download_ttl)
                   if datetime.utcnow() > download_ttl_dt:
                       raise ValueError("Download TTL has expired")
               
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
           
           encrypted_bytes = base64.urlsafe_b64decode(encrypted_metadata)
           decrypted = self.link_generator.cipher.decrypt(encrypted_bytes)
           return json.loads(decrypted.decode("utf-8"))
       
       def _decrypt_permissions(self, encrypted_permissions: str) -> Dict[str, Any]:
           """Decrypt permission keys."""
           # Add padding if needed
           padding = 4 - len(encrypted_permissions) % 4
           if padding != 4:
               encrypted_permissions += "=" * padding
           
           encrypted_bytes = base64.urlsafe_b64decode(encrypted_permissions)
           decrypted = self.link_generator.cipher.decrypt(encrypted_bytes)
           return json.loads(decrypted.decode("utf-8"))
   ```

**Code Reference**: See `app/utils/nexus_file_parser.py` (NEW)

---

### Project 2: Permission Keys System

**Objective**: Implement permission keys (wallet keys, application keys) for unlocking access to shared files and deals.

#### Task 2.1: Permission Key Models

**File**: `app/db/models.py` (UPDATE)

**Lines**: ~4000-4200

**Subtasks**:
1. **Add PermissionKey model**:
   ```python
   class PermissionKeyType(str, enum.Enum):
       """Permission key types."""
       WALLET = "wallet"  # Ethereum wallet address
       APPLICATION = "application"  # Application API key
       WHITELIST = "whitelist"  # Whitelist entry
       ORGANIZATION = "organization"  # Organization-level key
   
   class PermissionKey(Base):
       """Permission keys for unlocking shared files/deals."""
       __tablename__ = "permission_keys"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       
       # Key identification
       key_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID
       key_type = Column(String(50), nullable=False, index=True)  # wallet, application, whitelist, organization
       
       # Key data (encrypted)
       encrypted_key = Column(EncryptedJSON(), nullable=False)  # Encrypted key data
       key_hash = Column(String(255), nullable=False, index=True)  # SHA-256 hash for lookup
       
       # Permissions
       permissions = Column(JSONB, nullable=False)  # ["view", "download", "sign", "edit"]
       
       # Scope
       deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
       document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
       organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
       workflow_id = Column(String(255), nullable=True, index=True)
       
       # Key metadata
       wallet_address = Column(String(255), nullable=True, index=True)  # For wallet keys
       application_key_id = Column(String(255), nullable=True, index=True)  # For application keys
       whitelist_id = Column(String(255), nullable=True, index=True)  # For whitelist keys
       
       # Expiration
       expires_at = Column(DateTime, nullable=True, index=True)
       download_ttl = Column(DateTime, nullable=True, index=True)  # Separate TTL for downloads
       
       # Usage tracking
       usage_count = Column(Integer, default=0, nullable=False)
       last_used_at = Column(DateTime, nullable=True)
       
       # Creator
       created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
       
       # Relationships
       deal = relationship("Deal", backref="permission_keys")
       document = relationship("Document", backref="permission_keys")
       organization = relationship("Organization", backref="permission_keys")
       creator = relationship("User", foreign_keys=[created_by])
       
       def to_dict(self):
           """Convert to dictionary (excludes encrypted_key)."""
           return {
               "key_id": self.key_id,
               "key_type": self.key_type,
               "permissions": self.permissions,
               "deal_id": self.deal_id,
               "document_id": self.document_id,
               "organization_id": self.organization_id,
               "workflow_id": self.workflow_id,
               "wallet_address": self.wallet_address,
               "application_key_id": self.application_key_id,
               "whitelist_id": self.whitelist_id,
               "expires_at": self.expires_at.isoformat() if self.expires_at else None,
               "download_ttl": self.download_ttl.isoformat() if self.download_ttl else None,
               "usage_count": self.usage_count,
               "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
               "created_at": self.created_at.isoformat() if self.created_at else None,
           }
   ```

**Code Reference**: See `app/db/models.py` lines 4000-4200

#### Task 2.2: Permission Key Service

**File**: `app/services/permission_key_service.py` (NEW)

**Lines**: 1-300

**Subtasks**:
1. **Create PermissionKeyService**:
   ```python
   from typing import Dict, Any, List, Optional
   from sqlalchemy.orm import Session
   from datetime import datetime, timedelta
   import uuid
   import hashlib
   import secrets
   
   from app.db.models import PermissionKey, PermissionKeyType
   from app.utils.link_payload import LinkPayloadGenerator
   
   class PermissionKeyService:
       """Service for managing permission keys."""
       
       def __init__(self, db: Session):
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
               encrypted_key=encrypted_key,
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
           """Create application-based permission key."""
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
               return None
           
           # Check expiration
           if permission_key.expires_at and datetime.utcnow() > permission_key.expires_at:
               return None
           
           # Check download TTL (if applicable)
           if required_permission == "download" and permission_key.download_ttl:
               if datetime.utcnow() > permission_key.download_ttl:
                   return None
           
           # Verify key type matches
           if permission_key.key_type == PermissionKeyType.WALLET.value:
               if not wallet_address or permission_key.wallet_address != wallet_address.lower():
                   return None
           elif permission_key.key_type == PermissionKeyType.APPLICATION.value:
               if not application_key_id or permission_key.application_key_id != application_key_id:
                   return None
           
           # Check permissions
           if required_permission not in permission_key.permissions:
               return None
           
           # Update usage tracking
           permission_key.usage_count += 1
           permission_key.last_used_at = datetime.utcnow()
           self.db.commit()
           
           return permission_key
       
       def _encrypt_key_data(self, key_data: Dict[str, Any]) -> str:
           """Encrypt key data using Fernet."""
           import json
           import base64
           
           json_data = json.dumps(key_data, sort_keys=True, separators=(",", ":"))
           encrypted = self.link_generator.cipher.encrypt(json_data.encode("utf-8"))
           return base64.urlsafe_b64encode(encrypted).decode("utf-8")
   ```

**Code Reference**: See `app/services/permission_key_service.py` (NEW)

---

### Project 3: Client-Server-Client Connectivity

**Objective**: Implement direct CreditNexus-to-CreditNexus connectivity with WebRTC/WebSocket support.

#### Task 3.1: P2P Connection Service

**File**: `app/services/p2p_connection_service.py` (NEW)

**Lines**: 1-400

**Subtasks**:
1. **Create P2PConnectionService**:
   ```python
   import asyncio
   import websockets
   from typing import Dict, Any, Optional, Callable
   from datetime import datetime
   import logging
   
   logger = logging.getLogger(__name__)
   
   class P2PConnectionService:
       """Service for P2P connections between CreditNexus instances."""
       
       def __init__(self):
           self.active_connections: Dict[str, websockets.WebSocketServerProtocol] = {}
           self.connection_callbacks: Dict[str, Callable] = {}
       
       async def create_connection(
           self,
           connection_id: str,
           target_url: Optional[str] = None,
       ) -> Dict[str, Any]:
           """Create P2P connection (WebRTC preferred, WebSocket fallback).
           
           Args:
               connection_id: Unique connection ID
               target_url: Optional target URL for direct connection
               
           Returns:
               Connection info with WebRTC offer or WebSocket URL
           """
           # Try WebRTC first (if aiortc available)
           try:
               from aiortc import RTCPeerConnection, RTCSessionDescription, RTCIceCandidate
               
               # Create WebRTC offer
               pc = RTCPeerConnection()
               offer = await pc.createOffer()
               await pc.setLocalDescription(offer)
               
               return {
                   "connection_id": connection_id,
                   "type": "webrtc",
                   "offer": {
                       "sdp": offer.sdp,
                       "type": offer.type
                   },
                   "ice_servers": [
                       {"urls": "stun:stun.l.google.com:19302"},
                       # Add TURN servers if configured
                   ],
                   "created_at": datetime.utcnow().isoformat(),
               }
           except ImportError:
               logger.warning("aiortc not available, using WebSocket fallback")
               
               # Fallback to WebSocket
               if target_url:
                   return {
                       "connection_id": connection_id,
                       "type": "websocket",
                       "url": target_url,
                       "created_at": datetime.utcnow().isoformat(),
                   }
               else:
                   # Return WebSocket server URL
                   return {
                       "connection_id": connection_id,
                       "type": "websocket",
                       "url": f"wss://creditnexus.ai/p2p/{connection_id}",
                       "created_at": datetime.utcnow().isoformat(),
                   }
       
       async def send_file_via_p2p(
           self,
           connection_id: str,
           file_data: bytes,
           metadata: Dict[str, Any],
       ) -> bool:
           """Send file via P2P connection.
           
           Args:
               connection_id: Connection ID
               file_data: File bytes
               metadata: File metadata
               
           Returns:
               True if sent successfully
           """
           if connection_id in self.active_connections:
               websocket = self.active_connections[connection_id]
               try:
                   # Send metadata first
                   await websocket.send(json.dumps({
                       "type": "file_metadata",
                       "metadata": metadata
                   }))
                   
                   # Send file in chunks
                   chunk_size = 64 * 1024  # 64KB chunks
                   for i in range(0, len(file_data), chunk_size):
                       chunk = file_data[i:i + chunk_size]
                       await websocket.send(chunk)
                       
                   # Send completion
                   await websocket.send(json.dumps({
                       "type": "file_complete",
                       "size": len(file_data)
                   }))
                   
                   return True
               except Exception as e:
                   logger.error(f"Failed to send file via P2P: {e}")
                   return False
           return False
       
       async def receive_file_via_p2p(
           self,
           connection_id: str,
           on_file_received: Callable[[bytes, Dict[str, Any]], None],
       ):
           """Receive file via P2P connection.
           
           Args:
               connection_id: Connection ID
               on_file_received: Callback when file is received
           """
           # This would be implemented in WebSocket handler
           pass
   ```

**Code Reference**: See `app/services/p2p_connection_service.py` (NEW)

#### Task 3.2: WebSocket P2P Handler

**File**: `app/api/p2p_routes.py` (NEW)

**Lines**: 1-200

**Subtasks**:
1. **Create WebSocket endpoints**:
   ```python
   from fastapi import APIRouter, WebSocket, WebSocketDisconnect
   from app.services.p2p_connection_service import P2PConnectionService
   
   router = APIRouter(prefix="/p2p", tags=["p2p"])
   p2p_service = P2PConnectionService()
   
   @router.websocket("/{connection_id}")
   async def p2p_websocket(websocket: WebSocket, connection_id: str):
       """WebSocket endpoint for P2P file sharing."""
       await websocket.accept()
       p2p_service.active_connections[connection_id] = websocket
       
       try:
           while True:
               data = await websocket.receive_text()
               message = json.loads(data)
               
               if message.get("type") == "file_metadata":
                   # Store metadata for file reception
                   pass
               elif message.get("type") == "file_complete":
                   # Process received file
                   pass
       except WebSocketDisconnect:
           del p2p_service.active_connections[connection_id]
   ```

**Code Reference**: See `app/api/p2p_routes.py` (NEW)

---

### Project 4: Blockchain Notarization for Sharing

**Objective**: Generate blockchain notarization events for send/receive operations.

#### Task 4.1: Sharing Event Models

**File**: `app/db/models.py` (UPDATE)

**Lines**: ~4200-4400

**Subtasks**:
1. **Add SharingEvent model**:
   ```python
   class SharingEvent(Base):
       """Blockchain-notarized sharing events."""
       __tablename__ = "sharing_events"
       
       id = Column(Integer, primary_key=True, autoincrement=True)
       
       # Event identification
       event_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID
       event_type = Column(String(50), nullable=False, index=True)  # send, receive
       
       # Sharing details
       sharing_method = Column(String(50), nullable=False)  # nexus_file, link, p2p
       workflow_id = Column(String(255), nullable=True, index=True)
       deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
       document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
       
       # Participants
       sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
       receiver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
       receiver_email = Column(String(255), nullable=True, index=True)
       receiver_wallet_address = Column(String(255), nullable=True, index=True)
       
       # File information
       file_hash = Column(String(255), nullable=False, index=True)  # SHA-256 of .nexus file or link payload
       file_size = Column(Integer, nullable=True)
       files_included = Column(Integer, default=0, nullable=False)
       
       # Blockchain notarization
       blockchain_tx_hash = Column(String(255), nullable=True, index=True)
       blockchain_block_number = Column(Integer, nullable=True)
       notarized_at = Column(DateTime, nullable=True)
       
       # CDM event
       cdm_event = Column(JSONB, nullable=True)
       
       # Metadata
       metadata = Column(JSONB, nullable=True)
       created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
       
       # Relationships
       deal = relationship("Deal", backref="sharing_events")
       document = relationship("Document", backref="sharing_events")
       sender = relationship("User", foreign_keys=[sender_user_id])
       receiver = relationship("User", foreign_keys=[receiver_user_id])
   ```

**Code Reference**: See `app/db/models.py` lines 4200-4400

#### Task 4.2: Sharing Event Service

**File**: `app/services/sharing_event_service.py` (NEW)

**Lines**: 1-250

**Subtasks**:
1. **Create SharingEventService**:
   ```python
   from typing import Dict, Any, Optional
   from sqlalchemy.orm import Session
   from datetime import datetime
   import uuid
   import hashlib
   
   from app.db.models import SharingEvent
   from app.models.cdm_events import generate_cdm_sharing_event
   from app.services.blockchain_service import BlockchainService
   
   class SharingEventService:
       """Service for creating blockchain-notarized sharing events."""
       
       def __init__(self, db: Session):
           self.db = db
           self.blockchain_service = BlockchainService()
       
       def create_send_event(
           self,
           sender_user_id: int,
           sharing_method: str,  # nexus_file, link, p2p
           file_data: bytes,  # .nexus file or link payload
           workflow_id: Optional[str] = None,
           deal_id: Optional[int] = None,
           document_id: Optional[int] = None,
           receiver_user_id: Optional[int] = None,
           receiver_email: Optional[str] = None,
           receiver_wallet_address: Optional[str] = None,
           metadata: Optional[Dict[str, Any]] = None,
       ) -> SharingEvent:
           """Create send event and notarize on blockchain.
           
           Args:
               sender_user_id: Sender user ID
               sharing_method: Method used (nexus_file, link, p2p)
               file_data: File data or link payload
               workflow_id: Optional workflow ID
               deal_id: Optional deal ID
               document_id: Optional document ID
               receiver_user_id: Optional receiver user ID
               receiver_email: Optional receiver email
               receiver_wallet_address: Optional receiver wallet
               metadata: Optional metadata
               
           Returns:
               Created SharingEvent with blockchain notarization
           """
           event_id = str(uuid.uuid4())
           file_hash = hashlib.sha256(file_data).hexdigest()
           file_size = len(file_data)
           
           # Count files (if .nexus file, parse manifest)
           files_included = 0
           if sharing_method == "nexus_file":
               try:
                   from app.utils.nexus_file_parser import NexusFileParser
                   parser = NexusFileParser()
                   parsed = parser.parse_nexus_file(file_data)
                   files_included = len(parsed.get('embedded_files', {})) + len(parsed.get('large_file_references', []))
               except Exception as e:
                   logger.warning(f"Failed to parse .nexus file for file count: {e}")
           
           # Create sharing event
           sharing_event = SharingEvent(
               event_id=event_id,
               event_type="send",
               sharing_method=sharing_method,
               workflow_id=workflow_id,
               deal_id=deal_id,
               document_id=document_id,
               sender_user_id=sender_user_id,
               receiver_user_id=receiver_user_id,
               receiver_email=receiver_email,
               receiver_wallet_address=receiver_wallet_address,
               file_hash=file_hash,
               file_size=file_size,
               files_included=files_included,
               metadata=metadata or {},
           )
           
           self.db.add(sharing_event)
           self.db.flush()
           
           # Generate CDM event
           cdm_event = generate_cdm_sharing_event(
               event_id=event_id,
               event_type="send",
               sender_user_id=sender_user_id,
               receiver_user_id=receiver_user_id,
               receiver_email=receiver_email,
               receiver_wallet_address=receiver_wallet_address,
               file_hash=file_hash,
               workflow_id=workflow_id,
               deal_id=str(deal_id) if deal_id else None,
           )
           
           sharing_event.cdm_event = cdm_event
           
           # Notarize on blockchain
           try:
               tx_hash, block_number = self.blockchain_service.notarize_sharing_event(
                   event_id=event_id,
                   file_hash=file_hash,
                   sender_address=sender_user_id,  # Would need wallet address
                   receiver_address=receiver_wallet_address,
               )
               
               sharing_event.blockchain_tx_hash = tx_hash
               sharing_event.blockchain_block_number = block_number
               sharing_event.notarized_at = datetime.utcnow()
           except Exception as e:
               logger.error(f"Failed to notarize sharing event on blockchain: {e}")
           
           self.db.commit()
           self.db.refresh(sharing_event)
           
           return sharing_event
       
       def create_receive_event(
           self,
           receiver_user_id: int,
           sharing_method: str,
           file_data: bytes,
           file_hash: str,
           sender_user_id: Optional[int] = None,
           sender_email: Optional[str] = None,
           sender_wallet_address: Optional[str] = None,
           workflow_id: Optional[str] = None,
           deal_id: Optional[int] = None,
           metadata: Optional[Dict[str, Any]] = None,
       ) -> SharingEvent:
           """Create receive event and notarize on blockchain."""
           event_id = str(uuid.uuid4())
           
           sharing_event = SharingEvent(
               event_id=event_id,
               event_type="receive",
               sharing_method=sharing_method,
               workflow_id=workflow_id,
               deal_id=deal_id,
               receiver_user_id=receiver_user_id,
               sender_user_id=sender_user_id,
               receiver_email=None,  # Receiver is current user
               file_hash=file_hash,
               file_size=len(file_data),
               metadata=metadata or {},
           )
           
           self.db.add(sharing_event)
           self.db.flush()
           
           # Generate CDM event
           cdm_event = generate_cdm_sharing_event(
               event_id=event_id,
               event_type="receive",
               sender_user_id=sender_user_id,
               receiver_user_id=receiver_user_id,
               receiver_email=None,
               receiver_wallet_address=None,
               file_hash=file_hash,
               workflow_id=workflow_id,
               deal_id=str(deal_id) if deal_id else None,
           )
           
           sharing_event.cdm_event = cdm_event
           
           # Notarize on blockchain
           try:
               tx_hash, block_number = self.blockchain_service.notarize_sharing_event(
                   event_id=event_id,
                   file_hash=file_hash,
                   sender_address=sender_wallet_address,
                   receiver_address=receiver_user_id,  # Would need wallet address
               )
               
               sharing_event.blockchain_tx_hash = tx_hash
               sharing_event.blockchain_block_number = block_number
               sharing_event.notarized_at = datetime.utcnow()
           except Exception as e:
               logger.error(f"Failed to notarize receive event on blockchain: {e}")
           
           self.db.commit()
           self.db.refresh(sharing_event)
           
           return sharing_event
   ```

**Code Reference**: See `app/services/sharing_event_service.py` (NEW)

#### Task 4.3: CDM Sharing Event Generator

**File**: `app/models/cdm_events.py` (UPDATE)

**Lines**: Find end of file, add new function

**Subtasks**:
1. **Add generate_cdm_sharing_event function**:
   ```python
   def generate_cdm_sharing_event(
       event_id: str,
       event_type: str,  # "send" or "receive"
       sender_user_id: Optional[int],
       receiver_user_id: Optional[int],
       receiver_email: Optional[str],
       receiver_wallet_address: Optional[str],
       file_hash: str,
       workflow_id: Optional[str] = None,
       deal_id: Optional[str] = None,
       blockchain_tx_hash: Optional[str] = None,
   ) -> Dict[str, Any]:
       """Generate CDM-compliant Sharing event.
       
       Args:
           event_id: Sharing event ID
           event_type: "send" or "receive"
           sender_user_id: Sender user ID
           receiver_user_id: Receiver user ID
           receiver_email: Receiver email
           receiver_wallet_address: Receiver wallet address
           file_hash: SHA-256 hash of shared file
           workflow_id: Optional workflow ID
           deal_id: Optional deal ID
           blockchain_tx_hash: Optional blockchain transaction hash
           
       Returns:
           CDM-compliant Sharing event dictionary
       """
       return {
           "eventType": "Sharing",
           "eventDate": datetime.datetime.now().isoformat(),
           "sharing": {
               "sharingIdentifier": {
                   "issuer": "CreditNexus_SharingService",
                   "assignedIdentifier": [{"identifier": {"value": f"SHARING_{event_id}"}}]
               },
               "eventType": event_type,  # send or receive
               "senderPartyReference": {
                   "globalReference": str(sender_user_id) if sender_user_id else None
               },
               "receiverPartyReference": {
                   "globalReference": str(receiver_user_id) if receiver_user_id else None,
                   "email": receiver_email,
                   "walletAddress": receiver_wallet_address,
               },
               "fileHash": file_hash,
               "workflowIdentifier": {
                   "assignedIdentifier": [{"identifier": {"value": workflow_id}}]
               } if workflow_id else None,
               "dealIdentifier": {
                   "assignedIdentifier": [{"identifier": {"value": deal_id}}]
               } if deal_id else None,
               "blockchainTransactionHash": blockchain_tx_hash,
               "sharingDate": {"date": datetime.date.today().isoformat()}
           },
           "meta": {
               "globalKey": str(uuid.uuid4()),
               "sourceSystem": "CreditNexus_SharingService_v1",
               "version": 1
           }
       }
   ```

**Code Reference**: See `app/models/cdm_events.py`

---

### Project 5: API Endpoints for .nexus Files

**Objective**: Create API endpoints for generating, uploading, and parsing .nexus files.

#### Task 5.1: Nexus File Generation Endpoint

**File**: `app/api/nexus_routes.py` (NEW)

**Lines**: 1-300

**Subtasks**:
1. **Create nexus file generation endpoint**:
   ```python
   from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
   from fastapi.responses import Response
   from sqlalchemy.orm import Session
   from typing import Optional, List
   from pydantic import BaseModel, Field
   
   from app.db import get_db
   from app.auth.jwt_auth import get_current_user
   from app.db.models import User
   from app.utils.nexus_file_generator import NexusFileGenerator
   from app.services.workflow_delegation_service import WorkflowDelegationService
   from app.services.permission_key_service import PermissionKeyService
   from app.services.sharing_event_service import SharingEventService
   
   router = APIRouter(prefix="/api/nexus", tags=["nexus"])
   
   class GenerateNexusFileRequest(BaseModel):
       """Request to generate .nexus file."""
       workflow_type: str = Field(..., description="Workflow type")
       deal_id: Optional[int] = Field(None, description="Deal ID")
       document_id: Optional[int] = Field(None, description="Document ID")
       workflow_metadata: Optional[dict] = Field(None, description="Workflow metadata")
       file_categories: Optional[List[str]] = Field(None, description="File categories to include")
       file_document_ids: Optional[List[int]] = Field(None, description="Specific document IDs")
       receiver_email: Optional[str] = Field(None, description="Receiver email")
       receiver_wallet_address: Optional[str] = Field(None, description="Receiver wallet address")
       permission_keys: Optional[dict] = Field(None, description="Permission keys to include")
       expires_in_hours: int = Field(72, description="Link expiration in hours")
       download_ttl_hours: Optional[int] = Field(None, description="Download TTL in hours")
       include_files: bool = Field(True, description="Whether to embed files")
       max_embedded_size: int = Field(10 * 1024 * 1024, description="Max size for embedded files")
   
   @router.post("/generate")
   async def generate_nexus_file(
       request: GenerateNexusFileRequest,
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user),
   ):
       """Generate .nexus file for sharing.
       
       Returns:
           .nexus file as download
       """
       from app.services.workflow_delegation_service import WorkflowDelegationService
       from app.services.cdm_payload_generator import get_deal_cdm_payload
       from app.db.models import Deal, Document
       
       # Get deal data if deal_id provided
       deal_data = {}
       cdm_payload = {}
       if request.deal_id:
           deal = db.query(Deal).filter(Deal.id == request.deal_id).first()
           if not deal:
               raise HTTPException(status_code=404, detail="Deal not found")
           
           deal_data = {
               "deal_id": deal.deal_id,
               "status": deal.status,
               "deal_type": deal.deal_type,
               "deal_data": deal.deal_data or {},
           }
           cdm_payload = get_deal_cdm_payload(db, deal)
       
       # Get file references
       file_references = []
       if request.include_files and request.deal_id:
           delegation_service = WorkflowDelegationService(db)
           file_references = delegation_service._get_file_references(
               deal_id=request.deal_id,
               file_categories=request.file_categories,
               file_document_ids=request.file_document_ids,
           )
       
       # Get sender info
       sender_info = {
           "user_id": current_user.id,
           "email": current_user.email,
           "name": current_user.display_name,
           "organization": current_user.organization_id,
       }
       
       # Get receiver info
       receiver_info = {}
       if request.receiver_email:
           receiver_info["email"] = request.receiver_email
       if request.receiver_wallet_address:
           receiver_info["wallet_address"] = request.receiver_wallet_address
       
       # Generate .nexus file
       generator = NexusFileGenerator()
       nexus_bytes = generator.generate_nexus_file(
           workflow_type=request.workflow_type,
           workflow_id=str(uuid.uuid4()),
           deal_id=request.deal_id,
           deal_data=deal_data,
           cdm_payload=cdm_payload,
           workflow_metadata=request.workflow_metadata,
           file_references=file_references,
           sender_info=sender_info,
           receiver_info=receiver_info,
           permission_keys=request.permission_keys,
           expires_in_hours=request.expires_in_hours,
           download_ttl_hours=request.download_ttl_hours,
           include_files=request.include_files,
           max_embedded_size=request.max_embedded_size,
       )
       
       # Create send event and notarize
       sharing_service = SharingEventService(db)
       sharing_event = sharing_service.create_send_event(
           sender_user_id=current_user.id,
           sharing_method="nexus_file",
           file_data=nexus_bytes,
           workflow_id=None,  # Would be generated
           deal_id=request.deal_id,
           receiver_email=request.receiver_email,
           receiver_wallet_address=request.receiver_wallet_address,
       )
       
       # Return .nexus file
       filename = f"deal_share_{request.deal_id or 'workflow'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.nexus"
       return Response(
           content=nexus_bytes,
           media_type="application/octet-stream",
           headers={
               "Content-Disposition": f'attachment; filename="{filename}"',
               "X-Sharing-Event-Id": sharing_event.event_id,
               "X-Blockchain-Tx-Hash": sharing_event.blockchain_tx_hash or "",
           }
       )
   ```

**Code Reference**: See `app/api/nexus_routes.py` (NEW)

#### Task 5.2: Nexus File Upload/Parse Endpoint

**File**: `app/api/nexus_routes.py` (UPDATE)

**Lines**: 300-500

**Subtasks**:
1. **Create nexus file upload endpoint**:
   ```python
   @router.post("/upload")
   async def upload_nexus_file(
       file: UploadFile = File(...),
       db: Session = Depends(get_db),
       current_user: User = Depends(get_current_user),
   ):
       """Upload and parse .nexus file.
       
       Returns:
           Parsed workflow data
       """
       from app.utils.nexus_file_parser import NexusFileParser
       from app.services.sharing_event_service import SharingEventService
       from app.services.workflow_delegation_service import WorkflowDelegationService
       
       # Read file
       file_bytes = await file.read()
       
       # Parse .nexus file
       parser = NexusFileParser()
       parsed_data = parser.parse_nexus_file(file_bytes)
       
       # Verify permissions if provided
       permissions = parsed_data.get('permissions')
       if permissions:
           permission_service = PermissionKeyService(db)
           # Verify wallet or application key
           # ...
       
       # Process workflow
       delegation_service = WorkflowDelegationService(db)
       workflow_data = delegation_service.process_workflow_link(
           encrypted_payload=None,  # Not a link, but parsed data
           receiver_user_id=current_user.id,
       )
       
       # Store embedded files
       embedded_files = parsed_data.get('embedded_files', {})
       for filename, file_info in embedded_files.items():
           # Store file using FileStorageService
           # ...
       
       # Download large files if TTL not expired
       large_file_references = parsed_data.get('large_file_references', [])
       for file_ref in large_file_references:
           download_ttl = file_ref.get('download_ttl')
           if download_ttl:
               ttl_dt = datetime.fromisoformat(download_ttl)
               if datetime.utcnow() > ttl_dt:
                   logger.warning(f"Download TTL expired for {file_ref['filename']}")
                   continue
           
           # Download file
           # ...
       
       # Create receive event and notarize
       sharing_service = SharingEventService(db)
       file_hash = hashlib.sha256(file_bytes).hexdigest()
       receive_event = sharing_service.create_receive_event(
           receiver_user_id=current_user.id,
           sharing_method="nexus_file",
           file_data=file_bytes,
           file_hash=file_hash,
           workflow_id=parsed_data['metadata'].get('workflow_id'),
           deal_id=parsed_data['metadata'].get('deal_id'),
       )
       
       return {
           "status": "success",
           "workflow_data": workflow_data,
           "files_processed": len(embedded_files) + len(large_file_references),
           "receive_event_id": receive_event.event_id,
           "blockchain_tx_hash": receive_event.blockchain_tx_hash,
       }
   ```

**Code Reference**: See `app/api/nexus_routes.py`

---

### Project 6: Frontend Integration

**Objective**: Create frontend components for .nexus file generation, upload, and parsing.

#### Task 6.1: Nexus File Generator UI

**File**: `client/src/components/NexusFileGenerator.tsx` (NEW)

**Subtasks**:
1. **Create NexusFileGenerator component**:
   ```typescript
   import { useState } from 'react';
   import { Button } from '@/components/ui/button';
   import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
   import { Input } from '@/components/ui/input';
   import { Label } from '@/components/ui/label';
   import { Download, Upload, FileText } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   
   export function NexusFileGenerator({
     dealId,
     documentId,
     onFileGenerated,
   }: {
     dealId?: number;
     documentId?: number;
     onFileGenerated?: (filename: string) => void;
   }) {
     const [generating, setGenerating] = useState(false);
     const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
     const [filename, setFilename] = useState<string | null>(null);
     
     const handleGenerate = async () => {
       setGenerating(true);
       try {
         const response = await fetchWithAuth('/api/nexus/generate', {
           method: 'POST',
           headers: { 'Content-Type': 'application/json' },
           body: JSON.stringify({
             workflow_type: 'verification',
             deal_id: dealId,
             document_id: documentId,
             include_files: true,
             download_ttl_hours: 168,  // 7 days
           }),
         });
         
         if (response.ok) {
           const blob = await response.blob();
           const url = URL.createObjectURL(blob);
           const contentDisposition = response.headers.get('Content-Disposition');
           const extractedFilename = contentDisposition
             ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
             : `deal_share_${Date.now()}.nexus`;
           
           setDownloadUrl(url);
           setFilename(extractedFilename);
           onFileGenerated?.(extractedFilename);
         }
       } catch (err) {
         console.error('Failed to generate .nexus file:', err);
       } finally {
         setGenerating(false);
       }
     };
     
     const handleDownload = () => {
       if (downloadUrl && filename) {
         const a = document.createElement('a');
         a.href = downloadUrl;
         a.download = filename;
         a.click();
       }
     };
     
     return (
       <Card>
         <CardHeader>
           <CardTitle>Generate .nexus File</CardTitle>
         </CardHeader>
         <CardContent>
           <Button onClick={handleGenerate} disabled={generating}>
             {generating ? 'Generating...' : 'Generate .nexus File'}
           </Button>
           {downloadUrl && (
             <Button onClick={handleDownload} variant="outline">
               <Download className="h-4 w-4 mr-2" />
               Download {filename}
             </Button>
           )}
         </CardContent>
       </Card>
     );
   }
   ```

**Code Reference**: See `client/src/components/NexusFileGenerator.tsx` (NEW)

#### Task 6.2: Nexus File Upload UI

**File**: `client/src/components/NexusFileUploader.tsx` (NEW)

**Subtasks**:
1. **Create NexusFileUploader component**:
   ```typescript
   import { useState } from 'react';
   import { Button } from '@/components/ui/button';
   import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
   import { Upload, FileText, Check } from 'lucide-react';
   import { fetchWithAuth } from '@/context/AuthContext';
   
   export function NexusFileUploader({
     onFileParsed,
   }: {
     onFileParsed?: (data: any) => void;
   }) {
     const [uploading, setUploading] = useState(false);
     const [uploaded, setUploaded] = useState(false);
     
     const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
       const file = event.target.files?.[0];
       if (!file || !file.name.endsWith('.nexus')) {
         alert('Please select a .nexus file');
         return;
       }
       
       setUploading(true);
       try {
         const formData = new FormData();
         formData.append('file', file);
         
         const response = await fetchWithAuth('/api/nexus/upload', {
           method: 'POST',
           body: formData,
         });
         
         if (response.ok) {
           const data = await response.json();
           setUploaded(true);
           onFileParsed?.(data);
         }
       } catch (err) {
         console.error('Failed to upload .nexus file:', err);
       } finally {
         setUploading(false);
       }
     };
     
     return (
       <Card>
         <CardHeader>
           <CardTitle>Upload .nexus File</CardTitle>
         </CardHeader>
         <CardContent>
           <input
             type="file"
             accept=".nexus"
             onChange={handleUpload}
             disabled={uploading}
           />
           {uploaded && (
             <div className="flex items-center gap-2 text-green-600">
               <Check className="h-4 w-4" />
               File uploaded and processed successfully
             </div>
           )}
         </CardContent>
       </Card>
     );
   }
   ```

**Code Reference**: See `client/src/components/NexusFileUploader.tsx` (NEW)

---

## Implementation Checklist

### Phase 1: File Format & Parsing (Weeks 1-3)
- [ ] Define .nexus file format specification
- [ ] Create `NexusFileGenerator` class
- [ ] Create `NexusFileParser` class
- [ ] Implement file embedding (<10MB) and referencing (>10MB)
- [ ] Add checksum verification
- [ ] Test file generation and parsing

### Phase 2: Permission Keys (Weeks 4-5)
- [ ] Create `PermissionKey` database model
- [ ] Create `PermissionKeyService`
- [ ] Implement wallet key creation/verification
- [ ] Implement application key creation/verification
- [ ] Integrate with .nexus file generation
- [ ] Test permission key system

### Phase 3: P2P Connectivity (Weeks 6-7)
- [ ] Create `P2PConnectionService`
- [ ] Implement WebSocket P2P handler
- [ ] Add WebRTC support (optional, if aiortc available)
- [ ] Create P2P API endpoints
- [ ] Test P2P file transfer

### Phase 4: Blockchain Notarization (Week 8)
- [ ] Create `SharingEvent` database model
- [ ] Create `SharingEventService`
- [ ] Add `generate_cdm_sharing_event` function
- [ ] Integrate with blockchain service
- [ ] Test send/receive event notarization

### Phase 5: API Endpoints (Week 9)
- [ ] Create `/api/nexus/generate` endpoint
- [ ] Create `/api/nexus/upload` endpoint
- [ ] Add permission key verification
- [ ] Add download TTL checking
- [ ] Test API endpoints

### Phase 6: Frontend Integration (Week 10)
- [ ] Create `NexusFileGenerator` component
- [ ] Create `NexusFileUploader` component
- [ ] Integrate with workflow sharing UI
- [ ] Add permission key UI
- [ ] Test frontend integration

### Phase 7: Testing & Documentation (Weeks 11-12)
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Document .nexus file format
- [ ] Create user guide
- [ ] Performance testing

---

## Success Criteria

1. ✅ `.nexus` files can be generated with embedded metadata and files
2. ✅ `.nexus` files can be parsed and processed offline
3. ✅ Permission keys (wallet, application) can be created and verified
4. ✅ Download TTL is enforced separately from link expiration
5. ✅ P2P connectivity works (WebSocket, optional WebRTC)
6. ✅ Blockchain notarization events are created for send/receive
7. ✅ Large files (>10MB) are referenced, not embedded
8. ✅ Small files (<10MB) are embedded in .nexus file
9. ✅ Whitelist configuration is supported
10. ✅ Frontend UI is integrated and functional

---

## Related Plans

- **`WORKFLOW_DELEGATION_PLAN.md`** - Existing workflow delegation system
- **`WHITELISTING_DASHBOARD_PLAN.md`** - Whitelist configuration
- **`AUDIT_TRACEABILITY_PLAN.md`** - Audit logging for sharing events
- **`REMOTE_VERIFICATION_IMPLEMENTATION_PLAN.md`** - Remote API integration

---

## Blockchain Integration Details

### Sharing Event Notarization

**Smart Contract**: Extend `SecuritizationNotarization.sol` or create new `SharingNotarization.sol`

**Contract Methods**:
```solidity
function notarizeSharingEvent(
    string memory eventId,
    bytes32 fileHash,
    address sender,
    address receiver,
    string memory workflowId
) external returns (bytes32 txHash) {
    // Store sharing event on-chain
    // Emit SharingEventNotarized event
    // Return transaction hash
}
```

**Service Integration**:
```python
# In BlockchainService
def notarize_sharing_event(
    self,
    event_id: str,
    file_hash: str,
    sender_address: str,
    receiver_address: Optional[str],
) -> Tuple[str, int]:
    """Notarize sharing event on blockchain.
    
    Returns:
        (transaction_hash, block_number)
    """
    # Call smart contract
    # Return tx hash and block number
```

---

## Integration with Existing Systems

### Workflow Delegation Service Integration

**File**: `app/services/workflow_delegation_service.py` (UPDATE)

**Changes**:
1. Add method to generate .nexus file instead of link:
   ```python
   def delegate_workflow_as_nexus_file(
       self,
       workflow_type: str,
       deal_id: int,
       sender_user_id: int,
       # ... other params
   ) -> bytes:
       """Delegate workflow as .nexus file instead of link."""
       # Use NexusFileGenerator
       # Return .nexus file bytes
   ```

### File Storage Service Integration

**File**: `app/services/file_storage_service.py` (UPDATE)

**Changes**:
1. Add method to get file content for embedding:
   ```python
   def get_file_content(
       self,
       user_id: int,
       deal_id: str,
       filename: str,
       subdirectory: str,
   ) -> Optional[bytes]:
       """Get file content as bytes for embedding."""
       # Read file from storage
       # Return bytes
   ```

### Remote Routes Integration

**File**: `app/api/remote_routes.py` (UPDATE)

**Changes**:
1. Add endpoint to generate .nexus file:
   ```python
   @remote_router.post("/verification/{verification_id}/generate-nexus")
   async def generate_nexus_file(
       verification_id: str,
       request: GenerateNexusFileRequest,
       # ...
   ):
       """Generate .nexus file instead of link."""
   ```

---

## Workflow Sharing Assessment

### Current Workflow Sharing Capabilities

**✅ Strengths**:
1. **Self-Contained Links**: Encrypted payloads contain all necessary data
2. **Multiple Workflow Types**: Verification, notarization, document review, deal approval
3. **File References**: Can include file metadata and download URLs
4. **Whitelist Support**: Whitelist configuration can be included
5. **State Synchronization**: Callback mechanism for state updates
6. **FDC3 Integration**: Desktop app integration for workflow links

**❌ Weaknesses**:
1. **Server Dependency**: Requires sender's server to be accessible
2. **No Offline Support**: Cannot process links without server
3. **No File Embedding**: Files are always referenced, never embedded
4. **No Permission Keys**: Cannot unlock permissions for shared content
5. **No Download TTL**: Single expiration for link and files
6. **No Blockchain Events**: No notarization for sharing activities
7. **No P2P**: All sharing goes through servers

### Proposed Improvements

1. **.nexus File Format**: Self-contained files that work offline
2. **File Embedding**: Small files embedded, large files referenced
3. **Permission Keys**: Wallet/app keys for access control
4. **Download TTL**: Separate expiration for file downloads
5. **Blockchain Notarization**: Send/receive events on-chain
6. **P2P Connectivity**: Direct client-to-client transfer when possible

---

## Connection Issues Analysis

### Issue 1: Download URL Accessibility

**Problem**: 
- Download URLs point to sender's server (`/api/deals/{deal_id}/files/{filename}`)
- If sender's server is down, receiver cannot download files
- URLs may require authentication

**Root Cause**:
- `app/api/remote_routes.py` line 283: `download_url = f"/api/deals/{deal.id}/files/{latest_version.source_filename}"`
- Relative URLs require server to be accessible
- File download endpoints require JWT authentication

**Solution**:
1. **Embed Small Files**: Files <10MB embedded in .nexus file
2. **P2P for Large Files**: Use WebRTC/WebSocket for direct transfer
3. **Permission Keys**: Unlock access without server authentication
4. **Download TTL**: Time-limited download URLs with permission keys

### Issue 2: Authentication Barriers

**Problem**:
- File download endpoints require JWT tokens
- Receiver may not have valid credentials for sender's server

**Root Cause**:
- `app/api/routes.py` file download endpoints use `Depends(get_current_user)`
- No mechanism to share temporary access tokens

**Solution**:
1. **Permission Keys**: Encrypted keys in .nexus file unlock access
2. **Temporary Tokens**: Generate time-limited tokens for file downloads
3. **Public Download URLs**: Optional public URLs with permission key validation

### Issue 3: Connection Creation Failures

**Problem**:
- P2P connections may fail due to NAT/firewall
- WebSocket connections require server availability

**Root Cause**:
- No P2P implementation exists
- All connections go through servers

**Solution**:
1. **WebRTC with STUN/TURN**: Direct P2P when possible
2. **WebSocket Fallback**: Server-mediated transfer when P2P fails
3. **Hybrid Approach**: Try P2P first, fallback to server download

---

## Dependencies

### Python Dependencies

**File**: `pyproject.toml` (UPDATE)

**Add**:
```toml
# P2P Connectivity
"aiortc>=1.6.0",  # WebRTC support (optional)
"websockets>=12.0",  # WebSocket support
```

### Frontend Dependencies

**File**: `client/package.json` (UPDATE)

**Add**:
```json
{
  "simple-peer": "^9.11.1",
  "ws": "^8.16.0"
}
```

---

## Testing Strategy

### Unit Tests

**File**: `tests/test_nexus_file_generator.py` (NEW)

**Test Cases**:
1. Generate .nexus file with embedded files
2. Generate .nexus file with file references
3. Parse .nexus file and extract metadata
4. Verify checksums
5. Test expiration and download TTL

### Integration Tests

**File**: `tests/test_nexus_sharing.py` (NEW)

**Test Cases**:
1. Generate .nexus file → Upload → Parse workflow
2. Permission key creation and verification
3. Blockchain notarization for send/receive
4. P2P file transfer (WebSocket)
5. Download TTL enforcement

---

## Migration Path

### Phase 1: Backward Compatibility

1. **Support Both Formats**: 
   - Keep existing link format working
   - Add .nexus file format as alternative
   - Auto-detect format when processing

2. **Gradual Migration**:
   - Update UI to offer both options
   - Default to .nexus for new shares
   - Support legacy links indefinitely

### Phase 2: Enhanced Features

1. **Permission Keys**: 
   - Add to existing link format (optional)
   - Required for .nexus files

2. **Download TTL**:
   - Add to existing link format
   - Enforce in .nexus files

3. **Blockchain Events**:
   - Add to all sharing methods
   - Notarize send/receive for both formats

---

## Security Considerations

1. **Encryption**: All metadata encrypted with Fernet (shared key)
2. **Permission Keys**: Encrypted with recipient's public key or shared secret
3. **File Integrity**: SHA-256 checksums for all files
4. **Expiration**: Link expiration and download TTL enforced
5. **Blockchain Verification**: Send/receive events notarized on-chain
6. **Access Control**: Permission keys required for file access

---

## Performance Considerations

1. **File Size Limits**: 
   - Embed files <10MB
   - Reference files >10MB
   - Configurable threshold

2. **P2P Transfer**:
   - WebRTC for direct transfer (faster)
   - WebSocket fallback (slower but reliable)

3. **Caching**:
   - Cache parsed .nexus files
   - Cache permission key verifications

---

**Last Updated**: 2024-12-XX  
**Status**: Planning  
**Version**: 1.0
