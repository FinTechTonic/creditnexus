"""Configuration API routes for CreditNexus.

Provides endpoints for managing system configuration, including verification
file whitelist configuration.
"""

import yaml
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.verification_file_config import VerificationFileConfig
from app.db import get_db
from app.auth.jwt_auth import require_auth as require_jwt_auth
from app.db.models import User, AuditAction, UserRole
from app.utils.audit import log_audit_action

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["configuration"])


class ConfigYAMLRequest(BaseModel):
    """Request model for updating configuration.
    
    Attributes:
        yaml: YAML configuration content as a string. Must be valid YAML syntax.
    """
    yaml: str = Field(..., description="YAML configuration content", min_length=1)
    
    @field_validator('yaml')
    @classmethod
    def validate_yaml(cls, v: str) -> str:
        """Validate YAML syntax.
        
        Args:
            v: YAML string to validate.
            
        Returns:
            Validated YAML string.
            
        Raises:
            ValueError: If YAML syntax is invalid.
        """
        try:
            yaml.safe_load(v)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax: {str(e)}")
        return v


class ConfigYAMLResponse(BaseModel):
    """Response model for configuration retrieval.
    
    Attributes:
        yaml: Current YAML configuration content.
        config: Parsed configuration as JSON (dict).
        last_modified: ISO format timestamp of last modification, or None if using defaults.
        version: Configuration version number, or None if not versioned.
    """
    yaml: str
    config: Optional[Dict[str, Any]] = None
    last_modified: Optional[str] = None
    version: Optional[int] = None


class ConfigUpdateResponse(BaseModel):
    """Response model for configuration update operation.
    
    Attributes:
        status: Operation status (typically "success").
        message: Human-readable message describing the result.
        last_modified: ISO format timestamp of the update.
    """
    status: str
    message: str
    last_modified: str


def _validate_config_structure(config_dict: dict) -> List[str]:
    """Validate configuration structure and return list of errors.
    
    Validates the structure of the verification file whitelist configuration,
    checking that required sections exist and have correct types.
    
    Args:
        config_dict: Parsed YAML configuration as a dictionary.
        
    Returns:
        List of validation error messages. Empty list if validation passes.
        
    Note:
        This function performs structural validation only. It does not validate
        business logic or semantic correctness of the configuration values.
    """
    errors = []
    
    if not isinstance(config_dict, dict):
        errors.append("Configuration must be a YAML object")
        return errors
    
    # Validate enabled_categories
    if "enabled_categories" in config_dict:
        if not isinstance(config_dict["enabled_categories"], list):
            errors.append("enabled_categories must be a list")
    
    # Validate file_types
    if "file_types" in config_dict:
        file_types = config_dict["file_types"]
        if not isinstance(file_types, dict):
            errors.append("file_types must be an object")
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
    if "categories" in config_dict:
        categories = config_dict["categories"]
        if not isinstance(categories, dict):
            errors.append("categories must be an object")
        else:
            for cat_name, cat_config in categories.items():
                if not isinstance(cat_config, dict):
                    errors.append(f"categories.{cat_name} must be an object")
                    continue
                if "enabled" in cat_config and not isinstance(cat_config["enabled"], bool):
                    errors.append(f"categories.{cat_name}.enabled must be a boolean")
                if "required" in cat_config and not isinstance(cat_config["required"], bool):
                    errors.append(f"categories.{cat_name}.required must be a boolean")
                if "file_types" in cat_config:
                    if not isinstance(cat_config["file_types"], list):
                        errors.append(f"categories.{cat_name}.file_types must be a list")
    
    # Validate subdirectories
    if "subdirectories" in config_dict:
        subdirs = config_dict["subdirectories"]
        if not isinstance(subdirs, dict):
            errors.append("subdirectories must be an object")
        else:
            for subdir_name, subdir_config in subdirs.items():
                if not isinstance(subdir_config, dict):
                    errors.append(f"subdirectories.{subdir_name} must be an object")
                    continue
                if "enabled" in subdir_config and not isinstance(subdir_config["enabled"], bool):
                    errors.append(f"subdirectories.{subdir_name}.enabled must be a boolean")
                if "priority" in subdir_config:
                    if not isinstance(subdir_config["priority"], int):
                        errors.append(f"subdirectories.{subdir_name}.priority must be an integer")
                    elif subdir_config["priority"] < 0:
                        errors.append(f"subdirectories.{subdir_name}.priority must be non-negative")
    
    return errors


@router.get("/verification-file-whitelist", response_model=ConfigYAMLResponse)
async def get_verification_file_config(
    current_user: User = Depends(require_jwt_auth),
    db: Session = Depends(get_db)
):
    """
    Get current verification file whitelist configuration.
    
    Retrieves the current YAML configuration file for verification file whitelisting.
    If the configuration file doesn't exist, returns the default configuration.
    
    Args:
        current_user: Authenticated admin user (from dependency injection).
        db: Database session (from dependency injection).
        
    Returns:
        ConfigYAMLResponse containing:
            - yaml: The configuration YAML content
            - last_modified: ISO timestamp of file modification
            - version: Configuration version number if available
            
    Raises:
        HTTPException: 
            - 403 if user is not an admin
            - 500 if configuration cannot be loaded.
        
    Requires:
        Admin role (enforced via role check).
    """
    # Check admin role
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    
    try:
        config = VerificationFileConfig()
        config_path = config.config_path
        
        # Read YAML file
        if not config_path.exists():
            # Return default config as YAML
            default_config = config._get_default_config()
            yaml_content = yaml.dump(default_config, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return ConfigYAMLResponse(
                yaml=yaml_content,
                config=default_config,
                last_modified=None,
                version=1
            )
        
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_content = f.read()
        
        # Parse YAML to dict
        try:
            config_dict = yaml.safe_load(yaml_content)
            if config_dict is None:
                config_dict = {}
        except Exception as e:
            logger.warning(f"Failed to parse YAML, using empty config: {e}")
            config_dict = {}
        
        # Get file modification time
        mtime = os.path.getmtime(config_path)
        last_modified = datetime.fromtimestamp(mtime).isoformat()
        
        # Try to get version from config
        version = config_dict.get("_version", None)
        
        return ConfigYAMLResponse(
            yaml=yaml_content,
            config=config_dict,
            last_modified=last_modified,
            version=version
        )
    except Exception as e:
        logger.error(f"Failed to load config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load configuration: {str(e)}"
        )


@router.post("/verification-file-whitelist", response_model=ConfigUpdateResponse)
async def update_verification_file_config(
    request: ConfigYAMLRequest,
    current_user: User = Depends(require_jwt_auth),
    db: Session = Depends(get_db),
    http_request: Request = None
):
    """
    Update verification file whitelist configuration.
    
    Validates and saves a new verification file whitelist configuration.
    Creates a backup of the existing configuration before overwriting.
    Reloads the configuration singleton after successful save.
    Logs the update action for audit purposes.
    
    Args:
        request: ConfigYAMLRequest containing the YAML configuration to save.
        current_user: Authenticated admin user (from dependency injection).
        db: Database session (from dependency injection).
        http_request: HTTP request object for audit logging (optional).
        
    Returns:
        ConfigUpdateResponse containing:
            - status: "success"
            - message: Success message
            - last_modified: ISO timestamp of the update
            
    Raises:
        HTTPException: 
            - 403 if user is not an admin
            - 400 if configuration structure validation fails
            - 422 if YAML syntax is invalid (handled by Pydantic)
            - 500 if file write operation fails
            
    Requires:
        Admin role (enforced via role check).
        
    Side Effects:
        - Creates backup file (.yaml.backup) if existing config exists
        - Writes new configuration to file system
        - Reloads VerificationFileConfig singleton
        - Creates audit log entry
    """
    # Check admin role
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin permissions required"
        )
    
    try:
        # Validate YAML syntax (already done by Pydantic)
        config_dict = yaml.safe_load(request.yaml)
        
        # Validate configuration structure
        validation_errors = _validate_config_structure(config_dict)
        if validation_errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Configuration validation failed",
                    "validation_errors": validation_errors
                }
            )
        
        # Get config path
        config = VerificationFileConfig()
        config_path = config.config_path
        
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Backup existing config if it exists
        backup_path = None
        if config_path.exists():
            backup_path = config_path.with_suffix('.yaml.backup')
            try:
                shutil.copy2(config_path, backup_path)
                logger.info(f"Backed up config to {backup_path}")
            except Exception as e:
                logger.warning(f"Failed to create backup: {e}")
        
        # Write new config
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(request.yaml)
        except Exception as e:
            # Restore from backup if write failed
            if backup_path and backup_path.exists():
                try:
                    shutil.copy2(backup_path, config_path)
                    logger.info("Restored config from backup after write failure")
                except Exception as restore_error:
                    logger.error(f"Failed to restore from backup: {restore_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to write configuration file: {str(e)}"
            )
        
        # Reload config singleton
        try:
            config.reload()
        except AttributeError:
            # If reload method doesn't exist yet, reload manually
            config._load_config()
        
        # Log audit action
        try:
            log_audit_action(
                db=db,
                action=AuditAction.UPDATE,
                target_type="configuration",
                target_id=None,
                user_id=current_user.id,
                metadata={
                    "config_path": str(config_path),
                    "backup_path": str(backup_path) if backup_path else None,
                    "config_version": config_dict.get("_version", None)
                },
                request=http_request
            )
            db.commit()
        except Exception as e:
            logger.warning(f"Failed to log audit action: {e}")
            db.rollback()
        
        logger.info(f"Configuration updated by user {current_user.id} ({current_user.email})")
        
        return ConfigUpdateResponse(
            status="success",
            message="Configuration updated successfully",
            last_modified=datetime.utcnow().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update configuration: {str(e)}"
        )
