"""Workflow type definitions and registry for link-based workflow delegation."""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

logger = None  # Will be initialized if needed


class WorkflowType(str, Enum):
    """Supported workflow types for link-based delegation."""
    
    VERIFICATION = "verification"
    NOTARIZATION = "notarization"
    DOCUMENT_REVIEW = "document_review"
    DEAL_APPROVAL = "deal_approval"
    DEAL_REVIEW = "deal_review"
    SIGNATURE = "signature"
    COMPLIANCE_CHECK = "compliance_check"
    CUSTOM = "custom"


class WorkflowTypeMetadata(BaseModel):
    """Metadata schema for workflow type configuration."""
    
    workflow_type: WorkflowType = Field(..., description="Workflow type identifier")
    title: str = Field(..., description="Human-readable workflow title")
    description: str = Field(..., description="Workflow description")
    required_actions: list[str] = Field(default_factory=list, description="Required actions for workflow completion")
    allowed_actions: list[str] = Field(default_factory=list, description="Allowed actions in workflow")
    default_whitelist_categories: list[str] = Field(
        default_factory=list, 
        description="Default file categories to include in whitelist"
    )
    default_expires_in_hours: int = Field(72, description="Default expiration time in hours")
    requires_authentication: bool = Field(True, description="Whether workflow requires user authentication")
    supports_batch: bool = Field(False, description="Whether workflow supports batch processing")
    metadata_schema: Optional[Dict[str, Any]] = Field(
        None, 
        description="Optional JSON schema for workflow-specific metadata"
    )


# Workflow Type Registry
WORKFLOW_TYPE_REGISTRY: Dict[WorkflowType, WorkflowTypeMetadata] = {
    WorkflowType.VERIFICATION: WorkflowTypeMetadata(
        workflow_type=WorkflowType.VERIFICATION,
        title="Deal Verification",
        description="Verify deal documents and CDM compliance",
        required_actions=["accept", "decline"],
        allowed_actions=["view", "download", "comment"],
        default_whitelist_categories=["legal", "financial", "compliance"],
        default_expires_in_hours=72,
        requires_authentication=True,
        supports_batch=False,
        metadata_schema={
            "type": "object",
            "properties": {
                "verification_id": {"type": "string"},
                "verifier_user_id": {"type": "integer"},
                "verification_metadata": {"type": "object"}
            }
        }
    ),
    
    WorkflowType.NOTARIZATION: WorkflowTypeMetadata(
        workflow_type=WorkflowType.NOTARIZATION,
        title="Document Notarization",
        description="Notarize documents with blockchain signatures",
        required_actions=["sign", "verify"],
        allowed_actions=["view", "download", "sign"],
        default_whitelist_categories=["legal"],
        default_expires_in_hours=168,  # 7 days
        requires_authentication=True,
        supports_batch=False,
        metadata_schema={
            "type": "object",
            "properties": {
                "notarization_id": {"type": "integer"},
                "required_signers": {"type": "array", "items": {"type": "string"}},
                "message_prefix": {"type": "string"}
            }
        }
    ),
    
    WorkflowType.DOCUMENT_REVIEW: WorkflowTypeMetadata(
        workflow_type=WorkflowType.DOCUMENT_REVIEW,
        title="Document Review",
        description="Review and approve document revisions",
        required_actions=["approve", "reject", "request_changes"],
        allowed_actions=["view", "download", "comment", "request_changes"],
        default_whitelist_categories=["legal", "financial", "compliance"],
        default_expires_in_hours=120,  # 5 days
        requires_authentication=True,
        supports_batch=True,
        metadata_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer"},
                "document_version": {"type": "integer"},
                "review_type": {"type": "string", "enum": ["legal", "financial", "compliance", "general"]},
                "review_instructions": {"type": "string"}
            }
        }
    ),
    
    WorkflowType.DEAL_APPROVAL: WorkflowTypeMetadata(
        workflow_type=WorkflowType.DEAL_APPROVAL,
        title="Deal Approval",
        description="Approve or reject deal proposals",
        required_actions=["approve", "reject"],
        allowed_actions=["view", "download", "comment", "request_changes"],
        default_whitelist_categories=["legal", "financial", "compliance"],
        default_expires_in_hours=168,  # 7 days
        requires_authentication=True,
        supports_batch=False,
        metadata_schema={
            "type": "object",
            "properties": {
                "deal_id": {"type": "integer"},
                "approval_level": {"type": "string", "enum": ["initial", "final", "executive"]},
                "approval_requirements": {"type": "array", "items": {"type": "string"}}
            }
        }
    ),
    
    WorkflowType.DEAL_REVIEW: WorkflowTypeMetadata(
        workflow_type=WorkflowType.DEAL_REVIEW,
        title="Deal Review",
        description="Review deal details and provide feedback",
        required_actions=["submit_review"],
        allowed_actions=["view", "download", "comment", "request_changes"],
        default_whitelist_categories=["legal", "financial", "compliance"],
        default_expires_in_hours=120,  # 5 days
        requires_authentication=True,
        supports_batch=False,
        metadata_schema={
            "type": "object",
            "properties": {
                "deal_id": {"type": "integer"},
                "review_focus": {"type": "array", "items": {"type": "string"}},
                "review_questions": {"type": "array", "items": {"type": "string"}}
            }
        }
    ),
    
    WorkflowType.SIGNATURE: WorkflowTypeMetadata(
        workflow_type=WorkflowType.SIGNATURE,
        title="Document Signature",
        description="Sign documents electronically",
        required_actions=["sign"],
        allowed_actions=["view", "download", "sign"],
        default_whitelist_categories=["legal"],
        default_expires_in_hours=168,  # 7 days
        requires_authentication=True,
        supports_batch=True,
        metadata_schema={
            "type": "object",
            "properties": {
                "document_id": {"type": "integer"},
                "signature_type": {"type": "string", "enum": ["electronic", "digital", "wet"]},
                "signature_requirements": {"type": "array", "items": {"type": "string"}}
            }
        }
    ),
    
    WorkflowType.COMPLIANCE_CHECK: WorkflowTypeMetadata(
        workflow_type=WorkflowType.COMPLIANCE_CHECK,
        title="Compliance Check",
        description="Perform compliance verification and checks",
        required_actions=["verify", "flag_issues"],
        allowed_actions=["view", "download", "comment", "flag_issues"],
        default_whitelist_categories=["compliance", "legal"],
        default_expires_in_hours=120,  # 5 days
        requires_authentication=True,
        supports_batch=False,
        metadata_schema={
            "type": "object",
            "properties": {
                "compliance_type": {"type": "string", "enum": ["regulatory", "policy", "cdm", "custom"]},
                "checklist": {"type": "array", "items": {"type": "string"}},
                "regulations": {"type": "array", "items": {"type": "string"}}
            }
        }
    ),
    
    WorkflowType.CUSTOM: WorkflowTypeMetadata(
        workflow_type=WorkflowType.CUSTOM,
        title="Custom Workflow",
        description="Custom workflow with extensible metadata",
        required_actions=[],
        allowed_actions=["view", "download", "comment"],
        default_whitelist_categories=[],
        default_expires_in_hours=72,
        requires_authentication=True,
        supports_batch=False,
        metadata_schema=None  # Fully extensible
    )
}


def get_workflow_metadata(workflow_type: WorkflowType) -> Optional[WorkflowTypeMetadata]:
    """Get metadata for a workflow type.
    
    Args:
        workflow_type: Workflow type enum value
        
    Returns:
        WorkflowTypeMetadata if found, None otherwise
    """
    return WORKFLOW_TYPE_REGISTRY.get(workflow_type)


def register_custom_workflow_type(
    workflow_type: str,
    title: str,
    description: str,
    required_actions: Optional[list[str]] = None,
    allowed_actions: Optional[list[str]] = None,
    default_whitelist_categories: Optional[list[str]] = None,
    default_expires_in_hours: int = 72,
    requires_authentication: bool = True,
    supports_batch: bool = False,
    metadata_schema: Optional[Dict[str, Any]] = None
) -> bool:
    """Register a custom workflow type at runtime.
    
    Args:
        workflow_type: Custom workflow type identifier (must be unique)
        title: Human-readable title
        description: Workflow description
        required_actions: List of required actions
        allowed_actions: List of allowed actions
        default_whitelist_categories: Default file categories
        default_expires_in_hours: Default expiration time
        requires_authentication: Whether authentication is required
        supports_batch: Whether batch processing is supported
        metadata_schema: Optional JSON schema for metadata
        
    Returns:
        True if registered successfully, False if workflow_type already exists
    """
    # Check if workflow_type is already in registry
    for existing_type in WorkflowType:
        if existing_type.value == workflow_type:
            return False
    
    # Create custom workflow type enum value (runtime extension not supported by Enum)
    # Instead, we'll store custom types in a separate registry
    if not hasattr(register_custom_workflow_type, '_custom_registry'):
        register_custom_workflow_type._custom_registry = {}
    
    if workflow_type in register_custom_workflow_type._custom_registry:
        return False
    
    metadata = WorkflowTypeMetadata(
        workflow_type=WorkflowType.CUSTOM,  # Use CUSTOM as base
        title=title,
        description=description,
        required_actions=required_actions or [],
        allowed_actions=allowed_actions or ["view", "download", "comment"],
        default_whitelist_categories=default_whitelist_categories or [],
        default_expires_in_hours=default_expires_in_hours,
        requires_authentication=requires_authentication,
        supports_batch=supports_batch,
        metadata_schema=metadata_schema
    )
    
    register_custom_workflow_type._custom_registry[workflow_type] = metadata
    return True


def validate_workflow_type(workflow_type: str) -> bool:
    """Validate that a workflow type exists in the registry.
    
    Args:
        workflow_type: Workflow type string identifier
        
    Returns:
        True if workflow type is valid, False otherwise
    """
    # Check standard workflow types
    try:
        wt_enum = WorkflowType(workflow_type)
        return wt_enum in WORKFLOW_TYPE_REGISTRY
    except ValueError:
        pass
    
    # Check custom workflow types
    if hasattr(register_custom_workflow_type, '_custom_registry'):
        return workflow_type in register_custom_workflow_type._custom_registry
    
    return False


def get_custom_workflow_metadata(workflow_type: str) -> Optional[WorkflowTypeMetadata]:
    """Get metadata for a custom workflow type.
    
    Args:
        workflow_type: Custom workflow type identifier
        
    Returns:
        WorkflowTypeMetadata if found, None otherwise
    """
    if hasattr(register_custom_workflow_type, '_custom_registry'):
        return register_custom_workflow_type._custom_registry.get(workflow_type)
    return None
