import pytest
from decimal import Decimal
from datetime import date, timedelta
from pydantic import ValidationError
from app.models.cdm import (
    CreditAgreement,
    LoanFacility,
    Money,
    Currency,
    InterestRatePayout,
    FloatingRateOption,
    Frequency,
    PeriodEnum,
    ExtractionStatus,
    Party
)

# --- Helper Fixtures ---

@pytest.fixture
def valid_money():
    return Money(amount="1000000.00", currency=Currency.USD)

@pytest.fixture
def valid_interest():
    return InterestRatePayout(
        rate_option=FloatingRateOption(benchmark="SOFR", spread_bps="350.0"),
        payment_frequency=Frequency(period=PeriodEnum.Month, period_multiplier=3)
    )

@pytest.fixture
def valid_facility(valid_money, valid_interest):
    return LoanFacility(
        facility_name="Term Loan B",
        commitment_amount=valid_money,
        interest_terms=valid_interest,
        maturity_date=date.today() + timedelta(days=365)
    )

@pytest.fixture
def valid_party():
    return Party(id="p1", name="Acme Corp", role="Borrower")

# --- Tests ---

def test_money_precision():
    """Verify Money uses Decimal and preserves precision from string input."""
    m = Money(amount="1000000.00", currency=Currency.USD)
    assert isinstance(m.amount, Decimal)
    assert m.amount == Decimal("1000000.00")
    
    # Ensure it doesn't introduce float errors
    # If this were float, 1.1 + 2.2 might not equal 3.3 exactly
    m2 = Money(amount="1.1", currency=Currency.USD)
    m3 = Money(amount="2.2", currency=Currency.USD)
    assert m2.amount + m3.amount == Decimal("3.3")

def test_spread_bps_precision():
    """Verify spread_bps converts to Decimal."""
    fro = FloatingRateOption(benchmark="SOFR", spread_bps="250.0")
    assert isinstance(fro.spread_bps, Decimal)
    assert fro.spread_bps == Decimal("250.0")

def test_maturity_date_validation(valid_facility, valid_party):
    """Verify validation fails if maturity date is before agreement date."""
    agreement_date = date.today()
    
    # Create a facility with maturity BEFORE agreement
    bad_facility = valid_facility.model_copy()
    bad_facility.maturity_date = agreement_date - timedelta(days=1)

    with pytest.raises(ValidationError) as exc:
        CreditAgreement(
            agreement_date=agreement_date,
            parties=[valid_party],
            facilities=[bad_facility],
            governing_law="NY"
        )
    
    assert "maturity_date" in str(exc.value)
    assert "must be after agreement_date" in str(exc.value)

def test_currency_consistency(valid_facility, valid_party):
    """Verify validation fails if facilities have different currencies."""
    # Facility 1 is USD (from fixture)
    fac1 = valid_facility
    
    # Facility 2 is EUR
    fac2 = valid_facility.model_copy()
    fac2.facility_name = "Euro Tranche"
    fac2.commitment_amount = Money(amount="500000.00", currency=Currency.EUR)

    with pytest.raises(ValidationError) as exc:
        CreditAgreement(
            agreement_date=date.today(),
            parties=[valid_party],
            facilities=[fac1, fac2],
            governing_law="NY"
        )
    
    assert "Currency mismatch" in str(exc.value)

def test_borrower_existence(valid_facility):
    """Verify validation warns/fails if no Borrower is present."""
    # Party is a Lender, not Borrower
    lender = Party(id="p1", name="Big Bank", role="Lender")
    
    ca = CreditAgreement(
        agreement_date=date.today(),
        parties=[lender],
        facilities=[valid_facility],
        governing_law="NY"
    )
    
    # Should downgrade status to PARTIAL because Borrower is missing
    assert ca.extraction_status == ExtractionStatus.PARTIAL