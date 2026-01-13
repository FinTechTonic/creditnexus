"""Database SSL/TLS configuration utilities for PostgreSQL connections.

This module provides utilities for building SSL-enabled database connection strings
and validating SSL configuration. It integrates with automatic certificate generation
and supports various SSL modes (prefer, require, verify-ca, verify-full).
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl

from app.core.config import settings

logger = logging.getLogger(__name__)


def build_ssl_connection_string(
    database_url: str,
    ssl_mode: Optional[str] = None,
    ssl_ca_cert: Optional[str] = None,
    ssl_client_cert: Optional[str] = None,
    ssl_client_key: Optional[str] = None,
) -> str:
    """Build a PostgreSQL connection string with SSL parameters.
    
    Args:
        database_url: Base database connection URL
        ssl_mode: SSL mode (prefer, require, verify-ca, verify-full)
        ssl_ca_cert: Path to CA certificate file
        ssl_client_cert: Path to client certificate file (mutual TLS)
        ssl_client_key: Path to client private key file (mutual TLS)
        
    Returns:
        Connection string with SSL parameters added
    """
    if not database_url or database_url.startswith("sqlite"):
        # SQLite doesn't support SSL
        return database_url
    
    # Parse the connection URL
    parsed = urlparse(database_url)
    
    # Get existing query parameters
    query_params = dict(parse_qsl(parsed.query))
    
    # Add SSL parameters
    if ssl_mode:
        query_params["sslmode"] = ssl_mode
    
    if ssl_ca_cert and Path(ssl_ca_cert).exists():
        query_params["sslrootcert"] = str(Path(ssl_ca_cert).absolute())
    elif ssl_ca_cert:
        logger.warning(f"CA certificate file not found: {ssl_ca_cert}")
    
    if ssl_client_cert and Path(ssl_client_cert).exists():
        query_params["sslcert"] = str(Path(ssl_client_cert).absolute())
    elif ssl_client_cert:
        logger.warning(f"Client certificate file not found: {ssl_client_cert}")
    
    if ssl_client_key and Path(ssl_client_key).exists():
        query_params["sslkey"] = str(Path(ssl_client_key).absolute())
    elif ssl_client_key:
        logger.warning(f"Client key file not found: {ssl_client_key}")
    
    # Reconstruct URL with SSL parameters
    new_query = urlencode(query_params)
    ssl_url = urlunparse(parsed._replace(query=new_query))
    
    return ssl_url


def build_ssl_connect_args(
    ssl_mode: Optional[str] = None,
    ssl_ca_cert: Optional[str] = None,
    ssl_client_cert: Optional[str] = None,
    ssl_client_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Build connect_args dictionary for SQLAlchemy engine with SSL parameters.
    
    This is an alternative to URL parameters, providing more control over SSL configuration.
    
    Args:
        ssl_mode: SSL mode (prefer, require, verify-ca, verify-full)
        ssl_ca_cert: Path to CA certificate file
        ssl_client_cert: Path to client certificate file (mutual TLS)
        ssl_client_key: Path to client private key file (mutual TLS)
        
    Returns:
        Dictionary of connect_args for SQLAlchemy engine
    """
    connect_args: Dict[str, Any] = {
        "connect_timeout": 10,
    }
    
    if ssl_mode:
        connect_args["sslmode"] = ssl_mode
    
    if ssl_ca_cert and Path(ssl_ca_cert).exists():
        connect_args["sslrootcert"] = str(Path(ssl_ca_cert).absolute())
    elif ssl_ca_cert:
        logger.warning(f"CA certificate file not found: {ssl_ca_cert}")
    
    if ssl_client_cert and Path(ssl_client_cert).exists():
        connect_args["sslcert"] = str(Path(ssl_client_cert).absolute())
    elif ssl_client_cert:
        logger.warning(f"Client certificate file not found: {ssl_client_cert}")
    
    if ssl_client_key and Path(ssl_client_key).exists():
        connect_args["sslkey"] = str(Path(ssl_client_key).absolute())
    elif ssl_client_key:
        logger.warning(f"Client key file not found: {ssl_client_key}")
    
    return connect_args


def validate_ssl_config() -> tuple[bool, Optional[str]]:
    """Validate SSL configuration from settings.
    
    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if configuration is valid
        - error_message: Error message if invalid, None if valid
    """
    # Check if SSL is required
    if settings.DB_SSL_REQUIRED:
        if not settings.DB_SSL_MODE or settings.DB_SSL_MODE == "disable":
            return False, (
                "DB_SSL_REQUIRED=true but DB_SSL_MODE is not set or is 'disable'. "
                "Set DB_SSL_MODE to 'require', 'verify-ca', or 'verify-full'."
            )
        
        # Check certificate requirements for verification modes
        if settings.DB_SSL_MODE in ["verify-ca", "verify-full"]:
            if not settings.DB_SSL_CA_CERT:
                # Check if auto-generation is enabled
                if not settings.DB_SSL_AUTO_GENERATE:
                    return False, (
                        f"DB_SSL_MODE={settings.DB_SSL_MODE} requires DB_SSL_CA_CERT to be set, "
                        "or enable DB_SSL_AUTO_GENERATE=true."
                    )
            elif not Path(settings.DB_SSL_CA_CERT).exists():
                # Check if auto-generation will create it
                if not settings.DB_SSL_AUTO_GENERATE:
                    return False, (
                        f"DB_SSL_CA_CERT file not found: {settings.DB_SSL_CA_CERT}. "
                        "Enable DB_SSL_AUTO_GENERATE=true to auto-generate certificates."
                    )
    
    # Validate client certificate configuration (mutual TLS)
    if settings.DB_SSL_CLIENT_CERT or settings.DB_SSL_CLIENT_KEY:
        if not settings.DB_SSL_CLIENT_CERT:
            return False, "DB_SSL_CLIENT_KEY is set but DB_SSL_CLIENT_CERT is missing."
        if not settings.DB_SSL_CLIENT_KEY:
            return False, "DB_SSL_CLIENT_CERT is set but DB_SSL_CLIENT_KEY is missing."
        
        if settings.DB_SSL_CLIENT_CERT and not Path(settings.DB_SSL_CLIENT_CERT).exists():
            if not settings.DB_SSL_AUTO_GENERATE_CLIENT:
                return False, (
                    f"DB_SSL_CLIENT_CERT file not found: {settings.DB_SSL_CLIENT_CERT}. "
                    "Enable DB_SSL_AUTO_GENERATE_CLIENT=true to auto-generate client certificate."
                )
    
    return True, None


def get_ssl_connection_string(database_url: Optional[str] = None) -> Optional[str]:
    """Get SSL-enabled database connection string from settings.
    
    This function:
    1. Validates SSL configuration
    2. Attempts auto-generation if enabled and certificates missing
    3. Builds connection string with SSL parameters
    
    Args:
        database_url: Optional database URL (defaults to settings.DATABASE_URL)
        
    Returns:
        SSL-enabled connection string, or None if SQLite or disabled
    """
    if not database_url:
        database_url = settings.DATABASE_URL
    
    if not database_url or database_url.startswith("sqlite"):
        return database_url
    
    # Validate SSL configuration
    is_valid, error_msg = validate_ssl_config()
    if not is_valid:
        logger.error(f"SSL configuration validation failed: {error_msg}")
        if settings.DB_SSL_REQUIRED:
            raise ValueError(f"SSL configuration invalid: {error_msg}")
        # If not required, continue without SSL
        return database_url
    
    # Attempt auto-generation if enabled
    ca_cert_path = settings.DB_SSL_CA_CERT
    client_cert_path = settings.DB_SSL_CLIENT_CERT
    client_key_path = settings.DB_SSL_CLIENT_KEY
    
    if settings.DB_SSL_AUTO_GENERATE:
        from app.utils.ssl_auto_setup import auto_setup_database_ssl
        
        auto_ca, auto_server, auto_key = auto_setup_database_ssl()
        if auto_ca:
            # Use auto-generated certificates if not explicitly provided
            if not ca_cert_path:
                ca_cert_path = str(auto_ca)
            if settings.DB_SSL_AUTO_GENERATE_CLIENT and not client_cert_path:
                client_cert_path = str(auto_server) if auto_server else None
                client_key_path = str(auto_key) if auto_key else None
    
    # Build SSL connection string
    ssl_mode = settings.DB_SSL_MODE or "prefer"
    ssl_url = build_ssl_connection_string(
        database_url=database_url,
        ssl_mode=ssl_mode,
        ssl_ca_cert=ca_cert_path,
        ssl_client_cert=client_cert_path,
        ssl_client_key=client_key_path,
    )
    
    logger.info(f"Built SSL connection string with mode: {ssl_mode}")
    return ssl_url
