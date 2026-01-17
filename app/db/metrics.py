"""Database metrics collection for Prometheus.

This module sets up metrics collection for database connections and queries
using SQLAlchemy event listeners.
"""

import time
import logging
from typing import Any
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from app.core.metrics import (
    db_connections_active,
    db_connections_idle,
    db_query_duration_seconds,
    db_transactions_total,
)

logger = logging.getLogger(__name__)


def setup_db_metrics(engine: Engine) -> None:
    """Set up database metrics collection for an SQLAlchemy engine.
    
    This function registers event listeners to track:
    - Connection pool size (active/idle)
    - Query duration by operation type
    - Transaction commits/rollbacks
    
    Args:
        engine: SQLAlchemy engine to instrument
    """
    if engine is None:
        logger.warning("Cannot setup database metrics: engine is None")
        return

    # Track connection pool metrics
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn: Any, connection_record: Any) -> None:
        """Track when a connection is created."""
        # Connection is created but not yet in use
        db_connections_idle.inc()

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
        """Track when a connection is checked out from the pool."""
        db_connections_idle.dec()
        db_connections_active.labels(state="in_use").inc()

    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_conn: Any, connection_record: Any) -> None:
        """Track when a connection is returned to the pool."""
        db_connections_active.labels(state="in_use").dec()
        db_connections_idle.inc()

    # Track query duration
    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Store start time before query execution."""
        context._query_start_time = time.time()

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        """Track query duration after execution."""
        if hasattr(context, "_query_start_time"):
            duration = time.time() - context._query_start_time
            
            # Determine operation type from SQL statement
            operation = "select"  # default
            statement_upper = statement.strip().upper()
            if statement_upper.startswith("SELECT"):
                operation = "select"
            elif statement_upper.startswith("INSERT"):
                operation = "insert"
            elif statement_upper.startswith("UPDATE"):
                operation = "update"
            elif statement_upper.startswith("DELETE"):
                operation = "delete"
            elif statement_upper.startswith("CREATE") or statement_upper.startswith("ALTER"):
                operation = "ddl"
            
            db_query_duration_seconds.labels(operation=operation).observe(duration)

    # Track transactions
    @event.listens_for(engine, "commit")
    def on_commit(conn: Any) -> None:
        """Track committed transactions."""
        db_transactions_total.labels(status="committed").inc()

    @event.listens_for(engine, "rollback")
    def on_rollback(conn: Any) -> None:
        """Track rolled back transactions."""
        db_transactions_total.labels(status="rolled_back").inc()

    logger.info("Database metrics collection enabled")


def setup_query_metrics(engine: Engine) -> None:
    """Set up query-level metrics (alias for setup_db_metrics for clarity).
    
    Args:
        engine: SQLAlchemy engine to instrument
    """
    setup_db_metrics(engine)


def update_connection_pool_metrics(pool: Pool) -> None:
    """Manually update connection pool metrics.
    
    This can be called periodically to ensure accurate metrics,
    especially for connection pools that don't fire all events.
    
    Args:
        pool: SQLAlchemy connection pool
    """
    try:
        # Get pool statistics
        checked_in = pool.checkedin()
        checked_out = pool.checkedout()
        overflow = pool.overflow()
        size = pool.size()
        
        # Update metrics
        # Note: These are approximations as we track incrementally via events
        # This function provides a snapshot for verification
        db_connections_idle._value._value = checked_in
        db_connections_active.labels(state="in_use")._value._value = checked_out
        
    except Exception as e:
        logger.warning(f"Error updating connection pool metrics: {e}")
