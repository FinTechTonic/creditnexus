"""Encrypted SQLAlchemy types for transparent encryption at rest.

This module provides TypeDecorator classes that automatically encrypt/decrypt
data when storing/retrieving from the database. Uses EncryptionService for
actual encryption operations.

Supports:
- EncryptedString: For String columns (email, names, etc.)
- EncryptedText: For Text columns (large text fields like document content)
- EncryptedJSON: For JSONB columns (profile_data, cdm_events, etc.)

Grace Period Support:
- During migration, can handle both plain text and encrypted data
- Automatically detects format and handles accordingly
"""

import logging
import json
from typing import Optional, Any, Dict
from sqlalchemy import TypeDecorator, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import TypeEngine, TEXT

from app.services.encryption_service import get_encryption_service
from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptedString(TypeDecorator):
    """SQLAlchemy type that transparently encrypts/decrypts string values.
    
    Usage:
        email = Column(EncryptedString(255), nullable=False)
    
    The value is stored as encrypted bytes in the database but appears
    as plain text in Python code.
    """
    
    impl = String
    cache_ok = True
    
    def __init__(self, length: Optional[int] = None, **kwargs):
        """Initialize encrypted string type.
        
        Args:
            length: Maximum length of the string (before encryption)
            **kwargs: Additional arguments passed to String type
        """
        super().__init__(length=length, **kwargs)
        self._encryption_service = None
    
    def _get_encryption_service(self):
        """Lazy-load encryption service."""
        if self._encryption_service is None:
            self._encryption_service = get_encryption_service()
        return self._encryption_service
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt value before storing in database.
        
        Args:
            value: Plain text string to encrypt
            dialect: SQLAlchemy dialect (unused)
            
        Returns:
            Encrypted string (ASCII), or None if value is None
        """
        if value is None:
            return None
        
        if not settings.ENCRYPTION_ENABLED:
            # If encryption disabled, store as plain text (for development)
            return value
        
        try:
            encryption_service = self._get_encryption_service()
            encrypted = encryption_service.encrypt(value)
            
            if encrypted is None:
                # Encryption service returned None (disabled or error)
                logger.warning("Encryption service returned None, storing as plain text")
                return value
            
            # Fernet tokens are ASCII-safe base64, so we can store them as strings in VARCHAR/TEXT columns
            # This avoids "operator does not exist: character varying = bytea" errors
            return encrypted.decode('ascii')
        except Exception as e:
            logger.error(f"Failed to encrypt string value: {e}")
            # In production, this should raise; for now, log and store plain text
            # TODO: Make this configurable (fail-safe vs fail-secure)
            if settings.ENCRYPTION_ENABLED:
                raise ValueError(f"Encryption failed and ENCRYPTION_ENABLED=True: {e}")
            return value
    
    def process_result_value(self, value: Optional[Any], dialect) -> Optional[str]:
        """Decrypt value after retrieving from database.
        
        Args:
            value: Encrypted data from database (bytes or ASCII string)
            dialect: SQLAlchemy dialect (unused)
            
        Returns:
            Decrypted plain text string, or None if value is None
        """
        if value is None:
            return None
        
        if not settings.ENCRYPTION_ENABLED:
            # If encryption disabled, assume plain text
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8')
                except UnicodeDecodeError:
                    # Might be encrypted data from before encryption was disabled
                    pass
            elif isinstance(value, str):
                return value
            return value
        
        try:
            encryption_service = self._get_encryption_service()
            
            # If value is string, it might be an encrypted Fernet token or plain text
            if isinstance(value, str):
                if value.startswith('gAAAAA'):
                    try:
                        # Attempt to decrypt the string value
                        decrypted = encryption_service.decrypt(value.encode('ascii'))
                        if decrypted:
                            if isinstance(decrypted, bytes):
                                return decrypted.decode('utf-8')
                            return str(decrypted)
                    except Exception:
                        # If decryption fails, it might be plain text that happens to start with gAAAAA
                        pass
                return value
            
            # Try to decrypt bytes directly
            decrypted = encryption_service.decrypt(value)
            
            if decrypted is None:
                # Decryption failed, might be plain text from before encryption
                logger.warning("Decryption returned None, attempting to decode as plain text")
                try:
                    return value.decode('utf-8')
                except (UnicodeDecodeError, AttributeError):
                    logger.error("Failed to decrypt and failed to decode as plain text")
                    raise ValueError("Failed to decrypt value and not valid UTF-8")
            
            if isinstance(decrypted, str):
                return decrypted
            elif isinstance(decrypted, bytes):
                return decrypted.decode('utf-8')
            else:
                return str(decrypted)
                
        except Exception as e:
            logger.error(f"Failed to decrypt string value: {e}")
            # Grace period: try to decode as plain text
            try:
                if isinstance(value, bytes):
                    return value.decode('utf-8')
                return str(value)
            except Exception:
                raise ValueError(f"Failed to decrypt value: {e}")
    
    def load_dialect_impl(self, dialect) -> TypeEngine:
        """Return the underlying database type.
        
        For PostgreSQL, use BYTEA or TEXT depending on dialect.
        For SQLite, use BLOB or TEXT.
        """
        if dialect.name == 'postgresql':
            # PostgreSQL: Use BYTEA for binary data
            return dialect.type_descriptor(Text())
        else:
            # SQLite and others: Use BLOB
            return dialect.type_descriptor(String(self.length))


class EncryptedText(TypeDecorator):
    """SQLAlchemy type that transparently encrypts/decrypts large text values.
    
    Usage:
        original_text = Column(EncryptedText(), nullable=True)
    
    Similar to EncryptedString but uses Text type (unlimited length) instead of String.
    The value is stored as encrypted bytes in the database but appears
    as plain text in Python code.
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(self, **kwargs):
        """Initialize encrypted text type.
        
        Args:
            **kwargs: Additional arguments passed to Text type
        """
        super().__init__(**kwargs)
        self._encryption_service = None
    
    def _get_encryption_service(self):
        """Lazy-load encryption service."""
        if self._encryption_service is None:
            self._encryption_service = get_encryption_service()
        return self._encryption_service
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt value before storing in database.
        
        Args:
            value: Plain text string to encrypt
            dialect: SQLAlchemy dialect (unused)
            
        Returns:
            Encrypted string (ASCII), or None if value is None
        """
        if value is None:
            return None
        
        if not settings.ENCRYPTION_ENABLED:
            # If encryption disabled, store as plain text (for development)
            return value
        
        try:
            encryption_service = self._get_encryption_service()
            encrypted = encryption_service.encrypt(value)
            
            if encrypted is None:
                # Encryption service returned None (disabled or error)
                logger.warning("Encryption service returned None, storing as plain text")
                return value
            
            # Return as ASCII string to avoid bytea type mismatch in Postgres
            return encrypted.decode('ascii')
        except Exception as e:
            logger.error(f"Failed to encrypt text value: {e}")
            # In production, this should raise; for now, log and store plain text
            if settings.ENCRYPTION_ENABLED:
                raise ValueError(f"Encryption failed and ENCRYPTION_ENABLED=True: {e}")
            return value
    
    def process_result_value(self, value: Optional[Any], dialect) -> Optional[str]:
        """Decrypt value after retrieving from database.
        
        Args:
            value: Encrypted data from database (bytes or ASCII string)
            dialect: SQLAlchemy dialect (unused)
            
        Returns:
            Decrypted plain text string, or None if value is None
        """
        if value is None:
            return None
        
        if not settings.ENCRYPTION_ENABLED:
            # If encryption disabled, assume plain text
            if isinstance(value, bytes):
                try:
                    return value.decode('utf-8')
                except UnicodeDecodeError:
                    # Might be encrypted data from before encryption was disabled
                    pass
            elif isinstance(value, str):
                return value
            return value
        
        try:
            encryption_service = self._get_encryption_service()
            
            # If value is string, it might be an encrypted Fernet token or plain text
            if isinstance(value, str):
                if value.startswith('gAAAAA'):
                    try:
                        # Attempt to decrypt the string value
                        decrypted = encryption_service.decrypt(value.encode('ascii'))
                        if decrypted:
                            if isinstance(decrypted, bytes):
                                return decrypted.decode('utf-8')
                            return str(decrypted)
                    except (ValueError, Exception) as e:
                        # If decryption fails in strict mode, re-raise
                        if settings.ENCRYPTION_STRICT_MODE:
                            raise
                        # Otherwise, assume it's plain text
                        logger.warning(f"Decryption failed for string value (graceful mode): {e}")
                return value
            
            # Try to decrypt bytes directly
            decrypted = encryption_service.decrypt(value)
            
            if decrypted is None:
                # Decryption failed, might be plain text from before encryption
                if settings.ENCRYPTION_STRICT_MODE:
                    logger.error("Decryption returned None in strict mode")
                    raise ValueError("Failed to decrypt value: decryption returned None")
                else:
                    logger.warning("Decryption returned None, attempting to decode as plain text")
                    try:
                        return value.decode('utf-8')
                    except (UnicodeDecodeError, AttributeError):
                        logger.warning("Failed to decrypt and failed to decode as plain text, returning empty string")
                        return ""  # Return empty string instead of raising error
            
            if isinstance(decrypted, str):
                return decrypted
            elif isinstance(decrypted, bytes):
                return decrypted.decode('utf-8')
            else:
                return str(decrypted)
                
        except ValueError as e:
            # Handle decryption errors based on strict mode
            if settings.ENCRYPTION_STRICT_MODE:
                logger.error(f"Failed to decrypt text value: {e}")
                raise
            else:
                logger.warning(f"Failed to decrypt text value (graceful mode): {e}. Attempting fallback.")
                # Grace period: try to decode as plain text
                try:
                    if isinstance(value, bytes):
                        return value.decode('utf-8')
                    return str(value)
                except Exception:
                    logger.warning("Fallback decoding also failed, returning empty string")
                    return ""
        except Exception as e:
            if settings.ENCRYPTION_STRICT_MODE:
                logger.error(f"Failed to decrypt text value: {e}")
                raise ValueError(f"Failed to decrypt value: {e}")
            else:
                logger.warning(f"Failed to decrypt text value (graceful mode): {e}. Attempting fallback.")
                try:
                    if isinstance(value, bytes):
                        return value.decode('utf-8')
                    return str(value)
                except Exception:
                    logger.warning("Fallback decoding also failed, returning empty string")
                    return ""
    
    def load_dialect_impl(self, dialect) -> TypeEngine:
        """Return the underlying database type.
        
        For PostgreSQL, use TEXT.
        For SQLite, use TEXT.
        """
        # Both PostgreSQL and SQLite use TEXT for large text fields
        return dialect.type_descriptor(Text())


class EncryptedJSON(TypeDecorator):
    """SQLAlchemy type that transparently encrypts/decrypts JSON values.
    
    Usage:
        profile_data = Column(EncryptedJSON, nullable=True)
    
    The value is stored as encrypted bytes in the database but appears
    as a Python dict/list in code.
    """
    
    impl = JSONB
    cache_ok = True
    
    def __init__(self, **kwargs):
        """Initialize encrypted JSON type.
        
        Args:
            **kwargs: Additional arguments passed to JSONB type
        """
        super().__init__(**kwargs)
        self._encryption_service = None
    
    def _get_encryption_service(self):
        """Lazy-load encryption service."""
        if self._encryption_service is None:
            self._encryption_service = get_encryption_service()
        return self._encryption_service
    
    def process_bind_param(self, value: Optional[Dict[str, Any]], dialect) -> Optional[Any]:
        """Encrypt JSON value before storing in database.
        
        Args:
            value: Python dict/list to encrypt
            dialect: SQLAlchemy dialect (unused)
            
        Returns:
            Base64-encoded encrypted string (for JSONB) or encrypted bytes, or None if value is None
        """
        if value is None:
            return None
        
        if not settings.ENCRYPTION_ENABLED:
            # If encryption disabled, return as dict (JSONB will serialize it)
            return value
        
        try:
            encryption_service = self._get_encryption_service()
            encrypted = encryption_service.encrypt(value)
            
            if encrypted is None:
                # Encryption service returned None (disabled or error)
                logger.warning("Encryption service returned None, storing as plain JSON")
                return value
            
            # For JSONB columns, we need to store as a JSON string containing base64-encoded encrypted data
            # This allows JSONB to accept it while keeping it encrypted
            import base64
            encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
            # Store as a JSON object with encryption marker
            return {"_encrypted": True, "_data": encrypted_b64}
        except Exception as e:
            logger.error(f"Failed to encrypt JSON value: {e}")
            # In production, this should raise; for now, log and store plain JSON
            if settings.ENCRYPTION_ENABLED:
                raise ValueError(f"Encryption failed and ENCRYPTION_ENABLED=True: {e}")
            return value
    
    def process_result_value(self, value: Optional[Any], dialect) -> Optional[Dict[str, Any]]:
        """Decrypt JSON value after retrieving from database.
        
        Args:
            value: Encrypted JSON object from database, or plain dict/list (grace period)
            dialect: SQLAlchemy dialect (unused)
            
        Returns:
            Decrypted Python dict/list, or None if value is None
        """
        if value is None:
            return None
        
        if not settings.ENCRYPTION_ENABLED:
            # If encryption disabled, return as-is (should be dict/list)
            if isinstance(value, (dict, list)):
                return value
            elif isinstance(value, str):
                return json.loads(value)
            return value
        
        try:
            encryption_service = self._get_encryption_service()
            
            # Handle encrypted format: {"_encrypted": True, "_data": "base64..."}
            if isinstance(value, dict) and value.get("_encrypted") and "_data" in value:
                # This is encrypted data stored in JSONB
                import base64
                encrypted_b64 = value["_data"]
                encrypted_bytes = base64.b64decode(encrypted_b64.encode('utf-8'))
                
                # Decrypt
                decrypted = encryption_service.decrypt(encrypted_bytes)
                
                if decrypted is None:
                    if settings.ENCRYPTION_STRICT_MODE:
                        logger.error("Failed to decrypt JSON value")
                        raise ValueError("Decryption returned None")
                    else:
                        logger.warning("Decryption returned None for JSON value (graceful mode), returning empty dict")
                        return {}
                
                # Decrypted value should be a dict/list or JSON string
                if isinstance(decrypted, (dict, list)):
                    return decrypted
                elif isinstance(decrypted, str):
                    try:
                        return json.loads(decrypted)
                    except json.JSONDecodeError:
                        return decrypted
                elif isinstance(decrypted, bytes):
                    try:
                        return json.loads(decrypted.decode('utf-8'))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        return decrypted
                else:
                    return decrypted
            
            # Handle plain JSON (grace period - data from before encryption)
            if isinstance(value, (dict, list)):
                return value
            elif isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse as JSON, might be encrypted")
                    # Try to decrypt as base64-encoded string
                    try:
                        import base64
                        encrypted_bytes = base64.b64decode(value.encode('utf-8'))
                        decrypted = encryption_service.decrypt(encrypted_bytes)
                        if decrypted and isinstance(decrypted, (dict, list)):
                            return decrypted
                    except Exception:
                        pass
                    if settings.ENCRYPTION_STRICT_MODE:
                        raise ValueError("Value is not valid JSON and decryption failed")
                    else:
                        logger.warning("Value is not valid JSON and decryption failed (graceful mode), returning empty dict")
                        return {}
            elif isinstance(value, bytes):
                # Try to decrypt bytes directly
                decrypted = encryption_service.decrypt(value)
                if decrypted and isinstance(decrypted, (dict, list)):
                    return decrypted
                # Try to parse as JSON
                try:
                    return json.loads(value.decode('utf-8'))
                except Exception:
                    if settings.ENCRYPTION_STRICT_MODE:
                        raise ValueError("Failed to decrypt or parse as JSON")
                    else:
                        logger.warning("Failed to decrypt or parse as JSON (graceful mode), returning empty dict")
                        return {}
            
            return value
                
        except ValueError as e:
            # Handle decryption errors based on strict mode
            if settings.ENCRYPTION_STRICT_MODE:
                logger.error(f"Failed to decrypt JSON value: {e}")
                raise
            else:
                logger.warning(f"Failed to decrypt JSON value (graceful mode): {e}. Attempting fallback.")
                # Grace period: try to return as plain JSON
                if isinstance(value, (dict, list)):
                    return value
                elif isinstance(value, str):
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return {}
                return {}
        except Exception as e:
            if settings.ENCRYPTION_STRICT_MODE:
                logger.error(f"Failed to decrypt JSON value: {e}")
                raise ValueError(f"Failed to decrypt value: {e}")
            else:
                logger.warning(f"Failed to decrypt JSON value (graceful mode): {e}. Attempting fallback.")
                # Grace period: try to return as plain JSON
                if isinstance(value, (dict, list)):
                    return value
                elif isinstance(value, str):
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return {}
                return {}
    
    def load_dialect_impl(self, dialect) -> TypeEngine:
        """Return the underlying database type.
        
        For PostgreSQL, keep JSONB type (encrypted bytes stored as JSONB text).
        For SQLite, use TEXT.
        
        Note: We keep JSONB type to avoid schema migration issues.
        Encrypted bytes are base64-encoded and stored as JSONB text.
        """
        if dialect.name == 'postgresql':
            # PostgreSQL: Keep JSONB type (encrypted data stored as base64 string in JSONB)
            return dialect.type_descriptor(JSONB())
        else:
            # SQLite and others: Use TEXT
            return dialect.type_descriptor(Text())
