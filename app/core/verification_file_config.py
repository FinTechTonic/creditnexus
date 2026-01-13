"""File whitelist configuration for verification links."""

import yaml
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

logger = logging.getLogger(__name__)


class VerificationFileConfig:
    """Loads and manages file whitelist configuration from YAML.
    
    Implements singleton pattern for thread-safe access and efficient
    configuration management across the application.
    """
    
    _instance: Optional['VerificationFileConfig'] = None
    _lock = threading.Lock()
    _config: Optional[Dict[str, Any]] = None
    _config_path: Optional[Path] = None
    _change_callbacks: List[Callable] = []

    def __new__(cls, config_path: Optional[Path] = None):
        """Create or return existing singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize(config_path)
        return cls._instance
    
    def _initialize(self, config_path: Optional[Path] = None):
        """Initialize singleton instance."""
        if not config_path:
            config_path = Path("app/config/verification_file_whitelist.yaml")
        self._config_path = config_path
        self._load_config()

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize instance (called after __new__ for singleton)."""
        # Initialization is handled by _initialize in __new__
        pass
    
    @property
    def config_path(self) -> Path:
        """Get the configuration file path."""
        if self._config_path is None:
            self._config_path = Path("app/config/verification_file_whitelist.yaml")
        return self._config_path
    

    def _load_config(self):
        """Load configuration from YAML file."""
        if not self._config_path or not self._config_path.exists():
            logger.warning(f"File whitelist config not found: {self._config_path}, using defaults")
            self._config = self._get_default_config()
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load file whitelist config: {e}")
            self._config = self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "enabled_categories": ["legal", "financial", "compliance"],
            "file_types": {
                "allowed_extensions": [".pdf", ".doc", ".docx", ".txt", ".json"],
                "max_file_size_mb": 50,
            },
            "categories": {
                "legal": {
                    "enabled": True,
                    "required": True,
                    "file_types": [".pdf", ".doc", ".docx"],
                },
                "financial": {
                    "enabled": True,
                    "required": False,
                    "file_types": [".pdf", ".xlsx", ".csv"],
                },
                "compliance": {"enabled": True, "required": False, "file_types": [".pdf", ".doc"]},
                "supporting": {
                    "enabled": False,
                    "required": False,
                    "file_types": [".pdf", ".jpg", ".png"],
                },
            },
            "subdirectories": {
                "documents": {"enabled": True, "priority": 1},
                "extractions": {"enabled": True, "priority": 2},
                "generated": {"enabled": False, "priority": 3},
                "notes": {"enabled": False, "priority": 4},
            },
        }

    def is_file_allowed(self, filename: str, category: Optional[str] = None) -> bool:
        """Check if file is allowed based on whitelist."""
        if not self._config:
            return True  # Allow all if no config

        # Check extension
        ext = Path(filename).suffix.lower()
        allowed_exts = self._config.get("file_types", {}).get("allowed_extensions", [])
        if ext not in allowed_exts:
            return False

        # Check category if specified
        if category:
            cat_config = self._config.get("categories", {}).get(category, {})
            if not cat_config.get("enabled", False):
                return False
            cat_file_types = cat_config.get("file_types", [])
            if ext not in cat_file_types:
                return False

        return True

    def get_enabled_categories(self) -> List[str]:
        """Get list of enabled categories."""
        if not self._config:
            return []
        return [
            cat
            for cat, config in self._config.get("categories", {}).items()
            if config.get("enabled", False)
        ]

    def get_required_categories(self) -> List[str]:
        """Get list of required categories."""
        if not self._config:
            return []
        return [
            cat
            for cat, config in self._config.get("categories", {}).items()
            if config.get("required", False)
        ]

    def get_enabled_subdirectories(self) -> List[str]:
        """Get list of enabled subdirectories."""
        if not self._config:
            return ["documents"]
        return [
            subdir
            for subdir, config in self._config.get("subdirectories", {}).items()
            if config.get("enabled", True)
        ]
    
    def reload(self):
        """Reload configuration from file.
        
        Thread-safe reload that updates the singleton instance and
        notifies registered callbacks of changes.
        """
        with self._lock:
            self._load_config()
            self._notify_change()
    
    def _notify_change(self):
        """Notify registered callbacks of config changes."""
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in config change callback: {e}")
    
    def register_change_callback(self, callback: Callable):
        """Register a callback to be called when config changes.
        
        Args:
            callback: Function to call when configuration is reloaded.
        """
        self._change_callbacks.append(callback)
    
    def is_file_size_allowed(self, file_size_bytes: int) -> bool:
        """Check if file size is within allowed limits.
        
        Args:
            file_size_bytes: File size in bytes.
            
        Returns:
            True if file size is within limits, False otherwise.
        """
        if not self._config:
            return True
        
        max_size_mb = self._config.get("file_types", {}).get("max_file_size_mb", 50)
        max_size_bytes = max_size_mb * 1024 * 1024
        return file_size_bytes <= max_size_bytes
    
    def category_exists(self, category: str) -> bool:
        """Check if category exists in configuration.
        
        Args:
            category: Category name to check.
            
        Returns:
            True if category exists, False otherwise.
        """
        if not self._config:
            return False
        return category in self._config.get("categories", {})
    
    def get_category_file_types(self, category: str) -> List[str]:
        """Get allowed file types for a category.
        
        Args:
            category: Category name.
            
        Returns:
            List of allowed file extensions for the category.
        """
        if not self._config:
            return []
        cat_config = self._config.get("categories", {}).get(category, {})
        return cat_config.get("file_types", [])
    
    def is_subdirectory_enabled(self, subdirectory: str) -> bool:
        """Check if subdirectory is enabled.
        
        Args:
            subdirectory: Subdirectory name to check.
            
        Returns:
            True if subdirectory is enabled, False otherwise.
        """
        if not self._config:
            return subdirectory == "documents"  # Default
        subdir_config = self._config.get("subdirectories", {}).get(subdirectory, {})
        return subdir_config.get("enabled", False)
    
    def get_subdirectory_priority(self, subdirectory: str) -> int:
        """Get priority for subdirectory (lower = higher priority).
        
        Args:
            subdirectory: Subdirectory name.
            
        Returns:
            Priority value (lower numbers = higher priority).
        """
        if not self._config:
            return 1
        subdir_config = self._config.get("subdirectories", {}).get(subdirectory, {})
        return subdir_config.get("priority", 999)
    
    def get_config_version(self) -> int:
        """Get current configuration version.
        
        Returns:
            Configuration version number.
        """
        if not self._config:
            return 1
        return self._config.get("_version", 1)
    
    def _increment_version(self):
        """Increment configuration version."""
        if self._config:
            current_version = self._config.get("_version", 1)
            self._config["_version"] = current_version + 1