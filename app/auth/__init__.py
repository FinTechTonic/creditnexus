"""Authentication module for CreditNexus using Replit OAuth2 PKCE."""

from app.auth.dependencies import get_current_user, get_optional_user, require_role
from app.auth.routes import auth_router

__all__ = ["auth_router", "get_current_user", "get_optional_user", "require_role"]
