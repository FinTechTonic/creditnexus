"""Pydantic models for signature request generation."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Signer(BaseModel):
    """Represents a document signer."""
    name: str = Field(..., description="Signer full name")
    email: str = Field(..., description="Signer email address")
    role: str = Field(..., description="Signer role (e.g., 'Borrower', 'Lender', 'Guarantor')")
    signing_order: int = Field(default=0, description="Order in which signer must sign (0 = parallel)")
    required: bool = Field(default=True, description="Whether signature is required")


class SignatureRequestGeneration(BaseModel):
    """AI-generated signature request configuration."""
    signers: List[Signer] = Field(default_factory=list)
    signing_workflow: str = Field(default="parallel", description="'parallel' or 'sequential'")
    expiration_days: int = Field(default=30, description="Days until signature request expires")
    reminder_enabled: bool = Field(default=True, description="Enable email reminders")
    reminder_days: List[int] = Field(default_factory=lambda: [7, 3, 1], description="Days before expiration to send reminders")
    message: Optional[str] = Field(None, description="Custom message for signers")
    metadata: Dict[str, Any] = Field(default_factory=dict)
