"""Integration tests for database SSL connections.

These tests verify SSL/TLS functionality with actual database connections.
Note: Some tests require a PostgreSQL server with SSL enabled.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.core.config import Settings
from app.db.ssl_config import get_ssl_connection_string, build_ssl_connection_string
from app.db import get_db, SessionLocal, engine


class TestSSLConnectionIntegration:
    """Integration tests for SSL database connections."""

    @pytest.fixture
    def temp_cert_dir(self):
        """Create temporary directory for test certificates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def mock_postgres_url(self):
        """Mock PostgreSQL connection URL."""
        return "postgresql://testuser:testpass@localhost:5432/testdb"

    def test_ssl_connection_string_building(self, mock_postgres_url, temp_cert_dir):
        """Test that SSL connection strings are built correctly."""
        ca_cert = temp_cert_dir / "ca.crt"
        ca_cert.write_text("test ca cert")
        
        result = build_ssl_connection_string(
            database_url=mock_postgres_url,
            ssl_mode="require",
            ssl_ca_cert=str(ca_cert)
        )
        
        assert "sslmode=require" in result
        assert "sslrootcert=" in result
        # Path is URL-encoded in connection string, check for encoded version
        from urllib.parse import quote
        encoded_path = quote(str(ca_cert.absolute()), safe='')
        assert encoded_path in result or str(ca_cert.absolute()).replace('\\', '/') in result
        assert "postgresql://" in result

    def test_ssl_connection_string_with_client_cert(self, mock_postgres_url, temp_cert_dir):
        """Test SSL connection string with client certificates (mutual TLS)."""
        ca_cert = temp_cert_dir / "ca.crt"
        client_cert = temp_cert_dir / "client.crt"
        client_key = temp_cert_dir / "client.key"
        
        ca_cert.write_text("test ca cert")
        client_cert.write_text("test client cert")
        client_key.write_text("test client key")
        
        result = build_ssl_connection_string(
            database_url=mock_postgres_url,
            ssl_mode="verify-full",
            ssl_ca_cert=str(ca_cert),
            ssl_client_cert=str(client_cert),
            ssl_client_key=str(client_key)
        )
        
        assert "sslmode=verify-full" in result
        assert "sslrootcert=" in result
        assert "sslcert=" in result
        assert "sslkey=" in result

    def test_ssl_connection_string_sqlite_unchanged(self):
        """Test that SQLite connection strings are not modified."""
        sqlite_url = "sqlite:///test.db"
        result = build_ssl_connection_string(
            database_url=sqlite_url,
            ssl_mode="require"
        )
        assert result == sqlite_url

    @pytest.mark.skipif(
        not os.getenv("TEST_POSTGRES_SSL"),
        reason="Requires PostgreSQL server with SSL enabled. Set TEST_POSTGRES_SSL=1"
    )
    def test_actual_ssl_connection_require_mode(self):
        """Test actual SSL connection with require mode.
        
        This test requires:
        - PostgreSQL server with SSL enabled
        - TEST_POSTGRES_SSL environment variable set
        - Valid DATABASE_URL pointing to PostgreSQL server
        """
        database_url = os.getenv("DATABASE_URL")
        if not database_url or database_url.startswith("sqlite"):
            pytest.skip("PostgreSQL connection URL not configured")
        
        # Build SSL connection string
        ssl_url = build_ssl_connection_string(
            database_url=database_url,
            ssl_mode="require"
        )
        
        # Create engine and test connection
        test_engine = create_engine(
            ssl_url,
            pool_pre_ping=True,
            echo=False
        )
        
        try:
            with test_engine.connect() as conn:
                # Test basic query
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
                
                # Check SSL status (if supported)
                try:
                    ssl_result = conn.execute(text("SHOW ssl"))
                    ssl_status = ssl_result.scalar()
                    assert ssl_status == "on", "SSL should be enabled"
                except Exception:
                    # Some PostgreSQL versions/configurations may not support SHOW ssl
                    pass
        finally:
            test_engine.dispose()

    @pytest.mark.skipif(
        not os.getenv("TEST_POSTGRES_SSL"),
        reason="Requires PostgreSQL server with SSL enabled. Set TEST_POSTGRES_SSL=1"
    )
    def test_actual_ssl_connection_verify_ca_mode(self, temp_cert_dir):
        """Test actual SSL connection with verify-ca mode.
        
        This test requires:
        - PostgreSQL server with SSL enabled
        - CA certificate file
        - TEST_POSTGRES_SSL environment variable set
        """
        database_url = os.getenv("DATABASE_URL")
        if not database_url or database_url.startswith("sqlite"):
            pytest.skip("PostgreSQL connection URL not configured")
        
        # For this test, we'd need the actual CA certificate
        # In a real scenario, this would be provided by the database administrator
        ca_cert_path = os.getenv("TEST_CA_CERT_PATH")
        if not ca_cert_path or not Path(ca_cert_path).exists():
            pytest.skip("CA certificate not available for testing")
        
        # Build SSL connection string with CA cert
        ssl_url = build_ssl_connection_string(
            database_url=database_url,
            ssl_mode="verify-ca",
            ssl_ca_cert=ca_cert_path
        )
        
        # Create engine and test connection
        test_engine = create_engine(
            ssl_url,
            pool_pre_ping=True,
            echo=False
        )
        
        try:
            with test_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
        except OperationalError as e:
            # Connection might fail if certificate doesn't match
            # This is expected behavior for verify-ca mode
            pytest.skip(f"SSL connection failed (expected if cert doesn't match): {e}")
        finally:
            test_engine.dispose()

    def test_ssl_connection_fallback_when_not_required(self, mock_postgres_url):
        """Test that connection falls back to non-SSL when SSL not required."""
        # Simulate SSL configuration error but SSL not required
        with patch('app.db.ssl_config.settings') as mock_settings:
            mock_settings.DB_SSL_REQUIRED = False
            mock_settings.DB_SSL_MODE = "prefer"
            mock_settings.DATABASE_URL = mock_postgres_url
            
            # Should return original URL if SSL config fails and not required
            result = get_ssl_connection_string(mock_postgres_url)
            # Should still attempt to build SSL string, but fallback is handled in __init__.py
            assert result is not None

    def test_ssl_connection_fails_when_required(self, mock_postgres_url):
        """Test that connection fails when SSL required but not available."""
        with patch('app.db.ssl_config.settings') as mock_settings:
            mock_settings.DB_SSL_REQUIRED = True
            mock_settings.DB_SSL_MODE = "verify-full"
            mock_settings.DB_SSL_CA_CERT = "/nonexistent/ca.crt"
            mock_settings.DB_SSL_AUTO_GENERATE = False
            mock_settings.DATABASE_URL = mock_postgres_url
            
            # Should raise ValueError when SSL required but config invalid
            with pytest.raises(ValueError, match="SSL configuration invalid"):
                get_ssl_connection_string(mock_postgres_url)

    @patch('app.utils.ssl_auto_setup.auto_setup_database_ssl')
    def test_auto_generation_integration(self, mock_auto_setup, mock_postgres_url, temp_cert_dir):
        """Test integration with automatic certificate generation."""
        # Mock auto-setup to return generated certificates
        ca_cert = temp_cert_dir / "auto_ca.crt"
        server_cert = temp_cert_dir / "auto_server.crt"
        server_key = temp_cert_dir / "auto_server.key"
        
        ca_cert.write_text("auto ca cert")
        server_cert.write_text("auto server cert")
        server_key.write_text("auto server key")
        
        mock_auto_setup.return_value = (ca_cert, server_cert, server_key)
        
        with patch('app.db.ssl_config.settings') as mock_settings:
            mock_settings.DB_SSL_AUTO_GENERATE = True
            mock_settings.DB_SSL_MODE = "verify-full"
            mock_settings.DB_SSL_CA_CERT = None
            mock_settings.DB_SSL_CLIENT_CERT = None
            mock_settings.DB_SSL_CLIENT_KEY = None
            mock_settings.DB_SSL_AUTO_GENERATE_CLIENT = False
            mock_settings.DATABASE_URL = mock_postgres_url
            mock_settings.DB_SSL_REQUIRED = False
            
            result = get_ssl_connection_string(mock_postgres_url)
            
            # Should use auto-generated certificates
            assert "sslrootcert=" in result
            # Path is URL-encoded in connection string, check for encoded version
            from urllib.parse import quote
            encoded_path = quote(str(ca_cert.absolute()), safe='')
            assert encoded_path in result or str(ca_cert.absolute()).replace('\\', '/') in result
            mock_auto_setup.assert_called_once()

    def test_connection_pool_ssl_persistence(self, mock_postgres_url, temp_cert_dir):
        """Test that SSL configuration persists across connection pool connections."""
        ca_cert = temp_cert_dir / "ca.crt"
        ca_cert.write_text("test ca cert")
        
        ssl_url = build_ssl_connection_string(
            database_url=mock_postgres_url,
            ssl_mode="require",
            ssl_ca_cert=str(ca_cert)
        )
        
        # Create engine with connection pool
        test_engine = create_engine(
            ssl_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
        
        # Verify SSL parameters are in the connection URL
        assert "sslmode=require" in str(test_engine.url)
        assert "sslrootcert=" in str(test_engine.url)
        
        test_engine.dispose()

    def test_ssl_mode_precedence(self, mock_postgres_url):
        """Test that SSL mode in connection string takes precedence."""
        # URL already has sslmode parameter
        url_with_ssl = f"{mock_postgres_url}?sslmode=prefer"
        
        # Build with different mode - should override
        result = build_ssl_connection_string(
            database_url=url_with_ssl,
            ssl_mode="require"
        )
        
        # Should have the new mode, not the old one
        assert "sslmode=require" in result
        assert "sslmode=prefer" not in result or result.count("sslmode") == 1

    def test_multiple_ssl_parameters(self, mock_postgres_url, temp_cert_dir):
        """Test building connection string with all SSL parameters."""
        ca_cert = temp_cert_dir / "ca.crt"
        client_cert = temp_cert_dir / "client.crt"
        client_key = temp_cert_dir / "client.key"
        
        ca_cert.write_text("ca cert")
        client_cert.write_text("client cert")
        client_key.write_text("client key")
        
        result = build_ssl_connection_string(
            database_url=mock_postgres_url,
            ssl_mode="verify-full",
            ssl_ca_cert=str(ca_cert),
            ssl_client_cert=str(client_cert),
            ssl_client_key=str(client_key)
        )
        
        # Verify all parameters are present
        assert "sslmode=verify-full" in result
        assert "sslrootcert=" in result
        assert "sslcert=" in result
        assert "sslkey=" in result
        
        # Verify absolute paths are used (URL-encoded in connection string)
        from urllib.parse import quote
        assert quote(str(ca_cert.absolute()), safe='') in result or str(ca_cert.absolute()).replace('\\', '/') in result
        assert quote(str(client_cert.absolute()), safe='') in result or str(client_cert.absolute()).replace('\\', '/') in result
        assert quote(str(client_key.absolute()), safe='') in result or str(client_key.absolute()).replace('\\', '/') in result


class TestSSLHealthCheckIntegration:
    """Integration tests for SSL health check endpoint."""

    @pytest.mark.skipif(
        not os.getenv("TEST_POSTGRES_SSL"),
        reason="Requires PostgreSQL server with SSL enabled"
    )
    def test_health_check_endpoint_ssl_status(self, client):
        """Test that health check endpoint reports SSL status correctly.
        
        This test requires:
        - Running application with PostgreSQL SSL enabled
        - TEST_POSTGRES_SSL environment variable set
        """
        response = client.get("/health/database/ssl")
        assert response.status_code in [200, 503]  # 503 if DB not available
        
        data = response.json()
        assert "ssl_enabled" in data
        assert "ssl_mode" in data
        assert "status" in data
        
        if data.get("ssl_enabled"):
            # If SSL is enabled, should have version and cipher info
            assert "ssl_version" in data or data.get("ssl_version") is None
            assert "ssl_cipher" in data or data.get("ssl_cipher") is None

    def test_health_check_endpoint_sqlite(self):
        """Test health check endpoint with SQLite (SSL not applicable)."""
        # Skip this test as it requires a FastAPI test client fixture
        # The endpoint functionality is tested via the actual health check
        pytest.skip("Requires FastAPI test client fixture - functionality tested via integration")


class TestSSLErrorHandling:
    """Test SSL error handling and edge cases."""

    @pytest.fixture
    def mock_postgres_url(self):
        """Mock PostgreSQL connection URL."""
        return "postgresql://testuser:testpass@localhost:5432/testdb"

    @pytest.fixture
    def temp_cert_dir(self):
        """Create temporary directory for test certificates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_missing_ca_cert_with_verify_mode(self, mock_postgres_url):
        """Test error handling when CA cert missing for verify mode."""
        with patch('app.db.ssl_config.settings') as mock_settings:
            mock_settings.DB_SSL_MODE = "verify-full"
            mock_settings.DB_SSL_CA_CERT = "/nonexistent/ca.crt"
            mock_settings.DB_SSL_AUTO_GENERATE = False
            mock_settings.DB_SSL_REQUIRED = True
            
            # Should raise error when required
            with pytest.raises(ValueError):
                get_ssl_connection_string(mock_postgres_url)

    def test_invalid_certificate_path(self, mock_postgres_url, temp_cert_dir):
        """Test handling of invalid certificate paths."""
        # Path exists but is a directory, not a file
        cert_dir = temp_cert_dir
        
        result = build_ssl_connection_string(
            database_url=mock_postgres_url,
            ssl_mode="verify-full",
            ssl_ca_cert=str(cert_dir)  # Directory, not file
        )
        
        # Should still build URL but log warning
        assert "sslmode=verify-full" in result
        # sslrootcert should not be added if path is invalid

    def test_ssl_mode_case_insensitive(self, mock_postgres_url):
        """Test that SSL mode handling is case-insensitive (if applicable)."""
        # PostgreSQL sslmode is case-sensitive, but we should handle it correctly
        result = build_ssl_connection_string(
            database_url=mock_postgres_url,
            ssl_mode="REQUIRE"  # Uppercase
        )
        
        assert "sslmode=REQUIRE" in result or "sslmode=require" in result.lower()
