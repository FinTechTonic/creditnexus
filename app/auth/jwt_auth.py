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
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import bcrypt
import hashlib

from app.db import get_db
from app.db.models import (
    AuditAction,
    AuditLog,
    Organization,
    RefreshToken,
    User,
    UserImplementationConnection,
    UserRole,
    VerifiedImplementation,
)
from app.core.config import settings
from app.utils import get_debug_log_path

logger = logging.getLogger(__name__)

jwt_router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)

# Rate limiting will be applied via decorators using limiter from app.state
# For routes that need rate limiting, use: @limiter.limit("X/minute")
# where limiter is obtained from request.app.state.limiter at route definition
# Using bcrypt directly instead of passlib to avoid initialization issues
# with long passwords during backend setup

# JWT secret keys - load from settings
try:
    JWT_SECRET_KEY = settings.JWT_SECRET_KEY.get_secret_value()
except (AttributeError, ValueError):
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

try:
    JWT_REFRESH_SECRET_KEY = settings.JWT_REFRESH_SECRET_KEY.get_secret_value()
except (AttributeError, ValueError):
    JWT_REFRESH_SECRET_KEY = os.environ.get("JWT_REFRESH_SECRET_KEY")

# Validate JWT secrets in production
# Only treat as production if explicitly set to production environment
# REPLIT_DEPLOYMENT alone is not sufficient - must be actual production deployment
environment = os.environ.get("ENVIRONMENT", "").lower()
is_production = environment == "production"
if is_production:
    if not JWT_SECRET_KEY or JWT_SECRET_KEY == "your-secret-key-here-min-32-chars":
        raise RuntimeError(
            "JWT_SECRET_KEY must be set in production. "
            "Generate secure keys: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
    if (
        not JWT_REFRESH_SECRET_KEY
        or JWT_REFRESH_SECRET_KEY == "your-refresh-secret-key-here-min-32-chars"
    ):
        raise RuntimeError(
            "JWT_REFRESH_SECRET_KEY must be set in production. "
            "Generate secure keys: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )
else:
    # Development fallback - generate temporary secrets if placeholder or missing
    if not JWT_SECRET_KEY or JWT_SECRET_KEY == "your-secret-key-here-min-32-chars":
        JWT_SECRET_KEY = "dev-secret-key-must-be-persistent-for-local-dev-12345"
        logger.warning("JWT_SECRET_KEY not set or placeholder, using persistent dev secret")
    if (
        not JWT_REFRESH_SECRET_KEY
        or JWT_REFRESH_SECRET_KEY == "your-refresh-secret-key-here-min-32-chars"
    ):
        JWT_REFRESH_SECRET_KEY = "dev-refresh-key-must-be-persistent-for-local-dev-12345"
        logger.warning("JWT_REFRESH_SECRET_KEY not set or placeholder, using persistent dev secret")

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

MIN_PASSWORD_LENGTH = 12

class PasswordStrengthError(Exception):
    """Raised when password doesn't meet security requirements."""

    pass

class UserRegister(BaseModel):
    """Registration request schema."""

    email: EmailStr
    password: str
    display_name: str
    organization_identifier: Optional[str] = None  # Organization alias, blockchain address, or key
    organization_id: Optional[int] = None  # FK to organizations.id (optional)
    invited_role: Optional[str] = None  # Org role when signing up via invite (e.g. member, admin)
    implementation_ids: Optional[List[int]] = None  # Implementation selection (multi-select)
    
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
    """Token response schema. Includes optional organization and implementations for hydrated sign-in."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    organization: Optional[Dict[str, Any]] = None
    implementations: Optional[List[Dict[str, Any]]] = None

class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""


    refresh_token: str

class UserSignupStep1(BaseModel):
    """Step 1 signup request: Basic info, role, organization, and implementation selection."""

    email: Optional[EmailStr] = None
    password: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[UserRole] = None  # Selected role
    organization_id: Optional[int] = None  # Organization selection
    implementation_ids: Optional[List[int]] = None  # Implementation selection (multi-select)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        """Validate password meets bank-grade security requirements (only if provided)."""
        if v is None:
            return v
        
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

class UserSignupStep2(BaseModel):
    """Step 2 signup request: Profile enrichment data."""

    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    address: Optional[str] = None
    # Additional role-specific fields can be added here
    # For applicants: business_type, individual/business, etc.
    # For bankers: bank_name, department, etc.
    # For law officers: law_firm, bar_number, etc.
    # For accountants: firm_name, certification_number, etc.

class SignupTokenResponse(BaseModel):
    """Response for step 1 signup with temporary signup token."""

    signup_token: str
    expires_in: int  # seconds until expiration
    message: str = "User created successfully. Please complete profile in step 2."

def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Bcrypt has a 72-byte limit, so we pre-hash longer passwords with SHA-256
    to ensure they fit within the limit while maintaining security.
    Uses bcrypt directly to avoid passlib initialization issues.
    """
    password_bytes = password.encode("utf-8")

    # If password is longer than 72 bytes, pre-hash it with SHA-256
    if len(password_bytes) > 72:
        # Pre-hash with SHA-256 to get a fixed 64-character hex string (64 bytes)
        pre_hashed = hashlib.sha256(password_bytes).hexdigest().encode("utf-8")
        # Hash the pre-hashed value with bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pre_hashed, salt).decode("utf-8")
    else:
        # For passwords <= 72 bytes, hash directly with bcrypt
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    If the password was pre-hashed (longer than 72 bytes), we need to
    apply the same pre-hashing before verification.
    Uses bcrypt directly to avoid passlib initialization issues.
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")

    # If password is longer than 72 bytes, pre-hash it the same way
    if len(password_bytes) > 72:
        pre_hashed = hashlib.sha256(password_bytes).hexdigest().encode("utf-8")
        return bcrypt.checkpw(pre_hashed, hashed_bytes)
    else:
        return bcrypt.checkpw(password_bytes, hashed_bytes)

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

def create_refresh_token(data: dict, db: Session, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token and store it in the database."""
    
    logger.debug("create_refresh_token called", extra={"user_id": data.get("sub")})

    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    jti = secrets.token_urlsafe(16)
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
        "jti": jti
    })
    
    try:
        token_record = RefreshToken(
            jti=jti, user_id=int(data.get("sub")), expires_at=expire, is_revoked=False
        )
        db.add(token_record)
    except Exception as e:
        raise
    
    try:
        db.commit()
    except Exception as e:
        raise

    logger.debug("Refresh token created", extra={"jti": jti, "user_id": data.get("sub")})
    
    try:
        token = jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, algorithm=JWT_ALGORITHM)
    except Exception as e:
        raise
    
    return token

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate an access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None

def decode_refresh_token(token: str, db: Session) -> Optional[Dict[str, Any]]:
    """Decode and validate a refresh token, checking database for revocation."""
    try:
        payload = jwt.decode(token, JWT_REFRESH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            return None

        jti = payload.get("jti")
        if not jti:
            return None

        token_record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
        if not token_record:
            return None

        if token_record.is_revoked:
            return None

        if token_record.expires_at < datetime.utcnow():
            return None

        return payload
    except JWTError:
        return None

def revoke_refresh_token(jti: str, db: Session) -> None:
    """Revoke a refresh token by its JTI in the database."""
    token_record = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if token_record:
        token_record.is_revoked = True
        token_record.revoked_at = datetime.utcnow()
        db.commit()

def revoke_all_user_tokens(user_id: int, db: Session) -> None:
    """Revoke all refresh tokens for a user."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.is_revoked == False
    ).update({"is_revoked": True, "revoked_at": datetime.utcnow()})
    db.commit()

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
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
    credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)
) -> User:
    """Require valid authentication - raises exception if not authenticated."""

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    return user

def check_account_lockout(user: User) -> None:
    """Check if the user account is locked."""
    if user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account is locked. Try again in {remaining} minutes.",
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


def _hydrate_user_context(user: User, db: Session) -> Dict[str, Any]:
    """Load organization and implementations for hydrated sign-in and /me."""
    org = None
    if user.organization_id:
        o = db.query(Organization).filter(Organization.id == user.organization_id).first()
        if o:
            org = o.to_dict()
    conns = (
        db.query(UserImplementationConnection)
        .filter(
            UserImplementationConnection.user_id == user.id,
            UserImplementationConnection.is_active.is_(True),
        )
        .all()
    )
    impls: List[Dict[str, Any]] = []
    for c in conns:
        if c.implementation:
            impls.append({
                "id": c.implementation.id,
                "name": c.implementation.name,
                "display_name": c.implementation.display_name,
                "category": c.implementation.category,
            })
    return {"organization": org, "implementations": impls}


@jwt_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: Request,
    user_data: UserRegister,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
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
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Validate implementations if provided
    if user_data.implementation_ids:
        impls = db.query(VerifiedImplementation).filter(
            VerifiedImplementation.id.in_(user_data.implementation_ids),
            VerifiedImplementation.is_active == True
        ).all()
        if len(impls) != len(user_data.implementation_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more implementations are invalid or inactive"
            )

    # When signing up via invite (organization_id + invited_role), store pending org/role in profile_data
    # until admin approves; do not set user.organization_id until approval.
    org_id_for_user = user_data.organization_id
    profile_data = None
    if user_data.invited_role is not None and user_data.organization_id is not None:
        org_id_for_user = None
        profile_data = {
            "pending_organization_id": user_data.organization_id,
            "invited_role": user_data.invited_role,
        }
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        display_name=user_data.display_name,
        organization_identifier=user_data.organization_identifier,
        organization_id=org_id_for_user,
        profile_data=profile_data,
        role=UserRole.ANALYST.value,
        is_active=False,  # Require admin approval
        is_email_verified=False,
        password_changed_at=datetime.utcnow(),
        signup_status="pending",
        signup_submitted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create implementation connections
    if user_data.implementation_ids:
        for impl_id in user_data.implementation_ids:
            connection = UserImplementationConnection(
                user_id=user.id,
                implementation_id=impl_id,
                is_active=True,
                connection_data=None
            )
            db.add(connection)
        db.commit()

    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.CREATE.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"method": "jwt_register"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_log)
    db.commit()

    # Enqueue post-signup tasks: populate dashboard from Plaid + person search (parallel)
    if background_tasks:
        try:
            from app.services.signup_service import run_post_signup_tasks
            background_tasks.add_task(run_post_signup_tasks, user.id)
        except Exception as e:
            logger.debug("Signup background tasks not added: %s", e)

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)}, db)
    ctx = _hydrate_user_context(user, db)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        organization=ctx["organization"],
        implementations=ctx["implementations"],
    )


@jwt_router.post("/signup/step1", response_model=SignupTokenResponse, status_code=status.HTTP_201_CREATED)
async def signup_step1(
    request: Request,
    user_data: UserSignupStep1,
    db: Session = Depends(get_db)
):
    """Step 1: Create user account with role, organization, and implementation selection.

    Creates a user account with basic information, selected role, organization, and implementations.
    Returns a temporary signup token (expires in 1 hour) for step 2.
    """
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user with selected role
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        display_name=user_data.display_name,
        role=user_data.role.value,
        organization_id=user_data.organization_id,
        is_active=False,  # Require admin approval
        is_email_verified=False,
        password_changed_at=datetime.utcnow(),
        signup_status="pending",
        signup_submitted_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create implementation connections
    if user_data.implementation_ids:
        for impl_id in user_data.implementation_ids:
            connection = UserImplementationConnection(
                user_id=user.id,
                implementation_id=impl_id,
                is_active=True,
                connection_data=None  # Will be populated in step 2 or later
            )
            db.add(connection)
        db.commit()

    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.CREATE.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"method": "signup_step1", "role": user_data.role.value},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_log)
    db.commit()

    # Create temporary signup token (expires in 1 hour)
    signup_token_expires = timedelta(hours=1)
    signup_token = jwt.encode(
        {
            "sub": str(user.id),
            "email": user.email,
            "type": "signup",
            "exp": datetime.utcnow() + signup_token_expires,
            "iat": datetime.utcnow(),
        },
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )

    return SignupTokenResponse(
        signup_token=signup_token,
        expires_in=int(signup_token_expires.total_seconds()),
        message="User created successfully. Please complete profile in step 2.",
    )

class SignupProgressData(BaseModel):
    """Request model for saving signup progress."""

    user_id: int
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[str] = None
    profile_data: Optional[dict] = None

@jwt_router.post("/signup/save-progress")
async def save_signup_progress(
    request: Request, progress_data: SignupProgressData, db: Session = Depends(get_db)
):
    """Save signup progress without completing signup.

    Allows users to save their progress during the signup flow
    without submitting for approval. Updates user with partial data.
    """
    user = db.query(User).filter(User.id == progress_data.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Update user with partial data (only if provided)
    if progress_data.email:
        # Check if email is already taken by another user
        existing_user = (
            db.query(User).filter(User.email == progress_data.email, User.id != user.id).first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
            )
        user.email = progress_data.email

    if progress_data.display_name:
        user.display_name = progress_data.display_name

    if progress_data.role:
        user.role = progress_data.role

    # Store profile data in metadata or separate table if needed
    # For now, we'll just update the signup_status to indicate progress
    if user.signup_status == "pending":
        user.signup_status = "in_progress"

    db.commit()
    db.refresh(user)

    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.UPDATE.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"method": "save_signup_progress"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_log)
    db.commit()

    return {"status": "saved", "user_id": user.id, "message": "Signup progress saved successfully"}

@jwt_router.post("/signup/step2", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def signup_step2(
    request: Request,
    signup_token: str,
    profile_data: UserSignupStep2,
    db: Session = Depends(get_db),
):
    """Step 2: Complete user profile with enrichment data.

    Accepts signup token from step 1, profile data, and optional file uploads.
    Updates user profile and returns full JWT tokens for login.
    """
    # Decode and validate signup token
    try:
        payload = jwt.decode(signup_token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "signup":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signup token type"
            )

        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired signup token"
        )

    # Update user profile data
    # Store profile enrichment in profile_data JSONB column
    profile_dict = {
        "phone": profile_data.phone,
        "company": profile_data.company,
        "job_title": profile_data.job_title,
        "address": profile_data.address,
    }

    # Remove None values
    profile_dict = {k: v for k, v in profile_dict.items() if v is not None}

    # Update user profile_data
    if profile_dict:
        user.profile_data = profile_dict

    db.commit()
    db.refresh(user)

    # Index user profile in ChromaDB
    try:
        from app.chains.document_retrieval_chain import add_user_profile

        if profile_dict:
            add_user_profile(
                user_id=user.id, profile_data=profile_dict, role=user.role, email=user.email
            )
            logger.info(f"Indexed user profile {user.id} in ChromaDB after signup step 2")
    except Exception as e:
        logger.warning(f"Failed to index user profile in ChromaDB: {e}")
        # Don't fail signup if indexing fails

    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        action=AuditAction.UPDATE.value,
        target_type="user",
        target_id=user.id,
        action_metadata={"method": "signup_step2"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_log)
    db.commit()

    # Check if user is approved (can log in)
    if user.signup_status != "approved" or not user.is_active:
        # User is pending approval, return message instead of tokens
        from fastapi import status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "status": "pending_approval",
                "message": "Your account is pending admin approval. You will be notified once your account is approved.",
            },
        )

    # Generate full JWT tokens for login
    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)}, db)
    ctx = _hydrate_user_context(user, db)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        organization=ctx["organization"],
        implementations=ctx["implementations"],
    )

@jwt_router.post("/login", response_model=TokenResponse)
async def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return JWT tokens.

    Account will be locked after 5 failed attempts for 30 minutes.
    Rate limited via slowapi default_limits (60/minute) with additional
    account lockout protection (5 failed attempts = 30 min lockout).
    """
    
    # Rate limiting is handled by slowapi's default_limits (60/minute)
    # Additional protection via account lockout mechanism (5 failed attempts)
    logger.debug("Login attempt", extra={"email": credentials.email})
    
    # Fix for encrypted email query: The EncryptedString type encrypts to bytes via process_bind_param,
    # but the database column is VARCHAR, causing a type mismatch error (character varying = bytea).
    # Workaround: Query all users and filter in Python by decrypting emails.
    # This is inefficient but works around the schema/type mismatch.
    # TODO: Fix by either migrating email column to BYTEA/TEXT or updating EncryptedString to handle VARCHAR properly.
    from app.services.encryption_service import get_encryption_service

    try:
        # If encryption is disabled, use normal query
        if not settings.ENCRYPTION_ENABLED:
            user = db.query(User).filter(User.email == credentials.email).first()
        else:
            
            # Workaround: Query all users and filter by comparing decrypted emails
            # This is not ideal for performance but works around the type mismatch
            all_users = db.query(User).all()
            user = None
            for u in all_users:
                try:
                    # Accessing u.email will trigger process_result_value which decrypts
                    if u.email == credentials.email:
                        user = u
                        break
                except Exception as email_error:
                    # If decryption fails for this user, skip it
                    continue
    except Exception as e:
        raise
    
    if not user:
        logger.warning("Login failed: user not found", extra={"email": credentials.email})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    try:
        check_account_lockout(user)
    except Exception as e:
        raise
    
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Password login not configured for this account. Use OAuth instead.",
        )
    
    try:
        password_valid = verify_password(credentials.password, user.password_hash)
    except Exception as e:
        raise
    
    if not password_valid:
        handle_failed_login(user, db)
        remaining_attempts = MAX_LOGIN_ATTEMPTS - user.failed_login_attempts
        if remaining_attempts > 0:
            detail = f"Invalid email or password. {remaining_attempts} attempts remaining."
        else:
            detail = f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes due to too many failed attempts."
        logger.warning(
            "Login failed: invalid password",
            extra={"email": credentials.email, "remaining_attempts": remaining_attempts},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated. Contact support."
        )
    
    try:
        reset_login_attempts(user, db)
    except Exception as e:
        raise
    
    try:
        audit_log = AuditLog(
            user_id=user.id,
            action=AuditAction.LOGIN.value,
            target_type="user",
            target_id=user.id,
            action_metadata={"method": "jwt_login"},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        db.add(audit_log)
        db.commit()
    except Exception as e:
        raise
    
    try:
        access_token = create_access_token({"sub": str(user.id), "email": user.email})
    except Exception as e:
        raise

    try:
        refresh_token = create_refresh_token({"sub": str(user.id)}, db)
    except Exception as e:
        raise
    
    logger.info("Login successful", extra={"user_id": user.id, "email": user.email})
    ctx = _hydrate_user_context(user, db)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        organization=ctx["organization"],
        implementations=ctx["implementations"],
    )

@jwt_router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(token_request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    payload = decode_refresh_token(token_request.refresh_token, db)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )

    old_jti = payload.get("jti")
    if old_jti:
        revoke_refresh_token(old_jti, db)

    access_token = create_access_token({"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token({"sub": str(user.id)}, db)
    ctx = _hydrate_user_context(user, db)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        organization=ctx["organization"],
        implementations=ctx["implementations"],
    )

@jwt_router.post("/logout")
async def logout(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    """Logout and revoke all refresh tokens for the user."""
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                revoke_all_user_tokens(int(user_id), db)

                audit_log = AuditLog(
                    user_id=int(user_id),
                    action=AuditAction.LOGOUT.value,
                    target_type="user",
                    target_id=int(user_id),
                    action_metadata={"method": "jwt_logout"},
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                db.add(audit_log)
                db.commit()

    return {"message": "Successfully logged out"}

@jwt_router.post("/change-password")
async def change_password(
    request: Request,
    password_data: PasswordChange,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """Change the current user's password.

    Requires current password verification.
    New password must meet security requirements.
    """
    if not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password not configured for this account",
        )

    if not verify_password(password_data.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Current password is incorrect"
        )

    if verify_password(password_data.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
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
        user_agent=request.headers.get("user-agent"),
    )
    db.add(audit_log)
    db.commit()

    return {"message": "Password changed successfully"}

def _safe_user_dict(user: User) -> Dict[str, Any]:
    """Build user dict without raising (handles EncryptedString, etc.)."""
    try:
        return user.to_dict()
    except Exception as e:
        logger.warning("user.to_dict() failed for user %s: %s", getattr(user, "id", None), e)
    email = getattr(user, "email", None)
    if hasattr(email, "get_secret_value"):
        try:
            email = email.get_secret_value()
        except Exception:
            email = ""
    email = str(email or "")
    return {
        "id": getattr(user, "id", None),
        "email": email,
        "display_name": str(getattr(user, "display_name", None) or ""),
        "profile_image": getattr(user, "profile_image", None),
        "role": getattr(user, "role", None) or "viewer",
        "is_active": getattr(user, "is_active", True),
        "last_login": None,
        "wallet_address": getattr(user, "wallet_address", None),
        "signup_status": getattr(user, "signup_status", None),
        "profile_data": getattr(user, "profile_data", None),
        "created_at": None,
    }


@jwt_router.get("/me")
async def get_current_user_info(
    user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current authenticated user's information with organization and implementations.
    Never returns 500: on any error returns minimal payload so client stays usable.
    """
    if not user:
        return {"authenticated": False, "user": None, "organization": None, "implementations": []}
    try:
        user_dict = _safe_user_dict(user)
        try:
            ctx = _hydrate_user_context(user, db)
            org, impls = ctx.get("organization"), ctx.get("implementations") or []
        except Exception as e:
            logger.warning("_hydrate_user_context failed for user %s: %s", user.id, e)
            org, impls = None, []
        return {
            "authenticated": True,
            "user": user_dict,
            "organization": org,
            "implementations": impls,
        }
    except Exception as e:
        logger.error("get_current_user_info failed: %s", e, exc_info=True)
        return {
            "authenticated": True,
            "user": _safe_user_dict(user),
            "organization": None,
            "implementations": [],
        }

@jwt_router.get("/verify")
async def verify_token(user: User = Depends(require_auth)):
    """Verify the current access token is valid."""
    return {"valid": True, "user_id": user.id, "email": user.email, "role": user.role}
