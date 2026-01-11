"""
Audit logging utilities for CreditNexus.

Provides centralized audit logging functionality for tracking user actions
and maintaining compliance audit trails.
"""

from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session

from app.db.models import AuditLog, AuditAction


def log_audit_action(
    db: Session,
    action: AuditAction,
    target_type: str,
    target_id: Optional[int] = None,
    user_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    request: Optional[Request] = None
) -> AuditLog:
    """Log an audit action to the database.
    
    Args:
        db: Database session.
        action: The type of action being logged.
        target_type: The type of entity being acted upon (e.g., 'document', 'workflow').
        target_id: The ID of the target entity.
        user_id: The ID of the user performing the action.
        metadata: Additional context data for the action.
        request: The HTTP request (to extract IP and user agent).
        
    Returns:
        The created AuditLog record.
    """
    ip_address = None
    user_agent = None
    
    if request:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:500]
    
    audit_log = AuditLog(
        user_id=user_id,
        action=action.value,
        target_type=target_type,
        target_id=target_id,
        action_metadata=metadata,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_log)
    return audit_log


# Export AuditAction for convenience
__all__ = ["log_audit_action", "AuditAction"]
