# .nexus File Format Specification

**Version**: 1.0  
**Last Updated**: 2024-12-XX  
**Status**: Draft

## Overview

The `.nexus` file format is a self-contained, encrypted ZIP-based archive designed for CreditNexus-to-CreditNexus sharing. It enables offline file sharing, embedded metadata, permission keys, and blockchain-verified send/receive events.

## File Structure

```
deal_share_2024_001.nexus
├── META-INF/
│   ├── manifest.json          # File manifest with checksums
│   ├── metadata.json          # Encrypted workflow metadata
│   ├── permissions.json       # Permission keys (encrypted)
│   └── whitelist.json         # Whitelist configuration (optional)
├── files/
│   ├── document_1.pdf          # Embedded files (<10MB)
│   ├── document_2.docx
│   └── ...
├── references/
│   └── large_files.json       # References to large files (>10MB)
└── signature.nexus            # Digital signature (optional, future)
```

## Manifest Structure

The `META-INF/manifest.json` file contains the file manifest with checksums and metadata.

```json
{
  "version": "1.0",
  "format": "nexus",
  "created_at": "2024-12-XXT00:00:00Z",
  "created_by": {
    "user_id": 123,
    "email": "sender@example.com",
    "name": "John Doe",
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
      "checksum": "sha256:abc123...",
      "embedded": true
    }
  ],
  "references": [
    {
      "filename": "large_file.pdf",
      "size": 50000000,
      "download_url": "https://...",
      "download_ttl": "2024-12-XXT00:00:00Z",
      "checksum": "sha256:def456...",
      "embedded": false
    }
  ],
  "metadata_encryption": {
    "algorithm": "fernet",
    "key_id": "shared-key"
  }
}
```

### Manifest Fields

- **version**: Manifest format version (currently "1.0")
- **format**: File format identifier ("nexus")
- **created_at**: ISO 8601 timestamp of file creation
- **created_by**: Sender information (user_id, email, name, organization)
- **workflow_type**: Type of workflow (verification, notarization, document_review, etc.)
- **workflow_id**: Unique workflow identifier (UUID)
- **files**: Array of embedded file metadata
  - **path**: Path within ZIP archive
  - **filename**: Original filename
  - **size**: File size in bytes
  - **category**: File category (legal, financial, compliance, etc.)
  - **checksum**: SHA-256 checksum (format: "sha256:hexdigest")
  - **embedded**: Always `true` for embedded files
- **references**: Array of large file references
  - **filename**: Original filename
  - **size**: File size in bytes
  - **download_url**: URL to download file (may require permission keys)
  - **download_ttl**: ISO 8601 timestamp when download URL expires
  - **checksum**: SHA-256 checksum
  - **embedded**: Always `false` for referenced files
- **metadata_encryption**: Encryption algorithm information

## Metadata Structure (Encrypted)

The `META-INF/metadata.json` file contains encrypted workflow metadata.

**Before Encryption**:
```json
{
  "version": "3.0",
  "workflow_type": "verification",
  "workflow_id": "uuid",
  "deal_id": 123,
  "deal_data": {
    "deal_id": "DEAL-2024-001",
    "status": "pending",
    "deal_type": "credit_facility",
    "deal_data": {}
  },
  "cdm_payload": {
    "eventType": "Verification",
    ...
  },
  "workflow_metadata": {
    "title": "Deal Verification",
    "description": "Please verify this deal",
    "instructions": [],
    "deadline": "2024-12-XXT00:00:00Z",
    "priority": "medium",
    "required_actions": ["accept", "decline"],
    "allowed_actions": ["view", "download", "comment"]
  },
  "sender_info": {
    "user_id": 123,
    "email": "sender@example.com",
    "name": "John Doe",
    "organization": "Bank A"
  },
  "receiver_info": {
    "email": "receiver@example.com",
    "wallet_address": "0x...",
    "required_role": "verifier"
  },
  "whitelist_config": {
    "enabled_categories": ["legal", "financial"],
    "file_types": {...},
    "categories": {...}
  },
  "expires_at": "2024-12-XXT00:00:00Z",
  "download_ttl": "2024-12-XXT00:00:00Z",
  "created_at": "2024-12-XXT00:00:00Z"
}
```

**After Encryption**: Base64url-encoded Fernet-encrypted JSON string

### Metadata Fields

- **version**: Payload version (currently "3.0", matches workflow link payload)
- **workflow_type**: Type of workflow
- **workflow_id**: Unique workflow identifier
- **deal_id**: Optional deal database ID
- **deal_data**: Optional deal information
- **cdm_payload**: Optional full CDM event payload
- **workflow_metadata**: Workflow-specific metadata (title, description, instructions, deadline, priority, required_actions, allowed_actions)
- **sender_info**: Sender metadata (user_id, email, name, organization)
- **receiver_info**: Receiver metadata (email, wallet_address, required_role)
- **whitelist_config**: Optional whitelist configuration
- **expires_at**: ISO 8601 timestamp when link expires
- **download_ttl**: ISO 8601 timestamp when download URLs expire (separate from link expiration)
- **created_at**: ISO 8601 timestamp of creation

## Permissions Structure (Encrypted)

The `META-INF/permissions.json` file contains encrypted permission keys.

**Before Encryption**:
```json
{
  "wallet_keys": [
    {
      "wallet_address": "0x1234...",
      "permissions": ["view", "download", "sign"],
      "encrypted_key": "fernet-encrypted-key-data"
    }
  ],
  "application_keys": [
    {
      "key_id": "app-key-uuid",
      "permissions": ["view", "download"],
      "encrypted_key": "fernet-encrypted-key-data",
      "organization_id": 456
    }
  ],
  "whitelist_keys": [
    {
      "whitelist_id": "whitelist-uuid",
      "permissions": ["view"],
      "encrypted_key": "fernet-encrypted-key-data"
    }
  ]
}
```

**After Encryption**: Base64url-encoded Fernet-encrypted JSON string

### Permission Key Types

1. **Wallet Keys**: Ethereum wallet address-based permissions
   - **wallet_address**: Ethereum wallet address (lowercase)
   - **permissions**: Array of permission strings (view, download, sign, edit)
   - **encrypted_key**: Encrypted key data for unlocking access

2. **Application Keys**: Application API key-based permissions
   - **key_id**: Application key identifier (UUID)
   - **permissions**: Array of permission strings
   - **encrypted_key**: Encrypted key data
   - **organization_id**: Optional organization ID

3. **Whitelist Keys**: Whitelist entry-based permissions
   - **whitelist_id**: Whitelist identifier (UUID)
   - **permissions**: Array of permission strings
   - **encrypted_key**: Encrypted key data

## File Embedding Rules

### Small Files (<10MB)
- **Embedded**: Files smaller than 10MB are embedded directly in the `.nexus` file
- **Location**: Stored in `files/` directory within ZIP
- **Checksum**: SHA-256 checksum included in manifest
- **Verification**: Checksum verified when parsing

### Large Files (>10MB)
- **Referenced**: Files larger than 10MB are referenced, not embedded
- **Location**: Stored in `references/large_files.json`
- **Download URL**: URL to download file (may require permission keys)
- **Download TTL**: Separate expiration for download URLs
- **Checksum**: SHA-256 checksum included in reference

### Configurable Threshold
- Default: 10MB (10 * 1024 * 1024 bytes)
- Configurable via `max_embedded_size` parameter

## Encryption

### Metadata Encryption
- **Algorithm**: Fernet (symmetric encryption)
- **Key**: Shared encryption key (from `LINK_ENCRYPTION_KEY` setting)
- **Encoding**: Base64url encoding for URL-safe storage
- **Format**: Encrypted JSON string

### Permission Key Encryption
- **Algorithm**: Fernet (symmetric encryption)
- **Key**: Shared encryption key (same as metadata)
- **Encoding**: Base64url encoding
- **Format**: Encrypted JSON string

## Expiration and TTL

### Link Expiration (`expires_at`)
- Controls when the entire `.nexus` file becomes invalid
- Stored in encrypted metadata
- Checked during parsing
- Default: 72 hours from creation

### Download TTL (`download_ttl`)
- Controls when download URLs for large files expire
- Separate from link expiration
- Stored in encrypted metadata and file references
- Checked when downloading large files
- Optional: Can be `null` if no TTL

## Checksum Verification

### File Checksums
- **Algorithm**: SHA-256
- **Format**: `sha256:hexdigest` (e.g., `sha256:abc123...`)
- **Verification**: Checksums verified when parsing embedded files
- **Mismatch**: Raises `ValueError` if checksum mismatch detected

## Whitelist Configuration

The `META-INF/whitelist.json` file (optional) contains whitelist configuration.

```json
{
  "enabled_categories": ["legal", "financial", "compliance"],
  "file_types": {
    "allowed_extensions": [".pdf", ".doc", ".docx", ".txt", ".json", ".xlsx", ".csv"],
    "max_file_size_mb": 50
  },
  "categories": {
    "legal": {
      "enabled": true,
      "required": true,
      "file_types": [".pdf", ".doc", ".docx"],
      "description": "Legal documents (agreements, contracts)"
    },
    "financial": {
      "enabled": true,
      "required": false,
      "file_types": [".pdf", ".xlsx", ".csv"],
      "description": "Financial statements and reports"
    }
  },
  "subdirectories": {
    "documents": {
      "enabled": true,
      "priority": 1,
      "description": "Main deal documents"
    }
  }
}
```

## Backward Compatibility

The `.nexus` file format is designed to work alongside existing link-based sharing:
- Links continue to work as before
- `.nexus` files can be generated from existing link payloads
- Both formats use the same encryption key and metadata structure
- Parsers can handle both formats

## Security Considerations

1. **Encryption**: All metadata and permission keys are encrypted
2. **Checksums**: File integrity verified via SHA-256 checksums
3. **Expiration**: Link expiration and download TTL enforced
4. **Permission Keys**: Required for accessing files and unlocking permissions
5. **Blockchain Verification**: Send/receive events can be notarized on blockchain

## Future Enhancements

1. **Digital Signatures**: Optional `signature.nexus` file for sender verification
2. **Compression**: Additional compression options for embedded files
3. **Streaming**: Support for streaming large files during generation
4. **Multi-part Files**: Support for splitting very large files across multiple `.nexus` files

---

**Related Documents**:
- `WORKFLOW_DELEGATION_PLAN.md` - Workflow delegation system
- `NEXUS_FILE_P2P_SHARING_PLAN.md` - Complete implementation plan
