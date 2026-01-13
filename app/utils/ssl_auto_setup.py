"""Automatic SSL/TLS setup utilities for database and remote API.

This module provides automatic certificate generation and setup for:
- Database SSL/TLS connections (PostgreSQL)
- Remote API SSL/TLS with whitelisting integration
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Tuple

from app.core.config import settings
from app.utils.cert_generator import CertificateGenerator

logger = logging.getLogger(__name__)


def auto_setup_database_ssl() -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """Automatically set up database SSL certificates if enabled and not provided.
    
    This function:
    1. Checks if auto-generation is enabled
    2. Checks if certificates already exist
    3. Generates CA and server certificates if needed
    4. Returns paths to CA cert, server cert, and server key
    
    Returns:
        Tuple of (ca_cert_path, server_cert_path, server_key_path) or (None, None, None) if disabled
    """
    # Check if auto-generation is enabled
    if not settings.DB_SSL_AUTO_GENERATE:
        logger.debug("Database SSL auto-generation is disabled")
        return None, None, None
    
    # Check if certificates are already provided
    if settings.DB_SSL_CA_CERT and Path(settings.DB_SSL_CA_CERT).exists():
        logger.info(f"Using existing database CA certificate: {settings.DB_SSL_CA_CERT}")
        ca_cert_path = Path(settings.DB_SSL_CA_CERT)
        server_cert_path = Path(settings.DB_SSL_CLIENT_CERT) if settings.DB_SSL_CLIENT_CERT else None
        server_key_path = Path(settings.DB_SSL_CLIENT_KEY) if settings.DB_SSL_CLIENT_KEY else None
        return ca_cert_path, server_cert_path, server_key_path
    
    # Create certificate directory
    cert_dir = Path(settings.DB_SSL_AUTO_CERT_DIR)
    cert_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if certificates already exist in auto-directory
    ca_cert_path = cert_dir / "ca.crt"
    server_cert_path = cert_dir / "server.crt"
    server_key_path = cert_dir / "server.key"
    
    if ca_cert_path.exists() and server_cert_path.exists() and server_key_path.exists():
        logger.info(f"Using existing auto-generated database certificates in {cert_dir}")
        return ca_cert_path, server_cert_path, server_key_path
    
    # Generate certificates
    logger.info(f"Auto-generating database SSL certificates in {cert_dir}")
    generator = CertificateGenerator(cert_dir=str(cert_dir))
    
    try:
        # Generate CA certificate
        if settings.DB_SSL_AUTO_GENERATE_CA:
            ca_cert_path, ca_key_path = generator.generate_ca_certificate(
                common_name="CreditNexus Database CA",
                validity_days=settings.DB_SSL_AUTO_CERT_VALIDITY_DAYS
            )
            logger.info(f"Generated database CA certificate: {ca_cert_path}")
        else:
            logger.warning("CA auto-generation disabled, but no CA cert provided")
            return None, None, None
        
        # Generate server certificate (for PostgreSQL server)
        server_cert_path, server_key_path = generator.generate_server_certificate(
            common_name="CreditNexus Database Server",
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
            subject_alternative_names=[
                "localhost",
                "postgres",
                "postgresql",
                "127.0.0.1",
                "::1"
            ],
            validity_days=settings.DB_SSL_AUTO_CERT_VALIDITY_DAYS
        )
        logger.info(f"Generated database server certificate: {server_cert_path}")
        
        # Generate client certificate if enabled (for mutual TLS)
        if settings.DB_SSL_AUTO_GENERATE_CLIENT:
            client_cert_path, client_key_path = generator.generate_client_certificate(
                common_name="CreditNexus Database Client",
                ca_cert_path=ca_cert_path,
                ca_key_path=ca_key_path,
                validity_days=settings.DB_SSL_AUTO_CERT_VALIDITY_DAYS
            )
            logger.info(f"Generated database client certificate: {client_cert_path}")
            # For mutual TLS, return client cert/key paths
            return ca_cert_path, client_cert_path, client_key_path
        
        return ca_cert_path, server_cert_path, server_key_path
        
    except Exception as e:
        logger.error(f"Failed to auto-generate database SSL certificates: {e}", exc_info=True)
        return None, None, None


def auto_setup_remote_api_ssl(
    whitelisted_ips: Optional[List[str]] = None
) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
    """Automatically set up remote API SSL certificates with whitelisting integration.
    
    This function:
    1. Checks if auto-generation is enabled
    2. Checks if certificates already exist
    3. Generates CA and server certificates with whitelisted IPs in SANs
    4. Returns paths to CA cert, server cert, and server key
    
    Args:
        whitelisted_ips: List of IP addresses/CIDR blocks to include in certificate SANs.
                        If None, will attempt to load from RemoteAppProfile models.
    
    Returns:
        Tuple of (ca_cert_path, server_cert_path, server_key_path) or (None, None, None) if disabled
    """
    # Check if remote API SSL auto-generation is enabled
    if not settings.REMOTE_API_SSL_AUTO_GENERATE:
        logger.debug("Remote API SSL auto-generation is disabled")
        return None, None, None
    
    # Check if certificates are already provided
    if settings.REMOTE_API_SSL_CERT_PATH and Path(settings.REMOTE_API_SSL_CERT_PATH).exists():
        logger.info(f"Using existing remote API certificate: {settings.REMOTE_API_SSL_CERT_PATH}")
        cert_path = Path(settings.REMOTE_API_SSL_CERT_PATH)
        key_path = Path(settings.REMOTE_API_SSL_KEY_PATH) if settings.REMOTE_API_SSL_KEY_PATH else None
        chain_path = Path(settings.REMOTE_API_SSL_CERT_CHAIN_PATH) if settings.REMOTE_API_SSL_CERT_CHAIN_PATH else None
        return chain_path, cert_path, key_path
    
    # Create certificate directory
    cert_dir = Path(settings.REMOTE_API_SSL_AUTO_CERT_DIR)
    cert_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if certificates already exist in auto-directory
    ca_cert_path = cert_dir / "ca.crt"
    server_cert_path = cert_dir / "server.crt"
    server_key_path = cert_dir / "server.key"
    
    if ca_cert_path.exists() and server_cert_path.exists() and server_key_path.exists():
        logger.info(f"Using existing auto-generated remote API certificates in {cert_dir}")
        return ca_cert_path, server_cert_path, server_key_path
    
    # Load whitelisted IPs from database if not provided
    if whitelisted_ips is None:
        whitelisted_ips = _load_whitelisted_ips_from_database()
    
    # Generate certificates
    logger.info(f"Auto-generating remote API SSL certificates in {cert_dir}")
    generator = CertificateGenerator(cert_dir=str(cert_dir))
    
    try:
        # Generate CA certificate
        ca_cert_path, ca_key_path = generator.generate_ca_certificate(
            common_name="CreditNexus Remote API CA",
            validity_days=settings.REMOTE_API_SSL_AUTO_CERT_VALIDITY_DAYS
        )
        logger.info(f"Generated remote API CA certificate: {ca_cert_path}")
        
        # Prepare SANs: DNS names and IP addresses
        subject_alternative_names = ["localhost", "creditnexus-remote-api", "127.0.0.1", "::1"]
        
        # Add whitelisted IPs to SANs
        if whitelisted_ips:
            for ip_entry in whitelisted_ips:
                # Handle CIDR blocks (extract base IP)
                if "/" in ip_entry:
                    base_ip = ip_entry.split("/")[0]
                    subject_alternative_names.append(base_ip)
                else:
                    subject_alternative_names.append(ip_entry)
            logger.info(f"Added {len(whitelisted_ips)} whitelisted IPs to certificate SANs")
        
        # Generate server certificate with whitelisted IPs in SANs
        server_cert_path, server_key_path = generator.generate_server_certificate(
            common_name="CreditNexus Remote API Server",
            ca_cert_path=ca_cert_path,
            ca_key_path=ca_key_path,
            subject_alternative_names=subject_alternative_names,
            validity_days=settings.REMOTE_API_SSL_AUTO_CERT_VALIDITY_DAYS
        )
        logger.info(f"Generated remote API server certificate with whitelisting: {server_cert_path}")
        
        return ca_cert_path, server_cert_path, server_key_path
        
    except Exception as e:
        logger.error(f"Failed to auto-generate remote API SSL certificates: {e}", exc_info=True)
        return None, None, None


def _load_whitelisted_ips_from_database() -> List[str]:
    """Load whitelisted IPs from RemoteAppProfile models in database.
    
    Returns:
        List of IP addresses/CIDR blocks from all active remote app profiles
    """
    try:
        from app.db import get_db
        from app.db.models import RemoteAppProfile
        
        # Get database session
        db = next(get_db())
        
        # Query all active profiles with allowed_ips
        profiles = db.query(RemoteAppProfile).filter(
            RemoteAppProfile.is_active == True
        ).all()
        
        whitelisted_ips = []
        for profile in profiles:
            if profile.allowed_ips:
                # allowed_ips is a JSONB field, should be a list
                if isinstance(profile.allowed_ips, list):
                    whitelisted_ips.extend(profile.allowed_ips)
                elif isinstance(profile.allowed_ips, dict) and "ips" in profile.allowed_ips:
                    whitelisted_ips.extend(profile.allowed_ips["ips"])
        
        # Remove duplicates
        whitelisted_ips = list(set(whitelisted_ips))
        
        logger.info(f"Loaded {len(whitelisted_ips)} whitelisted IPs from database")
        return whitelisted_ips
        
    except Exception as e:
        logger.warning(f"Failed to load whitelisted IPs from database: {e}")
        return []
