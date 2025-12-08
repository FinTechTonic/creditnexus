"""Authentication routes for Replit OAuth2 PKCE flow."""

import os
import logging
import secrets
import hashlib
import base64
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode
from typing import Optional, Dict, Any

import httpx
import jwt
from jwt import PyJWKClient
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User, OAuth, AuditLog, AuditAction, UserRole

logger = logging.getLogger(__name__)

auth_router = APIRouter(prefix="/auth", tags=["authentication"])

REPLIT_ISSUER_URL = "https://replit.com/oidc"
REPLIT_JWKS_URL = f"{REPLIT_ISSUER_URL}/.well-known/jwks.json"
SCOPES = ["openid", "profile", "email", "offline_access"]

_jwks_client: Optional[PyJWKClient] = None
_jwks_cache_time: float = 0
JWKS_CACHE_DURATION = 3600


def get_jwks_client() -> PyJWKClient:
    """Get or create a cached JWKS client for token verification."""
    global _jwks_client, _jwks_cache_time
    
    current_time = time.time()
    if _jwks_client is None or (current_time - _jwks_cache_time) > JWKS_CACHE_DURATION:
        _jwks_client = PyJWKClient(REPLIT_JWKS_URL)
        _jwks_cache_time = current_time
    
    return _jwks_client


def verify_id_token(id_token: str, client_id: str) -> Dict[str, Any]:
    """Verify and decode the ID token using Replit's JWKS.
    
    Args:
        id_token: The JWT ID token from the OAuth response
        client_id: The expected audience (REPL_ID)
    
    Returns:
        Decoded token claims if valid
        
    Raises:
        HTTPException if token is invalid
    """
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(id_token)
        
        claims = jwt.decode(
            id_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=client_id,
            issuer=REPLIT_ISSUER_URL,
            options={
                "verify_signature": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_exp": True,
            }
        )
        return claims
    except jwt.ExpiredSignatureError:
        logger.error("ID token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID token has expired"
        )
    except jwt.InvalidAudienceError:
        logger.error("Invalid audience in ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token audience"
        )
    except jwt.InvalidIssuerError:
        logger.error("Invalid issuer in ID token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer"
        )
    except jwt.PyJWTError as e:
        logger.error(f"Failed to verify ID token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid ID token"
        )
    except Exception as e:
        logger.error(f"Unexpected error verifying ID token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to verify authentication"
        )


def generate_pkce_pair():
    """Generate PKCE code verifier and challenge."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode().rstrip("=")
    return code_verifier, code_challenge


def get_redirect_uri(request: Request) -> str:
    """Build the OAuth callback URL."""
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    return f"{scheme}://{host}/api/auth/callback"


@auth_router.get("/login")
async def login(request: Request, next_url: Optional[str] = None):
    """Initiate OAuth2 PKCE login flow with Replit."""
    repl_id = os.environ.get("REPL_ID")
    if not repl_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="REPL_ID environment variable not set"
        )
    
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(32)
    
    request.session["oauth_code_verifier"] = code_verifier
    request.session["oauth_state"] = state
    if next_url:
        request.session["oauth_next_url"] = next_url
    
    params = {
        "client_id": repl_id,
        "redirect_uri": get_redirect_uri(request),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "login consent",
    }
    
    auth_url = f"{REPLIT_ISSUER_URL}/auth?{urlencode(params)}"
    return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)


@auth_router.get("/callback")
async def callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle OAuth2 callback from Replit."""
    if error:
        logger.error(f"OAuth error: {error} - {error_description}")
        return RedirectResponse(url="/?auth_error=" + (error_description or error))
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter"
        )
    
    stored_state = request.session.get("oauth_state")
    if state != stored_state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )
    
    code_verifier = request.session.get("oauth_code_verifier")
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code verifier"
        )
    
    repl_id = os.environ.get("REPL_ID")
    
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": get_redirect_uri(request),
        "client_id": repl_id,
        "code_verifier": code_verifier,
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{REPLIT_ISSUER_URL}/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            tokens = response.json()
        except httpx.HTTPError as e:
            logger.error(f"Token exchange failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to exchange authorization code"
            )
    
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No ID token in response"
        )
    
    claims = verify_id_token(id_token, repl_id)
    
    replit_user_id = claims.get("sub")
    email = claims.get("email")
    first_name = claims.get("first_name", "")
    last_name = claims.get("last_name", "")
    profile_image_url = claims.get("profile_image_url")
    
    display_name = f"{first_name} {last_name}".strip() or email or f"User {replit_user_id}"
    
    user = db.query(User).filter(User.replit_user_id == replit_user_id).first()
    
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.replit_user_id = replit_user_id
    
    if not user:
        user = User(
            replit_user_id=replit_user_id,
            email=email or f"{replit_user_id}@replit.user",
            display_name=display_name,
            profile_image=profile_image_url,
            role=UserRole.ANALYST.value,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created new user: {user.id} ({user.email})")
    else:
        user.display_name = display_name
        user.profile_image = profile_image_url
        user.last_login = datetime.utcnow()
        db.commit()
        logger.info(f"User logged in: {user.id} ({user.email})")
    
    browser_session_key = request.session.get("_browser_session_key")
    if not browser_session_key:
        browser_session_key = secrets.token_hex(16)
        request.session["_browser_session_key"] = browser_session_key
    
    expires_in = tokens.get("expires_in", 3600)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    db.query(OAuth).filter(
        OAuth.user_id == user.id,
        OAuth.browser_session_key == browser_session_key,
        OAuth.provider == "replit"
    ).delete()
    
    oauth_token = OAuth(
        user_id=user.id,
        provider="replit",
        browser_session_key=browser_session_key,
        access_token=tokens.get("access_token"),
        refresh_token=tokens.get("refresh_token"),
        token_type=tokens.get("token_type"),
        expires_at=expires_at,
        id_token=id_token,
    )
    db.add(oauth_token)
    
    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"provider": "replit"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_log)
    
    db.commit()
    
    request.session["user_id"] = user.id
    request.session.pop("oauth_code_verifier", None)
    request.session.pop("oauth_state", None)
    
    next_url = request.session.pop("oauth_next_url", "/")
    
    return RedirectResponse(url=next_url, status_code=status.HTTP_302_FOUND)


@auth_router.get("/logout")
async def logout(request: Request, db: Session = Depends(get_db)):
    """Log out the current user."""
    user_id = request.session.get("user_id")
    browser_session_key = request.session.get("_browser_session_key")
    
    if user_id and browser_session_key:
        db.query(OAuth).filter(
            OAuth.user_id == user_id,
            OAuth.browser_session_key == browser_session_key
        ).delete()
        
        audit_log = AuditLog(
            user_id=user_id,
            action=AuditAction.LOGOUT.value,
            target_type="user",
            target_id=user_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(audit_log)
        db.commit()
    
    request.session.clear()
    
    repl_id = os.environ.get("REPL_ID")
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    post_logout_uri = f"{scheme}://{host}/"
    
    logout_params = urlencode({
        "client_id": repl_id,
        "post_logout_redirect_uri": post_logout_uri,
    })
    logout_url = f"{REPLIT_ISSUER_URL}/session/end?{logout_params}"
    
    return RedirectResponse(url=logout_url, status_code=status.HTTP_302_FOUND)


@auth_router.get("/me")
async def get_current_user_info(request: Request, db: Session = Depends(get_db)):
    """Get the current authenticated user's information.
    
    Supports both session-based auth (Replit OAuth) and JWT Bearer token auth.
    """
    user = None
    
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        from app.auth.jwt_auth import decode_access_token
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == int(user_id)).first()
                if user and user.is_active:
                    return {
                        "authenticated": True,
                        "user": user.to_dict()
                    }
    
    user_id = request.session.get("user_id")
    
    if not user_id:
        return {"authenticated": False, "user": None}
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        request.session.clear()
        return {"authenticated": False, "user": None}
    
    return {
        "authenticated": True,
        "user": user.to_dict()
    }
