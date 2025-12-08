"""FINOS Common Domain Model (CDM) implementation using Pydantic.

This module defines the data structures for representing Credit Agreements
in a standardized, machine-readable format that ensures interoperability
with other CDM-compliant financial systems.
"""

from decimal import Decimal
from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class Currency(str, Enum):
    """Supported currency codes."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"


class PeriodEnum(str, Enum):
    """Time period units for frequency calculations."""
    Day = "Day"
    Week = "Week"
    Month = "Month"
    Year = "Year"


class Money(BaseModel):
    """Represents a monetary amount with currency.
    
    Uses Decimal for precision to avoid floating-point errors
    in financial calculations.
    """
    amount: Decimal = Field(..., description="The numerical monetary amount")
    currency: Currency = Field(..., description="The currency code (USD, EUR, GBP, JPY)")


class Frequency(BaseModel):
    """Represents a payment or calculation frequency."""
    period: PeriodEnum = Field(..., description="The time period unit (Day, Week, Month, Year)")
    period_multiplier: int = Field(..., description="The number of periods (e.g., 3 for 'every 3 months')")
    
    @field_validator('period_multiplier')
    @classmethod
    def validate_multiplier(cls, v: int) -> int:
        """Ensure period multiplier is positive."""
        if v <= 0:
            raise ValueError("period_multiplier must be greater than 0")
        return v


class Party(BaseModel):
    """Represents a legal entity involved in the credit agreement."""
    id: str = Field(..., description="A unique identifier for the party in the document")
    name: str = Field(..., description="The legal name of the party")
    role: str = Field(..., description="The role of the party (e.g., 'Borrower', 'Lender', 'Administrative Agent')")


class FloatingRateOption(BaseModel):
    """Defines the floating rate index and spread for interest calculations."""
    benchmark: str = Field(..., description="The floating rate index used (e.g., 'SOFR', 'EURIBOR', 'Term SOFR')")
    spread_bps: float = Field(
        ...,
        description="The margin added to the benchmark in basis points. Example: 2.5% should be extracted as 250.0"
    )
    
    @field_validator('spread_bps')
    @classmethod
    def validate_spread(cls, v: float) -> float:
        """Ensure spread is a reasonable value (between -10000 and 10000 bps)."""
        if v < -10000 or v > 10000:
            raise ValueError("spread_bps must be between -10000 and 10000 basis points")
        return v


class InterestRatePayout(BaseModel):
    """Defines the interest rate structure and payment frequency."""
    rate_option: FloatingRateOption = Field(..., description="The floating rate option with benchmark and spread")
    payment_frequency: Frequency = Field(..., description="How often interest payments are made")


class LoanFacility(BaseModel):
    """Represents a single loan facility within a credit agreement."""
    facility_name: str = Field(..., description="The name of the facility (e.g., 'Term Loan B', 'Revolving Credit Facility')")
    commitment_amount: Money = Field(..., description="The total commitment amount for this facility")
    interest_terms: InterestRatePayout = Field(..., description="The interest rate structure for this facility")
    maturity_date: date = Field(..., description="The maturity date when the facility must be repaid (ISO 8601 format: YYYY-MM-DD)")


class ExtractionStatus(str, Enum):
    """Status of the extraction process."""
    SUCCESS = "success"
    PARTIAL = "partial_data_missing"
    FAILURE = "irrelevant_document"


class CreditAgreement(BaseModel):
    """Represents the key economic terms of a syndicated credit agreement.
    
    This is the root object that contains all parties, facilities, and
    governing terms extracted from a credit agreement document.
    """
    extraction_status: ExtractionStatus = Field(
        default=ExtractionStatus.SUCCESS,
        description="Status of extraction: success, partial_data_missing, or irrelevant_document"
    )
    agreement_date: Optional[date] = Field(
        None,
        description="The date the agreement was executed (ISO 8601 format: YYYY-MM-DD)"
    )
    parties: Optional[List[Party]] = Field(
        None,
        description="List of all parties involved in the agreement"
    )
    facilities: Optional[List[LoanFacility]] = Field(
        None,
        description="List of loan facilities defined in the agreement"
    )
    governing_law: Optional[str] = Field(
        None,
        description="The jurisdiction governing the agreement (e.g., 'State of New York', 'English Law')"
    )

    @model_validator(mode='after')
    def check_core_fields_completeness(self) -> 'CreditAgreement':
        """Check core fields and adjust extraction status if needed."""
        if self.extraction_status == ExtractionStatus.FAILURE:
            return self

        missing = []
        if self.agreement_date is None:
            missing.append("agreement_date")
        if not self.parties:
            missing.append("parties")
        if not self.facilities:
            missing.append("facilities")
        if not self.governing_law:
            missing.append("governing_law")

        if missing and self.extraction_status == ExtractionStatus.SUCCESS:
            object.__setattr__(self, 'extraction_status', ExtractionStatus.PARTIAL)

        return self
    
    @model_validator(mode='after')
    def validate_agreement_date(self) -> 'CreditAgreement':
        """Ensure agreement_date is not in the future."""
        if self.extraction_status == ExtractionStatus.FAILURE:
            return self
        if self.agreement_date is None:
            return self
        today = date.today()
        if self.agreement_date > today:
            raise ValueError(f"agreement_date ({self.agreement_date}) cannot be in the future (today: {today})")
        return self
    
    @model_validator(mode='after')
    def validate_facilities(self) -> 'CreditAgreement':
        """Ensure at least one facility exists for successful extractions."""
        if self.extraction_status != ExtractionStatus.SUCCESS:
            return self
        if not self.facilities:
            object.__setattr__(self, 'extraction_status', ExtractionStatus.PARTIAL)
        return self
    
    @model_validator(mode='after')
    def validate_parties(self) -> 'CreditAgreement':
        """Ensure at least one party exists for successful extractions."""
        if self.extraction_status != ExtractionStatus.SUCCESS:
            return self
        if not self.parties:
            object.__setattr__(self, 'extraction_status', ExtractionStatus.PARTIAL)
        return self

    @model_validator(mode='after')
    def validate_maturity_after_agreement(self) -> 'CreditAgreement':
        """Ensure each facility's maturity_date is after the agreement_date."""
        if self.extraction_status == ExtractionStatus.FAILURE:
            return self
        if not self.facilities or self.agreement_date is None:
            return self
        for facility in self.facilities:
            if facility.maturity_date <= self.agreement_date:
                raise ValueError(
                    f"maturity_date ({facility.maturity_date}) must be after "
                    f"agreement_date ({self.agreement_date}) for facility '{facility.facility_name}'"
                )
        return self

    @model_validator(mode='after')
    def validate_currency_consistency(self) -> 'CreditAgreement':
        """Ensure all facilities use the same currency for commitments."""
        if self.extraction_status == ExtractionStatus.FAILURE:
            return self
        if not self.facilities:
            return self

        first_currency = self.facilities[0].commitment_amount.currency
        for facility in self.facilities[1:]:
            if facility.commitment_amount.currency != first_currency:
                raise ValueError(
                    f"Currency mismatch: facility '{facility.facility_name}' uses "
                    f"{facility.commitment_amount.currency}, expected {first_currency}. "
                    "All facilities must use the same currency."
                )
        return self

    @model_validator(mode='after')
    def validate_party_reconciliation(self) -> 'CreditAgreement':
        """Check if at least one Borrower exists among parties."""
        if self.extraction_status == ExtractionStatus.FAILURE:
            return self
        if not self.parties:
            return self
        borrower_parties = [p for p in self.parties if "borrower" in p.role.lower()]
        if not borrower_parties and self.extraction_status == ExtractionStatus.SUCCESS:
            object.__setattr__(self, 'extraction_status', ExtractionStatus.PARTIAL)
        return self


class ExtractionResult(BaseModel):
    """Envelope for extraction responses with refusal support.

    This allows irrelevant documents to return FAILURE without requiring
    populated agreement fields.
    """

    status: ExtractionStatus = Field(
        default=ExtractionStatus.SUCCESS,
        description="Extraction status: success, partial_data_missing, or irrelevant_document"
    )
    agreement: Optional[CreditAgreement] = Field(
        None,
        description="The extracted credit agreement when status is success or partial_data_missing"
    )
    message: Optional[str] = Field(
        None,
        description="Optional message when status is failure/irrelevant_document"
    )

    @model_validator(mode='after')
    def validate_status_consistency(self) -> 'ExtractionResult':
        """Adjust status if agreement is missing or incomplete."""
        if self.status == ExtractionStatus.FAILURE:
            return self
        if self.agreement is None:
            object.__setattr__(self, 'status', ExtractionStatus.FAILURE)
            object.__setattr__(self, 'message', "Could not extract data from this document")
        elif self.agreement.extraction_status != ExtractionStatus.SUCCESS:
            object.__setattr__(self, 'status', self.agreement.extraction_status)
        return self

