"""SQLAlchemy models for CreditNexus database."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric, Date, Float
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
    subscriptions = relationship("UserSubscription", back_populates="user")
    subscription_tier = Column(String(20), default=SubscriptionTier.FREE.value, nullable=False)

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
        return {
            "id": self.id,
            "document_id": self.document_id,
            "generated_document_id": self.generated_document_id,
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



    """Remote application profile for API access control."""



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
    asset_type = Column(String(50), nullable=False)  # 'deal', 'loan_asset'
    asset_id = Column(String(255), nullable=False)  # Composite identifier
    asset_value = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False)
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
            "asset_value": str(self.asset_value),
            "currency": self.currency,
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


class PermissionKeyType(str, enum.Enum):
    """Permission key types."""

    WALLET = "wallet"  # Ethereum wallet address
    APPLICATION = "application"  # Application API key
    WHITELIST = "whitelist"  # Whitelist entry
    ORGANIZATION = "organization"  # Organization-level key


class PermissionKey(Base):
    """Permission keys for unlocking shared files/deals."""

    __tablename__ = "permission_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Key identification
    key_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID
    key_type = Column(String(50), nullable=False, index=True)  # wallet, application, whitelist, organization

    # Key data (encrypted)
    encrypted_key = Column(EncryptedJSON(), nullable=False)  # Encrypted key data
    key_hash = Column(String(255), nullable=False, index=True)  # SHA-256 hash for lookup

    # Permissions
    permissions = Column(JSONB, nullable=False)  # ["view", "download", "sign", "edit"]

    # Scope
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)
    organization_id = Column(Integer, nullable=True, index=True)  # No FK - organizations table doesn't exist yet
    workflow_id = Column(String(255), nullable=True, index=True)

    # Key metadata
    wallet_address = Column(String(255), nullable=True, index=True)  # For wallet keys
    application_key_id = Column(String(255), nullable=True, index=True)  # For application keys
    whitelist_id = Column(String(255), nullable=True, index=True)  # For whitelist keys

    # Expiration
    expires_at = Column(DateTime, nullable=True, index=True)
    download_ttl = Column(DateTime, nullable=True, index=True)  # Separate TTL for downloads

    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Creator
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    deal = relationship("Deal", backref="permission_keys")
    document = relationship("Document", backref="permission_keys")
    # organization relationship removed - organizations table doesn't exist yet
    creator = relationship("User", foreign_keys=[created_by])

    def to_dict(self):
        """Convert to dictionary (excludes encrypted_key)."""
        return {
            "key_id": self.key_id,
            "key_type": self.key_type,
            "permissions": self.permissions,
            "deal_id": self.deal_id,
            "document_id": self.document_id,
            "organization_id": self.organization_id,
            "workflow_id": self.workflow_id,
            "wallet_address": self.wallet_address,
            "application_key_id": self.application_key_id,
            "whitelist_id": self.whitelist_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "download_ttl": self.download_ttl.isoformat() if self.download_ttl else None,
            "usage_count": self.usage_count,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SharingEvent(Base):
    """Blockchain-notarized sharing events."""

    __tablename__ = "sharing_events"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Event identification
    event_id = Column(String(255), unique=True, nullable=False, index=True)  # UUID
    event_type = Column(String(50), nullable=False, index=True)  # send, receive

    # Sharing details
    sharing_method = Column(String(50), nullable=False)  # nexus_file, link, p2p
    workflow_id = Column(String(255), nullable=True, index=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=True, index=True)

    # Participants
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    receiver_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    receiver_email = Column(String(255), nullable=True, index=True)
    receiver_wallet_address = Column(String(255), nullable=True, index=True)

    # File information
    file_hash = Column(String(255), nullable=False, index=True)  # SHA-256 of .nexus file or link payload
    file_size = Column(Integer, nullable=True)
    files_included = Column(Integer, default=0, nullable=False)

    # Blockchain notarization
    blockchain_tx_hash = Column(String(255), nullable=True, index=True)
    blockchain_block_number = Column(Integer, nullable=True)
    notarized_at = Column(DateTime, nullable=True)

    # CDM event
    cdm_event = Column(JSONB, nullable=True)

    # Event metadata (renamed from 'metadata' to avoid SQLAlchemy reserved name)
    event_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    deal = relationship("Deal", backref="sharing_events")
    document = relationship("Document", backref="sharing_events")
    sender = relationship("User", foreign_keys=[sender_user_id])
    receiver = relationship("User", foreign_keys=[receiver_user_id])

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "sharing_method": self.sharing_method,
            "workflow_id": self.workflow_id,
            "deal_id": self.deal_id,
            "document_id": self.document_id,
            "sender_user_id": self.sender_user_id,
            "receiver_user_id": self.receiver_user_id,
            "receiver_email": self.receiver_email,
            "receiver_wallet_address": self.receiver_wallet_address,
            "file_hash": self.file_hash,
            "file_size": self.file_size,
            "files_included": self.files_included,
            "blockchain_tx_hash": self.blockchain_tx_hash,
            "blockchain_block_number": self.blockchain_block_number,
            "notarized_at": self.notarized_at.isoformat() if self.notarized_at else None,
            "cdm_event": self.cdm_event,
            "event_metadata": self.event_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

