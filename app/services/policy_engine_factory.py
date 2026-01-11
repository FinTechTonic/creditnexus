"""
Policy Engine Factory for CreditNexus.

Provides factory functions for creating policy engine instances based on
vendor configuration. Supports multiple policy engine implementations
through a vendor-agnostic interface.
"""

import logging
from typing import Optional
from pathlib import Path

from app.services.policy_engine_interface import PolicyEngineInterface, MockPolicyEngine

logger = logging.getLogger(__name__)


def get_policy_engine(vendor: Optional[str] = None) -> PolicyEngineInterface:
    """
    Get a policy engine instance (convenience wrapper for create_policy_engine).
    
    This function provides a consistent interface for obtaining policy engine
    instances. It reads the vendor from environment configuration if not provided.
    
    Args:
        vendor: Policy engine vendor identifier (defaults to environment setting or "default")
        
    Returns:
        PolicyEngineInterface instance
    """
    # Try to get vendor from environment if not provided
    if vendor is None:
        try:
            from app.core.config import settings
            vendor = settings.POLICY_ENGINE_VENDOR
        except Exception:
            # If config not available, use default
            vendor = "default"
    
    return create_policy_engine(vendor=vendor)


def create_policy_engine(vendor: Optional[str] = None) -> PolicyEngineInterface:
    """
    Create a policy engine instance based on vendor configuration.
    
    Supported vendors:
    - "default" or None: MockPolicyEngine (for development/testing)
    - "aspasia": Aspasia policy engine (if available)
    - "custom": Custom policy engine implementation
    
    Args:
        vendor: Policy engine vendor identifier (defaults to "default")
        
    Returns:
        PolicyEngineInterface instance
        
    Raises:
        ValueError: If vendor is unsupported
        RuntimeError: If engine initialization fails
    """
    vendor = vendor or "default"
    vendor_lower = vendor.lower()
    
    if vendor_lower == "default":
        logger.info("Creating default (mock) policy engine")
        return MockPolicyEngine()
    
    elif vendor_lower == "aspasia":
        # Future: Integrate with Aspasia policy engine
        # For now, fall back to mock
        logger.warning("Aspasia policy engine not yet implemented, using mock engine")
        return MockPolicyEngine()
    
    elif vendor_lower == "custom":
        # Future: Load custom policy engine implementation
        logger.warning("Custom policy engine not yet implemented, using mock engine")
        return MockPolicyEngine()
    
    else:
        raise ValueError(
            f"Unsupported policy engine vendor: {vendor}. "
            f"Supported vendors: 'default', 'aspasia', 'custom'"
        )


def load_policy_rules(rules_path: Path) -> str:
    """
    Load policy rules from a YAML file.
    
    Args:
        rules_path: Path to YAML file containing policy rules
        
    Returns:
        YAML string containing policy rules
        
    Raises:
        FileNotFoundError: If rules file does not exist
        ValueError: If file cannot be read or is invalid
    """
    if not rules_path.exists():
        raise FileNotFoundError(f"Policy rules file not found: {rules_path}")
    
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules_yaml = f.read()
        
        if not rules_yaml.strip():
            logger.warning(f"Policy rules file is empty: {rules_path}")
            return ""
        
        return rules_yaml
    
    except Exception as e:
        raise ValueError(f"Failed to load policy rules from {rules_path}: {e}") from e

















