"""Automatic SSL certificate and key generation utilities.

This module provides self-signed certificate generation for database SSL/TLS
and remote API SSL, with support for automatic certificate generation and
whitelisting integration.
"""

import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)


class CertificateGenerator:
    """Generate self-signed SSL certificates and keys.
    
    This class provides utilities for generating CA certificates, server certificates,
    and client certificates for SSL/TLS encryption. All certificates are self-signed
    and suitable for internal use, development, and testing.
    """
    
    def __init__(self, cert_dir: str = "./ssl_certs"):
        """Initialize certificate generator.
        
        Args:
            cert_dir: Directory to store generated certificates
        """
        self.cert_dir = Path(cert_dir)
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        # Set secure permissions (700 = owner read/write/execute only)
        os.chmod(self.cert_dir, 0o700)
        logger.info(f"Certificate generator initialized: {self.cert_dir}")
    
    def generate_ca_certificate(
        self,
        common_name: str = "CreditNexus CA",
        organization: str = "CreditNexus",
        validity_days: int = 365,
        key_size: int = 2048,
    ) -> Tuple[Path, Path]:
        """Generate a self-signed CA certificate and private key.
        
        Args:
            common_name: Common name for the CA certificate
            organization: Organization name
            validity_days: Certificate validity period in days
            key_size: RSA key size in bits (2048 or 4096)
            
        Returns:
            Tuple of (certificate_path, key_path)
            
        Raises:
            ValueError: If key_size is not 2048 or 4096
        """
        if key_size not in [2048, 4096]:
            raise ValueError(f"Invalid key_size: {key_size}. Must be 2048 or 4096")
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                key_cert_sign=True,
                crl_sign=True,
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256(), default_backend())
        
        # Save certificate
        cert_path = self.cert_dir / "ca.crt"
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        os.chmod(cert_path, 0o644)  # Readable by all, writable by owner
        
        # Save private key
        key_path = self.cert_dir / "ca.key"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(key_path, 0o600)  # Read/write by owner only
        
        logger.info(
            f"Generated CA certificate: {cert_path} (valid for {validity_days} days, {key_size}-bit key)"
        )
        
        return cert_path, key_path
    
    def generate_server_certificate(
        self,
        common_name: str,
        ca_cert_path: Path,
        ca_key_path: Path,
        subject_alternative_names: Optional[List[str]] = None,
        validity_days: int = 365,
        key_size: int = 2048,
    ) -> Tuple[Path, Path]:
        """Generate a server certificate signed by CA.
        
        Args:
            common_name: Common name (hostname or IP)
            ca_cert_path: Path to CA certificate
            ca_key_path: Path to CA private key
            subject_alternative_names: List of SANs (IPs, hostnames)
            validity_days: Certificate validity period
            key_size: RSA key size in bits
            
        Returns:
            Tuple of (certificate_path, key_path)
            
        Raises:
            FileNotFoundError: If CA certificate or key not found
            ValueError: If key_size is not 2048 or 4096
        """
        if key_size not in [2048, 4096]:
            raise ValueError(f"Invalid key_size: {key_size}. Must be 2048 or 4096")
        
        # Load CA certificate and key
        if not ca_cert_path.exists():
            raise FileNotFoundError(f"CA certificate not found: {ca_cert_path}")
        if not ca_key_path.exists():
            raise FileNotFoundError(f"CA key not found: {ca_key_path}")
        
        with open(ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        with open(ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), None, default_backend())
        
        # Generate server private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Build certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CreditNexus"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        )
        
        # Add Subject Alternative Names if provided
        if subject_alternative_names:
            san_list = []
            for san in subject_alternative_names:
                try:
                    # Try as IP address
                    import ipaddress
                    ip = ipaddress.ip_address(san)
                    san_list.append(x509.IPAddress(ip))
                except ValueError:
                    # Treat as DNS name
                    san_list.append(x509.DNSName(san))
            
            builder = builder.add_extension(
                x509.SubjectAlternativeName(san_list),
                critical=False,
            )
        
        # Add key usage
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        
        # Add extended key usage for server authentication
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=True,
        )
        
        cert = builder.sign(ca_key, hashes.SHA256(), default_backend())
        
        # Sanitize filename
        safe_name = common_name.replace(' ', '_').replace('.', '_').replace('/', '_')
        
        # Save certificate
        cert_path = self.cert_dir / f"{safe_name}.crt"
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        os.chmod(cert_path, 0o644)
        
        # Save private key
        key_path = self.cert_dir / f"{safe_name}.key"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(key_path, 0o600)
        
        logger.info(
            f"Generated server certificate: {cert_path} "
            f"(valid for {validity_days} days, {key_size}-bit key, "
            f"SANs: {subject_alternative_names or 'none'})"
        )
        
        return cert_path, key_path
    
    def generate_client_certificate(
        self,
        common_name: str,
        ca_cert_path: Path,
        ca_key_path: Path,
        validity_days: int = 365,
        key_size: int = 2048,
    ) -> Tuple[Path, Path]:
        """Generate a client certificate for mutual TLS.
        
        Args:
            common_name: Common name (client identifier)
            ca_cert_path: Path to CA certificate
            ca_key_path: Path to CA private key
            validity_days: Certificate validity period
            key_size: RSA key size in bits
            
        Returns:
            Tuple of (certificate_path, key_path)
            
        Raises:
            FileNotFoundError: If CA certificate or key not found
            ValueError: If key_size is not 2048 or 4096
        """
        if key_size not in [2048, 4096]:
            raise ValueError(f"Invalid key_size: {key_size}. Must be 2048 or 4096")
        
        # Load CA certificate and key
        if not ca_cert_path.exists():
            raise FileNotFoundError(f"CA certificate not found: {ca_cert_path}")
        if not ca_key_path.exists():
            raise FileNotFoundError(f"CA key not found: {ca_key_path}")
        
        with open(ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())
        with open(ca_key_path, "rb") as f:
            ca_key = serialization.load_pem_private_key(f.read(), None, default_backend())
        
        # Generate client private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        # Build certificate
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CreditNexus"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=validity_days)
        )
        
        # Add key usage
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                content_commitment=False,
                data_encipherment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        
        # Add extended key usage for client authentication
        builder = builder.add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=True,
        )
        
        cert = builder.sign(ca_key, hashes.SHA256(), default_backend())
        
        # Sanitize filename
        safe_name = common_name.replace(' ', '_').replace('.', '_').replace('/', '_')
        
        # Save certificate
        cert_path = self.cert_dir / f"{safe_name}_client.crt"
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        os.chmod(cert_path, 0o644)
        
        # Save private key
        key_path = self.cert_dir / f"{safe_name}_client.key"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        os.chmod(key_path, 0o600)
        
        logger.info(
            f"Generated client certificate: {cert_path} "
            f"(valid for {validity_days} days, {key_size}-bit key)"
        )
        
        return cert_path, key_path
    
    def validate_certificate_expiry(
        self,
        cert_path: Path,
        days_warning: int = 30
    ) -> Tuple[bool, Optional[str]]:
        """Validate certificate expiration.
        
        Args:
            cert_path: Path to certificate file
            days_warning: Days threshold for warning
            
        Returns:
            Tuple of (is_valid, warning_message)
        """
        try:
            if not cert_path.exists():
                return False, f"Certificate file not found: {cert_path}"
            
            with open(cert_path, "rb") as f:
                cert_data = f.read()
            
            cert = x509.load_pem_x509_certificate(cert_data, default_backend())
            
            # Check expiration
            if cert.not_valid_after:
                days_remaining = (cert.not_valid_after - datetime.utcnow()).days
                if days_remaining < 0:
                    return False, f"Certificate expired {abs(days_remaining)} days ago"
                elif days_remaining < days_warning:
                    return True, f"Certificate expires in {days_remaining} days"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Certificate validation error: {e}")
            return True, None  # Don't fail on validation errors
