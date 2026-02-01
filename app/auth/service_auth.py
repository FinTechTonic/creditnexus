"""
Service authentication: JWT or X-API-Key (admin-generated API key).
Used so the MCP server can call CreditNexus APIs with X-API-Key; when valid and permission 'mcp',
requests are treated as MCP_DEMO_USER_ID. All MCP-called endpoints should be credentialled via this.
"""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.jwt_auth import get_current_user
from app.auth.remote_auth import get_remote_profile
from app.core.config import settings
from app.db import get_db
from app.db.models import User

logger = logging.getLogger(__name__)

# Permission required on RemoteAppProfile for MCP/service access
MCP_PERMISSION = "mcp"
API_ACCESS_PERMISSION = "api_access"


async def get_user_for_api(
    current_user: Optional[User] = Depends(get_current_user),
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    request=None,
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve authenticated user from JWT or X-API-Key (admin-generated API key).
    Use for banking, stock-prediction, and any endpoint called by the MCP server.

    - JWT Bearer: returns that user.
    - X-API-Key: validates key via RemoteProfileService; if profile has permission 'mcp' or
      'api_access', returns the user identified by MCP_DEMO_USER_ID (must be set in config).
    - Otherwise: 401.
    """
    if current_user:
        return current_user

    if api_key:
        try:
            profile = await get_remote_profile(api_key=api_key, request=request, db=db)
        except HTTPException:
            profile = None
        if profile:
            has_mcp = profile.permissions and (
                profile.permissions.get(MCP_PERMISSION) or profile.permissions.get(API_ACCESS_PERMISSION)
            )
            if has_mcp:
                demo_id = getattr(settings, "MCP_DEMO_USER_ID", None)
                if demo_id is None:
                    logger.warning("X-API-Key valid but MCP_DEMO_USER_ID not set")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MCP demo user not configured (MCP_DEMO_USER_ID). Contact admin.",
                    )
                user = db.query(User).filter(User.id == int(demo_id), User.is_active == True).first()
                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="MCP demo user not found or inactive. Contact admin.",
                    )
                return user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key or missing mcp/api_access permission",
            headers={"WWW-Authenticate": "Bearer"},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide JWT Bearer token or X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )
