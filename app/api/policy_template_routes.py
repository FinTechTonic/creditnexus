"""
Policy Template API Routes for CreditNexus.

Provides endpoints for policy template management.
"""

import logging
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth.jwt_auth import require_auth, get_current_user
from app.db.models import User, PolicyTemplate
from app.services.policy_editor_service import PolicyEditorService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/policy-templates", tags=["policy-templates"])


# Request/Response Models

class CreateTemplateRequest(BaseModel):
    """Request model for creating a policy template."""
    name: str = Field(..., description="Template name")
    category: str = Field(..., description="Template category")
    description: Optional[str] = Field(None, description="Template description")
    rules_yaml: str = Field(..., description="Template YAML rules")
    use_case: Optional[str] = Field(None, description="Template use case")
    is_system_template: bool = Field(False, description="Whether this is a system template")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")


class UpdateTemplateRequest(BaseModel):
    """Request model for updating a policy template."""
    name: Optional[str] = Field(None, description="Template name")
    category: Optional[str] = Field(None, description="Template category")
    description: Optional[str] = Field(None, description="Template description")
    rules_yaml: Optional[str] = Field(None, description="Template YAML rules")
    use_case: Optional[str] = Field(None, description="Template use case")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Template metadata")


# Routes

@router.get("", response_model=Dict[str, Any])
async def get_templates(
    category: Optional[str] = Query(None, description="Filter by category"),
    use_case: Optional[str] = Query(None, description="Filter by use case"),
    is_system_template: Optional[bool] = Query(None, description="Filter by system template flag"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get list of policy templates.
    
    Args:
        category: Optional category filter
        use_case: Optional use case filter
        is_system_template: Optional system template filter
        limit: Maximum number of results
        offset: Offset for pagination
        db: Database session
        current_user: Authenticated user
        
    Returns:
        List of policy templates
    """
    try:
        query = db.query(PolicyTemplate)
        
        if category:
            query = query.filter(PolicyTemplate.category == category)
        if use_case:
            query = query.filter(PolicyTemplate.use_case == use_case)
        if is_system_template is not None:
            query = query.filter(PolicyTemplate.is_system_template == is_system_template)
        
        templates = query.order_by(PolicyTemplate.created_at.desc()).limit(limit).offset(offset).all()
        
        return {
            "status": "success",
            "templates": [template.to_dict() for template in templates],
            "count": len(templates),
            "limit": limit,
            "offset": offset
        }
    
    except Exception as e:
        logger.error(f"Error getting templates: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting templates: {str(e)}")


@router.get("/{template_id}", response_model=Dict[str, Any])
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get a specific policy template.
    
    Args:
        template_id: Template ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Policy template details
    """
    try:
        template = db.query(PolicyTemplate).filter(PolicyTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        return {
            "status": "success",
            "template": template.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting template: {str(e)}")


@router.post("", response_model=Dict[str, Any])
async def create_template(
    request: CreateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Create a new policy template.
    
    Args:
        request: CreateTemplateRequest with template data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Created template details
    """
    try:
        # Check if template with same name exists
        existing = db.query(PolicyTemplate).filter(
            PolicyTemplate.name == request.name
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Template with name '{request.name}' already exists")
        
        template = PolicyTemplate(
            name=request.name,
            category=request.category,
            description=request.description,
            rules_yaml=request.rules_yaml,
            use_case=request.use_case,
            metadata_=request.metadata,
            is_system_template=request.is_system_template,
            created_by=current_user.id
        )
        
        db.add(template)
        db.commit()
        db.refresh(template)
        
        return {
            "status": "success",
            "message": f"Template '{request.name}' created successfully",
            "template": template.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating template: {str(e)}")


@router.put("/{template_id}", response_model=Dict[str, Any])
async def update_template(
    template_id: int,
    request: UpdateTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Update a policy template.
    
    Args:
        template_id: Template ID
        request: UpdateTemplateRequest with updated data
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Updated template details
    """
    try:
        template = db.query(PolicyTemplate).filter(PolicyTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Only allow updating user-created templates (not system templates)
        if template.is_system_template and current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Only admins can update system templates"
            )
        
        # Update fields
        if request.name is not None:
            # Check for name conflicts
            existing = db.query(PolicyTemplate).filter(
                PolicyTemplate.name == request.name,
                PolicyTemplate.id != template_id
            ).first()
            if existing:
                raise HTTPException(status_code=400, detail=f"Template with name '{request.name}' already exists")
            template.name = request.name
        
        if request.category is not None:
            template.category = request.category
        if request.description is not None:
            template.description = request.description
        if request.rules_yaml is not None:
            template.rules_yaml = request.rules_yaml
        if request.use_case is not None:
            template.use_case = request.use_case
        if request.metadata is not None:
            template.metadata_ = request.metadata
        
        db.commit()
        db.refresh(template)
        
        return {
            "status": "success",
            "message": f"Template {template_id} updated successfully",
            "template": template.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating template: {str(e)}")


@router.delete("/{template_id}", response_model=Dict[str, Any])
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Delete a policy template.
    
    Args:
        template_id: Template ID
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Deletion confirmation
    """
    try:
        template = db.query(PolicyTemplate).filter(PolicyTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Only allow deleting user-created templates (not system templates)
        if template.is_system_template and current_user.role != 'admin':
            raise HTTPException(
                status_code=403,
                detail="Only admins can delete system templates"
            )
        
        db.delete(template)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Template {template_id} deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting template: {str(e)}")


@router.post("/{template_id}/clone", response_model=Dict[str, Any])
async def clone_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Clone a template to create a new policy.
    
    Args:
        template_id: Template ID to clone
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Created policy details
    """
    try:
        template = db.query(PolicyTemplate).filter(PolicyTemplate.id == template_id).first()
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Create new policy from template
        service = PolicyEditorService(db)
        policy = service.create_policy(
            name=f"{template.name} (Copy)",
            category=template.category,
            description=template.description or f"Cloned from template: {template.name}",
            rules_yaml=template.rules_yaml,
            created_by=current_user.id
        )
        
        return {
            "status": "success",
            "message": f"Policy created from template '{template.name}'",
            "policy": policy.to_dict()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cloning template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error cloning template: {str(e)}")
