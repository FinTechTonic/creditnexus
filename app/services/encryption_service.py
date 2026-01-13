"""Encryption service for encrypting sensitive data at rest.

This service provides encryption/decryption functionality for:
- PII (email addresses, profile data)
- Financial data (CDM events, extracted document data)
- File storage (credit agreement PDFs)

Uses Fernet (symmetric encryption) for application-level encryption.
"""

import logging
import os
from pathlib import Path
from typing import Optional, Union, Dict, Any
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

from app.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data at rest."""

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service.
        
        Args:
            encryption_key: Optional encryption key (defaults to ENCRYPTION_KEY from settings)
                           If not provided and ENCRYPTION_KEY not set, generates a new key
        """
        self.encryption_key = encryption_key or settings.ENCRYPTION_KEY
        self.fernet: Optional[Fernet] = None
        
        if not settings.ENCRYPTION_ENABLED:
            logger.warning("Encryption is disabled. Data will not be encrypted.")
            return
        
        if not self.encryption_key:
            logger.warning(
                "ENCRYPTION_KEY not set. Generating a new key. "
                "WARNING: This key will be lost on restart. Set ENCRYPTION_KEY in environment for production."
            )
            self.encryption_key = self._generate_key()
            logger.warning(f"Generated encryption key: {self.encryption_key.decode()[:20]}...")
        
        try:
            # Convert string key to bytes if needed
            if isinstance(self.encryption_key, str):
                key_bytes = self.encryption_key.encode()
            else:
                key_bytes = self.encryption_key
            
            # Ensure key is valid Fernet key (32 bytes, base64-encoded)
            if len(key_bytes) != 44:  # Fernet keys are 44 bytes when base64-encoded
                logger.warning("Encryption key format invalid. Generating new key.")
                self.encryption_key = self._generate_key()
                key_bytes = self.encryption_key
            
            self.fernet = Fernet(key_bytes)
            logger.info("Encryption service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize encryption service: {e}")
            raise ValueError(f"Encryption service initialization failed: {e}")

    @staticmethod
    def _generate_key() -> bytes:
        """Generate a new Fernet encryption key."""
        return Fernet.generate_key()

    @staticmethod
    def generate_key_from_password(password: str, salt: Optional[bytes] = None) -> bytes:
        """
        Generate a Fernet key from a password using PBKDF2.
        
        Args:
            password: Password to derive key from
            salt: Optional salt (generates new salt if not provided)
            
        Returns:
            Fernet-compatible encryption key
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

    def encrypt(self, data: Union[str, bytes, Dict[str, Any]]) -> Optional[bytes]:
        """
        Encrypt data.
        
        Args:
            data: Data to encrypt (string, bytes, or dict)
            
        Returns:
            Encrypted data as bytes, or None if encryption is disabled
        """
        if not settings.ENCRYPTION_ENABLED or not self.fernet:
            return None
        
        try:
            # Convert data to bytes
            if isinstance(data, dict):
                import json
                data_bytes = json.dumps(data).encode('utf-8')
            elif isinstance(data, str):
                data_bytes = data.encode('utf-8')
            else:
                data_bytes = data
            
            encrypted = self.fernet.encrypt(data_bytes)
            return encrypted
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt data: {e}")

    def decrypt(self, encrypted_data: bytes) -> Optional[Union[str, bytes, Dict[str, Any]]]:
        """
        Decrypt data.
        
        Args:
            encrypted_data: Encrypted data as bytes
            
        Returns:
            Decrypted data (string, bytes, or dict), or None if encryption is disabled
        """
        if not settings.ENCRYPTION_ENABLED or not self.fernet:
            # If encryption is disabled, assume data is not encrypted
            return encrypted_data
        
        try:
            decrypted = self.fernet.decrypt(encrypted_data)
            
            # Try to decode as UTF-8 string or JSON
            try:
                decoded = decrypted.decode('utf-8')
                # Try to parse as JSON
                try:
                    import json
                    return json.loads(decoded)
                except json.JSONDecodeError:
                    return decoded
            except UnicodeDecodeError:
                return decrypted
        except InvalidToken:
            logger.error("Invalid encryption token - data may be corrupted or key mismatch")
            raise ValueError("Failed to decrypt data: invalid token")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Failed to decrypt data: {e}")

    def encrypt_string(self, data: str) -> Optional[str]:
        """
        Encrypt a string and return as base64-encoded string.
        
        Args:
            data: String to encrypt
            
        Returns:
            Base64-encoded encrypted string, or None if encryption is disabled
        """
        encrypted = self.encrypt(data)
        if encrypted is None:
            return None
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt_string(self, encrypted_data: str) -> Optional[str]:
        """
        Decrypt a base64-encoded encrypted string.
        
        Args:
            encrypted_data: Base64-encoded encrypted string
            
        Returns:
            Decrypted string, or None if encryption is disabled
        """
        if not settings.ENCRYPTION_ENABLED or not self.fernet:
            return encrypted_data
        
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            decrypted = self.decrypt(encrypted_bytes)
            if isinstance(decrypted, str):
                return decrypted
            elif isinstance(decrypted, bytes):
                return decrypted.decode('utf-8')
            return str(decrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt string: {e}")
            raise ValueError(f"Failed to decrypt string: {e}")

    def encrypt_file(self, file_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Encrypt a file.
        
        Args:
            file_path: Path to file to encrypt
            output_path: Optional output path (defaults to file_path.encrypted)
            
        Returns:
            Path to encrypted file
        """
        if not settings.ENCRYPTION_ENABLED or not self.fernet:
            logger.warning("Encryption disabled, returning original file path")
            return file_path
        
        if output_path is None:
            output_path = file_path.parent / f"{file_path.name}.encrypted"
        
        try:
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            encrypted_data = self.encrypt(file_data)
            if encrypted_data is None:
                logger.warning("Encryption returned None, returning original file path")
                return file_path
            
            with open(output_path, 'wb') as f:
                f.write(encrypted_data)
            
            logger.info(f"Encrypted file: {file_path} -> {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to encrypt file {file_path}: {e}")
            raise ValueError(f"Failed to encrypt file: {e}")

    def decrypt_file(self, encrypted_file_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Decrypt a file.
        
        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Optional output path (defaults to encrypted_file_path without .encrypted extension)
            
        Returns:
            Path to decrypted file
        """
        if not settings.ENCRYPTION_ENABLED or not self.fernet:
            logger.warning("Encryption disabled, returning original file path")
            return encrypted_file_path
        
        if output_path is None:
            if encrypted_file_path.name.endswith('.encrypted'):
                output_path = encrypted_file_path.parent / encrypted_file_path.name[:-10]
            else:
                output_path = encrypted_file_path.parent / f"{encrypted_file_path.name}.decrypted"
        
        try:
            with open(encrypted_file_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = self.decrypt(encrypted_data)
            if decrypted_data is None:
                logger.warning("Decryption returned None, returning original file path")
                return encrypted_file_path
            
            if isinstance(decrypted_data, str):
                decrypted_data = decrypted_data.encode('utf-8')
            
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            logger.info(f"Decrypted file: {encrypted_file_path} -> {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Failed to decrypt file {encrypted_file_path}: {e}")
            raise ValueError(f"Failed to decrypt file: {e}")


# Global encryption service instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create the global encryption service instance.
    
    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def reset_encryption_service():
    """Reset the global encryption service instance (for testing)."""
    global _encryption_service
    _encryption_service = None
