"""SQLAlchemy models for CreditNexus database."""

from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
import math
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric, Date, Float, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
import enum
import sqlalchemy as sa

from app.db import Base
from app.db.encrypted_types import EncryptedString, EncryptedJSON, EncryptedText


class UserRole(str, enum.Enum):
    """User roles for access control."""

    # New roles
    AUDITOR = "auditor"  # Full oversight, read-only access to all
    BANKER = "banker"  # Write permissions for deals, documents
    LAW_OFFICER = "law_officer"  # Write/edit for legal documents
    ACCOUNTANT = "accountant"  # Write/edit for financial data
    APPLICANT = "applicant"  # Apply and track applications
    TRADER = "trader"  # Trading and portfolio management
    COMPLIANCE_OFFICER = "compliance_officer"  # Compliance monitoring and reporting
    # Legacy roles for backward compatibility
    VIEWER = "viewer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class ExtractionStatus(str, enum.Enum):
    """Status of an extraction in the staging database."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkflowState(str, enum.Enum):
    """States for the document approval workflow."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    GENERATED = "generated"  # For LMA template-generated documents


class AuditAction(str, enum.Enum):
    """Types of auditable actions."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    APPROVE = "approve"
    REJECT = "reject"
    SIGN = "sign"
    FILE = "file"
    VERIFY = "verify"
    NOTARIZE = "notarize"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    PUBLISH = "publish"


class PolicyStatus(str, enum.Enum):
    """Status of a policy."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    ARCHIVED = "archived"


class TemplateCategory(str, enum.Enum):
    """Categories for LMA templates."""

    FACILITY_AGREEMENT = "Facility Agreement"
    TERM_SHEET = "Term Sheet"
    CONFIDENTIALITY_AGREEMENT = "Confidentiality Agreement"
    SECONDARY_TRADING = "Secondary Trading"
    SECURITY_INTERCREDITOR = "Security & Intercreditor"
    ORIGINATION = "Origination Documents"
    SUSTAINABLE_FINANCE = "Sustainable Finance"
    REGIONAL = "Regional Documents"
    REGULATORY = "Regulatory"
    RESTRUCTURING = "Restructuring"
    SUPPORTING = "Supporting Documents"


class GeneratedDocumentStatus(str, enum.Enum):
    """Status of generated documents."""

    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    EXECUTED = "executed"


class MappingType(str, enum.Enum):
    """Types of field mappings."""

    DIRECT = "direct"
    COMPUTED = "computed"
    AI_GENERATED = "ai_generated"


class ApplicationType(str, enum.Enum):
    """Types of applications."""

    INDIVIDUAL = "individual"
    BUSINESS = "business"


class ApplicationStatus(str, enum.Enum):
    """Status of applications."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class DealType(str, enum.Enum):
    """Types of deals."""

    LOAN_APPLICATION = "loan_application"
    DEBT_SALE = "debt_sale"
    LOAN_PURCHASE = "loan_purchase"
    REFINANCING = "refinancing"
    RESTRUCTURING = "restructuring"
    WITHDRAWN = "withdrawn"


class InquiryType(str, enum.Enum):
    """Types of inquiries."""

    GENERAL = "general"
    APPLICATION_STATUS = "application_status"
    TECHNICAL_SUPPORT = "technical_support"
    SALES = "sales"


class InquiryStatus(str, enum.Enum):
    """Status of inquiries."""

    NEW = "new"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SubscriptionTier(str, enum.Enum):
    """Subscription tier levels."""
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"
    LIFETIME = "lifetime"


class SubscriptionType(str, enum.Enum):
    """Subscription payment types."""
    PAY_AS_YOU_GO = "pay_as_you_go"  # Pro tier
    MONTHLY = "monthly"
    YEARLY = "yearly"
    LIFETIME = "lifetime"


class CreditType(str, enum.Enum):
    """Credit types for different workflows (rolling credits, billing)."""
    SIGNING = "signing"
    DOCUMENT_REVIEW = "document_review"
    VERIFICATION = "verification"
    TRADING = "trading"
    LOANING = "loaning"
    BORROWING = "borrowing"
    COMPLIANCE_CHECK = "compliance_check"
    SECURITIZATION = "securitization"
    RISK_ANALYSIS = "risk_analysis"
    QUANTITATIVE_ANALYSIS = "quantitative_analysis"
    STOCK_PREDICTION_DAILY = "stock_prediction_daily"
    STOCK_PREDICTION_HOURLY = "stock_prediction_hourly"
    STOCK_PREDICTION_15MIN = "stock_prediction_15min"
    UNIVERSAL = "universal"


class Organization(Base):
    """Organization for multi-blockchain and multi-tenant use."""

    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="organization", foreign_keys="User.organization_id")
    blockchain_deployments = relationship(
        "OrganizationBlockchainDeployment", back_populates="organization", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OrganizationBlockchainDeployment(Base):
    """Per-organization blockchain deployment (contracts, chain)."""

    __tablename__ = "organization_blockchain_deployments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    chain_id = Column(Integer, nullable=False, index=True)  # e.g. 137 Polygon, 8453 Base
    deployment_type = Column(String(50), nullable=False, index=True)  # notarization, token, router, etc.
    contract_address = Column(String(66), nullable=False, index=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    organization = relationship("Organization", back_populates="blockchain_deployments")

    def to_dict(self):
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "chain_id": self.chain_id,
            "deployment_type": self.deployment_type,
            "contract_address": self.contract_address,
            "is_primary": self.is_primary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)

    replit_user_id = Column(String(255), unique=True, nullable=True, index=True)

    email = Column(EncryptedString(255), unique=True, nullable=False, index=True)  # Encrypted PII

    password_hash = Column(String(255), nullable=True)  # Already hashed, don't encrypt

    display_name = Column(EncryptedString(255), nullable=False)  # Encrypted PII

    profile_image = Column(String(500), nullable=True)  # URL, not sensitive

    role = Column(String(20), default=UserRole.ANALYST.value, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False)

    is_email_verified = Column(Boolean, default=False, nullable=False)

    failed_login_attempts = Column(Integer, default=0, nullable=False)

    locked_until = Column(DateTime, nullable=True)

    password_changed_at = Column(DateTime, nullable=True)

    last_login = Column(DateTime, nullable=True)

    wallet_address = Column(EncryptedString(255), nullable=True, unique=True, index=True)  # Encrypted PII

    permissions = Column(
        JSONB(), nullable=True
    )  # Explicit user permissions (overrides role permissions) - Not sensitive

    profile_data = Column(
        EncryptedJSON(), nullable=True
    )  # Enriched profile information (phone, company, job_title, address, etc.) - Encrypted PII

    # Signup approval workflow fields
    signup_status = Column(
        String(20), default="pending", nullable=False, index=True
    )  # pending, approved, rejected
    signup_submitted_at = Column(DateTime, nullable=True)
    signup_reviewed_at = Column(DateTime, nullable=True)
    signup_reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    signup_rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    documents = relationship("Document", back_populates="uploaded_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    applications = relationship("Application", back_populates="user", foreign_keys="Application.user_id")
    deals = relationship("Deal", back_populates="applicant", foreign_keys="Deal.applicant_id")
    inquiries = relationship("Inquiry", back_populates="user", foreign_keys="Inquiry.user_id")
    organized_meetings = relationship(
        "Meeting", back_populates="organizer", foreign_keys="Meeting.organizer_id"
    )
    implementation_connections = relationship("UserImplementationConnection", back_populates="user")
    organization_identifier = Column(EncryptedString(255), nullable=True, index=True)  # Organization alias, blockchain address, or key
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    organization = relationship("Organization", back_populates="users", foreign_keys=[organization_id])
    subscriptions = relationship("UserSubscription", back_populates="user")
    credit_balance = relationship("CreditBalance", back_populates="user", uselist=False)
    subscription_tier = Column(String(20), default=SubscriptionTier.FREE.value, nullable=False)
    
    # Phase 2: KYC relationships
    # Explicit foreign_keys is required because KYCVerification also has a reviewed_by FK to users,
    # which would otherwise create multiple FK paths and break mapper configuration.
    kyc_verification = relationship(
        "KYCVerification",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="KYCVerification.user_id",
    )
    licenses = relationship("UserLicense", back_populates="user", cascade="all, delete-orphan")
    kyc_documents = relationship("KYCDocument", back_populates="user", cascade="all, delete-orphan")
    
    # Admin fields
    is_instance_admin = Column(Boolean, default=False, nullable=False, index=True)
    organization_role = Column(String(50), nullable=True, index=True)  # 'admin', 'member', etc.

    # Org-admin payment gating (Week 3)
    # For organization admins, signup requires payment (or instance-admin waiver).
    org_admin_payment_status = Column(String(20), nullable=True, index=True)  # pending, paid, waived
    org_admin_payment_id = Column(Integer, ForeignKey("payment_events.id", ondelete="SET NULL"), nullable=True)
    org_admin_paid_at = Column(DateTime, nullable=True)
    
    # User preferences and API keys
    preferences = Column(JSONB, nullable=True)  # User preferences (audio_input_mode, investment_mode, etc.)
    api_keys = Column(JSONB, nullable=True)  # Encrypted API keys for account linking
    
    # Phase 3: Structured Product relationships
    product_templates = relationship("StructuredProductTemplate", back_populates="creator")
    issued_products = relationship("StructuredProductInstance", back_populates="issuer")
    product_subscriptions = relationship("ProductSubscription", back_populates="investor")
    
    # Phase 7: GDPR relationships
    consent_records = relationship("ConsentRecord", back_populates="user", cascade="all, delete-orphan")
    data_processing_requests = relationship("DataProcessingRequest", foreign_keys="DataProcessingRequest.user_id", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "profile_image": self.profile_image,
            "role": self.role,
            "is_active": self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "wallet_address": self.wallet_address,
            "signup_status": self.signup_status,
            "signup_submitted_at": self.signup_submitted_at.isoformat()
            if self.signup_submitted_at
            else None,
            "signup_reviewed_at": self.signup_reviewed_at.isoformat()
            if self.signup_reviewed_at
            else None,
            "signup_reviewed_by": self.signup_reviewed_by,
            "signup_rejection_reason": self.signup_rejection_reason,
            "profile_data": self.profile_data,
            "organization_id": self.organization_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Document(Base):
    """Document model for storing credit agreement documents."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(String(500), nullable=False)

    borrower_name = Column(EncryptedString(255), nullable=True, index=True)  # Encrypted PII

    borrower_lei = Column(EncryptedString(20), nullable=True, index=True)  # Encrypted PII

    governing_law = Column(String(50), nullable=True)

    total_commitment = Column(Numeric(20, 2), nullable=True)

    currency = Column(String(3), nullable=True)

    agreement_date = Column(Date, nullable=True)

    sustainability_linked = Column(Boolean, default=False)

    esg_metadata = Column(JSONB, nullable=True)

    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    current_version_id = Column(Integer, nullable=True)

    # LMA Template Generation fields
    is_generated = Column(Boolean, default=False, nullable=False, index=True)
    template_id = Column(
        Integer, ForeignKey("lma_templates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_cdm_data = Column(EncryptedJSON(), nullable=True)  # CDM data used for generation - Encrypted

    # Phase 2: Document Model Enhancements
    classification = Column(String(50), nullable=True, index=True)  # legal, financial, KYC, collateral
    status = Column(String(50), server_default="draft", nullable=False, index=True)  # draft, finalized, archived
    retention_policy = Column(String(100), nullable=True)
    retention_expires_at = Column(DateTime, nullable=True)
    parent_document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)
    compliance_status = Column(String(50), server_default="pending", nullable=False, index=True)
    regulatory_check_metadata = Column(JSONB, nullable=True)

    # Deal relationship
    deal_id = Column(
        Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    uploaded_by_user = relationship("User", back_populates="documents")
    versions = relationship(
        "DocumentVersion",
        back_populates="document",
        order_by="DocumentVersion.version_number.desc()",
    )
    workflow = relationship("Workflow", back_populates="document", uselist=False)
    lma_template = relationship("LMATemplate", foreign_keys=[template_id])
    deal = relationship("Deal", back_populates="documents")
    signatures = relationship("DocumentSignature", back_populates="document", cascade="all, delete-orphan")
    filings = relationship("DocumentFiling", back_populates="document", cascade="all, delete-orphan")
    parent_document = relationship("Document", remote_side=[id], backref="amendments")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "borrower_name": self.borrower_name,
            "borrower_lei": self.borrower_lei,
            "governing_law": self.governing_law,
            "total_commitment": float(self.total_commitment) if self.total_commitment else None,
            "currency": self.currency,
            "agreement_date": self.agreement_date.isoformat() if self.agreement_date else None,
            "sustainability_linked": self.sustainability_linked,
            "current_version_id": self.current_version_id,
            "uploaded_by": self.uploaded_by,
            "is_generated": self.is_generated,
            "template_id": self.template_id,
            "source_cdm_data": self.source_cdm_data,
            # Phase 2 fields
            "classification": self.classification,
            "status": self.status,
            "retention_policy": self.retention_policy,
            "retention_expires_at": self.retention_expires_at.isoformat() if self.retention_expires_at else None,
            "parent_document_id": self.parent_document_id,
            "compliance_status": self.compliance_status,
            "regulatory_check_metadata": self.regulatory_check_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RemoteAppProfile(Base):
    """Remote application profile for API access control."""

    __tablename__ = "remote_app_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    profile_name = Column(String(100), unique=True, nullable=False, index=True)

    api_key_hash = Column(String(255), nullable=False)  # bcrypt hash

    allowed_ips = Column(JSONB, nullable=True)  # Array of IP addresses/CIDR blocks

    permissions = Column(JSONB, nullable=True)  # {"read": True, "verify": True, "sign": False}

    is_active = Column(Boolean, default=True, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "profile_name": self.profile_name,
            "allowed_ips": self.allowed_ips,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentVersion(Base):
    """Version tracking for document extractions."""

    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)

    version_number = Column(Integer, nullable=False, default=1)

    extracted_data = Column(EncryptedJSON(), nullable=False)  # Encrypted financial data

    original_text = Column(EncryptedText(), nullable=True)  # Encrypted document text (large field)

    source_filename = Column(EncryptedString(255), nullable=True)  # Encrypted PII

    extraction_method = Column(String(50), default="simple")

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="versions")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "version_number": self.version_number,
            "extracted_data": self.extracted_data,
            "source_filename": self.source_filename,
            "extraction_method": self.extraction_method,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Workflow(Base):
    """Approval workflow state machine for documents."""

    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, autoincrement=True)

    document_id = Column(
        Integer, ForeignKey("documents.id"), nullable=False, unique=True, index=True
    )

    state = Column(String(20), default=WorkflowState.DRAFT.value, nullable=False, index=True)

    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)

    submitted_at = Column(DateTime, nullable=True)

    approved_at = Column(DateTime, nullable=True)

    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    published_at = Column(DateTime, nullable=True)

    rejection_reason = Column(Text, nullable=True)

    due_date = Column(DateTime, nullable=True)

    priority = Column(String(20), default="normal")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    document = relationship("Document", back_populates="workflow")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "state": self.state,
            "assigned_to": self.assigned_to,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approved_by": self.approved_by,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "rejection_reason": self.rejection_reason,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "priority": self.priority,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class AuditLog(Base):
    """Audit trail for all user actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    action = Column(String(50), nullable=False, index=True)

    target_type = Column(String(50), nullable=False)

    target_id = Column(Integer, nullable=True)

    action_metadata = Column(EncryptedJSON(), nullable=True)  # Encrypted audit metadata

    ip_address = Column(EncryptedString(255), nullable=True)  # Encrypted PII (increased from 50 to accommodate encrypted values)

    user_agent = Column(String(500), nullable=True)  # Not sensitive

    occurred_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User", back_populates="audit_logs")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "action_metadata": self.action_metadata,
            "ip_address": self.ip_address,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }


class GeneratedReport(Base):
    """Storage for generated audit reports."""

    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(String(255), unique=True, nullable=False, index=True)
    report_type = Column(String(50), nullable=False)
    template = Column(String(50), nullable=False)
    request_params = Column(JSONB, nullable=True)
    report_data = Column(JSONB, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    creator = relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "report_id": self.report_id,
            "report_type": self.report_type,
            "template": self.template,
            "request_params": self.request_params,
            "report_data": self.report_data,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OAuth(Base):
    """OAuth token storage for Replit Auth sessions."""

    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    provider = Column(String(50), nullable=False, default="replit")

    browser_session_key = Column(String(255), nullable=False, index=True)

    access_token = Column(Text, nullable=True)

    refresh_token = Column(Text, nullable=True)

    token_type = Column(String(50), nullable=True)

    expires_at = Column(DateTime, nullable=True)

    id_token = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="oauth_tokens")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RefreshToken(Base):
    """Model for tracking JWT refresh tokens for secure revocation."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)

    jti = Column(String(255), unique=True, nullable=False, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    is_revoked = Column(Boolean, default=False, nullable=False)

    expires_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="refresh_tokens")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "jti": self.jti,
            "user_id": self.user_id,
            "is_revoked": self.is_revoked,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StagedExtraction(Base):
    """Model for storing staged credit agreement extractions (legacy support)."""

    __tablename__ = "staged_extractions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    status = Column(String(20), default=ExtractionStatus.PENDING.value, nullable=False, index=True)

    agreement_data = Column(EncryptedJSON(), nullable=False)  # Encrypted financial data

    original_text = Column(EncryptedText(), nullable=True)  # Encrypted document text (large field)

    source_filename = Column(EncryptedString(255), nullable=True)  # Encrypted PII

    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    reviewed_by = Column(String(255), nullable=True)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "status": self.status,
            "agreement_data": self.agreement_data,
            "original_text": self.original_text,
            "source_filename": self.source_filename,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "reviewed_by": self.reviewed_by,
        }


class PolicyDecision(Base):
    """Model for storing policy engine decisions and audit trail.

    Stores policy evaluation results with full CDM event support for
    machine-readable and machine-executable compliance tracking.
    """

    __tablename__ = "policy_decisions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Transaction identification
    transaction_id = Column(String(255), nullable=False, index=True)
    transaction_type = Column(String(50), nullable=False)

    # Policy decision
    decision = Column(String(10), nullable=False, index=True)  # 'ALLOW', 'BLOCK', 'FLAG'
    rule_applied = Column(String(255), nullable=True)
    trace_id = Column(String(255), unique=True, nullable=False)

    # Evaluation details
    trace = Column(EncryptedJSON(), nullable=True)  # Full evaluation trace - Encrypted
    matched_rules = Column(ARRAY(String), nullable=True)  # Array of matched rule names - Not sensitive
    additional_metadata = Column(JSONB, name="metadata", nullable=True)  # Additional context - Not sensitive

    # CDM Events (for full CDM compliance)
    cdm_events = Column(EncryptedJSON(), nullable=True)  # Full CDM PolicyEvaluation events - Encrypted

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Foreign keys to CreditNexus entities
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    # Note: loan_asset_id is NOT a foreign key because LoanAsset uses SQLModel (separate table creation)
    # The loan_assets table may not exist when PolicyDecision is created
    loan_asset_id = Column(Integer, nullable=True, index=True)  # Reference without FK constraint
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    document = relationship("Document", backref="policy_decisions")
    deal = relationship("Deal", backref="policy_decisions")
    user = relationship("User", backref="policy_decisions")

    def to_dict(self):
        """Convert model to dictionary for API serialization."""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type,
            "decision": self.decision,
            "rule_applied": self.rule_applied,
            "trace_id": self.trace_id,
            "trace": self.trace,
            "matched_rules": list(self.matched_rules) if self.matched_rules else [],
            "metadata": self.additional_metadata,
            "cdm_events": self.cdm_events,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "document_id": self.document_id,
            "loan_asset_id": self.loan_asset_id,
            "deal_id": self.deal_id,
            "user_id": self.user_id,
        }


class LMATemplate(Base):
    """LMA template model for document generation."""

    __tablename__ = "lma_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)

    template_code = Column(String(255), unique=True, nullable=False, index=True)

    name = Column(String(255), nullable=False)

    category = Column(String(100), nullable=False, index=True)

    subcategory = Column(String(100), nullable=True)

    governing_law = Column(String(50), nullable=True)

    version = Column(String(50), nullable=False)

    file_path = Column(String(500), nullable=False)

    additional_metadata = Column(JSONB, name="metadata", nullable=True)

    required_fields = Column(JSONB, nullable=True)

    optional_fields = Column(JSONB, nullable=True)

    ai_generated_sections = Column(JSONB, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    field_mappings = relationship("TemplateFieldMapping", back_populates="template", cascade="all, delete-orphan")
    generated_documents = relationship("GeneratedDocument", back_populates="template")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "template_code": self.template_code,
            "name": self.name,
            "category": self.category,
            "subcategory": self.subcategory,
            "governing_law": self.governing_law,
            "version": self.version,
            "file_path": self.file_path,
            "metadata": self.additional_metadata,
            "required_fields": self.required_fields,
            "optional_fields": self.optional_fields,
            "ai_generated_sections": self.ai_generated_sections,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class GeneratedDocument(Base):
    """Generated LMA documents from templates."""

    __tablename__ = "generated_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(
        Integer, ForeignKey("lma_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    cdm_data = Column(JSONB, nullable=False)
    generated_content = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    status = Column(String(50), server_default="draft", nullable=False, index=True)
    generation_summary = Column(JSONB, nullable=True)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    document_type = Column(String(100), nullable=True)  # For securitization templates
    source_type = Column(String(100), nullable=True)  # 'lma_template', 'securitization_template', etc.

    # Relationships
    template = relationship("LMATemplate", back_populates="generated_documents")
    source_document = relationship("Document", foreign_keys=[source_document_id])
    creator = relationship("User", foreign_keys=[created_by])
    signatures = relationship("DocumentSignature", back_populates="generated_document", cascade="all, delete-orphan")
    filings = relationship("DocumentFiling", back_populates="generated_document", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "source_document_id": self.source_document_id,
            "cdm_data": self.cdm_data,
            "generated_content": self.generated_content,
            "file_path": self.file_path,
            "status": self.status,
            "generation_summary": self.generation_summary,
            "created_by": self.created_by,
            "document_type": self.document_type,
            "source_type": self.source_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class TemplateFieldMapping(Base):
    """Field mappings from CDM to template placeholders."""

    __tablename__ = "template_field_mappings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(
        Integer, ForeignKey("lma_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    template_field = Column(String(255), nullable=False, index=True)
    cdm_field = Column(String(255), nullable=False)
    mapping_type = Column(String(50), nullable=True)
    transformation_rule = Column(Text, nullable=True)
    is_required = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    template = relationship("LMATemplate", back_populates="field_mappings")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "template_field": self.template_field,
            "cdm_field": self.cdm_field,
            "mapping_type": self.mapping_type,
            "transformation_rule": self.transformation_rule,
            "is_required": self.is_required,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ClauseCache(Base):
    """Cache for AI-generated clauses to reduce LLM costs."""

    __tablename__ = "clause_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)

    template_id = Column(
        Integer, ForeignKey("lma_templates.id", ondelete="CASCADE"), nullable=False, index=True
    )

    field_name = Column(
        String(100), nullable=False, index=True
    )  # e.g., "REPRESENTATIONS_AND_WARRANTIES"

    clause_content = Column(Text, nullable=False)  # The generated clause text

    context_hash = Column(
        String(64), nullable=True, index=True
    )  # Hash of CDM context for cache key

    context_summary = Column(JSONB, nullable=True)  # Summary of CDM context used (for display)

    usage_count = Column(
        Integer, default=0, nullable=False
    )  # How many times this clause has been used

    last_used_at = Column(DateTime, nullable=True, index=True)

    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    template = relationship("LMATemplate", foreign_keys=[template_id])
    creator = relationship("User", foreign_keys=[created_by])

    # Unique constraint: one clause per template+field_name+context_hash combination
    __table_args__ = ({"sqlite_autoincrement": True},)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "template_id": self.template_id,
            "field_name": self.field_name,
            "clause_content": self.clause_content,
            "context_hash": self.context_hash,
            "context_summary": self.context_summary,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DocumentSignature(Base):
    """Document signature model for tracking document signatures (DigiSigner requests)."""

    __tablename__ = "document_signatures"

    id = Column(Integer, primary_key=True, autoincrement=True)

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True, index=True)

    generated_document_id = Column(
        Integer, ForeignKey("generated_documents.id"), nullable=True, index=True
    )

    # DigiSigner signature request fields
    signature_provider = Column(String(50), nullable=False, server_default="digisigner", index=True)
    signature_request_id = Column(String(255), nullable=True, unique=True, index=True)
    digisigner_request_id = Column(String(255), nullable=True, index=True)  # Alias for signature_request_id (for webhook compatibility)
    digisigner_document_id = Column(String(255), nullable=True, index=True)  # DigiSigner document ID
    signature_status = Column(String(50), nullable=False, default="pending", index=True)  # pending, completed, declined, expired
    signers = Column(JSONB, nullable=True)  # Array of signer objects with name, email, role, status
    signature_provider_data = Column(JSONB, nullable=True)  # Full response from DigiSigner
    signed_document_url = Column(Text, nullable=True)
    signed_document_path = Column(Text, nullable=True)
    requested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)

    # Internal/native signature fields (Phase 2)
    access_token = Column(EncryptedString(255), nullable=True, index=True)
    coordinates = Column(JSONB, nullable=True)  # {"page": int, "x": float, "y": float, "width": float, "height": float}
    audit_data = Column(JSONB, nullable=True)  # Structured audit trail payload
    metamask_signature = Column(String(512), nullable=True)
    metamask_signed_at = Column(DateTime, nullable=True)

    # Legacy fields (for backward compatibility with old signature records)
    signer_name = Column(String(255), nullable=True)  # Changed to nullable for DigiSigner records
    signer_role = Column(String(100), nullable=True)
    signature_method = Column(String(50), nullable=True)  # Changed to nullable
    signature_data = Column(JSONB, nullable=True)  # Signature metadata
    signed_at = Column(DateTime, nullable=True)  # Changed to nullable

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="signatures")
    generated_document = relationship("GeneratedDocument", back_populates="signatures")

    def to_dict(self):
        """Convert model to dictionary."""
        # Get document title from relationship if available
        document_title = None
        if self.document:
            document_title = self.document.title
        elif self.generated_document:
            document_title = getattr(self.generated_document, 'title', None) or f"Generated Document {self.generated_document_id}"
        
        return {
            "id": self.id,
            "document_id": self.document_id,
            "generated_document_id": self.generated_document_id,
            "document_title": document_title,  # Added for frontend MyPendingSignatures component
            "signature_provider": self.signature_provider,
            "signature_request_id": self.signature_request_id,
            "signature_status": getattr(self, 'signature_status', 'pending'),
            "digisigner_request_id": getattr(self, 'digisigner_request_id', None),
            "digisigner_document_id": getattr(self, 'digisigner_document_id', None),
            "signers": self.signers,
            "signature_provider_data": self.signature_provider_data,
            "signed_document_url": self.signed_document_url,
            "signed_document_path": self.signed_document_path,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            # Phase 2 native fields
            "access_token": self.access_token,
            "coordinates": self.coordinates,
            "audit_data": self.audit_data,
            "metamask_signature": self.metamask_signature,
            "metamask_signed_at": self.metamask_signed_at.isoformat() if self.metamask_signed_at else None,
            # Legacy fields
            "signer_name": self.signer_name,
            "signer_role": self.signer_role,
            "signature_method": self.signature_method,
            "signature_data": self.signature_data,
            "signed_at": self.signed_at.isoformat() if self.signed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": getattr(self, 'updated_at', None).isoformat() if getattr(self, 'updated_at', None) else None,
        }


class DocumentFiling(Base):
    """Tracks regulatory filings for documents."""

    __tablename__ = "document_filings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    generated_document_id = Column(Integer, ForeignKey("generated_documents.id"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)

    # Filing metadata
    agreement_type = Column(String(100), nullable=False, index=True)  # "facility_agreement", "disclosure", etc.
    jurisdiction = Column(String(50), nullable=False, index=True)  # "US", "UK", "FR", "DE", etc.
    filing_authority = Column(String(255), nullable=False)  # "SEC", "Companies House", "AMF", etc.

    # Filing system info
    filing_system = Column(String(50), nullable=False)  # "companies_house_api", "manual_ui", etc.
    filing_reference = Column(String(255), nullable=True, unique=True, index=True)  # External filing ID
    filing_status = Column(String(50), nullable=False, index=True)  # "pending", "submitted", "accepted", "rejected"

    # Filing payload (for API submissions) or form data (for manual UI)
    filing_payload = Column(JSONB, nullable=True)  # Data sent to filing system or prepared for UI
    filing_response = Column(JSONB, nullable=True)  # Response from filing system

    # Filing URLs
    filing_url = Column(Text, nullable=True)  # URL to view filing
    confirmation_url = Column(Text, nullable=True)  # Confirmation/receipt URL
    manual_submission_url = Column(Text, nullable=True)  # URL to manual filing portal (for UI guidance)

    # Manual filing tracking
    submitted_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # User who submitted manually
    submitted_at = Column(DateTime, nullable=True)  # When manually submitted
    submission_notes = Column(Text, nullable=True)  # Notes from manual submission

    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Deadline tracking
    deadline = Column(DateTime, nullable=True, index=True)

    # Timestamps
    filed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="filings")
    generated_document = relationship("GeneratedDocument", back_populates="filings")
    deal = relationship("Deal", back_populates="filings")
    submitted_by_user = relationship("User", foreign_keys=[submitted_by])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "generated_document_id": self.generated_document_id,
            "deal_id": self.deal_id,
            "agreement_type": self.agreement_type,
            "jurisdiction": self.jurisdiction,
            "filing_authority": self.filing_authority,
            "filing_system": self.filing_system,
            "filing_reference": self.filing_reference,
            "filing_status": self.filing_status,
            "filing_payload": self.filing_payload,
            "filing_response": self.filing_response,
            "filing_url": self.filing_url,
            "confirmation_url": self.confirmation_url,
            "manual_submission_url": self.manual_submission_url,
            "submitted_by": self.submitted_by,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "submission_notes": self.submission_notes,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "filed_at": self.filed_at.isoformat() if self.filed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class DealStatus(str, enum.Enum):
    """Status of a deal."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"
    RESTRUCTURING = "restructuring"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"


class Application(Base):
    """Application model for loan applications."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    application_type = Column(String(50), nullable=False)  # "individual", "business"

    status = Column(String(50), default="pending", nullable=False, index=True)

    application_data = Column(JSONB, nullable=True)
    business_data = Column(JSONB, nullable=True)
    individual_data = Column(JSONB, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="applications")
    deal = relationship("Deal", back_populates="application")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "application_type": self.application_type,
            "status": self.status,
            "application_data": self.application_data,
            "business_data": self.business_data,
            "individual_data": self.individual_data,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Inquiry(Base):
    """Inquiry model for customer support and inquiries."""

    __tablename__ = "inquiries"

    id = Column(Integer, primary_key=True, autoincrement=True)

    inquiry_type = Column(String(50), nullable=False, index=True)  # "general", "application_status", "technical_support", "sales"

    status = Column(String(20), nullable=False, default="new", index=True)  # "new", "in_progress", "resolved", "closed"

    priority = Column(String(20), nullable=False, default="normal")  # "low", "normal", "high", "urgent"

    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    email = Column(String(255), nullable=False)

    name = Column(String(255), nullable=False)

    subject = Column(String(500), nullable=False)

    message = Column(Text, nullable=False)

    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    resolved_at = Column(DateTime, nullable=True)

    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)

    response_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id])
    user = relationship("User", foreign_keys=[user_id])
    assignee = relationship("User", foreign_keys=[assigned_to])
    resolver = relationship("User", foreign_keys=[resolved_by])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "inquiry_type": self.inquiry_type,
            "status": self.status,
            "priority": self.priority,
            "application_id": self.application_id,
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "subject": self.subject,
            "message": self.message,
            "assigned_to": self.assigned_to,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "response_message": self.response_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KYCVerification(Base):
    """KYC verification record for users."""

    __tablename__ = "kyc_verifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    kyc_status = Column(String(50), default="pending", nullable=False, index=True)  # pending, completed, rejected, expired
    kyc_level = Column(String(50), default="basic", nullable=False)  # basic, standard, enhanced
    
    # Verification checks
    identity_verified = Column(Boolean, default=False, nullable=False)
    address_verified = Column(Boolean, default=False, nullable=False)
    document_verified = Column(Boolean, default=False, nullable=False)
    license_verified = Column(Boolean, default=False, nullable=False)
    sanctions_check_passed = Column(Boolean, default=False, nullable=False)
    pep_check_passed = Column(Boolean, default=False, nullable=False)
    
    verification_metadata = Column(JSONB, nullable=True)
    policy_evaluation_result = Column(JSONB, nullable=True)
    peoplehub_profile_id = Column(String(255), nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relationships
    user = relationship("User", back_populates="kyc_verification", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    licenses = relationship("UserLicense", back_populates="kyc_verification", cascade="all, delete-orphan")
    documents = relationship("KYCDocument", back_populates="kyc_verification", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "kyc_status": self.kyc_status,
            "kyc_level": self.kyc_level,
            "identity_verified": self.identity_verified,
            "address_verified": self.address_verified,
            "document_verified": self.document_verified,
            "license_verified": self.license_verified,
            "sanctions_check_passed": self.sanctions_check_passed,
            "pep_check_passed": self.pep_check_passed,
            "verification_metadata": self.verification_metadata,
            "policy_evaluation_result": self.policy_evaluation_result,
            "peoplehub_profile_id": self.peoplehub_profile_id,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
        }


class UserLicense(Base):
    """Professional licenses and certifications for users."""

    __tablename__ = "user_licenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kyc_verification_id = Column(Integer, ForeignKey("kyc_verifications.id", ondelete="CASCADE"), nullable=True, index=True)
    
    license_type = Column(String(100), nullable=False)  # professional_license, certification, registration
    license_number = Column(EncryptedString(255), nullable=False)
    license_category = Column(String(50), nullable=False)  # banking, legal, accounting, etc.
    
    issuing_authority = Column(String(255), nullable=False)
    issue_date = Column(Date, nullable=True)
    expiration_date = Column(Date, nullable=True)
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    verification_status = Column(String(50), default="pending", nullable=False)  # pending, verified, rejected, expired
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="licenses")
    kyc_verification = relationship("KYCVerification", back_populates="licenses")
    document = relationship("Document")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "kyc_verification_id": self.kyc_verification_id,
            "license_type": self.license_type,
            "license_number": self.license_number,
            "license_category": self.license_category,
            "issuing_authority": self.issuing_authority,
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "document_id": self.document_id,
            "verification_status": self.verification_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KYCDocument(Base):
    """Identification and supporting documents for KYC."""

    __tablename__ = "kyc_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    kyc_verification_id = Column(Integer, ForeignKey("kyc_verifications.id", ondelete="CASCADE"), nullable=True, index=True)
    
    document_type = Column(String(100), nullable=False)  # id_document, proof_of_address, bank_statement, tax_document
    document_category = Column(String(100), nullable=False)  # passport, driver_license, utility_bill, etc.
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    verification_status = Column(String(50), default="pending", nullable=False)
    extracted_data = Column(JSONB, nullable=True)  # OCR-extracted data
    ocr_confidence = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="kyc_documents")
    kyc_verification = relationship("KYCVerification", back_populates="documents")
    document = relationship("Document")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "kyc_verification_id": self.kyc_verification_id,
            "document_type": self.document_type,
            "document_category": self.document_category,
            "document_id": self.document_id,
            "verification_status": self.verification_status,
            "extracted_data": self.extracted_data,
            "ocr_confidence": self.ocr_confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Meeting(Base):
    """Meeting model for scheduling meetings related to applications."""

    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, autoincrement=True)

    title = Column(String(255), nullable=False)

    description = Column(Text, nullable=True)

    scheduled_at = Column(DateTime, nullable=False, index=True)

    duration_minutes = Column(Integer, nullable=False, default=30)

    meeting_type = Column(String(50), nullable=True)  # "consultation", "review", "follow_up", etc.

    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)

    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    attendees = Column(JSONB, nullable=True)  # List of user IDs or email addresses

    meeting_link = Column(String(500), nullable=True)  # Video conference link

    ics_file_path = Column(String(500), nullable=True)  # Path to generated ICS file

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    application = relationship("Application", foreign_keys=[application_id])
    organizer = relationship("User", foreign_keys=[organizer_id])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "duration_minutes": self.duration_minutes,
            "meeting_type": self.meeting_type,
            "application_id": self.application_id,
            "organizer_id": self.organizer_id,
            "attendees": self.attendees,
            "meeting_link": self.meeting_link,
            "ics_file_path": self.ics_file_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Deal(Base):
    """Deal model for tracking deal lifecycle and file management."""

    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, autoincrement=True)

    deal_id = Column(
        String(255), unique=True, nullable=False, index=True
    )  # External deal identifier

    applicant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)

    status = Column(String(50), default=DealStatus.DRAFT.value, nullable=False, index=True)
    
    deal_type = Column(String(50), nullable=True, index=True)  # loan_application, debt_sale, loan_purchase, etc.
    
    is_demo = Column(Boolean, default=False, nullable=False, index=True)  # Flag for demo/seed data
    
    deal_data = Column(JSONB, nullable=True)  # Deal parameters, metadata

    folder_path = Column(String(500), nullable=True)  # File system path for deal documents

    verification_required = Column(Boolean, default=False, nullable=False)

    verification_completed_at = Column(DateTime, nullable=True)

    notarization_required = Column(Boolean, default=False, nullable=False)

    notarization_completed_at = Column(DateTime, nullable=True)

    # Signature tracking
    required_signatures = Column(JSONB, nullable=True)  # List of required signers: [{"name": "...", "email": "...", "role": "..."}]
    completed_signatures = Column(JSONB, nullable=True)  # List of completed: [{"signer_email": "...", "signed_at": "...", "signature_id": ...}]
    signature_status = Column(String(50), nullable=True, index=True)  # pending, in_progress, completed, expired
    signature_progress = Column(Integer, default=0, nullable=False)  # Percentage: 0-100
    signature_deadline = Column(DateTime, nullable=True, index=True)
    
    # Documentation tracking
    required_documents = Column(JSONB, nullable=True)  # List of required: [{"document_type": "...", "document_category": "...", "required_by": "..."}]
    completed_documents = Column(JSONB, nullable=True)  # List of completed: [{"document_id": ..., "document_type": "...", "completed_at": "..."}]
    documentation_status = Column(String(50), nullable=True, index=True)  # pending, in_progress, complete, non_compliant
    documentation_progress = Column(Integer, default=0, nullable=False)  # Percentage: 0-100
    documentation_deadline = Column(DateTime, nullable=True, index=True)
    
    # Compliance tracking
    compliance_status = Column(String(50), nullable=True, index=True)  # compliant, non_compliant, pending_review
    compliance_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    applicant = relationship("User", back_populates="deals", foreign_keys=[applicant_id])
    application = relationship("Application", back_populates="deal")
    documents = relationship("Document", back_populates="deal")
    notes = relationship("DealNote", back_populates="deal", cascade="all, delete-orphan")
    filings = relationship("DocumentFiling", back_populates="deal", cascade="all, delete-orphan")
    loan_defaults = relationship("LoanDefault", back_populates="deal", cascade="all, delete-orphan")
    borrower_contacts = relationship("BorrowerContact", back_populates="deal", cascade="all, delete-orphan")
    sfp_packages = relationship("SFPPackage", back_populates="deal", cascade="all, delete-orphan")
    market_events = relationship("MarketEvent", back_populates="deal", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert model to dictionary."""
        # Extract borrower info from deal_data or first document
        deal_data = self.deal_data or {}
        
        borrower_name = deal_data.get("borrower_name")
        if not borrower_name and self.documents:
            borrower_name = self.documents[0].borrower_name
        if not borrower_name:
            borrower_name = "Unknown"
            
        total_commitment = deal_data.get("total_commitment")
        if total_commitment is None and self.documents:
            total_commitment = float(self.documents[0].total_commitment) if self.documents[0].total_commitment else 0
        if total_commitment is None:
            total_commitment = 0
            
        currency = deal_data.get("currency")
        if not currency and self.documents:
            currency = self.documents[0].currency
        if not currency:
            currency = "USD"

        return {
            "id": self.id,
            "deal_id": self.deal_id,
            "applicant_id": self.applicant_id,
            "application_id": self.application_id,
            "status": self.status,
            "deal_type": self.deal_type,
            "is_demo": self.is_demo,
            "deal_data": self.deal_data,
            "borrower_name": borrower_name,
            "total_commitment": total_commitment,
            "currency": currency,
            "folder_path": self.folder_path,
            "verification_required": self.verification_required,
            "verification_completed_at": self.verification_completed_at.isoformat() if self.verification_completed_at else None,
            "notarization_required": self.notarization_required,
            "notarization_completed_at": self.notarization_completed_at.isoformat() if self.notarization_completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class DealNote(Base):
    """Deal note model for user notes on deals."""

    __tablename__ = "deal_notes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    deal_id = Column(
        Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True
    )

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    content = Column(Text, nullable=False)

    note_type = Column(String(50), nullable=True)  # general, verification, status_change, etc.

    # Note: Using note_metadata instead of metadata to avoid SQLAlchemy reserved attribute conflict
    note_metadata = Column(JSONB, name="metadata", nullable=True)  # Additional note metadata

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship("Deal", back_populates="notes")
    user = relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "deal_id": self.deal_id,
            "user_id": self.user_id,
            "content": self.content,
            "note_type": self.note_type,
            "metadata": self.note_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SFPPackage(Base):
    """Structured Financial Product bundle with Merkle root anchor."""

    __tablename__ = "sfp_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sfp_id = Column(String(255), unique=True, nullable=False, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=False, index=True)
    merkle_root = Column(String(66), nullable=False)
    cdm_hash = Column(String(66), nullable=False)
    signature_hashes = Column(JSONB, nullable=False)
    filing_hashes = Column(JSONB, nullable=False)
    transaction_hash = Column(String(66), nullable=True)
    block_number = Column(Integer, nullable=True)
    bundle_timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    market_event_type = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    deal = relationship("Deal", back_populates="sfp_packages")
    market_events = relationship("MarketEvent", back_populates="sfp_package", cascade="all, delete-orphan")


class MarketEvent(Base):
    """Polymarket prediction market event linked to SFP, or to pool/tranche/loan for listings and loan binary markets."""

    __tablename__ = "market_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_id = Column(String(255), unique=True, nullable=False, index=True)
    sfp_package_id = Column(Integer, ForeignKey("sfp_packages.id"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    pool_id = Column(Integer, ForeignKey("securitization_pools.id", ondelete="SET NULL"), nullable=True, index=True)
    tranche_id = Column(Integer, ForeignKey("securitization_tranches.id", ondelete="SET NULL"), nullable=True, index=True)
    loan_asset_id = Column(Integer, ForeignKey("loan_assets.id", ondelete="SET NULL"), nullable=True, index=True)
    question = Column(Text, nullable=False)
    outcome_type = Column(String(50), nullable=False)
    resolution_condition = Column(JSONB, nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    resolution_outcome = Column(String(20), nullable=True)
    oracle_triggered = Column(Boolean, default=False, nullable=False)
    liquidity_pool_address = Column(String(66), nullable=True)
    visibility = Column(String(20), default="public", nullable=False)

    sfp_package = relationship("SFPPackage", back_populates="market_events")
    deal = relationship("Deal", back_populates="market_events")
    creator = relationship("User", foreign_keys=[created_by])
    orders = relationship("MarketOrder", back_populates="market_event", cascade="all, delete-orphan")


class MarketOrder(Base):
    """Order in the internal SFP marketplace (Polymarket-like)."""

    __tablename__ = "market_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    market_event_id = Column(Integer, ForeignKey("market_events.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # "yes" | "no"
    price = Column(Numeric(20, 8), nullable=False)
    size = Column(Numeric(20, 8), nullable=False)
    status = Column(String(20), nullable=False, default="open", index=True)  # open, filled, cancelled
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    filled_at = Column(DateTime, nullable=True)

    market_event = relationship("MarketEvent", back_populates="orders")
    user = relationship("User", foreign_keys=[user_id])


class PolymarketSurveillanceBaseline(Base):
    """Baseline metrics for Polymarket surveillance (wallet, market, condition)."""

    __tablename__ = "polymarket_surveillance_baselines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False, index=True)  # "wallet", "market", "condition"
    entity_id = Column(String(255), nullable=False, index=True)
    window = Column(String(50), nullable=False)  # e.g. "1d", "7d", "30d"
    metric = Column(String(100), nullable=False, index=True)  # e.g. "volume", "trade_count", "first_seen_ts"
    value = Column(JSONB, nullable=True)  # flexible numeric/object
    computed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "window", "metric", name="uq_polymarket_surveillance_baseline"),
    )


class PolymarketSurveillanceAlert(Base):
    """Alerts from Polymarket surveillance detection (outsized bet, new wallet anomaly, etc.)."""

    __tablename__ = "polymarket_surveillance_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_type = Column(String(100), nullable=False, index=True)  # e.g. "outsized_bet", "new_wallet_anomaly"
    severity = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"
    condition_id = Column(String(255), nullable=True, index=True)
    proxy_wallet = Column(String(66), nullable=True, index=True)
    event_id = Column(String(255), nullable=True)
    signal_values = Column(JSONB, nullable=True)  # snapshot of signals that fired
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolution = Column(String(50), nullable=True)  # "dismissed", "escalated", "false_positive"

    reviewer = relationship("User", foreign_keys=[reviewed_by])


class CrossChainTransaction(Base):
    """Cross-chain bridge transfer for Polymarket/SFP outcome tokens."""

    __tablename__ = "cross_chain_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    source_chain_id = Column(Integer, nullable=False, index=True)  # e.g. 137 Polygon
    dest_chain_id = Column(Integer, nullable=False, index=True)  # e.g. 8453 Base
    bridge_external_id = Column(String(255), nullable=True, index=True)  # id from bridge API
    status = Column(String(50), nullable=False, index=True)  # pending, submitted, completed, failed
    amount = Column(Numeric(36, 18), nullable=True)
    token_address = Column(String(66), nullable=True)
    market_event_id = Column(Integer, ForeignKey("market_events.id"), nullable=True, index=True)
    outcome_token_id = Column(String(255), nullable=True, index=True)
    dest_tx_hash = Column(String(66), nullable=True, index=True)  # tx hash on destination chain
    extra_data = Column(JSONB, nullable=True)  # extra payload from bridge API
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="cross_chain_transactions")
    organization = relationship("Organization", foreign_keys=[organization_id])
    market_event = relationship("MarketEvent", backref="cross_chain_transactions")


class BridgeTrade(Base):
    """Bridge trade for ChallengeCoin NFT cross-chain transfers."""

    __tablename__ = "bridge_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_id = Column(Integer, nullable=False, index=True)
    source_chain_id = Column(Integer, nullable=False, index=True)
    target_chain_id = Column(Integer, nullable=False, index=True)
    target_address = Column(String(66), nullable=False, index=True)
    trade_type = Column(String(50), nullable=False, default="transfer", index=True)
    status = Column(String(50), nullable=False, index=True)  # pending, locked, bridging, completed, failed
    lock_tx_hash = Column(String(66), nullable=True, index=True)
    bridge_external_id = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="bridge_trades")


class Policy(Base):
    """Policy model for policy editor and management."""

    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String(255), nullable=False, index=True)
    category = Column(
        String(100), nullable=True, index=True
    )  # 'regulatory', 'credit_risk', 'esg', etc.
    description = Column(Text, nullable=True)
    rules_yaml = Column(Text, nullable=False)  # Full YAML content

    status = Column(
        String(50), default=PolicyStatus.DRAFT.value, nullable=False, index=True
    )  # 'draft', 'pending_approval', 'active', 'archived'
    version = Column(Integer, default=1, nullable=False)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Note: Using additional_metadata instead of metadata to avoid SQLAlchemy reserved attribute conflict
    additional_metadata = Column(
        JSONB, name="metadata", nullable=True
    )  # Additional metadata (tags, notes, etc.)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True, index=True)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_policies")
    approver = relationship("User", foreign_keys=[approved_by], backref="approved_policies")
    versions = relationship("PolicyVersion", back_populates="policy", cascade="all, delete-orphan")
    approvals = relationship(
        "PolicyApproval", back_populates="policy", cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "rules_yaml": self.rules_yaml,
            "status": self.status,
            "version": self.version,
            "created_by": self.created_by,
            "approved_by": self.approved_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.additional_metadata,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }


class PolicyVersion(Base):
    """Policy version model for tracking policy changes."""

    __tablename__ = "policy_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    policy_id = Column(Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True)

    version = Column(Integer, nullable=False)

    rules_yaml = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    policy = relationship("Policy", back_populates="versions")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "version": self.version,
            "rules_yaml": self.rules_yaml,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PolicyApproval(Base):
    """Policy approval history for audit trail."""

    __tablename__ = "policy_approvals"

    id = Column(Integer, primary_key=True, autoincrement=True)

    policy_id = Column(
        Integer, ForeignKey("policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version = Column(Integer, nullable=False)  # Version being approved

    approved_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approved_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    approval_status = Column(String(50), nullable=False)  # 'approved', 'rejected'
    approval_comment = Column(Text, nullable=True)  # Approval/rejection reason

    # Relationships
    policy = relationship("Policy", back_populates="approvals")
    approver = relationship("User", foreign_keys=[approved_by])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "policy_id": self.policy_id,
            "version": self.version,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "approval_status": self.approval_status,
            "approval_comment": self.approval_comment,
        }


class PolicyTemplate(Base):
    """Policy template model for storing pre-built policy templates."""

    __tablename__ = "policy_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(
        String(100), nullable=False, index=True
    )  # 'regulatory', 'credit_risk', 'esg', etc.
    description = Column(Text, nullable=True)
    rules_yaml = Column(Text, nullable=False)  # Template YAML content
    use_case = Column(
        String(255), nullable=True, index=True
    )  # e.g., 'basel_iii_capital', 'sanctions_screening'
    metadata_ = Column(
        JSONB, name="metadata", nullable=True
    )  # Additional metadata (tags, complexity, etc.)
    is_system_template = Column(
        Boolean, default=False, nullable=False, index=True
    )  # System vs user-created
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "rules_yaml": self.rules_yaml,
            "use_case": self.use_case,
            "metadata": self.metadata_,
            "is_system_template": self.is_system_template,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class FilingTemplate(Base):
    """Filing form template model for storing and reusing filing form templates."""
    
    __tablename__ = "filing_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Template identification
    name = Column(String(255), nullable=False, index=True)
    jurisdiction = Column(String(50), nullable=False, index=True)  # "US", "UK", "FR", "DE"
    authority = Column(String(255), nullable=False, index=True)  # "SEC", "Companies House", "AMF", "BaFin"
    form_type = Column(String(100), nullable=True, index=True)  # "8-K", "MR01", etc.
    agreement_type = Column(String(100), nullable=True, index=True)  # "facility_agreement", etc.
    
    # Template content
    template_data = Column(JSONB, nullable=False)  # FilingFormData structure
    field_mappings = Column(JSONB, nullable=True)  # CDM field to form field mappings
    required_fields = Column(JSONB, nullable=True)  # List of required fields
    
    # Metadata
    description = Column(Text, nullable=True)
    language = Column(String(10), nullable=True, default="en")  # "en", "fr", "de"
    is_system_template = Column(Boolean, default=False, nullable=False, index=True)
    usage_count = Column(Integer, default=0, nullable=False)  # How many times used
    
    # Ownership
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "jurisdiction": self.jurisdiction,
            "authority": self.authority,
            "form_type": self.form_type,
            "agreement_type": self.agreement_type,
            "template_data": self.template_data,
            "field_mappings": self.field_mappings,
            "required_fields": self.required_fields,
            "description": self.description,
            "language": self.language,
            "is_system_template": self.is_system_template,
            "usage_count": self.usage_count,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Permission(Base):
    """Permission definition model for granular access control."""

    __tablename__ = "permission_definitions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(
        String(50), nullable=False, index=True
    )  # 'document', 'deal', 'user', 'policy', etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    role_permissions = relationship("RolePermission", back_populates="permission")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class RolePermission(Base):
    """Junction table for role-permission mappings."""

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(50), nullable=False, index=True)
    permission_id = Column(
        Integer,
        ForeignKey("permission_definitions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    permission = relationship("Permission", back_populates="role_permissions")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "role": self.role,
            "permission_id": self.permission_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VerificationStatus(str, enum.Enum):
    """Status of verification requests."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class VerificationRequest(Base):
    """Verification request model for cross-machine verification."""

    __tablename__ = "verification_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    verification_id = Column(String(255), unique=True, nullable=False, index=True)

    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)

    verifier_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    verification_link_token = Column(String(255), unique=True, nullable=False, index=True)

    status = Column(
        String(20), default=VerificationStatus.PENDING.value, nullable=False, index=True
    )

    expires_at = Column(DateTime, nullable=False, index=True)

    accepted_at = Column(DateTime, nullable=True)

    declined_at = Column(DateTime, nullable=True)

    declined_reason = Column(Text, nullable=True)

    verification_metadata = Column(JSONB, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship("Deal", backref="verification_requests")
    verifier = relationship("User", foreign_keys=[verifier_user_id])
    creator = relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "verification_id": self.verification_id,
            "deal_id": self.deal_id,
            "verifier_user_id": self.verifier_user_id,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "declined_at": self.declined_at.isoformat() if self.declined_at else None,
            "declined_reason": self.declined_reason,
            "verification_metadata": self.verification_metadata,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowDelegationStatus(str, enum.Enum):
    """Status of workflow delegation."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WorkflowDelegation(Base):
    """Workflow delegation model for link-based workflow distribution."""

    __tablename__ = "workflow_delegations"

    id = Column(Integer, primary_key=True, autoincrement=True)

    workflow_id = Column(String(255), unique=True, nullable=False, index=True)

    workflow_type = Column(String(50), nullable=False, index=True)  # verification, notarization, document_review, etc.

    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)

    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)

    sender_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True)

    receiver_user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    receiver_email = Column(String(255), nullable=True, index=True)

    link_payload = Column(Text, nullable=True)  # Encrypted payload (for reference, not decrypted)

    workflow_metadata = Column(JSONB, nullable=True)  # Workflow-specific metadata

    whitelist_config = Column(JSONB, nullable=True)  # Whitelist configuration used

    status = Column(
        String(20), default=WorkflowDelegationStatus.PENDING.value, nullable=False, index=True
    )

    expires_at = Column(DateTime, nullable=False, index=True)

    completed_at = Column(DateTime, nullable=True)

    callback_url = Column(String(500), nullable=True)  # URL for state synchronization

    state_synced_at = Column(DateTime, nullable=True)  # Last state sync timestamp

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship("Deal", backref="workflow_delegations")
    document = relationship("Document", backref="workflow_delegations")
    sender = relationship("User", foreign_keys=[sender_user_id], backref="sent_workflow_delegations")
    receiver = relationship("User", foreign_keys=[receiver_user_id], backref="received_workflow_delegations")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_type": self.workflow_type,
            "deal_id": self.deal_id,
            "document_id": self.document_id,
            "sender_user_id": self.sender_user_id,
            "receiver_user_id": self.receiver_user_id,
            "receiver_email": self.receiver_email,
            "link_payload": self.link_payload,
            "workflow_metadata": self.workflow_metadata,
            "whitelist_config": self.whitelist_config,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "callback_url": self.callback_url,
            "state_synced_at": self.state_synced_at.isoformat() if self.state_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class WorkflowDelegationState(Base):
    """Workflow delegation state history for tracking state transitions."""

    __tablename__ = "workflow_delegation_states"

    id = Column(Integer, primary_key=True, autoincrement=True)

    delegation_id = Column(
        Integer, ForeignKey("workflow_delegations.id", ondelete="CASCADE"), nullable=False, index=True
    )

    state = Column(String(50), nullable=False, index=True)  # pending, processing, completed, etc.

    state_metadata = Column(JSONB, nullable=True)  # State-specific metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    delegation = relationship("WorkflowDelegation", backref="state_history")

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "delegation_id": self.delegation_id,
            "state": self.state,
            "metadata": self.state_metadata,  # Return as 'metadata' in API response
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class PermissionKeyType(str, enum.Enum):
    """Type of permission key for .nexus file access."""

    WALLET = "wallet"
    APPLICATION = "application"


class PermissionKey(Base):
    """Permission key for .nexus file access (wallet, application, whitelist)."""

    __tablename__ = "permission_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_id = Column(String(255), unique=True, nullable=False, index=True)
    key_type = Column(String(50), nullable=False, index=True)
    encrypted_key = Column(JSONB, nullable=False)
    key_hash = Column(String(255), nullable=False, index=True)
    permissions = Column(JSONB, nullable=False)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)
    workflow_id = Column(String(255), nullable=True, index=True)
    wallet_address = Column(String(255), nullable=True, index=True)
    application_key_id = Column(String(255), nullable=True, index=True)
    whitelist_id = Column(String(255), nullable=True, index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    download_ttl = Column(DateTime, nullable=True, index=True)
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WhitelistScope(str, enum.Enum):
    """Scope of a whitelist profile: file, ip, implementation, node, or unified."""

    FILE = "file"
    IP = "ip"
    IMPLEMENTATION = "implementation"
    NODE = "node"
    UNIFIED = "unified"


class WhitelistProfile(Base):
    """Unified whitelist: file categories/extensions, IP/CIDR, implementations, nodes."""

    __tablename__ = "whitelist_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    scope = Column(String(50), nullable=False, index=True)  # file, ip, implementation, node, unified

    # File: aligned with verification_file_whitelist YAML
    enabled_categories = Column(JSONB, nullable=True)  # ["legal","financial",...]
    file_types = Column(JSONB, nullable=True)  # {"allowed_extensions":[...],"max_file_size_mb":50}
    subdirectories = Column(JSONB, nullable=True)  # {"documents":{"enabled":true,"priority":1},...}

    # IP
    allowed_ips = Column(JSONB, nullable=True)  # ["1.2.3.4",...]
    allowed_cidrs = Column(JSONB, nullable=True)  # ["10.0.0.0/8",...]

    # Implementations and nodes
    implementation_ids = Column(JSONB, nullable=True)  # [1,2] FK to verified_implementations.id
    allowed_nodes = Column(JSONB, nullable=True)  # [{"id":"","host":"","purpose":"api"|"worker"|"blockchain"|"other"}]

    preset_implementation_id = Column(Integer, ForeignKey("verified_implementations.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "scope": self.scope,
            "enabled_categories": self.enabled_categories,
            "file_types": self.file_types,
            "subdirectories": self.subdirectories,
            "allowed_ips": self.allowed_ips,
            "allowed_cidrs": self.allowed_cidrs,
            "implementation_ids": self.implementation_ids,
            "allowed_nodes": self.allowed_nodes,
            "preset_implementation_id": self.preset_implementation_id,
            "organization_id": self.organization_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SharingEvent(Base):
    """Sharing event for blockchain-notarized send/receive of .nexus files."""

    __tablename__ = "sharing_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    sharing_method = Column(String(50), nullable=False)
    workflow_id = Column(String(255), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    receiver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    receiver_email = Column(String(255), nullable=True, index=True)
    receiver_wallet_address = Column(String(255), nullable=True, index=True)
    file_hash = Column(String(255), nullable=False, index=True)
    file_size = Column(Integer, nullable=True)
    files_included = Column(Integer, default=0, nullable=False)
    blockchain_tx_hash = Column(String(255), nullable=True, index=True)
    blockchain_block_number = Column(Integer, nullable=True)
    notarized_at = Column(DateTime, nullable=True)
    cdm_event = Column(JSONB, nullable=True)
    event_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class GreenFinanceAssessment(Base):
    """Green Finance Assessment model for storing comprehensive green finance assessments."""
    
    __tablename__ = "green_finance_assessments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Transaction/Deal reference
    transaction_id = Column(String(255), nullable=False, index=True)  # Deal ID or transaction ID
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    loan_asset_id = Column(Integer, ForeignKey("loan_assets.id"), nullable=True, index=True)
    
    # Location
    location_lat = Column(Numeric(10, 7), nullable=False)
    location_lon = Column(Numeric(10, 7), nullable=False)
    location_type = Column(String(50), nullable=True)  # "urban", "suburban", "rural"
    location_confidence = Column(Numeric(5, 4), nullable=True)  # 0.0-1.0
    
    # Environmental metrics (stored as JSONB for flexibility)
    environmental_metrics = Column(JSONB, nullable=True)  # Air quality, emissions, pollution
    urban_activity_metrics = Column(JSONB, nullable=True)  # Vehicle counts, traffic, OSM-based indicators
    sustainability_score = Column(Numeric(5, 4), nullable=True)  # Composite score 0.0-1.0
    sustainability_components = Column(JSONB, nullable=True)  # Component breakdown
    sdg_alignment = Column(JSONB, nullable=True)  # SDG alignment scores
    
    # Policy decisions and CDM events
    policy_decisions = Column(JSONB, nullable=True)  # List of policy decisions
    cdm_events = Column(JSONB, nullable=True)  # List of CDM events
    
    # Metadata
    assessed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    deal = relationship("Deal", backref="green_finance_assessments")
    # Note: LoanAsset is a SQLModel, so we can't use a string reference here
    # Access via loan_asset_id foreign key instead, or configure relationship after models load
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "deal_id": self.deal_id,
            "loan_asset_id": self.loan_asset_id,
            "location_lat": float(self.location_lat) if self.location_lat else None,
            "location_lon": float(self.location_lon) if self.location_lon else None,
            "location_type": self.location_type,
            "location_confidence": float(self.location_confidence) if self.location_confidence else None,
            "environmental_metrics": self.environmental_metrics,
            "urban_activity_metrics": self.urban_activity_metrics,
            "sustainability_score": float(self.sustainability_score) if self.sustainability_score else None,
            "sustainability_components": self.sustainability_components,
            "sdg_alignment": self.sdg_alignment,
            "policy_decisions": self.policy_decisions,
            "cdm_events": self.cdm_events,
            "assessed_at": self.assessed_at.isoformat() if self.assessed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class NotarizationStatus(str, enum.Enum):
    """Status of notarization records."""

    PENDING = "pending"
    SIGNED = "signed"
    COMPLETED = "completed"


class NotarizationRecord(Base):
    """Notarization record model for blockchain-based signing."""

    __tablename__ = "notarization_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    deal_id = Column(
        Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True  # Changed to nullable for securitization
    )

    notarization_hash = Column(String(255), nullable=False)  # Hash of CDM payload

    required_signers = Column(JSONB, nullable=False)  # Array of wallet addresses

    signatures = Column(
        JSONB, nullable=True
    )  # Array of {"wallet_address": "...", "signature": "...", "signed_at": "..."}

    status = Column(
        String(20), default=NotarizationStatus.PENDING.value, nullable=False, index=True
    )

    completed_at = Column(DateTime, nullable=True)

    cdm_event_id = Column(String(255), nullable=True)  # Reference to CDM event

    # Payment fields
    payment_event_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True, index=True)
    payment_status = Column(String(20), nullable=True, default="pending")  # pending, paid, skipped, failed
    payment_transaction_hash = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Securitization link
    securitization_pool_id = Column(Integer, ForeignKey("securitization_pools.id"), nullable=True, index=True)
    
    # Relationships
    deal = relationship("Deal", backref="notarization_records")
    payment_event = relationship("PaymentEvent", foreign_keys=[payment_event_id], backref="notarization_records")
    securitization_pool = relationship("SecuritizationPool", back_populates="notarizations", foreign_keys=[securitization_pool_id])

class DemoSeedingStatus(Base):
    """Model for tracking demo data seeding progress."""
    
    __tablename__ = "demo_seeding_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    stage = Column(String(50), nullable=False, index=True)  # users, templates, deals, documents, etc.
    
    progress = Column(Numeric(5, 2), nullable=False, default=0.00)  # 0.00 to 100.00
    
    total = Column(Integer, nullable=False, default=0)
    
    current = Column(Integer, nullable=False, default=0)
    
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    
    errors = Column(JSONB, nullable=True)  # List of error messages
    
    started_at = Column(DateTime, nullable=True)
    
    completed_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "stage": self.stage,
            "progress": float(self.progress) if self.progress else 0.0,
            "total": self.total,
            "current": self.current,
            "status": self.status,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }



    """Remote application profile for API access control."""



class VerificationAuditLog(Base):
    """Audit log for verification requests."""

    __tablename__ = "verification_audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)

    verification_id = Column(
        Integer,
        ForeignKey("verification_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    action = Column(String(50), nullable=False)  # created, viewed, accepted, declined

    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    actor_ip_address = Column(String(45), nullable=True)

    audit_metadata = Column(JSONB, name="metadata", nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    verification_request = relationship("VerificationRequest", backref="audit_logs")
    actor = relationship("User", foreign_keys=[actor_user_id])

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "verification_id": self.verification_id,
            "action": self.action,
            "actor_user_id": self.actor_user_id,
            "actor_ip_address": self.actor_ip_address,
            "metadata": self.audit_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
# Note: LoanAsset is a SQLModel and cannot have a direct relationship with SQLAlchemy Base models
# Access LoanAsset via loan_asset_id foreign key using queries instead
# Example: db.query(LoanAsset).filter(LoanAsset.id == assessment.loan_asset_id).first()


class SatelliteLayer(Base):
    """Satellite layer data for visualization and analysis."""

    __tablename__ = "satellite_layers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Reference to loan asset (no FK constraint since LoanAsset is SQLModel)
    loan_asset_id = Column(Integer, nullable=False, index=True)
    
    # Layer identification
    layer_type = Column(String(50), nullable=False, index=True)  # ndvi, false_color, classification, sentinel_band
    band_number = Column(String(10), nullable=True)  # B01, B02, etc. for Sentinel-2 bands
    
    # Storage
    file_path = Column(String(1000), nullable=False)  # Relative path from storage base
    layer_metadata = Column(JSONB, name="metadata", nullable=True)  # Layer metadata (resolution, bounds, etc.)
    
    # Geographic information
    resolution = Column(Integer, nullable=True)  # Resolution in meters
    bounds_north = Column(Numeric(10, 7), nullable=True)
    bounds_south = Column(Numeric(10, 7), nullable=True)
    bounds_east = Column(Numeric(10, 7), nullable=True)
    bounds_west = Column(Numeric(10, 7), nullable=True)
    crs = Column(String(50), default='EPSG:4326')  # Coordinate reference system
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "loan_asset_id": self.loan_asset_id,
            "layer_type": self.layer_type,
            "band_number": self.band_number,
            "file_path": self.file_path,
            "metadata": self.layer_metadata,
            "resolution": self.resolution,
            "bounds": {
                "north": float(self.bounds_north) if self.bounds_north else None,
                "south": float(self.bounds_south) if self.bounds_south else None,
                "east": float(self.bounds_east) if self.bounds_east else None,
                "west": float(self.bounds_west) if self.bounds_west else None,
            },
            "crs": self.crs,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Securitization Models
# ============================================================================

class SecuritizationPool(Base):
    """Securitization pool model for structured finance products."""
    
    __tablename__ = "securitization_pools"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(String(255), unique=True, nullable=False, index=True)
    pool_name = Column(String(255), nullable=False)
    pool_type = Column(String(50), nullable=False)  # 'ABS', 'CLO', 'MBS', etc.
    originator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    trustee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    total_pool_value = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    cdm_payload = Column(JSONB, nullable=False)  # Full CDM SecuritizationPool object
    cdm_data = Column(JSONB, nullable=True)  # Additional CDM data (payment schedule, etc.)
    status = Column(String(50), nullable=False, index=True)  # 'draft', 'pending_notarization', 'notarized', 'filed', 'active'
    lock_period_days = Column(Integer, nullable=True)  # Deterministic lock for equity bundles
    lock_until = Column(DateTime, nullable=True)  # Lock expiry (lock_until or created_at + lock_period_days)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notarized_at = Column(DateTime, nullable=True)
    filed_at = Column(DateTime, nullable=True)
    
    # Relationships
    originator = relationship("User", foreign_keys=[originator_id])
    trustee = relationship("User", foreign_keys=[trustee_id])
    tranches = relationship("SecuritizationTranche", back_populates="pool", cascade="all, delete-orphan")
    assets = relationship("SecuritizationPoolAsset", back_populates="pool", cascade="all, delete-orphan")
    filings = relationship("RegulatoryFiling", back_populates="pool", cascade="all, delete-orphan")
    notarizations = relationship("NotarizationRecord", back_populates="securitization_pool")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "pool_name": self.pool_name,
            "pool_type": self.pool_type,
            "originator_id": self.originator_id,
            "trustee_id": self.trustee_id,
            "total_pool_value": str(self.total_pool_value),
            "currency": self.currency,
            "cdm_payload": self.cdm_payload,
            "cdm_data": self.cdm_data,
            "status": self.status,
            "lock_period_days": self.lock_period_days,
            "lock_until": self.lock_until.isoformat() if self.lock_until else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "notarized_at": self.notarized_at.isoformat() if self.notarized_at else None,
            "filed_at": self.filed_at.isoformat() if self.filed_at else None,
        }


class LoanAsset(Base):
    """Loan asset model for ground truth protocol and securitization."""

    __tablename__ = "loan_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    loan_id = Column(String(255), nullable=False, index=True)

    # Legal Reality
    original_text = Column(EncryptedText(), nullable=True)  # Encrypted document text (large field)
    legal_vector = Column(JSONB, nullable=True)  # Vector embeddings - Not sensitive

    # Physical Reality
    geo_lat = Column(Float, nullable=True)  # Geographic data - Not sensitive
    geo_lon = Column(Float, nullable=True)  # Geographic data - Not sensitive
    collateral_address = Column(EncryptedString(500), nullable=True)  # Encrypted PII
    satellite_snapshot_url = Column(String(1000), nullable=True)
    geo_vector = Column(JSONB, nullable=True)

    # SPT Data
    spt_data = Column(JSONB, nullable=True)

    # Verification State
    last_verified_score = Column(Float, nullable=True)
    spt_threshold = Column(Float, nullable=True, default=0.8)
    risk_status = Column(String(50), nullable=False, default="PENDING", index=True)
    base_interest_rate = Column(Float, nullable=True, default=5.0)
    current_interest_rate = Column(Float, nullable=True, default=5.0)
    penalty_bps = Column(Float, nullable=True, default=50.0)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_verified_at = Column(DateTime, nullable=True)
    verification_error = Column(Text, nullable=True)
    asset_metadata = Column(JSONB, nullable=True, name="metadata")

    # Green Finance Metrics
    location_type = Column(String(50), nullable=True)
    air_quality_index = Column(Float, nullable=True)
    composite_sustainability_score = Column(Float, nullable=True)
    green_finance_metrics = Column(JSONB, nullable=True)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "loan_id": self.loan_id,
            "original_text": self.original_text,
            "collateral_address": self.collateral_address,
            "geo_lat": self.geo_lat,
            "geo_lon": self.geo_lon,
            "satellite_snapshot_url": self.satellite_snapshot_url,
            "spt_data": self.spt_data,
            "last_verified_score": self.last_verified_score,
            "spt_threshold": self.spt_threshold,
            "risk_status": self.risk_status,
            "base_interest_rate": self.base_interest_rate,
            "current_interest_rate": self.current_interest_rate,
            "penalty_bps": self.penalty_bps,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "verification_error": self.verification_error,
            "location_type": self.location_type,
            "air_quality_index": self.air_quality_index,
            "composite_sustainability_score": self.composite_sustainability_score,
            "green_finance_metrics": self.green_finance_metrics,
        }


class SecuritizationTranche(Base):
    """Securitization tranche model."""
    
    __tablename__ = "securitization_tranches"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(Integer, ForeignKey("securitization_pools.id", ondelete="CASCADE"), nullable=False, index=True)
    tranche_id = Column(String(255), nullable=False, index=True)
    tranche_name = Column(String(255), nullable=False)
    tranche_class = Column(String(50), nullable=False)  # 'Senior', 'Mezzanine', 'Equity'
    size = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    interest_rate = Column(Numeric(10, 4), nullable=False)
    risk_rating = Column(String(10), nullable=True)  # 'AAA', 'AA', 'A', 'BBB', etc.
    payment_priority = Column(Integer, nullable=False)  # Lower = higher priority
    principal_remaining = Column(Numeric(20, 2), nullable=False)
    interest_accrued = Column(Numeric(20, 2), nullable=False, default=0)
    token_id = Column(String(255), nullable=True, unique=True, index=True)  # ERC-721 token ID
    owner_wallet_address = Column(String(255), nullable=True, index=True)  # Token owner wallet
    cdm_data = Column(JSONB, nullable=False)  # Full CDM Tranche data
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    pool = relationship("SecuritizationPool", back_populates="tranches")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "tranche_id": self.tranche_id,
            "tranche_name": self.tranche_name,
            "tranche_class": self.tranche_class,
            "size": str(self.size),
            "currency": self.currency,
            "interest_rate": float(self.interest_rate),
            "risk_rating": self.risk_rating,
            "payment_priority": self.payment_priority,
            "principal_remaining": str(self.principal_remaining),
            "interest_accrued": str(self.interest_accrued),
            "token_id": self.token_id,
            "owner_wallet_address": self.owner_wallet_address,
            "cdm_data": self.cdm_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SecuritizationPoolAsset(Base):
    """Pool asset model (many-to-many: Pools <-> Deals/Loans)."""
    
    __tablename__ = "securitization_pool_assets"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(Integer, ForeignKey("securitization_pools.id", ondelete="CASCADE"), nullable=False, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    loan_asset_id = Column(Integer, ForeignKey("loan_assets.id"), nullable=True, index=True)
    asset_type = Column(String(50), nullable=False)  # 'deal', 'loan_asset', 'equity', 'commodity'
    asset_id = Column(String(255), nullable=True)  # Composite identifier (deal_N, loan_N, equity_SYM, commodity_CODE)
    asset_value = Column(Numeric(20, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    equity_symbol = Column(String(50), nullable=True)  # e.g. AAPL when asset_type=equity
    commodity_code = Column(String(50), nullable=True)  # e.g. GOLD, WTI when asset_type=commodity
    allocation_percentage = Column(Numeric(5, 2), nullable=True)
    allocation_amount = Column(Numeric(20, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    pool = relationship("SecuritizationPool", back_populates="assets")
    deal = relationship("Deal")
    # Note: LoanAsset is SQLModel, so relationship handled via foreign key
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "deal_id": self.deal_id,
            "loan_asset_id": self.loan_asset_id,
            "asset_type": self.asset_type,
            "asset_id": self.asset_id,
            "asset_value": str(self.asset_value) if self.asset_value is not None else None,
            "currency": self.currency,
            "equity_symbol": self.equity_symbol,
            "commodity_code": self.commodity_code,
            "allocation_percentage": float(self.allocation_percentage) if self.allocation_percentage else None,
            "allocation_amount": str(self.allocation_amount) if self.allocation_amount else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RegulatoryFiling(Base):
    """Regulatory filing model for securitization pools."""
    
    __tablename__ = "regulatory_filings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pool_id = Column(Integer, ForeignKey("securitization_pools.id", ondelete="CASCADE"), nullable=False, index=True)
    filing_type = Column(String(50), nullable=False)  # 'SEC_10D', 'PROSPECTUS', 'PSA', 'TRUST_AGREEMENT'
    regulatory_body = Column(String(100), nullable=False)  # 'SEC', 'FINRA', etc. (mapped from filing_body in migration)
    filing_number = Column(String(255), nullable=True)  # External filing number/receipt
    status = Column(String(50), nullable=False, index=True)  # 'pending', 'submitted', 'accepted', 'rejected' (mapped from filing_status)
    document_path = Column(String(500), nullable=True)
    filed_at = Column(DateTime, nullable=True)  # When filed (mapped from submitted_at)
    accepted_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    filing_metadata = Column(JSONB, name="metadata", nullable=True)  # Additional filing metadata (receipt, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    pool = relationship("SecuritizationPool", back_populates="filings")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "pool_id": self.pool_id,
            "filing_type": self.filing_type,
            "regulatory_body": self.regulatory_body,
            "filing_number": self.filing_number,
            "status": self.status,
            "document_path": self.document_path,
            "filed_at": self.filed_at.isoformat() if self.filed_at else None,
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "rejection_reason": self.rejection_reason,
            "metadata": self.filing_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Payment Models
# ============================================================================

class PaymentEvent(Base):
    """Payment event model for x402 payment tracking."""
    
    __tablename__ = "payment_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(String(255), unique=True, nullable=False, index=True)
    payment_type = Column(String(50), nullable=False, index=True)  # 'trade_settlement', 'loan_disbursement', 'notarization_fee', etc.
    amount = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    payer_wallet_address = Column(String(255), nullable=True, index=True)
    receiver_wallet_address = Column(String(255), nullable=True, index=True)
    transaction_hash = Column(String(255), nullable=True, index=True)
    payment_status = Column(String(50), nullable=False, index=True)  # 'pending', 'paid', 'failed', 'refunded'
    facilitator_url = Column(String(500), nullable=True)
    payment_payload = Column(JSONB, nullable=True)
    cdm_event = Column(JSONB, nullable=True)  # Full CDM PaymentEvent
    related_deal_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    related_notarization_id = Column(Integer, ForeignKey("notarization_records.id"), nullable=True, index=True)
    related_trade_id = Column(Integer, nullable=True)
    related_loan_id = Column(Integer, nullable=True)
    payment_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    payer = relationship("User", foreign_keys=[payer_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    deal = relationship("Deal", foreign_keys=[related_deal_id])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "payment_type": self.payment_type,
            "amount": str(self.amount),
            "currency": self.currency,
            "payer_id": self.payer_id,
            "receiver_id": self.receiver_id,
            "payer_wallet_address": self.payer_wallet_address,
            "receiver_wallet_address": self.receiver_wallet_address,
            "transaction_hash": self.transaction_hash,
            "payment_status": self.payment_status,
            "facilitator_url": self.facilitator_url,
            "payment_payload": self.payment_payload,
            "cdm_event": self.cdm_event,
            "related_deal_id": self.related_deal_id,
            "related_notarization_id": self.related_notarization_id,
            "related_trade_id": self.related_trade_id,
            "related_loan_id": self.related_loan_id,
            "metadata": self.payment_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ============================================================================
# Trade Execution Models
# ============================================================================

class TradeExecution(Base):
    """Trade execution model for LMA trade storage and settlement lookup."""
    
    __tablename__ = "trade_executions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trade_id = Column(String(255), unique=True, nullable=False, index=True)  # Trade identifier (e.g., "TRADE-MC-2024-TLA-1769110045402")
    
    # User and deal information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    credit_agreement_id = Column(Integer, ForeignKey("deals.id"), nullable=True, index=True)
    facility_id = Column(String(255), nullable=True, index=True)
    
    # Trade details
    trade_price = Column(Numeric(20, 8), nullable=True)
    trade_amount = Column(Numeric(20, 2), nullable=True)
    settlement_date = Column(Date, nullable=True)
    
    # Status tracking
    status = Column(String(50), nullable=False, default="executed", index=True)  # executed, settled, cancelled
    
    # CDM event storage
    cdm_event = Column(JSONB, nullable=False)  # Full CDM TradeExecution event
    policy_decision = Column(JSONB, nullable=True)  # Policy evaluation result
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    settled_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="trade_executions")
    credit_agreement = relationship("Deal", foreign_keys=[credit_agreement_id])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "trade_id": self.trade_id,
            "user_id": self.user_id,
            "credit_agreement_id": self.credit_agreement_id,
            "facility_id": self.facility_id,
            "trade_price": float(self.trade_price) if self.trade_price else None,
            "trade_amount": float(self.trade_amount) if self.trade_amount else None,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "status": self.status,
            "cdm_event": self.cdm_event,
            "policy_decision": self.policy_decision,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
        }


# ============================================================================
# Credit Models (Rolling Credits)
# ============================================================================


class CreditBalance(Base):
    """User credit balance with type support (rolling credits from subscriptions)."""

    __tablename__ = "credit_balances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, nullable=True, index=True)  # FK to organizations.id when that table exists

    balances = Column(JSONB, nullable=False, default=dict)
    total_balance = Column(Numeric(19, 4), default=0, nullable=False)

    lifetime_earned = Column(JSONB, nullable=False, default=dict)
    lifetime_spent = Column(JSONB, nullable=False, default=dict)

    blockchain_registered = Column(Boolean, default=False, nullable=False)
    blockchain_token_id = Column(String(255), nullable=True, unique=True, index=True)
    blockchain_tx_hash = Column(String(255), nullable=True, index=True)
    blockchain_chain_id = Column(Integer, nullable=True)

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="credit_balance")
    transactions = relationship("CreditTransaction", back_populates="balance", cascade="all, delete-orphan")

    def get_balance(self, credit_type: str = "universal") -> Decimal:
        if credit_type == "universal":
            return Decimal(str(self.total_balance or 0))
        b = self.balances or {}
        return Decimal(str(b.get(credit_type, 0)))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "balances": self.balances or {},
            "total_balance": float(self.total_balance) if self.total_balance is not None else 0,
            "lifetime_earned": self.lifetime_earned or {},
            "lifetime_spent": self.lifetime_spent or {},
            "blockchain_registered": self.blockchain_registered,
            "blockchain_token_id": self.blockchain_token_id,
            "blockchain_tx_hash": self.blockchain_tx_hash,
            "blockchain_chain_id": self.blockchain_chain_id,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CreditTransaction(Base):
    """Credit transaction with type support (subscription, purchase, usage, conversion, refund)."""

    __tablename__ = "credit_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    balance_id = Column(Integer, ForeignKey("credit_balances.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    organization_id = Column(Integer, nullable=True, index=True)

    transaction_type = Column(String(50), nullable=False)
    credit_type = Column(String(50), nullable=False, index=True)
    amount = Column(Numeric(19, 4), nullable=False)

    balance_before = Column(JSONB, nullable=True)
    balance_after = Column(JSONB, nullable=True)

    feature = Column(String(100), nullable=True, index=True)
    related_transaction_id = Column(String(255), nullable=True, index=True)

    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id", ondelete="SET NULL"), nullable=True, index=True)

    blockchain_verified = Column(Boolean, default=False, nullable=False)
    blockchain_tx_hash = Column(String(255), nullable=True, index=True)
    bridge_tx_hash = Column(String(255), nullable=True, index=True)

    base_cost = Column(Numeric(19, 4), nullable=True)
    adaptive_cost = Column(Numeric(19, 4), nullable=True)
    pricing_factors = Column(JSONB, nullable=True)

    description = Column(Text, nullable=True)
    payment_event_id = Column(Integer, ForeignKey("payment_events.id", ondelete="SET NULL"), nullable=True, index=True)
    extra_metadata = Column(JSONB, name="metadata", nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    balance = relationship("CreditBalance", back_populates="transactions")
    user = relationship("User", foreign_keys=[user_id])
    subscription = relationship("UserSubscription", foreign_keys=[subscription_id])
    payment_event = relationship("PaymentEvent", foreign_keys=[payment_event_id])


class StockPrediction(Base):
    """Stock price prediction from Chronos or technical strategy."""

    __tablename__ = "stock_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(20), nullable=False, index=True)  # daily, hourly, 15min
    model_id = Column(String(255), nullable=False)
    strategy = Column(String(50), nullable=False, index=True)  # chronos, technical
    forecast = Column(JSONB, nullable=True)
    lookback_days = Column(Integer, nullable=False)
    horizon = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    prediction_metadata = Column(JSONB, name="metadata", nullable=True)

    user = relationship("User", foreign_keys=[user_id])

    def to_dict(self):
        # Extract forecast array from stored dict
        forecast_data = self.forecast if isinstance(self.forecast, dict) else {}
        forecast_array = forecast_data.get("forecast", []) if isinstance(forecast_data, dict) else (self.forecast if isinstance(self.forecast, list) else [])
        if not isinstance(forecast_array, list):
            forecast_array = []
        
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "model_id": self.model_id,
            "strategy": self.strategy,
            "forecast": forecast_array,  # Return as array for API compatibility
            "lookback_days": self.lookback_days,
            "horizon": self.horizon,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "metadata": self.prediction_metadata,
        }


class StockPredictionCache(Base):
    """Cache for stock prediction results by cache_key."""

    __tablename__ = "stock_prediction_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(512), nullable=False, unique=True, index=True)
    result = Column(JSONB, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class DataCache(Base):
    """
    Unified cache for market data, tool responses, and external API results.
    Supports time series (OHLCV, aggregates) and punctual (snapshots, fundamentals, news, quotes).
    source: provider (market_data, polygon, alpha_vantage, tickertick, web_search, trading).
    kind: timeseries | punctual (for TTL and audit).
    """

    __tablename__ = "data_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(512), nullable=False, unique=True, index=True)
    source = Column(String(64), nullable=False, index=True)
    kind = Column(String(32), nullable=False, index=True)  # timeseries | punctual
    result = Column(JSONB, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "cache_key": self.cache_key,
            "source": self.source,
            "kind": self.kind,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PredictionOrderRecommendation(Base):
    """Order recommendation (buy/sell/hold) from prediction or strategy."""

    __tablename__ = "prediction_order_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    prediction_id = Column(Integer, ForeignKey("stock_predictions.id", ondelete="SET NULL"), nullable=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    action = Column(String(20), nullable=False, index=True)  # buy, sell, hold
    size = Column(Numeric(19, 4), nullable=True)
    confidence = Column(Float, nullable=False)
    strategy = Column(String(50), nullable=False, index=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    extra = Column(JSONB, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    prediction = relationship("StockPrediction", foreign_keys=[prediction_id])

    def to_dict(self):
        # Ensure confidence is a valid float, defaulting to 0.5 if None or NaN
        confidence_val = self.confidence
        if confidence_val is None or (isinstance(confidence_val, float) and math.isnan(confidence_val)):
            confidence_val = 0.5
        return {
            "id": self.id,
            "user_id": self.user_id,
            "prediction_id": self.prediction_id,
            "symbol": self.symbol,
            "action": self.action,
            "size": float(self.size) if self.size is not None else None,
            "confidence": float(confidence_val) if confidence_val is not None else 0.5,
            "strategy": self.strategy,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "extra": self.extra,
        }


class TrainingJob(Base):
    """Chronos or other model training job."""

    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(String(255), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)  # pending, running, completed, failed
    config = Column(JSONB, nullable=False)
    metrics = Column(JSONB, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "model_id": self.model_id,
            "status": self.status,
            "config": self.config,
            "metrics": self.metrics,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "error_message": self.error_message,
        }


class LoanDefault(Base):
    """Loan default model for tracking payment defaults and covenant breaches."""
    
    __tablename__ = "loan_defaults"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_id = Column(String(255), nullable=True, index=True)  # Foreign key to LoanAsset or Deal
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
    default_type = Column(String(50), nullable=False, index=True)  # payment_default, covenant_breach, infraction
    default_date = Column(DateTime, nullable=False, index=True)
    default_reason = Column(Text, nullable=True)
    amount_overdue = Column(Numeric(20, 2), nullable=True)  # If payment default
    days_past_due = Column(Integer, nullable=False, default=0)
    severity = Column(String(20), nullable=False, index=True)  # low, medium, high, critical
    status = Column(String(50), nullable=False, index=True, default="open")  # open, in_recovery, resolved, written_off
    resolved_at = Column(DateTime, nullable=True)
    cdm_events = Column(JSONB, nullable=True)  # CDM events for this default
    default_metadata = Column(JSONB, name="metadata", nullable=True)  # Additional data (renamed to avoid SQLAlchemy reserved name)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    deal = relationship("Deal", back_populates="loan_defaults")
    recovery_actions = relationship("RecoveryAction", back_populates="loan_default", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "loan_id": self.loan_id,
            "deal_id": self.deal_id,
            "default_type": self.default_type,
            "default_date": self.default_date.isoformat() if self.default_date else None,
            "default_reason": self.default_reason,
            "amount_overdue": str(self.amount_overdue) if self.amount_overdue else None,
            "days_past_due": self.days_past_due,
            "severity": self.severity,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "cdm_events": self.cdm_events,
            "metadata": self.default_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RecoveryAction(Base):
    """Recovery action model for tracking communication attempts."""
    
    __tablename__ = "recovery_actions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    loan_default_id = Column(Integer, ForeignKey("loan_defaults.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False, index=True)  # sms_reminder, voice_call, email, escalation, legal_notice
    communication_method = Column(String(20), nullable=False)  # sms, voice, email
    recipient_phone = Column(String(20), nullable=True)
    recipient_email = Column(String(255), nullable=True)
    message_template = Column(String(255), nullable=False)  # Template name or custom message
    message_content = Column(Text, nullable=False)  # Actual message sent
    twilio_message_sid = Column(String(255), nullable=True, index=True)  # For SMS
    twilio_call_sid = Column(String(255), nullable=True, index=True)  # For voice
    status = Column(String(50), nullable=False, index=True, default="pending")  # pending, sent, delivered, failed, responded
    scheduled_at = Column(DateTime, nullable=True, index=True)  # For scheduled actions
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    response_received_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_metadata = Column(JSONB, name="metadata", nullable=True)  # Additional data (renamed to avoid SQLAlchemy reserved name)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    loan_default = relationship("LoanDefault", back_populates="recovery_actions")
    creator = relationship("User", foreign_keys=[created_by])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "loan_default_id": self.loan_default_id,
            "action_type": self.action_type,
            "communication_method": self.communication_method,
            "recipient_phone": self.recipient_phone,
            "recipient_email": self.recipient_email,
            "message_template": self.message_template,
            "message_content": self.message_content,
            "twilio_message_sid": self.twilio_message_sid,
            "twilio_call_sid": self.twilio_call_sid,
            "status": self.status,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "response_received_at": self.response_received_at.isoformat() if self.response_received_at else None,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "metadata": self.action_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BorrowerContact(Base):
    """Borrower contact model for managing borrower contact information."""
    
    __tablename__ = "borrower_contacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # If borrower is a user
    contact_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)  # E.164 format
    email = Column(String(255), nullable=True)
    preferred_contact_method = Column(String(20), nullable=False, default="sms")  # sms, voice, email
    contact_preferences = Column(JSONB, nullable=True)  # timezone, preferred_hours, etc.
    is_primary = Column(Boolean, default=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    contact_metadata = Column(JSONB, name="metadata", nullable=True)  # Additional data (renamed to avoid SQLAlchemy reserved name)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    deal = relationship("Deal", back_populates="borrower_contacts")
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "deal_id": self.deal_id,
            "user_id": self.user_id,
            "contact_name": self.contact_name,
            "phone_number": self.phone_number,
            "email": self.email,
            "preferred_contact_method": self.preferred_contact_method,
            "contact_preferences": self.contact_preferences,
            "is_primary": self.is_primary,
            "is_active": self.is_active,
            "metadata": self.contact_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AccountingDocument(Base):
    """Accounting document model for storing extracted accounting data."""
    
    __tablename__ = "accounting_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    document_type = Column(String(50), nullable=False, index=True)  # balance_sheet, income_statement, etc.
    extracted_data = Column(JSONB, nullable=True)  # Full accounting document structure
    reporting_period_start = Column(Date, nullable=True)
    reporting_period_end = Column(Date, nullable=True)
    period_type = Column(String(20), nullable=True, index=True)  # quarterly, annual, monthly
    currency = Column(String(10), nullable=True)  # ISO currency code
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=sa.text('now()'), onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", backref="accounting_document")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "document_type": self.document_type,
            "extracted_data": self.extracted_data,
            "reporting_period_start": self.reporting_period_start.isoformat() if self.reporting_period_start else None,
            "reporting_period_end": self.reporting_period_end.isoformat() if self.reporting_period_end else None,
            "period_type": self.period_type,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DeepResearchResult(Base):
    """Deep research result model for storing research query results."""
    
    __tablename__ = "deep_research_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    research_id = Column(String(36), nullable=False, unique=True, index=True)  # UUID as string
    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    knowledge_items = Column(JSONB, nullable=True)  # List of knowledge items
    visited_urls = Column(ARRAY(String), nullable=True)
    searched_queries = Column(ARRAY(String), nullable=True)
    token_usage = Column(JSONB, nullable=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), server_default="pending", nullable=False, index=True)  # pending, processing, completed, failed
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    deal = relationship("Deal", backref="deep_research_results")
    workflow = relationship("Workflow", backref="deep_research_results")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "research_id": self.research_id,
            "query": self.query,
            "answer": self.answer,
            "knowledge_items": self.knowledge_items,
            "visited_urls": self.visited_urls,
            "searched_queries": self.searched_queries,
            "token_usage": self.token_usage,
            "deal_id": self.deal_id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
        }


class IndividualProfile(Base):
    """Individual profile model for business intelligence."""
    
    __tablename__ = "individual_profiles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_name = Column(String(255), nullable=False, index=True)
    linkedin_url = Column(String(500), nullable=True)
    profile_data = Column(JSONB, nullable=True)  # LinkedIn data, web summaries, research report
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=sa.text('now()'), onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    deal = relationship("Deal", backref="individual_profiles")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "person_name": self.person_name,
            "linkedin_url": self.linkedin_url,
            "profile_data": self.profile_data,
            "deal_id": self.deal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BusinessProfile(Base):
    """Business profile model for business intelligence."""
    
    __tablename__ = "business_profiles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    business_name = Column(String(255), nullable=False, index=True)
    business_lei = Column(String(20), nullable=True, index=True)
    business_type = Column(String(50), nullable=True)
    industry = Column(String(100), nullable=True)
    profile_data = Column(JSONB, nullable=True)  # Business research data
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=sa.text('now()'), onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    deal = relationship("Deal", backref="business_profiles")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "business_name": self.business_name,
            "business_lei": self.business_lei,
            "business_type": self.business_type,
            "industry": self.industry,
            "profile_data": self.profile_data,
            "deal_id": self.deal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class QuantitativeAnalysisStatus(str, enum.Enum):
    """Status of quantitative analysis."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class QuantitativeAnalysisResult(Base):
    """Quantitative analysis result model for LangAlpha analysis."""
    
    __tablename__ = "quantitative_analysis_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String(36), unique=True, nullable=False, index=True)  # UUID as string
    analysis_type = Column(String(50), nullable=False, index=True)  # company, market, loan_application
    query = Column(Text, nullable=False)
    report = Column(JSONB, nullable=True)  # Final analysis report
    market_data = Column(JSONB, nullable=True)  # Market data collected
    fundamental_data = Column(JSONB, nullable=True)  # Fundamental data collected
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(20), default=QuantitativeAnalysisStatus.PENDING.value, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    deal = relationship("Deal", backref="quantitative_analyses")
    workflow = relationship("Workflow", backref="quantitative_analyses")
    user = relationship("User", foreign_keys=[user_id])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "analysis_type": self.analysis_type,
            "query": self.query,
            "report": self.report,
            "market_data": self.market_data,
            "fundamental_data": self.fundamental_data,
            "deal_id": self.deal_id,
            "workflow_id": self.workflow_id,
            "user_id": self.user_id,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class PsychometricProfile(Base):
    """Psychometric profile model for business intelligence."""
    
    __tablename__ = "psychometric_profiles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    individual_profile_id = Column(Integer, ForeignKey("individual_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    psychometric_data = Column(JSONB, nullable=False)  # Full psychometric profile structure
    buying_behavior = Column(JSONB, nullable=True)  # Buying behavior profile
    savings_behavior = Column(JSONB, nullable=True)  # Savings behavior profile
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=sa.text('now()'), onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    individual_profile = relationship("IndividualProfile", backref="psychometric_profiles")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "individual_profile_id": self.individual_profile_id,
            "psychometric_data": self.psychometric_data,
            "buying_behavior": self.buying_behavior,
            "savings_behavior": self.savings_behavior,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class AuditReport(Base):
    """Audit report model for business intelligence."""
    
    __tablename__ = "audit_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(50), nullable=False, index=True)  # individual, business
    profile_id = Column(Integer, nullable=True, index=True)  # Can reference individual or business profile
    report_data = Column(JSONB, nullable=True)  # Report content including research, psychometric data, credit check
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=sa.text('now()'), onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    deal = relationship("Deal", backref="audit_reports")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "report_type": self.report_type,
            "profile_id": self.profile_id,
            "report_data": self.report_data,
            "deal_id": self.deal_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatbotSession(Base):
    """Chatbot session model for document digitizer chatbot."""
    
    __tablename__ = "chatbot_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), nullable=False, unique=True, index=True)  # UUID as string
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="SET NULL"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    updated_at = Column(DateTime, server_default=sa.text('now()'), onupdate=datetime.utcnow, nullable=False)
    
    # Conversation summary fields (for memory sharing across middleware)
    conversation_summary = Column(Text, nullable=True)  # LLM-generated summary
    summary_key_points = Column(JSONB, nullable=True)  # List of key points
    summary_updated_at = Column(DateTime, nullable=True)  # When summary was last updated
    message_count = Column(Integer, server_default='0', nullable=False)  # Total message count
    
    # Relationships
    user = relationship("User", backref="chatbot_sessions")
    deal = relationship("Deal", backref="chatbot_sessions")
    document = relationship("Document", backref="chatbot_sessions")
    messages = relationship("ChatbotMessage", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "deal_id": self.deal_id,
            "document_id": self.document_id,
            "conversation_summary": self.conversation_summary,
            "summary_key_points": self.summary_key_points,
            "summary_updated_at": self.summary_updated_at.isoformat() if self.summary_updated_at else None,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ChatbotMessage(Base):
    """Chatbot message model for document digitizer chatbot."""
    
    __tablename__ = "chatbot_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(36), ForeignKey("chatbot_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    workflow_launched = Column(String(100), nullable=True)  # peoplehub, deepresearch, langalpha
    cdm_events = Column(JSONB, nullable=True)  # CDM events generated for this message
    created_at = Column(DateTime, server_default=sa.text('now()'), nullable=False)
    
    # Relationships
    session = relationship("ChatbotSession", back_populates="messages")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "workflow_launched": self.workflow_launched,
            "cdm_events": self.cdm_events,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VerifiedImplementation(Base):
    """Verified implementation provider (e.g., Alpaca, Plaid, Polymarket)."""
    
    __tablename__ = "verified_implementations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # "alpaca", "plaid", "polymarket"
    display_name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)  # "trading", "banking", "market", "payment"
    api_key_encrypted = Column(EncryptedString(500), nullable=True)
    api_secret_encrypted = Column(EncryptedString(500), nullable=True)
    base_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    configuration = Column(JSONB, nullable=True)  # Provider-specific config
    whitelist_preset = Column(JSONB, nullable=True)  # Recommended enabled_categories, allowed_extensions, allowed_ips, etc. for "populate from verified implementation"
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user_connections = relationship("UserImplementationConnection", back_populates="implementation")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "category": self.category,
            "base_url": self.base_url,
            "is_active": self.is_active,
            "configuration": self.configuration,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserImplementationConnection(Base):
    """User's connection to a verified implementation."""
    
    __tablename__ = "user_implementation_connections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    implementation_id = Column(Integer, ForeignKey("verified_implementations.id"), nullable=False)
    connection_data = Column(EncryptedJSON(), nullable=True)  # OAuth tokens, API keys, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="implementation_connections")
    implementation = relationship("VerifiedImplementation", back_populates="user_connections")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "implementation_id": self.implementation_id,
            "is_active": self.is_active,
            "last_synced_at": self.last_synced_at.isoformat() if self.last_synced_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserSubscription(Base):
    """User subscription record."""
    
    __tablename__ = "user_subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tier = Column(String(20), nullable=False)  # SubscriptionTier enum
    subscription_type = Column(String(20), nullable=False)  # SubscriptionType enum
    is_active = Column(Boolean, default=True, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)  # NULL for lifetime
    payment_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True)
    auto_renew = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="subscriptions")
    payment = relationship("PaymentEvent", foreign_keys=[payment_id])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "tier": self.tier,
            "subscription_type": self.subscription_type,
            "is_active": self.is_active,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "payment_id": self.payment_id,
            "auto_renew": self.auto_renew,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SubscriptionUsage(Base):
    """Pay-as-you-go usage tracking for Pro tier."""
    
    __tablename__ = "subscription_usage"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=False)
    feature = Column(String(50), nullable=False)  # "trade_execution", "market_creation", etc.
    usage_count = Column(Integer, default=0, nullable=False)
    billing_period_start = Column(DateTime, nullable=False)
    billing_period_end = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User")
    subscription = relationship("UserSubscription")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "subscription_id": self.subscription_id,
            "feature": self.feature,
            "usage_count": self.usage_count,
            "billing_period_start": self.billing_period_start.isoformat() if self.billing_period_start else None,
            "billing_period_end": self.billing_period_end.isoformat() if self.billing_period_end else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PlaidUsageTracking(Base):
    """Track Plaid API usage for billing/credits (no secrets stored)."""

    __tablename__ = "plaid_usage_tracking"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)

    # Example: "transactions/get", "investments/holdings/get"
    api_endpoint = Column(String(100), nullable=False, index=True)

    # Plaid request correlation header (X-Request-ID) if captured upstream
    request_id = Column(String(255), nullable=True, index=True)

    # Internal cost accounting (in USD). Exact rates are configurable elsewhere.
    cost_usd = Column(Numeric(10, 4), nullable=False, default=0)

    # Optional linkage fields (not secrets)
    item_id = Column(String(255), nullable=True)
    account_id = Column(String(255), nullable=True)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    # NOTE: attribute name "metadata" is reserved by SQLAlchemy Declarative API
    usage_metadata = Column(JSONB(), nullable=True, name="usage_metadata")

    user = relationship("User")
    organization = relationship("Organization")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "organization_id": self.organization_id,
            "api_endpoint": self.api_endpoint,
            "request_id": self.request_id,
            "cost_usd": float(self.cost_usd) if self.cost_usd is not None else None,
            "item_id": self.item_id,
            "account_id": self.account_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "usage_metadata": self.usage_metadata,
        }


class PlaidPricingConfig(Base):
    """
    Configurable pricing for Plaid API calls.

    Resolution rules (enforced in service layer):
    - If organization_id is set: org-level override
    - Else: instance-level default (instance_id may be null for single-instance deployments)
    """

    __tablename__ = "plaid_pricing_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Example: "transactions/get", "investments/holdings/get"
    api_endpoint = Column(String(100), nullable=False, index=True)
    cost_per_call_usd = Column(Numeric(10, 4), nullable=False, default=0)
    cost_per_call_credits = Column(Numeric(10, 4), nullable=False, default=0)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization")

    def to_dict(self):
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "organization_id": self.organization_id,
            "api_endpoint": self.api_endpoint,
            "cost_per_call_usd": float(self.cost_per_call_usd) if self.cost_per_call_usd is not None else None,
            "cost_per_call_credits": float(self.cost_per_call_credits) if self.cost_per_call_credits is not None else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ServicePricingConfig(Base):
    """
    Configurable pricing for any external-service-backed operation (LLMs, Plaid, etc.).

    Resolution rules (enforced in service layer):
    - If organization_id is set: org-level override
    - Else: instance-level default (instance_id may be null for single-instance deployments)
    """

    __tablename__ = "service_pricing_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, nullable=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)

    # Example: "plaid.transactions.get", "llm.vllm.chat", "llm.huggingface.inference"
    service_name = Column(String(120), nullable=False, index=True)
    cost_per_call_usd = Column(Numeric(10, 4), nullable=False, default=0)
    cost_per_call_credits = Column(Numeric(10, 4), nullable=False, default=0)

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    organization = relationship("Organization")

    def to_dict(self):
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "organization_id": self.organization_id,
            "service_name": self.service_name,
            "cost_per_call_usd": float(self.cost_per_call_usd) if self.cost_per_call_usd is not None else None,
            "cost_per_call_credits": float(self.cost_per_call_credits) if self.cost_per_call_credits is not None else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CommissionConfig(Base):
    """Configurable commission and fee structure."""
    
    __tablename__ = "commission_configs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # "trade_execution", "market_creation", "deal_processing"
    category = Column(String(50), nullable=False)  # "trading", "market", "deal", "payment"
    fee_type = Column(String(20), nullable=False)  # "percentage", "fixed", "tiered"
    fee_value = Column(Numeric(10, 4), nullable=False)  # Percentage (0.01 = 1%) or fixed amount
    min_fee = Column(Numeric(19, 4), nullable=True)
    max_fee = Column(Numeric(19, 4), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    applies_to = Column(JSONB, nullable=True)  # Conditions: deal_type, workflow_type, etc.
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "fee_type": self.fee_type,
            "fee_value": float(self.fee_value) if self.fee_value else None,
            "min_fee": float(self.min_fee) if self.min_fee else None,
            "max_fee": float(self.max_fee) if self.max_fee else None,
            "currency": self.currency,
            "applies_to": self.applies_to,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CommissionCharge(Base):
    """Record of commission charges applied."""
    
    __tablename__ = "commission_charges"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    config_id = Column(Integer, ForeignKey("commission_configs.id"), nullable=False)
    transaction_id = Column(String(255), nullable=False, index=True)  # Deal ID, Trade ID, etc.
    transaction_type = Column(String(50), nullable=False)  # "trade", "deal", "market", etc.
    amount = Column(Numeric(19, 4), nullable=False)
    currency = Column(String(3), nullable=False)
    payer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    calculation_details = Column(JSONB, nullable=True)  # How fee was calculated
    payment_event_id = Column(Integer, ForeignKey("payment_events.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    config = relationship("CommissionConfig")
    payer = relationship("User")
    payment_event = relationship("PaymentEvent", foreign_keys=[payment_event_id])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "config_id": self.config_id,
            "transaction_id": self.transaction_id,
            "transaction_type": self.transaction_type,
            "amount": float(self.amount) if self.amount else None,
            "currency": self.currency,
            "payer_id": self.payer_id,
            "calculation_details": self.calculation_details,
            "payment_event_id": self.payment_event_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ============================================================================
# Trading Order Models
# ============================================================================

class OrderSide(str, enum.Enum):
    """Order side (buy or sell)."""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, enum.Enum):
    """Order type."""
    MARKET = "market"  # Execute immediately at market price
    LIMIT = "limit"  # Execute at specified price or better
    STOP = "stop"  # Stop loss order
    STOP_LIMIT = "stop_limit"  # Stop loss with limit price


class OrderStatus(str, enum.Enum):
    """Order status."""
    PENDING = "pending"  # Order created, awaiting validation
    SUBMITTED = "submitted"  # Order submitted to trading API
    PARTIALLY_FILLED = "partially_filled"  # Order partially executed
    FILLED = "filled"  # Order fully executed
    CANCELLED = "cancelled"  # Order cancelled by user
    REJECTED = "rejected"  # Order rejected by trading API
    EXPIRED = "expired"  # Order expired (time-based)


class Order(Base):
    """Order model for trading orders (stocks, securities, etc.)."""
    
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(255), unique=True, nullable=False, index=True)  # External order ID from trading API
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Order details
    symbol = Column(String(50), nullable=False, index=True)  # Stock symbol (e.g., "AAPL")
    side = Column(String(10), nullable=False, index=True)  # "buy" or "sell"
    order_type = Column(String(20), nullable=False, index=True)  # "market", "limit", "stop", "stop_limit"
    quantity = Column(Numeric(20, 8), nullable=False)  # Number of shares/units
    price = Column(Numeric(20, 8), nullable=True)  # Limit price (required for limit orders)
    stop_price = Column(Numeric(20, 8), nullable=True)  # Stop price (required for stop orders)
    
    # Execution details
    status = Column(String(20), default=OrderStatus.PENDING.value, nullable=False, index=True)
    filled_quantity = Column(Numeric(20, 8), default=0, nullable=False)  # Quantity filled so far
    average_fill_price = Column(Numeric(20, 8), nullable=True)  # Average execution price
    commission = Column(Numeric(20, 2), nullable=True)  # Commission charged
    commission_currency = Column(String(3), default="USD", nullable=False)
    
    # Trading API integration
    trading_api = Column(String(50), nullable=True, index=True)  # "alpaca", "polygon", etc.
    trading_api_order_id = Column(String(255), nullable=True, index=True)  # Order ID from trading API
    trading_api_response = Column(JSONB, nullable=True)  # Full response from trading API
    
    # Time-based fields
    time_in_force = Column(String(20), default="day", nullable=False)  # "day", "gtc", "ioc", "fok"
    expires_at = Column(DateTime, nullable=True)  # Expiration time for GTC orders
    
    # Audit and metadata
    submitted_at = Column(DateTime, nullable=True)  # When order was submitted to trading API
    filled_at = Column(DateTime, nullable=True)  # When order was fully filled
    cancelled_at = Column(DateTime, nullable=True)  # When order was cancelled
    rejection_reason = Column(Text, nullable=True)  # Reason for rejection
    
    # Additional metadata
    order_metadata = Column(JSONB, nullable=True)  # Additional order metadata

    # Timestamps (match alembic migration 8c92e21f2aa9)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        """Convert model to dictionary for OrderResponse (trading_routes)."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": float(self.quantity) if self.quantity is not None else 0.0,
            "price": float(self.price) if self.price is not None else None,
            "stop_price": float(self.stop_price) if self.stop_price is not None else None,
            "status": self.status,
            "filled_quantity": float(self.filled_quantity) if self.filled_quantity is not None else 0.0,
            "average_fill_price": float(self.average_fill_price) if self.average_fill_price is not None else None,
            "commission": float(self.commission) if self.commission is not None else None,
            "commission_currency": self.commission_currency or "USD",
            "trading_api": self.trading_api,
            "trading_api_order_id": self.trading_api_order_id,
            "time_in_force": self.time_in_force or "day",
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else "",
            "updated_at": self.updated_at.isoformat() if self.updated_at else "",
        }


class ManualHolding(Base):
    """Manually entered asset holding (Phase 0: Manual Asset Entry)."""

    __tablename__ = "manual_holdings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    quantity = Column(Numeric(20, 8), nullable=False)
    average_cost = Column(Numeric(20, 8), nullable=True)
    currency = Column(String(3), default="USD", nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="manual_holdings")


class ManualAsset(Base):
    """Manually entered asset with optional amortization (Phase 3: fixed income, real estate, etc.)."""

    __tablename__ = "manual_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    asset_type = Column(String(50), nullable=False, index=True)  # fixed_income, real_estate, physical, interest_account
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    purchase_price = Column(Numeric(19, 4), nullable=False)
    current_value = Column(Numeric(19, 4), nullable=True)
    quantity = Column(Numeric(19, 4), nullable=True)
    unit = Column(String(20), nullable=True)  # oz, kg, shares
    # Fixed income / amortization
    maturity_date = Column(Date, nullable=True, index=True)
    interest_rate = Column(Numeric(10, 4), nullable=True)
    payment_frequency = Column(String(20), nullable=True)  # monthly, quarterly, annually, at_maturity
    amortization_schedule = Column(JSONB, nullable=True)  # [{date, principal, interest, remaining}]
    purchase_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="manual_assets")
    alerts = relationship("AssetAlert", back_populates="asset", cascade="all, delete-orphan")


class AssetAlert(Base):
    """Alerts for manual assets: maturity, price threshold, amortization payment (Phase 3)."""

    __tablename__ = "asset_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("manual_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, index=True)  # maturity, price_threshold, amortization_payment
    trigger_date = Column(Date, nullable=True, index=True)
    trigger_price = Column(Numeric(19, 4), nullable=True)
    message = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notified = Column(Boolean, default=False, nullable=False)
    notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    asset = relationship("ManualAsset", back_populates="alerts")


class Watchlist(Base):
    """User watchlist of symbols (Trading Phase 4)."""

    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    symbols = Column(JSONB, nullable=False)  # ["AAPL","MSFT",...]; migration sets server_default '[]'::jsonb
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", backref="watchlists")


class PriceAlert(Base):
    """Price alert for monitoring symbol price movements."""
    
    __tablename__ = "price_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    
    # Alert conditions
    alert_type = Column(String(20), nullable=False, index=True)  # "above", "below", "change_percent"
    target_price = Column(Numeric(20, 8), nullable=True)  # For above/below alerts
    change_percent = Column(Numeric(5, 2), nullable=True)  # For change_percent alerts (e.g., 5.0 for 5%)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    triggered_at = Column(DateTime, nullable=True, index=True)
    triggered_price = Column(Numeric(20, 8), nullable=True)
    
    # Notification settings
    notify_email = Column(Boolean, default=False, nullable=False)
    notify_in_app = Column(Boolean, default=True, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="price_alerts")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "symbol": self.symbol,
            "alert_type": self.alert_type,
            "target_price": float(self.target_price) if self.target_price else None,
            "change_percent": float(self.change_percent) if self.change_percent else None,
            "is_active": self.is_active,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "triggered_price": float(self.triggered_price) if self.triggered_price else None,
            "notify_email": self.notify_email,
            "notify_in_app": self.notify_in_app,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Document Review Models
# ============================================================================

class CommentType(str, enum.Enum):
    """Types of review comments."""
    GENERAL = "general"  # General comment
    ANNOTATION = "annotation"  # Field-specific annotation
    CHANGE_REQUEST = "change_request"  # Request for specific change


class ReviewComment(Base):
    """Review comment model for document review workflows."""
    
    __tablename__ = "review_comments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(Integer, ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    comment_text = Column(Text, nullable=False)
    comment_type = Column(String(20), default=CommentType.GENERAL.value, nullable=False, index=True)
    
    # For field-specific annotations
    target_field = Column(String(255), nullable=True, index=True)  # e.g., "parties[0].name", "facilities[1].commitment_amount"
    target_range = Column(JSONB, nullable=True)  # For text selection ranges: {"start": 0, "end": 100}
    
    # Comment resolution
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Threading support (for replies)
    parent_comment_id = Column(Integer, ForeignKey("review_comments.id", ondelete="CASCADE"), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    document = relationship("Document", backref="review_comments")
    version = relationship("DocumentVersion", backref="review_comments")
    user = relationship("User", foreign_keys=[user_id], backref="review_comments")
    resolver = relationship("User", foreign_keys=[resolved_by])
    parent_comment = relationship("ReviewComment", remote_side=[id], backref="replies")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "version_id": self.version_id,
            "user_id": self.user_id,
            "comment_text": self.comment_text,
            "comment_type": self.comment_type,
            "target_field": self.target_field,
            "target_range": self.target_range,
            "resolved": self.resolved,
            "resolved_by": self.resolved_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "parent_comment_id": self.parent_comment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ReviewAssignmentStatus(str, enum.Enum):
    """Status of a review assignment."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReviewAssignment(Base):
    """Review assignment model for assigning reviewers to documents."""
    
    __tablename__ = "review_assignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id", ondelete="CASCADE"), nullable=True, index=True)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assigned_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_date = Column(DateTime, nullable=True, index=True)
    
    status = Column(String(20), default=ReviewAssignmentStatus.PENDING.value, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)  # Reviewer's notes/feedback
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    # Reserved: uncomment when needed; must set foreign_keys= to disambiguate (e.g. [reviewer_id] or [assigned_by]);
    # do not use backref="orders" (that belongs to Order). Example: user = relationship("User", foreign_keys=[reviewer_id])
    # user = relationship("User", backref="orders")
    document = relationship("Document", backref="review_assignments")
    workflow = relationship("Workflow", backref="review_assignments")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="assigned_reviews")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "workflow_id": self.workflow_id,
            "reviewer_id": self.reviewer_id,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at.isoformat() if self.assigned_at else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Phase 3: Structured Products Models
# ============================================================================

class StructuredProductTemplate(Base):
    """Template for generic structured products (ELNs, barrier options, etc.)."""
    __tablename__ = "structured_product_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    product_type = Column(String(100), nullable=False)  # equity_linked_note, barrier_option, etc.
    underlying_symbol = Column(String(50), nullable=False)
    payoff_formula = Column(JSONB, nullable=False)  # Formula definition
    maturity_days = Column(Integer, nullable=False)
    principal = Column(Numeric(20, 2), nullable=False)
    fees = Column(Numeric(20, 2), default=0)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = relationship("User", back_populates="product_templates", foreign_keys=[created_by])
    instances = relationship("StructuredProductInstance", back_populates="template")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "product_type": self.product_type,
            "underlying_symbol": self.underlying_symbol,
            "payoff_formula": self.payoff_formula,
            "maturity_days": self.maturity_days,
            "principal": float(self.principal),
            "fees": float(self.fees),
            "created_by": self.created_by,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StructuredProductInstance(Base):
    """Specific instance of an issued structured product."""
    __tablename__ = "structured_product_instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("structured_product_templates.id"), nullable=False)
    issuer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    total_notional = Column(Numeric(20, 2), nullable=False)
    issue_date = Column(Date, nullable=False)
    maturity_date = Column(Date, nullable=False)
    status = Column(String(50), default="active")  # active, matured, cancelled
    replication_trades = Column(JSONB, nullable=True)  # Alpaca order IDs or similar
    current_value = Column(Numeric(20, 2), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    template = relationship("StructuredProductTemplate", back_populates="instances")
    issuer = relationship("User", back_populates="issued_products", foreign_keys=[issuer_user_id])
    subscriptions = relationship("ProductSubscription", back_populates="instance")

    def to_dict(self):
        return {
            "id": self.id,
            "template_id": self.template_id,
            "issuer_user_id": self.issuer_user_id,
            "total_notional": float(self.total_notional),
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "maturity_date": self.maturity_date.isoformat() if self.maturity_date else None,
            "status": self.status,
            "current_value": float(self.current_value) if self.current_value else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ProductSubscription(Base):
    """Investor subscription to a structured product instance."""
    __tablename__ = "product_subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(Integer, ForeignKey("structured_product_instances.id"), nullable=False)
    investor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_amount = Column(Numeric(20, 2), nullable=False)
    subscription_date = Column(Date, nullable=False)
    status = Column(String(50), default="pending")  # pending, active, matured, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instance = relationship("StructuredProductInstance", back_populates="subscriptions")
    investor = relationship("User", back_populates="product_subscriptions", foreign_keys=[investor_user_id])

    def to_dict(self):
        return {
            "id": self.id,
            "instance_id": self.instance_id,
            "investor_user_id": self.investor_user_id,
            "subscription_amount": float(self.subscription_amount),
            "subscription_date": self.subscription_date.isoformat() if self.subscription_date else None,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Phase 7: GDPR Compliance Models
# ============================================================================

class ConsentRecord(Base):
    """GDPR consent record for data processing."""
    __tablename__ = "consent_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Consent details
    consent_type = Column(String(50), nullable=False, index=True)  # marketing, analytics, essential, third_party
    consent_purpose = Column(String(255), nullable=False)  # Description of purpose
    legal_basis = Column(String(50), nullable=False)  # consent, contract, legal_obligation, legitimate_interests
    
    # Consent status
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_withdrawn = Column(Boolean, default=False, nullable=False)
    consent_withdrawn_at = Column(DateTime, nullable=True)
    
    # Consent metadata
    consent_method = Column(String(50), nullable=True)  # explicit, opt_in
    consent_source = Column(String(100), nullable=True)  # signup, settings
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    # Timestamps
    consent_given_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="consent_records")
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "consent_type": self.consent_type,
            "consent_purpose": self.consent_purpose,
            "legal_basis": self.legal_basis,
            "consent_given": self.consent_given,
            "consent_withdrawn": self.consent_withdrawn,
            "consent_withdrawn_at": self.consent_withdrawn_at.isoformat() if self.consent_withdrawn_at else None,
            "consent_given_at": self.consent_given_at.isoformat() if self.consent_given_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class DataProcessingRequest(Base):
    """GDPR data processing requests (rectification, restriction, objection)."""
    __tablename__ = "data_processing_requests"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Request details
    request_type = Column(String(50), nullable=False, index=True)  # rectification, restriction, objection, portability
    request_status = Column(String(20), default="pending", nullable=False, index=True)  # pending, completed, rejected
    
    # Request data
    request_description = Column(Text, nullable=False)
    requested_changes = Column(JSONB, nullable=True)  # For rectification
    
    # Processing
    processed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    processed_at = Column(DateTime, nullable=True)
    processing_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="data_processing_requests")
    processor = relationship("User", foreign_keys=[processed_by])


class BreachRecord(Base):
    """Data breach record for GDPR Article 33 compliance."""
    __tablename__ = "breach_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Breach details
    breach_type = Column(String(50), nullable=False)
    breach_description = Column(Text, nullable=False)
    breach_discovered_at = Column(DateTime, nullable=False)
    breach_contained_at = Column(DateTime, nullable=True)
    
    # Affected data
    affected_users_count = Column(Integer, nullable=True)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Notification
    supervisory_authority_notified = Column(Boolean, default=False, nullable=False)
    users_notified = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
