"""FINOS CDM-compliant Sustainability Performance Target (SPT) models.

These Pydantic models define the structure for extracting and validating
sustainability-linked loan targets from legal documents.
"""

from enum import Enum
from typing import Optional, Literal
from pydantic import BaseModel, Field


class ComparisonDirection(str, Enum):
    """Direction of threshold comparison for SPT evaluation."""
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"
    EQUAL = "EQUAL"


class PenaltyType(str, Enum):
    """Types of financial penalties for SPT non-compliance."""
    MARGIN_RATCHET = "Margin_Ratchet"
    COMMITMENT_FEE_ADJUSTMENT = "Commitment_Fee_Adjustment"
    MANDATORY_PREPAYMENT = "Mandatory_Prepayment"
    EVENT_OF_DEFAULT = "Event_of_Default"


class TriggerMechanism(str, Enum):
    """How the penalty is triggered upon breach."""
    AUTOMATIC = "Automatic"
    LENDER_DISCRETION = "Lender_Discretion"
    BORROWER_NOTIFICATION = "Borrower_Notification"


class ResourceTarget(BaseModel):
    """
    Defines a measurable sustainability metric target.
    
    Example: "Forest cover must remain >= 80%"
    """
    metric: str = Field(
        ..., 
        description="The sustainability metric being tracked (e.g., 'Forest Cover', 'NDVI Index', 'CO2 Emissions')"
    )
    unit: str = Field(
        ..., 
        description="Unit of measurement (e.g., 'Percentage', 'Index', 'Tonnes')"
    )
    threshold: float = Field(
        ..., 
        description="The target threshold value"
    )
    direction: ComparisonDirection = Field(
        ..., 
        description="How to compare actual value against threshold"
    )


class FinancialConsequence(BaseModel):
    """
    Defines the financial penalty for SPT non-compliance.
    
    Example: "50 bps margin increase upon breach"
    """
    type: PenaltyType = Field(
        ..., 
        description="Type of financial penalty"
    )
    penalty_bps: float = Field(
        ..., 
        description="Penalty amount in basis points (e.g., 50 = 0.50%)"
    )
    trigger_mechanism: TriggerMechanism = Field(
        default=TriggerMechanism.AUTOMATIC,
        description="How the penalty is activated"
    )


class SustainabilityPerformanceTarget(BaseModel):
    """
    Complete FINOS CDM-compliant SPT structure.
    
    Combines the resource target (what to measure) with
    the financial consequence (what happens on breach).
    """
    resource_target: ResourceTarget = Field(
        ..., 
        description="The sustainability metric and threshold"
    )
    financial_consequence: FinancialConsequence = Field(
        ..., 
        description="The penalty for non-compliance"
    )
    verification_frequency: Optional[str] = Field(
        default="Annual",
        description="How often the target is verified (e.g., 'Annual', 'Quarterly', 'Monthly')"
    )
    grace_period_days: Optional[int] = Field(
        default=30,
        description="Days allowed to cure a breach before penalty applies"
    )


class CollateralAddress(BaseModel):
    """
    Extracted physical address of the collateral asset.
    Used for geocoding and satellite verification.
    """
    street: Optional[str] = Field(None, description="Street address")
    city: Optional[str] = Field(None, description="City name")
    state: Optional[str] = Field(None, description="State/Province")
    postal_code: Optional[str] = Field(None, description="ZIP/Postal code")
    country: str = Field(default="USA", description="Country")
    full_address: str = Field(..., description="Complete address string for geocoding")


class LegalExtractionResult(BaseModel):
    """
    Result of legal document analysis combining SPT and address extraction.
    """
    spt: Optional[SustainabilityPerformanceTarget] = Field(
        None, 
        description="Extracted sustainability performance target"
    )
    collateral_address: Optional[CollateralAddress] = Field(
        None, 
        description="Extracted collateral property address"
    )
    confidence_score: float = Field(
        default=0.0,
        description="Confidence in extraction accuracy (0.0 to 1.0)"
    )
    raw_covenant_text: Optional[str] = Field(
        None,
        description="The relevant covenant text that was analyzed"
    )
