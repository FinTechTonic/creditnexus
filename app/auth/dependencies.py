"""Authentication dependencies for FastAPI routes."""

import logging
from typing import Optional, List
from functools import wraps
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User, OAuth, UserRole

logger = logging.getLogger(__name__)


async def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Get the current user from session if logged in, otherwise return None."""
    session = request.session
    user_id = session.get("user_id")
    
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        session.clear()
        return None
    
    return user


async def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Get the current authenticated user. Raises 401 if not logged in."""
    user = await get_optional_user(request, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


# Alias require_auth for compatibility with routes that expect it
# This is equivalent to get_current_user but with a different name
require_auth = get_current_user


def require_role(allowed_roles: List[str]):
    """Decorator factory to require specific roles for a route."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            db = kwargs.get("db")
            
            if not request or not db:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            user = await get_current_user(request, db)
            
            if user.role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required roles: {', '.join(allowed_roles)}"
                )
            
            kwargs["current_user"] = user
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


class RoleChecker:
    """Dependency class for role-based access control.
    
    Note: This class is maintained for backward compatibility.
    New code should use PermissionChecker for granular permission control.
    """
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
        logger.warning(
            "RoleChecker is deprecated. Use PermissionChecker for granular permission control. "
            "RoleChecker will continue to work but may be removed in a future version."
        )
    
    async def __call__(
        self,
        user: User = Depends(get_current_user)
    ) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {', '.join(self.allowed_roles)}"
            )
        return user


require_admin = RoleChecker([UserRole.ADMIN.value])
require_reviewer = RoleChecker([UserRole.ADMIN.value, UserRole.REVIEWER.value])
require_analyst = RoleChecker([UserRole.ADMIN.value, UserRole.REVIEWER.value, UserRole.ANALYST.value])


class PermissionChecker:
    """Dependency class for permission-based access control."""
    
    def __init__(self, required_permissions: List[str]):
        self.required_permissions = required_permissions
    
    async def __call__(
        self,
        user: User = Depends(get_current_user)
    ) -> User:
        from app.core.permissions import has_permissions
        
        if not has_permissions(user, self.required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required permissions: {', '.join(self.required_permissions)}"
            )
        return user


def require_permission(permission: str):
    """Decorator factory to require a specific permission for a route.
    
    Usage:
        @require_permission("DOCUMENT_CREATE")
        @router.post("/documents")
        async def create_document(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            db = kwargs.get("db")
            
            if not request or not db:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            user = await get_current_user(request, db)
            
            from app.core.permissions import has_permission
            
            if not has_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required permission: {permission}"
                )
            
            kwargs["current_user"] = user
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permissions(permissions: List[str]):
    """Decorator factory to require multiple permissions for a route.
    
    Usage:
        @require_permissions(["DOCUMENT_CREATE", "DEAL_VIEW"])
        @router.post("/documents")
        async def create_document(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            db = kwargs.get("db")
            
            if not request or not db:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Request object not found"
                )
            
            user = await get_current_user(request, db)
            
            from app.core.permissions import has_permissions
            
            if not has_permissions(user, permissions):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required permissions: {', '.join(permissions)}"
                )
            
            kwargs["current_user"] = user
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator