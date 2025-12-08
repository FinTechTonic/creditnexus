"""Tests for FINOS CDM Pydantic models."""

import pytest
from datetime import date
from decimal import Decimal
from app.models.cdm import (
    CreditAgreement,
    Party,
    LoanFacility,
    Money,
    Currency,
    FloatingRateOption,
    InterestRatePayout,
    Frequency,
    PeriodEnum,
    ExtractionResult
)


def test_money_model():
    """Test Money model creation and validation."""
    money = Money(amount=Decimal("500000000"), currency=Currency.USD)
    assert money.amount == Decimal("500000000")
    assert money.currency == Currency.USD


def test_party_model():
    """Test Party model creation."""
    party = Party(
        id="borrower_1",
        name="ACME INDUSTRIES INC.",
        role="Borrower"
    )
    assert party.name == "ACME INDUSTRIES INC."
    assert party.role == "Borrower"


def test_frequency_model():
    """Test Frequency model with validation."""
    freq = Frequency(period=PeriodEnum.Month, period_multiplier=3)
    assert freq.period == PeriodEnum.Month
    assert freq.period_multiplier == 3
    
    # Test validation - negative multiplier should fail
    with pytest.raises(ValueError):
        Frequency(period=PeriodEnum.Month, period_multiplier=-1)


def test_floating_rate_option():
    """Test FloatingRateOption with spread in basis points."""
    rate_option = FloatingRateOption(
        benchmark="Term SOFR",
        spread_bps=275.0
    )
    assert rate_option.benchmark == "Term SOFR"
    assert rate_option.spread_bps == 275.0


def test_credit_agreement_validation():
    """Test CreditAgreement model with full validation."""
    parties = [
        Party(id="p1", name="ACME INDUSTRIES INC.", role="Borrower"),
        Party(id="p2", name="GLOBAL BANK CORP.", role="Lender")
    ]
    
    facilities = [
        LoanFacility(
            facility_name="Term Loan Facility",
            commitment_amount=Money(amount=Decimal("500000000"), currency=Currency.USD),
            interest_terms=InterestRatePayout(
                rate_option=FloatingRateOption(
                    benchmark="Term SOFR",
                    spread_bps=275.0
                ),
                payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
            ),
            maturity_date=date(2028, 10, 15)
        )
    ]
    
    agreement = CreditAgreement(
        agreement_date=date(2023, 10, 15),
        parties=parties,
        facilities=facilities,
        governing_law="State of New York"
    )
    
    assert agreement.agreement_date == date(2023, 10, 15)
    assert len(agreement.parties) == 2
    assert len(agreement.facilities) == 1
    assert agreement.facilities[0].commitment_amount.amount == Decimal("500000000")


def test_agreement_date_validation():
    """Test that future dates are rejected."""
    parties = [Party(id="p1", name="Test", role="Borrower")]
    facilities = [
        LoanFacility(
            facility_name="Term Loan",
            commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.USD),
            interest_terms=InterestRatePayout(
                rate_option=FloatingRateOption(benchmark="SOFR", spread_bps=250.0),
                payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
            ),
            maturity_date=date(2035, 1, 1)
        )
    ]
    with pytest.raises(ValueError, match="cannot be in the future"):
        CreditAgreement(
            agreement_date=date(2030, 1, 1),  # Future date
            parties=parties,
            facilities=facilities,
            governing_law="Test"
        )


def test_empty_facilities_validation():
    """Test that at least one facility is required."""
    with pytest.raises(ValueError, match="Missing required fields.*facilities"):
        CreditAgreement(
            agreement_date=date(2023, 10, 15),
            parties=[Party(id="p1", name="Test", role="Borrower")],
            facilities=[],  # Empty facilities
            governing_law="Test"
        )


def test_maturity_after_agreement_validation():
    """Test that maturity_date must be after agreement_date."""
    parties = [Party(id="p1", name="ACME", role="Borrower")]

    valid_facility = LoanFacility(
        facility_name="Term Loan",
        commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.USD),
        interest_terms=InterestRatePayout(
            rate_option=FloatingRateOption(benchmark="SOFR", spread_bps=250.0),
            payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
        ),
        maturity_date=date(2028, 10, 15)
    )

    agreement = CreditAgreement(
        agreement_date=date(2023, 10, 15),
        parties=parties,
        facilities=[valid_facility],
        governing_law="New York"
    )
    assert agreement.facilities[0].maturity_date > agreement.agreement_date

    invalid_facility = LoanFacility(
        facility_name="Term Loan",
        commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.USD),
        interest_terms=InterestRatePayout(
            rate_option=FloatingRateOption(benchmark="SOFR", spread_bps=250.0),
            payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
        ),
        maturity_date=date(2023, 10, 15)  # same as agreement_date -> invalid
    )

    with pytest.raises(ValueError, match="maturity_date.*must be after"):
        CreditAgreement(
            agreement_date=date(2023, 10, 15),
            parties=parties,
            facilities=[invalid_facility],
            governing_law="New York"
        )


def test_currency_consistency_validation():
    """Test that all facilities must use the same currency."""
    parties = [Party(id="p1", name="ACME", role="Borrower")]

    facility_usd = LoanFacility(
        facility_name="Term Loan A",
        commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.USD),
        interest_terms=InterestRatePayout(
            rate_option=FloatingRateOption(benchmark="SOFR", spread_bps=250.0),
            payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
        ),
        maturity_date=date(2028, 10, 15)
    )

    facility_eur = LoanFacility(
        facility_name="Term Loan B",
        commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.EUR),  # mismatch
        interest_terms=InterestRatePayout(
            rate_option=FloatingRateOption(benchmark="EURIBOR", spread_bps=250.0),
            payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
        ),
        maturity_date=date(2028, 10, 15)
    )

    with pytest.raises(ValueError, match="Currency mismatch"):
        CreditAgreement(
            agreement_date=date(2023, 10, 15),
            parties=parties,
            facilities=[facility_usd, facility_eur],
            governing_law="New York"
        )


def test_party_reconciliation_validation():
    """Test that at least one Borrower party must exist."""
    parties_no_borrower = [Party(id="p1", name="Bank", role="Lender")]

    facility = LoanFacility(
        facility_name="Term Loan",
        commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.USD),
        interest_terms=InterestRatePayout(
            rate_option=FloatingRateOption(benchmark="SOFR", spread_bps=250.0),
            payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
        ),
        maturity_date=date(2028, 10, 15)
    )

    with pytest.raises(ValueError, match="Borrower"):
        CreditAgreement(
            agreement_date=date(2023, 10, 15),
            parties=parties_no_borrower,
            facilities=[facility],
            governing_law="New York"
        )


def test_extraction_status_defaults_to_success():
    """Ensure extraction_status defaults to success."""
    agreement = CreditAgreement(
        agreement_date=date(2023, 10, 15),
        parties=[Party(id="p1", name="ACME", role="Borrower")],
        facilities=[
            LoanFacility(
                facility_name="Term Loan",
                commitment_amount=Money(amount=Decimal("1000000"), currency=Currency.USD),
                interest_terms=InterestRatePayout(
                    rate_option=FloatingRateOption(benchmark="SOFR", spread_bps=250.0),
                    payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
                ),
                maturity_date=date(2028, 10, 15)
            )
        ],
        governing_law="New York"
    )
    assert agreement.extraction_status == "success"


def test_failure_status_allows_missing_fields():
    """When extraction_status=FAILURE, core fields may be missing."""
    agreement = CreditAgreement(
        extraction_status="irrelevant_document",
        agreement_date=None,
        parties=None,
        facilities=None,
        governing_law=None
    )
    assert agreement.extraction_status == "irrelevant_document"


def test_extraction_result_requires_agreement_on_success():
    """ExtractionResult must include agreement when status is success."""
    with pytest.raises(ValueError, match="agreement must be provided"):
        ExtractionResult(status="success", agreement=None)


def test_extraction_result_allows_failure_without_agreement():
    """ExtractionResult may omit agreement when status is failure."""
    res = ExtractionResult(status="irrelevant_document", agreement=None, message="not a credit agreement")
    assert res.status == "irrelevant_document"
    assert res.agreement is None

