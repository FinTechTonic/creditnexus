"""Unit tests for database SSL configuration."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from app.core.config import Settings
from app.db.ssl_config import (
    build_ssl_connection_string,
    validate_ssl_config,
    get_ssl_connection_string,
    build_ssl_connect_args,
)


class TestSSLConfigurationValidation:
    """Test SSL configuration validation in Settings class."""

    def test_validate_ssl_config_valid_prefer_mode(self):
        """Test validation passes with prefer mode (default)."""
        settings = Settings(
            DB_SSL_MODE="prefer",
            DB_SSL_REQUIRED=False,
            OPENAI_API_KEY="test-key"
        )
        # Should not raise
        settings.validate_ssl_config()

    def test_validate_ssl_config_invalid_mode(self):
        """Test validation fails with invalid SSL mode."""
        settings = Settings(
            DB_SSL_MODE="invalid-mode",
            OPENAI_API_KEY="test-key"
        )
        with pytest.raises(ValueError, match="Invalid DB_SSL_MODE"):
            settings.validate_ssl_config()

    def test_validate_ssl_config_required_with_disable_mode(self):
        """Test validation fails when SSL required but mode is disable."""
        settings = Settings(
            DB_SSL_REQUIRED=True,
            DB_SSL_MODE="disable",
            OPENAI_API_KEY="test-key"
        )
        with pytest.raises(ValueError, match="DB_SSL_REQUIRED=true"):
            settings.validate_ssl_config()

    def test_validate_ssl_config_required_with_allow_mode(self):
        """Test validation fails when SSL required but mode is allow (insecure)."""
        settings = Settings(
            DB_SSL_REQUIRED=True,
            DB_SSL_MODE="allow",
            OPENAI_API_KEY="test-key"
        )
        with pytest.raises(ValueError, match="not secure"):
            settings.validate_ssl_config()

    def test_validate_ssl_config_verify_ca_without_cert(self):
        """Test validation fails when verify-ca mode but no CA cert and auto-gen disabled."""
        settings = Settings(
            DB_SSL_MODE="verify-ca",
            DB_SSL_CA_CERT=None,
            DB_SSL_AUTO_GENERATE=False,
            OPENAI_API_KEY="test-key"
        )
        # Should not raise if SSL not required
        settings.validate_ssl_config()
        
        # Should raise if SSL required
        settings.DB_SSL_REQUIRED = True
        with pytest.raises(ValueError, match="requires DB_SSL_CA_CERT"):
            settings.validate_ssl_config()

    def test_validate_ssl_config_verify_ca_with_missing_cert_file(self):
        """Test validation fails when CA cert path doesn't exist and auto-gen disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "nonexistent.crt"
            settings = Settings(
                DB_SSL_MODE="verify-ca",
                DB_SSL_CA_CERT=str(cert_path),
                DB_SSL_AUTO_GENERATE=False,
                DB_SSL_REQUIRED=True,
                OPENAI_API_KEY="test-key"
            )
            with pytest.raises(ValueError, match="file not found"):
                settings.validate_ssl_config()

    def test_validate_ssl_config_verify_ca_with_auto_generate(self):
        """Test validation passes when verify-ca mode with auto-generation enabled."""
        settings = Settings(
            DB_SSL_MODE="verify-ca",
            DB_SSL_CA_CERT=None,
            DB_SSL_AUTO_GENERATE=True,
            DB_SSL_REQUIRED=True,
            OPENAI_API_KEY="test-key"
        )
        # Should not raise when auto-generation is enabled
        settings.validate_ssl_config()

    def test_validate_ssl_config_client_cert_missing_cert(self):
        """Test validation fails when client key set but cert missing."""
        settings = Settings(
            DB_SSL_CLIENT_KEY="/path/to/key",
            DB_SSL_CLIENT_CERT=None,
            OPENAI_API_KEY="test-key"
        )
        with pytest.raises(ValueError, match="DB_SSL_CLIENT_KEY is set but DB_SSL_CLIENT_CERT is missing"):
            settings.validate_ssl_config()

    def test_validate_ssl_config_client_cert_missing_key(self):
        """Test validation fails when client cert set but key missing."""
        settings = Settings(
            DB_SSL_CLIENT_CERT="/path/to/cert",
            DB_SSL_CLIENT_KEY=None,
            OPENAI_API_KEY="test-key"
        )
        with pytest.raises(ValueError, match="DB_SSL_CLIENT_CERT is set but DB_SSL_CLIENT_KEY is missing"):
            settings.validate_ssl_config()

    def test_validate_ssl_config_client_cert_missing_file(self):
        """Test validation fails when client cert file doesn't exist and auto-gen disabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "nonexistent.crt"
            settings = Settings(
                DB_SSL_CLIENT_CERT=str(cert_path),
                DB_SSL_CLIENT_KEY="/path/to/key",
                DB_SSL_AUTO_GENERATE_CLIENT=False,
                OPENAI_API_KEY="test-key"
            )
            with pytest.raises(ValueError, match="file not found"):
                settings.validate_ssl_config()


class TestBuildSSLConnectionString:
    """Test building SSL connection strings."""

    def test_build_ssl_connection_string_sqlite(self):
        """Test SQLite connection string is returned unchanged."""
        url = "sqlite:///test.db"
        result = build_ssl_connection_string(url, ssl_mode="require")
        assert result == url

    def test_build_ssl_connection_string_postgresql_with_mode(self):
        """Test PostgreSQL connection string with SSL mode."""
        url = "postgresql://user:pass@localhost:5432/dbname"
        result = build_ssl_connection_string(url, ssl_mode="require")
        assert "sslmode=require" in result
        assert "postgresql://" in result

    def test_build_ssl_connection_string_with_ca_cert(self):
        """Test connection string includes CA certificate path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "ca.crt"
            cert_path.write_text("test cert")
            
            url = "postgresql://user:pass@localhost:5432/dbname"
            result = build_ssl_connection_string(
                url,
                ssl_mode="verify-full",
                ssl_ca_cert=str(cert_path)
            )
            assert "sslmode=verify-full" in result
            assert "sslrootcert=" in result
            # Path is URL-encoded in connection string, check for encoded version
            from urllib.parse import quote
            encoded_path = quote(str(cert_path.absolute()), safe='')
            assert encoded_path in result or str(cert_path.absolute()).replace('\\', '/') in result

    def test_build_ssl_connection_string_with_client_cert(self):
        """Test connection string includes client certificate paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "client.crt"
            key_path = Path(tmpdir) / "client.key"
            cert_path.write_text("test cert")
            key_path.write_text("test key")
            
            url = "postgresql://user:pass@localhost:5432/dbname"
            result = build_ssl_connection_string(
                url,
                ssl_mode="require",
                ssl_client_cert=str(cert_path),
                ssl_client_key=str(key_path)
            )
            assert "sslcert=" in result
            assert "sslkey=" in result

    def test_build_ssl_connection_string_nonexistent_cert_warning(self, caplog):
        """Test warning is logged when certificate file doesn't exist."""
        url = "postgresql://user:pass@localhost:5432/dbname"
        result = build_ssl_connection_string(
            url,
            ssl_mode="verify-full",
            ssl_ca_cert="/nonexistent/ca.crt"
        )
        assert "CA certificate file not found" in caplog.text
        assert "sslmode=verify-full" in result


class TestValidateSSLConfigFunction:
    """Test validate_ssl_config function from ssl_config module."""

    @patch('app.db.ssl_config.settings')
    def test_validate_ssl_config_valid(self, mock_settings):
        """Test validation passes with valid configuration."""
        mock_settings.DB_SSL_REQUIRED = False
        mock_settings.DB_SSL_MODE = "prefer"
        
        is_valid, error = validate_ssl_config()
        assert is_valid is True
        assert error is None

    @patch('app.db.ssl_config.settings')
    def test_validate_ssl_config_required_with_disable(self, mock_settings):
        """Test validation fails when SSL required but mode is disable."""
        mock_settings.DB_SSL_REQUIRED = True
        mock_settings.DB_SSL_MODE = "disable"
        
        is_valid, error = validate_ssl_config()
        assert is_valid is False
        assert "DB_SSL_REQUIRED=true" in error

    @patch('app.db.ssl_config.settings')
    def test_validate_ssl_config_verify_ca_without_cert(self, mock_settings):
        """Test validation fails when verify-ca mode but no CA cert."""
        mock_settings.DB_SSL_REQUIRED = True
        mock_settings.DB_SSL_MODE = "verify-ca"
        mock_settings.DB_SSL_CA_CERT = None
        mock_settings.DB_SSL_AUTO_GENERATE = False
        
        is_valid, error = validate_ssl_config()
        assert is_valid is False
        assert "requires DB_SSL_CA_CERT" in error


class TestBuildSSLConnectArgs:
    """Test building SSL connect_args for SQLAlchemy."""

    def test_build_ssl_connect_args_with_mode(self):
        """Test connect_args includes SSL mode."""
        args = build_ssl_connect_args(ssl_mode="require")
        assert args["sslmode"] == "require"
        assert "connect_timeout" in args

    def test_build_ssl_connect_args_with_ca_cert(self):
        """Test connect_args includes CA certificate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "ca.crt"
            cert_path.write_text("test cert")
            
            args = build_ssl_connect_args(
                ssl_mode="verify-full",
                ssl_ca_cert=str(cert_path)
            )
            assert args["sslmode"] == "verify-full"
            assert "sslrootcert" in args
            assert str(cert_path.absolute()) in args["sslrootcert"]

    def test_build_ssl_connect_args_with_client_cert(self):
        """Test connect_args includes client certificate."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cert_path = Path(tmpdir) / "client.crt"
            key_path = Path(tmpdir) / "client.key"
            cert_path.write_text("test cert")
            key_path.write_text("test key")
            
            args = build_ssl_connect_args(
                ssl_mode="require",
                ssl_client_cert=str(cert_path),
                ssl_client_key=str(key_path)
            )
            assert "sslcert" in args
            assert "sslkey" in args


class TestGetSSLConnectionString:
    """Test get_ssl_connection_string function."""

    @patch('app.db.ssl_config.settings')
    @patch('app.db.ssl_config.validate_ssl_config')
    @patch('app.db.ssl_config.build_ssl_connection_string')
    def test_get_ssl_connection_string_sqlite(self, mock_build, mock_validate, mock_settings):
        """Test SQLite connection string is returned unchanged."""
        mock_settings.DATABASE_URL = "sqlite:///test.db"
        
        result = get_ssl_connection_string()
        assert result == "sqlite:///test.db"
        mock_build.assert_not_called()

    @patch('app.db.ssl_config.settings')
    @patch('app.db.ssl_config.validate_ssl_config')
    @patch('app.db.ssl_config.build_ssl_connection_string')
    def test_get_ssl_connection_string_invalid_config_required(self, mock_build, mock_validate, mock_settings):
        """Test ValueError raised when SSL required but config invalid."""
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/dbname"
        mock_settings.DB_SSL_REQUIRED = True
        mock_validate.return_value = (False, "Invalid configuration")
        
        with pytest.raises(ValueError, match="SSL configuration invalid"):
            get_ssl_connection_string()

    @patch('app.db.ssl_config.settings')
    @patch('app.db.ssl_config.validate_ssl_config')
    @patch('app.db.ssl_config.build_ssl_connection_string')
    def test_get_ssl_connection_string_invalid_config_not_required(self, mock_build, mock_validate, mock_settings):
        """Test original URL returned when SSL not required but config invalid."""
        mock_settings.DATABASE_URL = "postgresql://user:pass@localhost:5432/dbname"
        mock_settings.DB_SSL_REQUIRED = False
        mock_validate.return_value = (False, "Invalid configuration")
        
        result = get_ssl_connection_string()
        assert result == "postgresql://user:pass@localhost:5432/dbname"
        mock_build.assert_not_called()
