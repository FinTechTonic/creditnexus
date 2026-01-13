"""Pydantic models for filing requirement evaluation."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from decimal import Decimal


class FilingRequirement(BaseModel):
    """Represents a filing requirement for an agreement."""
    authority: str = Field(..., description="Filing authority (e.g., 'SEC', 'Companies House')")
    jurisdiction: str = Field(..., description="Jurisdiction code (e.g., 'US', 'UK', 'FR', 'DE')")
    agreement_type: str = Field(..., description="Type of agreement (e.g., 'facility_agreement', 'disclosure')")
    filing_system: str = Field(..., description="Filing system ('companies_house_api', 'manual_ui')")
    deadline: datetime = Field(..., description="Filing deadline")
    required_fields: List[str] = Field(default_factory=list, description="Required fields for filing")
    api_available: bool = Field(default=False, description="Whether API filing is available")
    api_endpoint: Optional[str] = Field(None, description="API endpoint if available")
    penalty: Optional[str] = Field(None, description="Penalty for late filing")
    language_requirement: Optional[str] = Field(None, description="Required language for filing")
    form_type: Optional[str] = Field(None, description="Form type (e.g., '8-K', 'MR01')")
    priority: str = Field(default="medium", description="Priority: 'critical', 'high', 'medium', 'low'")


class FilingRequirementEvaluation(BaseModel):
    """Result of filing requirement evaluation."""
    required_filings: List[FilingRequirement] = Field(default_factory=list)
    compliance_status: str = Field(..., description="'compliant', 'non_compliant', 'pending'")
    missing_fields: List[str] = Field(default_factory=list)
    deadline_alerts: List[Dict[str, Any]] = Field(default_factory=list)
    trace_id: str = Field(..., description="Policy evaluation trace ID")
    metadata: Dict[str, Any] = Field(default_factory=dict)
