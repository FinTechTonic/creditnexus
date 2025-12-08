"""SQLAlchemy models for CreditNexus database."""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Enum
from sqlalchemy.dialects.postgresql import JSONB
import enum

from app.db import Base


class ExtractionStatus(str, enum.Enum):
    """Status of an extraction in the staging database."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class StagedExtraction(Base):
    """Model for storing staged credit agreement extractions."""
    
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
