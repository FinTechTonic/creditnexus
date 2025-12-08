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
    """Dependency class for role-based access control."""
    
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles
    
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
