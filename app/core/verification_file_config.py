"""File whitelist configuration for verification links."""

import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class VerificationFileConfig:
    """Loads and manages file whitelist configuration from YAML."""

    def __init__(self, config_path: Optional[Path] = None):
        if not config_path:
            config_path = Path("app/config/verification_file_whitelist.yaml")
        self.config_path = config_path
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            logger.warning(f"File whitelist config not found: {self.config_path}, using defaults")
            self._config = self._get_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
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
