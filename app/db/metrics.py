"""Database metrics collection for Prometheus.

This module sets up SQLAlchemy event listeners to collect database
connection pool and query performance metrics.
"""

from app.core.metrics import (
    db_connections_active,
    db_connections_total,
    db_query_duration_seconds
)
from sqlalchemy import event
from sqlalchemy.pool import Pool
from sqlalchemy.engine import Engine
import time
import logging

logger = logging.getLogger(__name__)


def setup_db_metrics(engine: Engine):
    """Setup database connection pool metrics.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    if not engine:
        logger.warning("Cannot setup database metrics: engine is None")
        return
    
    @event.listens_for(Pool, "connect")
    def on_connect(dbapi_conn, connection_record):
        """Track connection creation."""
        db_connections_total.labels(action="created").inc()
        db_connections_active.labels(state="idle").inc()
    
    @event.listens_for(Pool, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        """Track connection checkout."""
        db_connections_active.labels(state="idle").dec()
        db_connections_active.labels(state="in_use").inc()
    
    @event.listens_for(Pool, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        """Track connection checkin."""
        db_connections_active.labels(state="in_use").dec()
        db_connections_active.labels(state="idle").inc()
    
    @event.listens_for(Pool, "invalidate")
    def on_invalidate(dbapi_conn, connection_record, exception):
        """Track connection invalidation."""
        db_connections_total.labels(action="closed").inc()
        db_connections_active.labels(state="in_use").dec()
    
    logger.info("Database connection metrics initialized")


def setup_query_metrics(engine: Engine):
    """Setup database query performance metrics.
    
    Args:
        engine: SQLAlchemy engine instance
    """
    if not engine:
        logger.warning("Cannot setup query metrics: engine is None")
        return
    
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query start time."""
        context._query_start_time = time.time()
    
    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Record query duration."""
        if hasattr(context, '_query_start_time'):
            duration = time.time() - context._query_start_time
            
            # Determine operation type
            statement_upper = statement.upper().strip() if statement else ""
            if statement_upper.startswith('SELECT'):
                operation = "select"
            elif statement_upper.startswith('INSERT'):
                operation = "insert"
            elif statement_upper.startswith('UPDATE'):
                operation = "update"
            elif statement_upper.startswith('DELETE'):
                operation = "delete"
            else:
                operation = "other"
            
            db_query_duration_seconds.labels(
                operation=operation
            ).observe(duration)
    
    logger.info("Database query metrics initialized")
