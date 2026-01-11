"""SQLAlchemy models for CreditNexus database."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import relationship
import enum

from app.db import Base


class UserRole(str, enum.Enum):
    """User roles for access control."""
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
    APPROVE = "approve"
    REJECT = "reject"
    PUBLISH = "publish"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    BROADCAST = "broadcast"


class TemplateCategory(str, enum.Enum):
    """LMA template categories."""
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


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    replit_user_id = Column(String(255), unique=True, nullable=True, index=True)
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    password_hash = Column(String(255), nullable=True)
    
    display_name = Column(String(255), nullable=False)
    
    profile_image = Column(String(500), nullable=True)
    
    role = Column(String(20), default=UserRole.ANALYST.value, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    is_email_verified = Column(Boolean, default=False, nullable=False)
    
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    
    locked_until = Column(DateTime, nullable=True)
    
    password_changed_at = Column(DateTime, nullable=True)
    
    last_login = Column(DateTime, nullable=True)
    
    wallet_address = Column(String(255), nullable=True, unique=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    documents = relationship("Document", back_populates="uploaded_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    applications = relationship("Application", back_populates="user")
    inquiries = relationship("Inquiry", back_populates="user", foreign_keys="Inquiry.user_id")
    organized_meetings = relationship("Meeting", back_populates="organizer", foreign_keys="Meeting.organizer_id")
    
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Document(Base):
    """Document model for storing credit agreement documents."""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    title = Column(String(500), nullable=False)
    
    borrower_name = Column(String(255), nullable=True, index=True)
    
    borrower_lei = Column(String(20), nullable=True, index=True)
    
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
    template_id = Column(Integer, ForeignKey("lma_templates.id", ondelete="SET NULL"), nullable=True, index=True)
    source_cdm_data = Column(JSONB, nullable=True)  # CDM data used for generation
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    uploaded_by_user = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number.desc()")
    workflow = relationship("Workflow", back_populates="document", uselist=False)
    lma_template = relationship("LMATemplate", foreign_keys=[template_id])
    
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


class DocumentVersion(Base):
    """Version tracking for document extractions."""
    
    __tablename__ = "document_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    version_number = Column(Integer, nullable=False, default=1)
    
    extracted_data = Column(JSONB, nullable=False)
    
    original_text = Column(Text, nullable=True)
    
    source_filename = Column(String(255), nullable=True)
    
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
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, unique=True, index=True)
    
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


class AuditLog(Base):
    """Audit trail for all user actions."""
    
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    action = Column(String(50), nullable=False, index=True)
    
    target_type = Column(String(50), nullable=False)
    
    target_id = Column(Integer, nullable=True)
    
    action_metadata = Column(JSONB, nullable=True)
    
    ip_address = Column(String(50), nullable=True)
    
    user_agent = Column(String(500), nullable=True)
    
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
    
    status = Column(
        String(20),
        default=ExtractionStatus.PENDING.value,
        nullable=False,
        index=True
    )
    
    agreement_data = Column(JSONB, nullable=False)
    
    original_text = Column(Text, nullable=True)
    
    source_filename = Column(String(255), nullable=True)
    
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
    trace = Column(JSONB, nullable=True)  # Full evaluation trace
    matched_rules = Column(ARRAY(String), nullable=True)  # Array of matched rule names
    additional_metadata = Column(JSONB, name='metadata', nullable=True)  # Additional context
    
    # CDM Events (for full CDM compliance)
    cdm_events = Column(JSONB, nullable=True)  # Full CDM PolicyEvaluation events
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Foreign keys to CreditNexus entities
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    loan_asset_id = Column(Integer, ForeignKey("loan_assets.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Relationships
    document = relationship("Document", backref="policy_decisions")
    # Note: LoanAsset is a SQLModel in app.models.loan_asset, not in app.db.models
    # Relationship will work if loan_assets table exists
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
            "user_id": self.user_id,
        }


class PaymentEvent(Base):
    """Model for storing x402 payment events with CDM compliance.
    
    Stores payment processing results with full CDM event support for
    machine-readable and machine-executable payment tracking.
    """
    
    __tablename__ = "payment_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Payment identification
    payment_id = Column(String(255), nullable=False, unique=True, index=True)
    payment_method = Column(String(50), nullable=False)  # x402, wire, ach, swift
    payment_type = Column(String(50), nullable=False)  # loan_disbursement, trade_settlement, etc.
    
    # Party information
    payer_id = Column(String(255), nullable=False)
    payer_name = Column(String(255), nullable=False)
    receiver_id = Column(String(255), nullable=False)
    receiver_name = Column(String(255), nullable=False)
    
    # Payment amount
    amount = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    
    # Payment status (CDM state machine)
    status = Column(String(20), nullable=False, index=True)  # pending, verified, settled, failed, cancelled
    
    # x402-specific fields (JSONB for flexibility)
    x402_payment_payload = Column(JSONB, nullable=True)
    x402_verification = Column(JSONB, nullable=True)
    x402_settlement = Column(JSONB, nullable=True)
    transaction_hash = Column(String(255), nullable=True)
    
    # CDM references
    related_trade_id = Column(String(255), nullable=True, index=True)
    related_loan_id = Column(String(255), nullable=True, index=True)
    related_facility_id = Column(String(255), nullable=True)
    
    # Full CDM event (JSONB for complete CDM compliance)
    cdm_event = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    settled_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        """Convert model to dictionary for API serialization."""
        return {
            "id": self.id,
            "payment_id": self.payment_id,
            "payment_method": self.payment_method,
            "payment_type": self.payment_type,
            "payer_id": self.payer_id,
            "payer_name": self.payer_name,
            "receiver_id": self.receiver_id,
            "receiver_name": self.receiver_name,
            "amount": float(self.amount) if self.amount else None,
            "currency": self.currency,
            "status": self.status,
            "x402_payment_payload": self.x402_payment_payload,
            "x402_verification": self.x402_verification,
            "x402_settlement": self.x402_settlement,
            "transaction_hash": self.transaction_hash,
            "related_trade_id": self.related_trade_id,
            "related_loan_id": self.related_loan_id,
            "related_facility_id": self.related_facility_id,
            "cdm_event": self.cdm_event,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "settled_at": self.settled_at.isoformat() if self.settled_at else None,
        }


class PaymentSchedule(Base):
    """Model for storing scheduled payment information.
    
    Tracks periodic payments (interest, principal) that are scheduled
    for future processing via x402 payment service.
    """
    
    __tablename__ = "payment_schedules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Loan asset reference
    loan_asset_id = Column(Integer, nullable=False, index=True)
    
    # Payment details
    amount = Column(Numeric(20, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    payment_type = Column(String(50), nullable=False)  # interest, principal, penalty
    
    # Schedule information
    scheduled_date = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)  # pending, processed, failed, cancelled
    
    # Payment frequency (for recurring payments)
    payment_frequency_period = Column(String(20), nullable=True)  # Day, Week, Month, Year
    payment_frequency_multiplier = Column(Integer, nullable=True)  # e.g., 3 for "every 3 months"
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    # Metadata
    additional_metadata = Column(JSONB, name='metadata', nullable=True)  # Additional schedule information
    
    def to_dict(self):
        """Convert model to dictionary for API serialization."""
        return {
            "id": self.id,
            "loan_asset_id": self.loan_asset_id,
            "amount": float(self.amount) if self.amount else None,
            "currency": self.currency,
            "payment_type": self.payment_type,
            "scheduled_date": self.scheduled_date.isoformat() if self.scheduled_date else None,
            "status": self.status,
            "payment_frequency_period": self.payment_frequency_period,
            "payment_frequency_multiplier": self.payment_frequency_multiplier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "metadata": self.additional_metadata,
        }


class LMATemplate(Base):
    """LMA template metadata for document generation."""
    
    __tablename__ = "lma_templates"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=True, index=True)
    governing_law = Column(String(50), nullable=True)
    version = Column(String(20), nullable=False)
    file_path = Column(Text, nullable=False)
    additional_metadata = Column(JSONB, name='metadata', nullable=True)
    required_fields = Column(JSONB, nullable=True)
    optional_fields = Column(JSONB, nullable=True)
    ai_generated_sections = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    generated_documents = relationship("GeneratedDocument", back_populates="template", cascade="all, delete-orphan")
    field_mappings = relationship("TemplateFieldMapping", back_populates="template", cascade="all, delete-orphan")
    
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


class GeneratedDocument(Base):
    """Generated LMA documents from templates."""
    
    __tablename__ = "generated_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("lma_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    source_document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    cdm_data = Column(JSONB, nullable=False)
    generated_content = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    status = Column(String(50), server_default="draft", nullable=False, index=True)
    generation_summary = Column(JSONB, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("LMATemplate", back_populates="generated_documents")
    source_document = relationship("Document", foreign_keys=[source_document_id])
    creator = relationship("User", foreign_keys=[created_by])
    
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TemplateFieldMapping(Base):
    """Field mappings from CDM to template placeholders."""
    
    __tablename__ = "template_field_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey("lma_templates.id", ondelete="CASCADE"), nullable=False, index=True)
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
    
    template_id = Column(Integer, ForeignKey("lma_templates.id", ondelete="CASCADE"), nullable=False, index=True)
    
    field_name = Column(String(100), nullable=False, index=True)  # e.g., "REPRESENTATIONS_AND_WARRANTIES"
    
    clause_content = Column(Text, nullable=False)  # The generated clause text
    
    context_hash = Column(String(64), nullable=True, index=True)  # Hash of CDM context for cache key
    
    context_summary = Column(JSONB, nullable=True)  # Summary of CDM context used (for display)
    
    usage_count = Column(Integer, default=0, nullable=False)  # How many times this clause has been used
    
    last_used_at = Column(DateTime, nullable=True, index=True)
    
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    template = relationship("LMATemplate", foreign_keys=[template_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    # Unique constraint: one clause per template+field_name+context_hash combination
    __table_args__ = (
        {'sqlite_autoincrement': True},
    )
    
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


class Application(Base):
    """Application model for individual and business applications."""
    
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    application_type = Column(String(20), nullable=False, index=True)
    
    status = Column(String(20), default=ApplicationStatus.DRAFT.value, nullable=False, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    submitted_at = Column(DateTime, nullable=True)
    
    reviewed_at = Column(DateTime, nullable=True)
    
    approved_at = Column(DateTime, nullable=True)
    
    rejected_at = Column(DateTime, nullable=True)
    
    rejection_reason = Column(Text, nullable=True)
    
    application_data = Column(JSONB, nullable=True)  # Stores form data
    
    business_data = Column(JSONB, nullable=True)  # For business applications (debt selling, loan buying)
    
    individual_data = Column(JSONB, nullable=True)  # For individual applications
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="applications")
    inquiries = relationship("Inquiry", back_populates="application")
    meetings = relationship("Meeting", back_populates="application")
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "application_type": self.application_type,
            "status": self.status,
            "user_id": self.user_id,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "rejection_reason": self.rejection_reason,
            "application_data": self.application_data,
            "business_data": self.business_data,
            "individual_data": self.individual_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Inquiry(Base):
    """Inquiry model for customer support and inquiries."""
    
    __tablename__ = "inquiries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    inquiry_type = Column(String(50), nullable=False, index=True)
    
    status = Column(String(20), default=InquiryStatus.NEW.value, nullable=False, index=True)
    
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    email = Column(String(255), nullable=False)
    
    name = Column(String(255), nullable=False)
    
    subject = Column(String(500), nullable=False)
    
    message = Column(Text, nullable=False)
    
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    resolved_at = Column(DateTime, nullable=True)
    
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    response_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="inquiries")
    user = relationship("User", back_populates="inquiries", foreign_keys=[user_id])
    assigned_user = relationship("User", foreign_keys=[assigned_to])
    
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


class LoanDefaultSeverity(str, enum.Enum):
    """Severity levels for loan defaults."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LoanDefaultStatus(str, enum.Enum):
    """Status of loan defaults."""
    OPEN = "open"
    IN_RECOVERY = "in_recovery"
    RESOLVED = "resolved"
    WRITTEN_OFF = "written_off"


class RecoveryActionStatus(str, enum.Enum):
    """Status of recovery actions."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RESPONDED = "responded"


class RecoveryActionType(str, enum.Enum):
    """Types of recovery actions."""
    SMS_REMINDER = "sms_reminder"
    VOICE_CALL = "voice_call"
    EMAIL = "email"
    ESCALATION = "escalation"
    LEGAL_NOTICE = "legal_notice"


class CommunicationMethod(str, enum.Enum):
    """Communication methods for recovery actions."""
    SMS = "sms"
    VOICE = "voice"
    EMAIL = "email"


class LoanDefault(Base):
    """Model for tracking loan defaults and infractions."""
    
    __tablename__ = "loan_defaults"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(String, index=True)
    deal_id = Column(Integer, nullable=True)  # Will reference deals.id when Deal model is created
    default_type = Column(String)  # payment_default, covenant_breach, infraction
    default_date = Column(DateTime)
    default_reason = Column(String, nullable=True)
    amount_overdue = Column(Numeric(20, 2), nullable=True)
    days_past_due = Column(Integer)
    severity = Column(String, default=LoanDefaultSeverity.LOW.value)
    status = Column(String, default=LoanDefaultStatus.OPEN.value)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    cdm_events = Column(JSONB, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    recovery_actions = relationship("RecoveryAction", back_populates="loan_default", cascade="all, delete-orphan")
    resolved_by_user = relationship("User", foreign_keys=[resolved_by])
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            "id": self.id,
            "loan_id": self.loan_id,
            "deal_id": self.deal_id,
            "default_type": self.default_type,
            "default_date": self.default_date.isoformat() if self.default_date else None,
            "default_reason": self.default_reason,
            "amount_overdue": float(self.amount_overdue) if self.amount_overdue else None,
            "days_past_due": self.days_past_due,
            "severity": self.severity,
            "status": self.status,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "cdm_events": self.cdm_events,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RecoveryAction(Base):
    """Model for tracking recovery actions taken on loan defaults."""
    
    __tablename__ = "recovery_actions"
    
    id = Column(Integer, primary_key=True, index=True)
    loan_default_id = Column(Integer, ForeignKey("loan_defaults.id"))
    action_type = Column(String, default=RecoveryActionType.SMS_REMINDER.value)
    communication_method = Column(String, default=CommunicationMethod.SMS.value)
    recipient_phone = Column(String, nullable=True)
    recipient_email = Column(String, nullable=True)
    message_template = Column(String, nullable=True)  # template name or custom message
    message_content = Column(String)
    twilio_message_sid = Column(String, nullable=True)
    twilio_call_sid = Column(String, nullable=True)
    status = Column(String, default=RecoveryActionStatus.PENDING.value)
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    response_received_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    loan_default = relationship("LoanDefault", back_populates="recovery_actions")
    created_by_user = relationship("User", foreign_keys=[created_by])
    
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
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class BorrowerContact(Base):
    """Model for borrower contact information and preferences."""
    
    __tablename__ = "borrower_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    deal_id = Column(Integer, nullable=False)  # Will reference deals.id when Deal model is created
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    contact_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    preferred_contact_method = Column(String, default=CommunicationMethod.SMS.value)
    contact_preferences = Column(JSONB, nullable=True)  # timezone, preferred_hours, etc.
    is_primary = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
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
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Meeting(Base):
    """Meeting model for calendar and meeting management."""
    
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    title = Column(String(255), nullable=False)
    
    description = Column(Text, nullable=True)
    
    scheduled_at = Column(DateTime, nullable=False, index=True)
    
    duration_minutes = Column(Integer, default=30, nullable=False)
    
    meeting_type = Column(String(50), nullable=True)  # consultation, review, onboarding, etc.
    
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    
    organizer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    attendees = Column(JSONB, nullable=True)  # Array of {email, name, status}
    
    meeting_link = Column(String(500), nullable=True)  # Zoom/Teams link
    
    ics_file_path = Column(String(500), nullable=True)  # Path to generated .ics file
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="meetings")
    organizer = relationship("User", back_populates="organized_meetings", foreign_keys=[organizer_id])
    
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