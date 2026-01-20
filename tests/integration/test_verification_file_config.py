"""Unit tests for VerificationFileConfig class."""

import pytest
import tempfile
import yaml
from pathlib import Path
from app.core.verification_file_config import VerificationFileConfig


def test_config_loading_from_file():
    """Test loading configuration from YAML file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        config_data = {
            "enabled_categories": ["legal", "financial"],
            "file_types": {
                "allowed_extensions": [".pdf", ".doc", ".xlsx"],
                "max_file_size_mb": 100
            },
            "categories": {
                "legal": {
                    "enabled": True,
                    "required": True,
                    "file_types": [".pdf", ".doc"]
                },
                "financial": {
                    "enabled": True,
                    "required": False,
                    "file_types": [".pdf", ".xlsx"]
                }
            },
            "subdirectories": {
                "documents": {"enabled": True, "priority": 1},
                "extractions": {"enabled": False, "priority": 2}
            }
        }
        yaml.dump(config_data, f)
        config_path = Path(f.name)
    
    try:
        # Reset singleton for testing
        VerificationFileConfig._instance = None
        
        config = VerificationFileConfig(config_path=config_path)
        enabled_cats = config.get_enabled_categories()
        assert "legal" in enabled_cats
        assert "financial" in enabled_cats
        assert len(enabled_cats) == 2
        assert config.is_file_allowed("test.pdf", "legal")
        assert config.is_file_allowed("test.xlsx", "financial")
        assert not config.is_file_allowed("test.txt", "legal")
    finally:
        # Cleanup
        config_path.unlink(missing_ok=True)
        VerificationFileConfig._instance = None


def test_default_config():
    """Test default configuration when file doesn't exist."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig(config_path=Path("/nonexistent/path/config.yaml"))
    assert len(config.get_enabled_categories()) > 0
    assert config.is_file_allowed("test.pdf")
    assert "legal" in config.get_enabled_categories()
    
    VerificationFileConfig._instance = None


def test_singleton_pattern():
    """Test that singleton pattern works correctly."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config1 = VerificationFileConfig()
    config2 = VerificationFileConfig()
    assert config1 is config2
    
    VerificationFileConfig._instance = None


def test_file_size_validation():
    """Test file size validation."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    # Test with default max size (50 MB)
    assert config.is_file_size_allowed(10 * 1024 * 1024)  # 10 MB - should pass
    assert config.is_file_size_allowed(50 * 1024 * 1024)  # 50 MB - should pass (at limit)
    assert not config.is_file_size_allowed(100 * 1024 * 1024)  # 100 MB - should fail
    
    VerificationFileConfig._instance = None


def test_category_exists():
    """Test category existence check."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    assert config.category_exists("legal")
    assert config.category_exists("financial")
    assert not config.category_exists("nonexistent")
    
    VerificationFileConfig._instance = None


def test_get_category_file_types():
    """Test getting file types for a category."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    legal_types = config.get_category_file_types("legal")
    assert ".pdf" in legal_types
    assert ".doc" in legal_types
    
    financial_types = config.get_category_file_types("financial")
    assert ".pdf" in financial_types
    assert ".xlsx" in financial_types
    
    # Non-existent category
    assert config.get_category_file_types("nonexistent") == []
    
    VerificationFileConfig._instance = None


def test_is_subdirectory_enabled():
    """Test subdirectory enabled check."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    assert config.is_subdirectory_enabled("documents")
    assert config.is_subdirectory_enabled("extractions")
    assert not config.is_subdirectory_enabled("generated")
    assert not config.is_subdirectory_enabled("nonexistent")
    
    VerificationFileConfig._instance = None


def test_get_subdirectory_priority():
    """Test getting subdirectory priority."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    assert config.get_subdirectory_priority("documents") == 1
    assert config.get_subdirectory_priority("extractions") == 2
    assert config.get_subdirectory_priority("generated") == 3
    assert config.get_subdirectory_priority("nonexistent") == 999  # Default
    
    VerificationFileConfig._instance = None


def test_get_required_categories():
    """Test getting required categories."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    required = config.get_required_categories()
    assert "legal" in required
    assert "financial" not in required  # Should not be required by default
    
    VerificationFileConfig._instance = None


def test_get_enabled_subdirectories():
    """Test getting enabled subdirectories."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    enabled = config.get_enabled_subdirectories()
    assert "documents" in enabled
    assert "extractions" in enabled
    assert "generated" not in enabled
    
    VerificationFileConfig._instance = None


def test_config_reload():
    """Test reloading configuration."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        initial_config = {
            "enabled_categories": ["legal"],
            "file_types": {"allowed_extensions": [".pdf"], "max_file_size_mb": 50},
            "categories": {
                "legal": {"enabled": True, "required": True, "file_types": [".pdf"]}
            },
            "subdirectories": {"documents": {"enabled": True, "priority": 1}}
        }
        yaml.dump(initial_config, f)
        config_path = Path(f.name)
    
    try:
        # Reset singleton for testing
        VerificationFileConfig._instance = None
        
        config = VerificationFileConfig(config_path=config_path)
        assert len(config.get_enabled_categories()) == 1
        
        # Update file
        updated_config = {
            "enabled_categories": ["legal", "financial"],
            "file_types": {"allowed_extensions": [".pdf", ".xlsx"], "max_file_size_mb": 100},
            "categories": {
                "legal": {"enabled": True, "required": True, "file_types": [".pdf"]},
                "financial": {"enabled": True, "required": False, "file_types": [".xlsx"]}
            },
            "subdirectories": {"documents": {"enabled": True, "priority": 1}}
        }
        with open(config_path, 'w') as f:
            yaml.dump(updated_config, f)
        
        # Reload
        config.reload()
        assert len(config.get_enabled_categories()) == 2
        assert "financial" in config.get_enabled_categories()
    finally:
        config_path.unlink(missing_ok=True)
        VerificationFileConfig._instance = None


def test_get_config_version():
    """Test getting configuration version."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    # Default version should be 1
    version = config.get_config_version()
    assert version >= 1
    
    VerificationFileConfig._instance = None


def test_is_file_allowed_with_category():
    """Test file allowed check with category."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    # Legal category allows .pdf
    assert config.is_file_allowed("document.pdf", "legal")
    assert not config.is_file_allowed("document.xlsx", "legal")
    
    # Financial category allows .xlsx
    assert config.is_file_allowed("statement.xlsx", "financial")
    assert not config.is_file_allowed("statement.doc", "financial")
    
    VerificationFileConfig._instance = None


def test_is_file_allowed_without_category():
    """Test file allowed check without category."""
    # Reset singleton for testing
    VerificationFileConfig._instance = None
    
    config = VerificationFileConfig()
    
    # Should check against global allowed extensions
    assert config.is_file_allowed("document.pdf")
    assert config.is_file_allowed("document.doc")
    assert not config.is_file_allowed("document.exe")  # Not in allowed list
    
    VerificationFileConfig._instance = None
