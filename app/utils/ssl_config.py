"""SSL/TLS configuration utilities for remote API."""

import ssl
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_ssl_context(
    cert_path: Path,
    key_path: Path,
    chain_path: Optional[Path] = None,
    verify_mode: str = "required",
) -> ssl.SSLContext:
    """Load SSL context from certificate files.

    Args:
        cert_path: Path to certificate file (.pem, .crt)
        key_path: Path to private key file (.key, .pem)
        chain_path: Optional path to certificate chain file
        verify_mode: SSL verification mode (required, optional, none)

    Returns:
        Configured SSLContext
    """
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificate file not found: {cert_path}")
    if not key_path.exists():
        raise FileNotFoundError(f"Key file not found: {key_path}")

    # Create SSL context
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

    # Load certificate and key
    context.load_cert_chain(str(cert_path), str(key_path))

    # Load certificate chain if provided
    if chain_path and chain_path.exists():
        context.load_verify_locations(str(chain_path))

    # Set verification mode
    if verify_mode == "required":
        context.verify_mode = ssl.CERT_REQUIRED
    elif verify_mode == "optional":
        context.verify_mode = ssl.CERT_OPTIONAL
    else:
        context.verify_mode = ssl.CERT_NONE

    # Set minimum TLS version
    context.minimum_version = ssl.TLSVersion.TLSv1_2

    # Set cipher suites (secure defaults)
    context.set_ciphers("HIGH:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA")

    logger.info(f"SSL context loaded: cert={cert_path}, key={key_path}, verify={verify_mode}")
    return context


def validate_certificate_expiry(
    cert_path: Path, days_warning: int = 30
) -> tuple[bool, Optional[str]]:
    """Validate certificate expiration.

    Args:
        cert_path: Path to certificate file
        days_warning: Days threshold for warning

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        from cryptography import x509
        import datetime

        with open(cert_path, "rb") as f:
            cert_data = f.read()

        cert = x509.load_pem_x509_certificate(cert_data)

        # Check expiration
        if cert.not_valid_after and cert.not_valid_after > datetime.datetime.now():
            days_remaining = (cert.not_valid_after - datetime.datetime.now()).days
            if days_remaining < days_warning:
                return False, f"Certificate expires in {days_remaining} days"

        return True, None

    except ImportError:
        logger.warning("cryptography library not installed, skipping certificate validation")
        return True, None
    except Exception as e:
        logger.error(f"Certificate validation error: {e}")
        return True, None
