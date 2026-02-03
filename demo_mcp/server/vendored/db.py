"""
SQLite schema and session for standalone Plaid connections.
Tables: implementations, plaid_connections.
"""

import json
import os
import sqlite3
from pathlib import Path

_db_path: str | None = None


def _get_db_path() -> str:
    global _db_path
    if _db_path is not None:
        return _db_path
    path = os.getenv("STANDALONE_DB_PATH")
    if path:
        _db_path = path
    else:
        base = Path(__file__).resolve().parent.parent
        data_dir = base / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        _db_path = str(data_dir / "standalone.sqlite")
    return _db_path


def init_db() -> None:
    """Create tables implementations and plaid_connections if they do not exist."""
    path = _get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS implementations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                is_active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plaid_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                implementation_id INTEGER NOT NULL REFERENCES implementations(id),
                user_id TEXT NOT NULL,
                connection_data TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory=Row. Call init_db() once before first use."""
    init_db()
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    return conn
