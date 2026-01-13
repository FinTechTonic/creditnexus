"""Dynamic whitelist service for context-aware file filtering in workflow links."""

import logging
from typing import Dict, Any, Optional, List
from app.core.verification_file_config import VerificationFileConfig
from app.core.workflow_types import WorkflowType, get_workflow_metadata

logger = logging.getLogger(__name__)


class DynamicWhitelistService:
    """Service for context-aware file whitelist filtering.
    
    Provides dynamic whitelist configuration based on:
    - Workflow type
    - Deal type
    - User role
    - Custom overrides
    """

    def __init__(self):
        """Initialize dynamic whitelist service."""
        self.file_config = VerificationFileConfig()

    def get_whitelist_for_workflow(
        self,
        workflow_type: WorkflowType,
        deal_id: Optional[int] = None,
        user_role: Optional[str] = None,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get whitelist configuration for specific workflow context.
        
        Args:
            workflow_type: Workflow type enum
            deal_id: Optional deal ID for deal-specific overrides
            user_role: Optional user role for role-specific overrides
            custom_config: Optional custom configuration overrides
            
        Returns:
            Merged whitelist configuration dictionary
        """
        # 1. Load base config from VerificationFileConfig
        base_config = self._get_base_config()
        
        # 2. Apply workflow-type-specific overrides
        workflow_config = self._get_workflow_type_config(workflow_type)
        
        # 3. Apply deal-type-specific overrides (if deal_id provided)
        deal_config = {}
        if deal_id:
            deal_config = self._get_deal_type_config(deal_id)
        
        # 4. Apply user-role-specific overrides (if user_role provided)
        role_config = {}
        if user_role:
            role_config = self._get_user_role_config(user_role)
        
        # 5. Apply custom config overrides (highest priority)
        custom = custom_config or {}
        
        # 6. Merge configurations (custom > role > deal > workflow > base)
        merged_config = self._merge_configs(
            base_config,
            workflow_config,
            deal_config,
            role_config,
            custom
        )
        
        logger.debug(f"Generated whitelist config for workflow {workflow_type.value}")
        return merged_config

    def filter_files_by_whitelist(
        self,
        file_references: List[Dict[str, Any]],
        whitelist_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Filter file references based on whitelist configuration.
        
        Args:
            file_references: List of file reference dictionaries
            whitelist_config: Whitelist configuration dictionary
            
        Returns:
            Filtered list of file references
        """
        filtered_files = []
        
        # Get whitelist settings
        enabled_categories = whitelist_config.get("enabled_categories", [])
        allowed_extensions = whitelist_config.get("file_types", {}).get("allowed_extensions", [])
        max_file_size_mb = whitelist_config.get("file_types", {}).get("max_file_size_mb", 50)
        enabled_subdirectories = [
            subdir for subdir, config in whitelist_config.get("subdirectories", {}).items()
            if config.get("enabled", True)
        ]
        
        max_file_size_bytes = max_file_size_mb * 1024 * 1024
        
        for file_ref in file_references:
            # Check category
            category = file_ref.get("category", "")
            if enabled_categories and category not in enabled_categories:
                continue
            
            # Check file extension
            filename = file_ref.get("filename", "")
            if filename:
                ext = "." + filename.split(".")[-1] if "." in filename else ""
                if allowed_extensions and ext not in allowed_extensions:
                    continue
            
            # Check file size
            file_size = file_ref.get("size", 0)
            if file_size > max_file_size_bytes:
                logger.warning(f"File {filename} exceeds size limit: {file_size} > {max_file_size_bytes}")
                continue
            
            # Check subdirectory
            subdirectory = file_ref.get("subdirectory", "")
            if enabled_subdirectories and subdirectory not in enabled_subdirectories:
                continue
            
            # Check category-specific file types
            if category:
                category_config = whitelist_config.get("categories", {}).get(category, {})
                if category_config:
                    category_enabled = category_config.get("enabled", True)
                    if not category_enabled:
                        continue
                    
                    category_file_types = category_config.get("file_types", [])
                    if category_file_types and ext not in category_file_types:
                        continue
            
            filtered_files.append(file_ref)
        
        logger.debug(f"Filtered {len(file_references)} files to {len(filtered_files)} based on whitelist")
        return filtered_files

    def update_whitelist_from_link(
        self,
        link_payload: Dict[str, Any],
        user_id: Optional[int] = None,
        require_admin: bool = True,
    ) -> bool:
        """Update whitelist configuration from link payload.
        
        Args:
            link_payload: Parsed workflow link payload
            user_id: Optional user ID for permission checking
            require_admin: Whether admin role is required for updates
            
        Returns:
            True if update was successful, False otherwise
        """
        whitelist_config = link_payload.get("whitelist_config")
        if not whitelist_config:
            logger.debug("No whitelist config in link payload")
            return False
        
        # Check permissions if required
        if require_admin and user_id:
            from app.db.models import User, UserRole
            from app.db import get_db
            db = next(get_db())
            user = db.query(User).filter(User.id == user_id).first()
            if not user or user.role != UserRole.ADMIN.value:
                logger.warning(f"User {user_id} attempted to update whitelist without admin role")
                return False
        
        # Validate config structure
        validation_errors = self._validate_config_structure(whitelist_config)
        if validation_errors:
            logger.error(f"Invalid whitelist config structure: {validation_errors}")
            return False
        
        # Update VerificationFileConfig
        try:
            # Merge with existing config (don't overwrite completely)
            existing_config = self.file_config._config or {}
            merged_config = self._merge_configs(existing_config, whitelist_config)
            
            # Write to file
            import yaml
            config_path = self.file_config.config_path
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(merged_config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            # Reload config
            self.file_config.reload()
            
            logger.info(f"Updated whitelist config from link payload (user: {user_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update whitelist config: {e}")
            return False

    def get_whitelist_for_deal_type(self, deal_type: str) -> Dict[str, Any]:
        """Get deal-type-specific whitelist overrides.
        
        Args:
            deal_type: Deal type identifier (e.g., "sustainability_linked_loan", "syndicated_loan")
            
        Returns:
            Whitelist configuration overrides for deal type
        """
        # Deal-type-specific configurations
        deal_type_configs = {
            "sustainability_linked_loan": {
                "enabled_categories": ["legal", "financial", "compliance"],
                "categories": {
                    "compliance": {
                        "enabled": True,
                        "required": True,  # ESG compliance is required for SLL
                    }
                }
            },
            "syndicated_loan": {
                "enabled_categories": ["legal", "financial"],
                "categories": {
                    "legal": {
                        "enabled": True,
                        "required": True,
                    }
                }
            },
            "trade_finance": {
                "enabled_categories": ["legal", "financial", "compliance"],
                "file_types": {
                    "allowed_extensions": [".pdf", ".doc", ".docx", ".xlsx", ".csv", ".xml"]
                }
            }
        }
        
        return deal_type_configs.get(deal_type, {})

    def get_whitelist_for_user_role(self, user_role: str) -> Dict[str, Any]:
        """Get role-specific whitelist overrides.
        
        Args:
            user_role: User role identifier (e.g., "LAW_OFFICER", "BANKER", "AUDITOR")
            
        Returns:
            Whitelist configuration overrides for user role
        """
        # Role-specific configurations
        role_configs = {
            "LAW_OFFICER": {
                "enabled_categories": ["legal"],
                "categories": {
                    "legal": {
                        "enabled": True,
                        "required": True,
                    }
                }
            },
            "BANKER": {
                "enabled_categories": ["legal", "financial"],
                "categories": {
                    "financial": {
                        "enabled": True,
                        "required": True,
                    }
                }
            },
            "AUDITOR": {
                "enabled_categories": ["legal", "financial", "compliance"],
                "categories": {
                    "compliance": {
                        "enabled": True,
                        "required": True,
                    }
                }
            }
        }
        
        return role_configs.get(user_role, {})

    def _get_base_config(self) -> Dict[str, Any]:
        """Get base configuration from VerificationFileConfig."""
        if not self.file_config._config:
            return self.file_config._get_default_config()
        return self.file_config._config.copy()

    def _get_workflow_type_config(self, workflow_type: WorkflowType) -> Dict[str, Any]:
        """Get workflow-type-specific configuration."""
        metadata = get_workflow_metadata(workflow_type)
        if not metadata:
            return {}
        
        # Build config from workflow metadata
        config = {}
        
        # Use default_whitelist_categories from metadata
        if metadata.default_whitelist_categories:
            config["enabled_categories"] = metadata.default_whitelist_categories
        
        return config

    def _get_deal_type_config(self, deal_id: int) -> Dict[str, Any]:
        """Get deal-type-specific configuration."""
        try:
            from app.db import get_db
            from app.db.models import Deal
            
            db = next(get_db())
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            
            if deal and deal.deal_type:
                return self.get_whitelist_for_deal_type(deal.deal_type)
        except Exception as e:
            logger.warning(f"Failed to get deal type config for deal {deal_id}: {e}")
        
        return {}

    def _get_user_role_config(self, user_role: str) -> Dict[str, Any]:
        """Get user-role-specific configuration."""
        return self.get_whitelist_for_user_role(user_role)

    def _merge_configs(
        self,
        base: Dict[str, Any],
        workflow: Dict[str, Any],
        deal: Dict[str, Any],
        role: Dict[str, Any],
        custom: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries with priority: custom > role > deal > workflow > base."""
        merged = base.copy()
        
        # Merge in priority order
        for config in [workflow, deal, role, custom]:
            merged = self._deep_merge(merged, config)
        
        return merged

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result

    def _validate_config_structure(self, config: Dict[str, Any]) -> List[str]:
        """Validate whitelist configuration structure.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return errors
        
        # Validate enabled_categories
        if "enabled_categories" in config:
            if not isinstance(config["enabled_categories"], list):
                errors.append("enabled_categories must be a list")
        
        # Validate file_types
        if "file_types" in config:
            file_types = config["file_types"]
            if not isinstance(file_types, dict):
                errors.append("file_types must be a dictionary")
            else:
                if "allowed_extensions" in file_types:
                    if not isinstance(file_types["allowed_extensions"], list):
                        errors.append("file_types.allowed_extensions must be a list")
                if "max_file_size_mb" in file_types:
                    if not isinstance(file_types["max_file_size_mb"], (int, float)):
                        errors.append("file_types.max_file_size_mb must be a number")
                    elif file_types["max_file_size_mb"] <= 0:
                        errors.append("file_types.max_file_size_mb must be greater than 0")
        
        # Validate categories
        if "categories" in config:
            categories = config["categories"]
            if not isinstance(categories, dict):
                errors.append("categories must be a dictionary")
            else:
                for cat_name, cat_config in categories.items():
                    if not isinstance(cat_config, dict):
                        errors.append(f"categories.{cat_name} must be a dictionary")
                        continue
                    if "enabled" in cat_config and not isinstance(cat_config["enabled"], bool):
                        errors.append(f"categories.{cat_name}.enabled must be a boolean")
                    if "required" in cat_config and not isinstance(cat_config["required"], bool):
                        errors.append(f"categories.{cat_name}.required must be a boolean")
                    if "file_types" in cat_config:
                        if not isinstance(cat_config["file_types"], list):
                            errors.append(f"categories.{cat_name}.file_types must be a list")
        
        # Validate subdirectories
        if "subdirectories" in config:
            subdirs = config["subdirectories"]
            if not isinstance(subdirs, dict):
                errors.append("subdirectories must be a dictionary")
            else:
                for subdir_name, subdir_config in subdirs.items():
                    if not isinstance(subdir_config, dict):
                        errors.append(f"subdirectories.{subdir_name} must be a dictionary")
                        continue
                    if "enabled" in subdir_config and not isinstance(subdir_config["enabled"], bool):
                        errors.append(f"subdirectories.{subdir_name}.enabled must be a boolean")
                    if "priority" in subdir_config:
                        if not isinstance(subdir_config["priority"], int):
                            errors.append(f"subdirectories.{subdir_name}.priority must be an integer")
                        elif subdir_config["priority"] < 0:
                            errors.append(f"subdirectories.{subdir_name}.priority must be non-negative")
        
        return errors
