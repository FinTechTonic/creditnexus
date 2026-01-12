"""Remote authentication dependencies for API key validation."""

import logging
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.config import settings
from app.services.remote_profile_service import RemoteProfileService
from app.db.models import RemoteAppProfile

logger = logging.getLogger(__name__)


async def get_remote_profile(
    api_key: Optional[str] = Header(None, alias="X-API-Key"),
    request: Request = None,
    db: Session = Depends(get_db),
) -> RemoteAppProfile:
    """Get and validate remote app profile from API key.

    Args:
        api_key: API key from X-API-Key header
        request: Incoming request for IP extraction
        db: Database session

    Returns:
        Validated RemoteAppProfile

    Raises:
        HTTPException: If API key is missing, invalid, or IP not allowed
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key header is required"
        )

    # Validate API key
    profile_service = RemoteProfileService(db)
    profile = profile_service.validate_api_key(api_key)

    if not profile:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Validate IP address if whitelist is configured
    if profile.allowed_ips and request:
        client_ip = _get_client_ip(request)
        if not profile_service.validate_ip(profile, client_ip):
            logger.warning(
                f"IP check failed for profile {profile.profile_name}: "
                f"client IP {client_ip} not in whitelist"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"IP address {client_ip} not in whitelist",
            )

    return profile


def require_remote_permission(permission: str):
    """Factory function to create a dependency that checks for a specific permission.

    Args:
        permission: Permission key to check (e.g., "read", "verify", "sign")

    Returns:
        Dependency function that checks the permission

    Usage:
        @router.get("/endpoint")
        async def endpoint(
            profile: RemoteAppProfile = Depends(require_remote_permission("read"))
        ):
            ...
    """

    async def permission_dependency(
        profile: RemoteAppProfile = Depends(get_remote_profile), db: Session = Depends(get_db)
    ) -> RemoteAppProfile:
        """Check if profile has required permission."""
        profile_service = RemoteProfileService(db)

        if not profile_service.check_permission(profile, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' not granted for this profile",
            )

        return profile

    return permission_dependency


def _get_client_ip(request: Request) -> str:
    """Extract client IP address from request.

    Args:
        request: Incoming request

    Returns:
        Client IP address as string
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return "unknown"
