"""Enterprise-grade JWT authentication for CreditNexus.

This module implements bank-grade authentication with:
- JWT access and refresh tokens
- Password hashing with bcrypt
- Account lockout protection
- Secure password requirements
- Token blacklisting for logout
"""

import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.db import get_db
from app.db.models import User, AuditLog, AuditAction, UserRole

jwt_router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_REFRESH_SECRET_KEY = os.environ.get("JWT_REFRESH_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

MIN_PASSWORD_LENGTH = 12

_revoked_tokens: Set[str] = set()


class PasswordStrengthError(Exception):
    """Raised when password doesn't meet security requirements."""
    pass


class UserRegister(BaseModel):
    """Registration request schema."""
    email: EmailStr
    password: str
    display_name: str
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets bank-grade security requirements."""
        errors = []
        
        if len(v) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        if not re.search(r"[A-Z]", v):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", v):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", v):
            errors.append("Password must contain at least one number")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return v


class UserLogin(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    """Password change request schema."""
    current_password: str
    new_password: str
    
    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password meets security requirements."""
        errors = []
        
        if len(v) < MIN_PASSWORD_LENGTH:
            errors.append(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        
        if not re.search(r"[A-Z]", v):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r"[a-z]", v):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r"\d", v):
            errors.append("Password must contain at least one number")
        
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            errors.append("Password must contain at least one special character")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return v


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""
    refresh_token: str


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16)
    })
    return jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate an access token."""
    try:
        if token in _revoked_tokens:
            return None
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a refresh token."""
    try:
        if token in _revoked_tokens:
            return None
        payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload
    except JWTError:
        return None


def revoke_token(token: str) -> None:
    """Add a token to the revocation list."""
    _revoked_tokens.add(token)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get the current authenticated user from JWT token."""
    if not credentials:
        return None
    
    payload = decode_access_token(credentials.credentials)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        return None
    
    return user


async def require_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Require valid authentication - raises exception if not authenticated."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    return user


def check_account_lockout(user: User) -> None:
    """Check if the user account is locked."""
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account is locked. Try again in {remaining} minutes."
        )


def handle_failed_login(user: User, db: Session) -> None:
    """Handle a failed login attempt with progressive lockout."""
    user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
    
    if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    
    db.commit()


def reset_login_attempts(user: User, db: Session) -> None:
    """Reset failed login attempts after successful login."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()


@jwt_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """Register a new user account.
    
    Password requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    """
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        display_name=user_data.display_name,
        role=UserRole.ANALYST.value,
        is_active=True,
        is_email_verified=False,
        password_changed_at=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.CREATE.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"method": "jwt_register"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@jwt_router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT tokens.
    
    Account will be locked after 5 failed attempts for 30 minutes.
    """
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    check_account_lockout(user)
    
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password login not configured for this account. Use OAuth instead."
        )
    
    if not verify_password(credentials.password, user.password_hash):
        handle_failed_login(user, db)
        remaining_attempts = MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
        if remaining_attempts > 0:
            detail = f"Invalid email or password. {remaining_attempts} attempts remaining."
        else:
            detail = f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes due to too many failed attempts."
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact support."
        )
    
    reset_login_attempts(user, db)
    
    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.LOGIN.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"method": "jwt_login"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@jwt_router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(token_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    payload = decode_refresh_token(token_request.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    revoke_token(token_request.refresh_token)
    
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


@jwt_router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Logout and revoke the current access token."""
    if credentials:
        revoke_token(credentials.credentials)
        
        payload = decode_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                audit_log = AuditLog(
                    user_id=int(user_id),
                    action=AuditAction.LOGOUT.value,
                    target_type="user",
                    target_id=int(user_id),
                    action_metadata={"method": "jwt_logout"},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent")
                )
                db.add(audit_log)
                db.commit()
    
    return {"message": "Successfully logged out"}


@jwt_router.post("/change-password")
async def change_password(
    request: Request,
    password_data: PasswordChange,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Change the current user's password.
    
    Requires current password verification.
    New password must meet security requirements.
    """
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password not configured for this account"
        )
    
    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    if verify_password(password_data.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )
    
    user.password_hash = get_password_hash(password_data.new_password)
    user.password_changed_at = datetime.utcnow()
    db.commit()
    
    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.UPDATE.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"field": "password", "method": "jwt_change_password"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    db.add(audit_log)
    db.commit()
    
    return {"message": "Password changed successfully"}


@jwt_router.get("/me")
async def get_current_user_info(user: Optional[User] = Depends(get_current_user)):
    """Get the current authenticated user's information."""
    if not user:
        return {"authenticated": False, "user": None}
    
    return {
        "authenticated": True,
        "user": user.to_dict()
    }


@jwt_router.get("/verify")
async def verify_token(user: User = Depends(require_auth)):
    """Verify the current access token is valid."""
    return {
        "valid": True,
        "user_id": user.id,
        "email": user.email,
        "role": user.role
    }
