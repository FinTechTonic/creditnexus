"""Pydantic models for filing form data generation."""

from typing import List, Optional, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
from decimal import Decimal


class FilingFormField(BaseModel):
    """Represents a single form field."""
    field_name: str = Field(..., description="Form field name")
    field_value: Any = Field(..., description="Field value")
    field_type: str = Field(..., description="Field type: 'text', 'date', 'number', 'select', 'file'")
    required: bool = Field(default=True)
    validation_rules: Optional[Dict[str, Any]] = Field(None, description="Validation rules")
    help_text: Optional[str] = Field(None, description="Help text for user")


class FilingFormData(BaseModel):
    """Pre-filled form data for manual filing."""
    jurisdiction: str = Field(..., description="Jurisdiction code")
    authority: str = Field(..., description="Filing authority")
    form_type: str = Field(..., description="Form type")
    fields: List[FilingFormField] = Field(default_factory=list)
    document_references: List[str] = Field(default_factory=list, description="Document IDs to attach")
    submission_url: Optional[str] = Field(None, description="URL to submission portal")
    instructions: Optional[str] = Field(None, description="Submission instructions")
    language: str = Field(default="en", description="Form language")
