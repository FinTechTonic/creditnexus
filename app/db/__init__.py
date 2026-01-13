"""Database initialization for CreditNexus."""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

# Import settings - this will trigger SQLite fallback if DATABASE_URL not set
from app.core.config import settings

# Get database URL from settings (with SQLite fallback for development)
DATABASE_URL = settings.DATABASE_URL if settings.DATABASE_ENABLED else None

if DATABASE_URL:
    # Use different engine config for SQLite vs PostgreSQL
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False},  # SQLite-specific
            echo=False,
        )
        logger.info(f"Database initialized: SQLite ({DATABASE_URL})")
    else:
        # PostgreSQL connection with SSL/TLS support
        from app.db.ssl_config import get_ssl_connection_string
        
        # Get SSL-enabled connection string (auto-generates certificates if enabled)
        try:
            database_url_with_ssl = get_ssl_connection_string(DATABASE_URL)
            if database_url_with_ssl != DATABASE_URL:
                logger.info("Database SSL/TLS enabled")
        except ValueError as e:
            # SSL configuration error - if required, fail; otherwise continue without SSL
            if settings.DB_SSL_REQUIRED:
                logger.error(f"Database SSL required but configuration failed: {e}")
                raise
            logger.warning(f"Database SSL configuration error (not required): {e}")
            database_url_with_ssl = DATABASE_URL
        
        engine = create_engine(
            database_url_with_ssl,
            pool_recycle=300,
            pool_pre_ping=True,
            echo=False,
        )
        logger.info("Database initialized: PostgreSQL")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
else:
    engine = None
    SessionLocal = None
    logger.warning("Database is disabled (DATABASE_ENABLED=false)")

Base = declarative_base()


def get_db():
    """Dependency for getting database sessions.
    
    Raises:
        HTTPException: 503 Service Unavailable if database is not configured.
    """
    if SessionLocal is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Database not configured",
                "message": "Database is not available. Set DATABASE_URL environment variable or enable DATABASE_ENABLED.",
                "docs": "/docs#database-configuration",
                "hint": "For development, DATABASE_URL can be omitted to use SQLite automatically."
            }
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database tables."""
    if engine is None:
        logger.warning("Cannot initialize database: engine is None")
        return
    from app.db import models
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully")
