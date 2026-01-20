"""Startup script for remote API server with SSL."""

import logging
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.remote_routes import remote_router
from app.middleware.ip_whitelist import IPWhitelistMiddleware
from app.utils.ssl_config import load_ssl_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_remote_app() -> FastAPI:
    """Create and configure the remote API FastAPI app.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="CreditNexus Remote API",
        description="Remote API for cross-machine verification and notarization",
        version="1.0.0",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add IP whitelist middleware if configured
    allowed_ips = (
        settings.REMOTE_API_ALLOWED_IPS if hasattr(settings, "REMOTE_API_ALLOWED_IPS") else None
    )
    allowed_cidrs = (
        settings.REMOTE_API_ALLOWED_CIDRS if hasattr(settings, "REMOTE_API_ALLOWED_CIDRS") else None
    )

    if allowed_ips or allowed_cidrs:
        app.add_middleware(
            IPWhitelistMiddleware,
            allowed_ips=allowed_ips,
            allowed_cidrs=allowed_cidrs,
            allow_localhost=True,
        )
        logger.info("IP whitelist middleware enabled")

    # Include remote API routes
    app.include_router(remote_router)

    return app


def main():
    """Run the remote API server with SSL."""
    if not settings.REMOTE_API_ENABLED:
        logger.error("Remote API is disabled. Set REMOTE_API_ENABLED=true to enable.")
        sys.exit(1)

    # Create app
    app = create_remote_app()

    # Configure SSL
    ssl_context = None

    if settings.REMOTE_API_SSL_CERT_PATH and settings.REMOTE_API_SSL_KEY_PATH:
        try:
            ssl_context = load_ssl_context(
                cert_path=Path(settings.REMOTE_API_SSL_CERT_PATH),
                key_path=Path(settings.REMOTE_API_SSL_KEY_PATH),
                chain_path=Path(settings.REMOTE_API_SSL_CERT_CHAIN_PATH)
                if settings.REMOTE_API_SSL_CERT_CHAIN_PATH
                else None,
            )
            logger.info(f"SSL enabled on port {settings.REMOTE_API_PORT}")
        except Exception as e:
            logger.error(f"Failed to load SSL certificate: {e}")
            sys.exit(1)
    else:
        logger.warning(
            f"SSL not configured. Remote API will run over HTTP (insecure). "
            f"Set REMOTE_API_SSL_CERT_PATH and REMOTE_API_SSL_KEY_PATH to enable SSL."
        )

    # Run server
    logger.info(f"Starting Remote API server on port {settings.REMOTE_API_PORT}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.REMOTE_API_PORT,
        ssl_keyfile=settings.REMOTE_API_SSL_KEY_PATH if settings.REMOTE_API_SSL_KEY_PATH else None,
        ssl_certfile=settings.REMOTE_API_SSL_CERT_PATH
        if settings.REMOTE_API_SSL_CERT_PATH
        else None,
        reload=False,  # Production mode - no auto-reload
        access_log=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
