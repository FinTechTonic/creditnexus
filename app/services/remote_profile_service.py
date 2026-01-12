"""Remote profile service for managing remote app profiles."""

import logging
import secrets
from typing import Optional, List
from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import RemoteAppProfile

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RemoteProfileService:
    """Service for managing remote application profiles."""

    def __init__(self, db: Session):
        """Initialize remote profile service.

        Args:
            db: Database session
        """
        self.db = db

    def create_profile(
        self,
        profile_name: str,
        allowed_ips: Optional[List[str]] = None,
        permissions: Optional[dict] = None,
        api_key: Optional[str] = None,
    ) -> RemoteAppProfile:
        """Create a new remote app profile.

        Args:
            profile_name: Unique profile name
            allowed_ips: List of allowed IP addresses/CIDR blocks
            permissions: Permission dict e.g., {"read": True, "verify": True, "sign": False}
            api_key: Optional API key (will generate if not provided)

        Returns:
            Created RemoteAppProfile

        Raises:
            ValueError: If profile name already exists
        """
        existing = (
            self.db.query(RemoteAppProfile)
            .filter(RemoteAppProfile.profile_name == profile_name)
            .first()
        )

        if existing:
            raise ValueError(f"Profile name '{profile_name}' already exists")

        # Generate API key if not provided
        if not api_key:
            api_key = secrets.token_urlsafe(32)

        # Hash the API key
        api_key_hash = pwd_context.hash(api_key)

        profile = RemoteAppProfile(
            profile_name=profile_name,
            api_key_hash=api_key_hash,
            allowed_ips=allowed_ips or [],
            permissions=permissions or {"read": True, "verify": False, "sign": False},
            is_active=True,
        )

        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Created remote profile: {profile_name}")

        # Return the plain API key (only time it's returned)
        return profile, api_key

    def validate_api_key(self, api_key: str) -> Optional[RemoteAppProfile]:
        """Validate API key and return profile if valid.

        Args:
            api_key: Plain text API key from request header

        Returns:
            RemoteAppProfile if valid, None otherwise
        """
        profiles = self.db.query(RemoteAppProfile).filter(RemoteAppProfile.is_active == True).all()

        for profile in profiles:
            if pwd_context.verify(api_key, profile.api_key_hash):
                logger.debug(f"API key validated for profile: {profile.profile_name}")
                return profile

        logger.warning("API key validation failed")
        return None

    def check_permission(self, profile: RemoteAppProfile, permission: str) -> bool:
        """Check if profile has a specific permission.

        Args:
            profile: Remote app profile
            permission: Permission key to check (e.g., "read", "verify", "sign")

        Returns:
            True if permission is granted, False otherwise
        """
        if not profile.permissions:
            return False

        return profile.permissions.get(permission, False)

    def validate_ip(self, profile: RemoteAppProfile, client_ip: str) -> bool:
        """Check if client IP is in the profile's whitelist.

        Args:
            profile: Remote app profile
            client_ip: Client IP address

        Returns:
            True if IP is allowed, False otherwise
        """
        if not profile.allowed_ips:
            return True  # No IP restrictions

        import ipaddress

        try:
            ip = ipaddress.ip_address(client_ip)

            for allowed in profile.allowed_ips:
                # Check if it's a CIDR block
                if "/" in allowed:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if ip in network:
                        return True
                # Check if it's an exact IP match
                else:
                    if str(ip) == allowed:
                        return True

            return False

        except (ValueError, TypeError) as e:
            logger.error(f"IP validation error: {e}")
            return False

    def get_profile_by_name(self, profile_name: str) -> Optional[RemoteAppProfile]:
        """Get profile by name.

        Args:
            profile_name: Profile name

        Returns:
            RemoteAppProfile or None
        """
        return (
            self.db.query(RemoteAppProfile)
            .filter(RemoteAppProfile.profile_name == profile_name)
            .first()
        )

    def get_profile_by_id(self, profile_id: int) -> Optional[RemoteAppProfile]:
        """Get profile by ID.

        Args:
            profile_id: Profile ID

        Returns:
            RemoteAppProfile or None
        """
        return self.db.query(RemoteAppProfile).filter(RemoteAppProfile.id == profile_id).first()

    def list_profiles(
        self, is_active: Optional[bool] = None, limit: int = 100, offset: int = 0
    ) -> List[RemoteAppProfile]:
        """List profiles with optional filtering.

        Args:
            is_active: Filter by active status
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of RemoteAppProfile instances
        """
        query = self.db.query(RemoteAppProfile)

        if is_active is not None:
            query = query.filter(RemoteAppProfile.is_active == is_active)

        return query.order_by(RemoteAppProfile.created_at.desc()).limit(limit).offset(offset).all()

    def update_profile(
        self,
        profile_id: int,
        profile_name: Optional[str] = None,
        allowed_ips: Optional[List[str]] = None,
        permissions: Optional[dict] = None,
        is_active: Optional[bool] = None,
    ) -> RemoteAppProfile:
        """Update an existing profile.

        Args:
            profile_id: Profile ID
            profile_name: New profile name (optional)
            allowed_ips: New allowed IPs (optional)
            permissions: New permissions (optional)
            is_active: New active status (optional)

        Returns:
            Updated RemoteAppProfile

        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile_by_id(profile_id)

        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        if profile_name is not None and profile_name != profile.profile_name:
            # Check for duplicate name
            existing = (
                self.db.query(RemoteAppProfile)
                .filter(
                    RemoteAppProfile.profile_name == profile_name, RemoteAppProfile.id != profile_id
                )
                .first()
            )

            if existing:
                raise ValueError(f"Profile name '{profile_name}' already exists")

            profile.profile_name = profile_name

        if allowed_ips is not None:
            profile.allowed_ips = allowed_ips

        if permissions is not None:
            profile.permissions = permissions

        if is_active is not None:
            profile.is_active = is_active

        profile.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Updated remote profile: {profile.profile_name}")

        return profile

    def rotate_api_key(self, profile_id: int) -> tuple[RemoteAppProfile, str]:
        """Generate a new API key for a profile.

        Args:
            profile_id: Profile ID

        Returns:
            Tuple of (Updated profile, new API key)

        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile_by_id(profile_id)

        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        # Generate new API key
        new_api_key = secrets.token_urlsafe(32)
        profile.api_key_hash = pwd_context.hash(new_api_key)
        profile.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Rotated API key for profile: {profile.profile_name}")

        return profile, new_api_key

    def delete_profile(self, profile_id: int) -> RemoteAppProfile:
        """Soft delete a profile by setting is_active=False.

        Args:
            profile_id: Profile ID

        Returns:
            Deleted profile

        Raises:
            ValueError: If profile not found
        """
        profile = self.get_profile_by_id(profile_id)

        if not profile:
            raise ValueError(f"Profile {profile_id} not found")

        profile.is_active = False
        profile.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(profile)

        logger.info(f"Deactivated remote profile: {profile.profile_name}")

        return profile
