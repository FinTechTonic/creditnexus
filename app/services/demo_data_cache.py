"""
Demo Data Cache Service for CreditNexus.

Provides caching for AI-generated CDM data and deal scenarios to reduce
redundant LLM calls and improve performance.
"""

import logging
import hashlib
import json
import sqlite3
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Global cache instance
_cache_instance: Optional['DemoDataCache'] = None


class DemoDataCache:
    """Cache service for demo data using SQLite."""
    
    def __init__(self, cache_db_path: Optional[str] = None, ttl_seconds: int = 86400):
        """
        Initialize demo data cache.
        
        Args:
            cache_db_path: Path to SQLite cache database (default: in-memory)
            ttl_seconds: Time-to-live in seconds (default: 24 hours)
        """
        self.cache_db_path = cache_db_path or ":memory:"
        self.ttl_seconds = ttl_seconds
        
        # Initialize cache database
        self._init_cache_db()
    
    def _init_cache_db(self):
        """Initialize cache database schema."""
        with self._get_connection() as conn:
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS demo_cache (
                        cache_key TEXT PRIMARY KEY,
                        cache_type TEXT NOT NULL,
                        cache_data TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL,
                        expires_at TIMESTAMP NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_expires_at ON demo_cache(expires_at)
                """)
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_cache_type ON demo_cache(cache_type)
                """)
                conn.commit()
            except sqlite3.OperationalError as e:
                # Table might already exist or connection issue
                logger.warning(f"Cache table initialization warning: {e}")
                try:
                    conn.rollback()
                except:
                    pass
    
    def _ensure_table_exists(self, conn: sqlite3.Connection):
        """Ensure cache table exists, create if it doesn't."""
        try:
            conn.execute("SELECT 1 FROM demo_cache LIMIT 1")
        except sqlite3.OperationalError:
            # Table doesn't exist, create it
            conn.execute("""
                CREATE TABLE IF NOT EXISTS demo_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_type TEXT NOT NULL,
                    cache_data TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at ON demo_cache(expires_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_type ON demo_cache(cache_type)
            """)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.cache_db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _generate_cache_key(self, cache_type: str, **kwargs) -> str:
        """
        Generate cache key from parameters.
        
        Args:
            cache_type: Type of cache entry (deal, cdm, etc.)
            **kwargs: Parameters to hash
            
        Returns:
            Cache key string
        """
        # Sort kwargs for consistent hashing
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True, default=str)
        param_hash = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        
        return f"demo:{cache_type}:{param_hash}"
    
    def get_cached_deal(
        self,
        seed: int,
        deal_type: str,
        scenario: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached deal data.
        
        Args:
            seed: Random seed
            deal_type: Type of deal
            scenario: Scenario template (optional)
            
        Returns:
            Cached deal data or None
        """
        cache_key = self._generate_cache_key("deal", seed=seed, deal_type=deal_type, scenario=scenario)
        
        try:
            with self._get_connection() as conn:
                # Ensure table exists
                self._ensure_table_exists(conn)
                
                cursor = conn.execute("""
                    SELECT cache_data, expires_at
                    FROM demo_cache
                    WHERE cache_key = ? AND cache_type = 'deal' AND expires_at > ?
                """, (cache_key, datetime.utcnow()))
                
                row = cursor.fetchone()
                if row:
                    try:
                        return json.loads(row["cache_data"])
                    except Exception as e:
                        logger.warning(f"Failed to deserialize cached deal: {e}")
                        return None
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                logger.warning(f"Cache table not found, skipping cache lookup: {e}")
            else:
                logger.warning(f"Cache lookup failed: {e}")
        
        return None
    
    def cache_deal(
        self,
        seed: int,
        deal_type: str,
        deal_data: Dict[str, Any],
        scenario: Optional[str] = None
    ) -> None:
        """
        Cache deal data.
        
        Args:
            seed: Random seed
            deal_type: Type of deal
            deal_data: Deal data to cache
            scenario: Scenario template (optional)
        """
        cache_key = self._generate_cache_key("deal", seed=seed, deal_type=deal_type, scenario=scenario)
        
        try:
            cache_data = json.dumps(deal_data, default=str)
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(seconds=self.ttl_seconds)
            
            with self._get_connection() as conn:
                # Ensure table exists
                self._ensure_table_exists(conn)
                
                conn.execute("""
                    INSERT OR REPLACE INTO demo_cache
                    (cache_key, cache_type, cache_data, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (cache_key, "deal", cache_data, created_at, expires_at))
                conn.commit()
                
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                logger.warning(f"Cache table not found, skipping cache write: {e}")
            else:
                logger.error(f"Failed to cache deal: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to cache deal: {e}", exc_info=True)
    
    def get_cached_cdm(
        self,
        deal_type: str,
        hash_key: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached CDM data.
        
        Args:
            deal_type: Type of deal
            hash_key: Hash key for CDM
            
        Returns:
            Cached CDM data or None
        """
        cache_key = self._generate_cache_key("cdm", deal_type=deal_type, hash_key=hash_key)
        
        try:
            with self._get_connection() as conn:
                # Ensure table exists
                self._ensure_table_exists(conn)
                
                cursor = conn.execute("""
                    SELECT cache_data, expires_at
                    FROM demo_cache
                    WHERE cache_key = ? AND cache_type = 'cdm' AND expires_at > ?
                """, (cache_key, datetime.utcnow()))
                
                row = cursor.fetchone()
                if row:
                    try:
                        return json.loads(row["cache_data"])
                    except Exception as e:
                        logger.warning(f"Failed to deserialize cached CDM: {e}")
                        return None
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                logger.warning(f"Cache table not found, skipping cache lookup: {e}")
            else:
                logger.warning(f"Cache lookup failed: {e}")
        
        return None
    
    def cache_cdm(
        self,
        deal_type: str,
        hash_key: str,
        cdm_data: Dict[str, Any]
    ) -> None:
        """
        Cache CDM data.
        
        Args:
            deal_type: Type of deal
            hash_key: Hash key for CDM
            cdm_data: CDM data to cache
        """
        cache_key = self._generate_cache_key("cdm", deal_type=deal_type, hash_key=hash_key)
        
        try:
            cache_data = json.dumps(cdm_data, default=str)
            created_at = datetime.utcnow()
            expires_at = created_at + timedelta(seconds=self.ttl_seconds)
            
            with self._get_connection() as conn:
                # Ensure table exists
                self._ensure_table_exists(conn)
                
                conn.execute("""
                    INSERT OR REPLACE INTO demo_cache
                    (cache_key, cache_type, cache_data, created_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (cache_key, "cdm", cache_data, created_at, expires_at))
                conn.commit()
                
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                logger.warning(f"Cache table not found, skipping cache write: {e}")
            else:
                logger.error(f"Failed to cache CDM: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Failed to cache CDM: {e}", exc_info=True)
    
    def clear_cache(self, cache_type: Optional[str] = None) -> int:
        """
        Clear cache entries.
        
        Args:
            cache_type: Optional cache type to clear (if None, clears all)
            
        Returns:
            Number of entries cleared
        """
        with self._get_connection() as conn:
            if cache_type:
                cursor = conn.execute("""
                    DELETE FROM demo_cache WHERE cache_type = ?
                """, (cache_type,))
            else:
                cursor = conn.execute("DELETE FROM demo_cache")
            
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def clear_expired(self) -> int:
        """
        Clear expired cache entries.
        
        Returns:
            Number of entries cleared
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                DELETE FROM demo_cache WHERE expires_at <= ?
            """, (datetime.utcnow(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            return deleted_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM demo_cache").fetchone()[0]
            expired = conn.execute("""
                SELECT COUNT(*) FROM demo_cache WHERE expires_at <= ?
            """, (datetime.utcnow(),)).fetchone()[0]
            
            by_type = {}
            cursor = conn.execute("""
                SELECT cache_type, COUNT(*) as count
                FROM demo_cache
                GROUP BY cache_type
            """)
            for row in cursor:
                by_type[row["cache_type"]] = row["count"]
        
        return {
            "total_entries": total,
            "expired_entries": expired,
            "active_entries": total - expired,
            "by_type": by_type
        }


def get_demo_cache() -> DemoDataCache:
    """
    Get or create global demo cache instance.
    
    Returns:
        DemoDataCache instance
    """
    global _cache_instance
    
    if _cache_instance is None:
        # Get cache configuration from settings
        try:
            from app.core.config import settings
            cache_path = getattr(settings, "DEMO_DATA_CACHE_PATH", None)
            cache_ttl = getattr(settings, "DEMO_DATA_CACHE_TTL", 86400)
            
            if cache_path:
                cache_path = Path(cache_path)
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path = str(cache_path)
            
            _cache_instance = DemoDataCache(
                cache_db_path=cache_path,
                ttl_seconds=cache_ttl
            )
        except Exception as e:
            logger.warning(f"Failed to initialize cache with settings, using defaults: {e}")
            _cache_instance = DemoDataCache()
    
    return _cache_instance
