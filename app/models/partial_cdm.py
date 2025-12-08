"""Partial CDM models for Map-Reduce extraction strategy.

When processing long documents, we extract partial data from each section,
then merge them into a complete CreditAgreement. This module defines
the partial extraction models that allow for incomplete data.
"""

from decimal import Decimal
from datetime import date
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.cdm import (
    Currency, Money, Frequency, PeriodEnum,
    Party, FloatingRateOption, InterestRatePayout, LoanFacility
)


class PartialCreditAgreement(BaseModel):
    """Partial credit agreement data extracted from a document section.
    
    All fields are optional to allow for sections that don't contain
    all information. The reducer will merge multiple partials into
    a complete CreditAgreement.
    """
    agreement_date: Optional[date] = Field(
        None,
        description="The date the agreement was executed (ISO 8601 format: YYYY-MM-DD)"
    )
    parties: Optional[List[Party]] = Field(
        None,
        description="List of parties found in this section (may be incomplete)"
    )
    facilities: Optional[List[LoanFacility]] = Field(
        None,
        description="List of loan facilities found in this section (may be incomplete)"
    )
    governing_law: Optional[str] = Field(
        None,
        description="The jurisdiction governing the agreement"
    )
    
    # Metadata for merging
    source_section: Optional[str] = Field(
        None,
        description="The document section this partial was extracted from (e.g., 'Article I')"
    )

