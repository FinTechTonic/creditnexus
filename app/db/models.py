"""SQLAlchemy models for CreditNexus database."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Numeric, Date
from sqlalchemy.dialects.postgresql import JSONB
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


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    replit_user_id = Column(String(255), unique=True, nullable=True, index=True)
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    
    display_name = Column(String(255), nullable=False)
    
    profile_image = Column(String(500), nullable=True)
    
    role = Column(String(20), default=UserRole.ANALYST.value, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    
    last_login = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    documents = relationship("Document", back_populates="uploaded_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
    
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
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    uploaded_by_user = relationship("User", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.version_number.desc()")
    workflow = relationship("Workflow", back_populates="document", uselist=False)
    
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
