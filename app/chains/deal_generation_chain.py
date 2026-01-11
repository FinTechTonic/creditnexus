"""
Deal Generation Chain for Demo Data.

This module provides LangChain chains for generating realistic credit agreement
scenarios using LLMs with structured output validation.
"""

import logging
import random
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date
from decimal import Decimal

from langchain_core.language_models import BaseChatModel
from pydantic import ValidationError

from app.core.llm_client import get_chat_model
from app.models.cdm import CreditAgreement, Party, LoanFacility, Money, Currency, FloatingRateOption, InterestRatePayout, Frequency, PeriodEnum, ESGKPITarget, ESGKPIType
from app.prompts.demo.deal_generation import (
    create_deal_generation_prompt,
    get_scenario_config,
    get_industry_weights,
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS
)

logger = logging.getLogger(__name__)


def create_deal_generation_chain() -> BaseChatModel:
    """
    Create and configure the LangChain deal generation chain.
    
    Uses the LLM client abstraction to support multiple providers.
    The provider and model are configured via environment variables.
    
    Returns:
        A BaseChatModel instance configured with structured output
        bound to the CreditAgreement Pydantic model.
    """
    # Use global LLM configuration
    # Temperature set to 0.7 for more creative but still realistic generation
    llm = get_chat_model(temperature=0.7)
    
    # Bind the Pydantic model as a structured output
    structured_llm = llm.with_structured_output(CreditAgreement)
    
    return structured_llm


def generate_cdm_for_deal(
    deal_type: str = "loan_application",
    scenario: Optional[str] = None,
    seed: Optional[int] = None,
    industry: Optional[str] = None
) -> CreditAgreement:
    """
    Generate a CDM-compliant CreditAgreement for demo purposes.
    
    Args:
        deal_type: Type of deal (loan_application, refinancing, restructuring)
        scenario: Scenario template (corporate_lending, sustainability_linked, refinancing, restructuring)
                  If None, randomly selects based on deal_type
        seed: Random seed for reproducibility
        industry: Industry sector (if None, randomly selects)
        
    Returns:
        CreditAgreement instance with all required fields
        
    Raises:
        ValidationError: If generated data doesn't pass CDM validation
        RuntimeError: If LLM generation fails after retries
    """
    if seed is not None:
        random.seed(seed)
    
    # Select scenario if not provided
    if scenario is None:
        scenarios = ["corporate_lending", "sustainability_linked", "refinancing", "restructuring"]
        weights = [0.40, 0.30, 0.20, 0.10]  # Match distribution from plan
        scenario = random.choices(scenarios, weights=weights)[0]
    
    # Get scenario configuration
    scenario_config = get_scenario_config(scenario)
    
    # Select industry if not provided
    if industry is None:
        industry_weights = get_industry_weights()
        industries = list(industry_weights.keys())
        weights = list(industry_weights.values())
        industry = random.choices(industries, weights=weights)[0]
    
    # Create scenario-specific and industry-specific prompt
    prompt = create_deal_generation_prompt(deal_type, scenario, industry)
    
    # Format prompt with scenario details
    sustainability_note = ""
    if scenario == "sustainability_linked":
        sustainability_note = "Sustainability-Linked: YES - Must include ESG KPI targets with NDVI vegetation index"
    else:
        sustainability_note = "Sustainability-Linked: NO"
    
    prompt_vars = {
        "deal_type": deal_type,
        "scenario": scenario,
        "industry": industry,
        "loan_size_range": scenario_config["loan_size_range"],
        "term_range": scenario_config["term_range"],
        "interest_range": scenario_config["interest_range"],
        "sustainability_note": sustainability_note
    }
    
    # Create chain
    chain = create_deal_generation_chain()
    
    # Generate with retry logic
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Invoke chain
            formatted_prompt = prompt.format(**prompt_vars)
            result = chain.invoke(formatted_prompt)
            
            # Validate result
            if isinstance(result, CreditAgreement):
                # Additional validation
                _validate_generated_cdm(result, is_demo=True)
                return result
            else:
                # Convert dict to CreditAgreement if needed
                result = CreditAgreement(**result)
                _validate_generated_cdm(result, is_demo=True)
                return result
                
        except ValidationError as e:
            last_error = e
            logger.warning(f"Validation error on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                # Retry with different seed
                if seed is not None:
                    random.seed(seed + attempt + 1)
                continue
        except Exception as e:
            last_error = e
            logger.error(f"Error generating deal on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                continue
    
    # If all retries failed, raise error
    raise RuntimeError(
        f"Failed to generate valid CreditAgreement after {max_retries} attempts. "
        f"Last error: {last_error}"
    )


def _validate_generated_cdm(cdm: CreditAgreement, is_demo: bool = False) -> None:
    """
    Validate that generated CDM has all required fields.
    
    Args:
        cdm: CreditAgreement to validate
        is_demo: If True, be more lenient with validation (auto-fix common issues)
        
    Raises:
        ValueError: If required fields are missing or invalid (only for critical errors in demo mode)
    """
    errors = []
    warnings = []
    
    # Check required fields
    if not cdm.parties:
        if is_demo:
            warnings.append("Missing parties - will be auto-generated")
        else:
            errors.append("Missing parties")
    else:
        borrower = next((p for p in cdm.parties if p.role == "Borrower"), None)
        if not borrower:
            if is_demo:
                warnings.append("Missing Borrower party - will use first party")
                borrower = cdm.parties[0]
            else:
                errors.append("Missing Borrower party")
        if borrower:
            if not borrower.name:
                if is_demo:
                    borrower.name = "Demo Borrower Corp"
                    warnings.append("Borrower missing name - auto-filled")
                else:
                    errors.append("Borrower missing name")
            if not borrower.lei:
                if is_demo:
                    borrower.lei = generate_lei()
                    warnings.append("Borrower missing LEI - auto-generated")
                else:
                    errors.append("Borrower missing LEI")
            elif borrower.lei and len(borrower.lei) != 20:
                if is_demo:
                    # Auto-fix LEI length
                    if len(borrower.lei) < 20:
                        borrower.lei = borrower.lei.ljust(20, '0')
                    else:
                        borrower.lei = borrower.lei[:20]
                    warnings.append(f"Borrower LEI length fixed from {len(borrower.lei)} to 20")
                else:
                    errors.append(f"Borrower LEI must be 20 characters, got {len(borrower.lei)}")
    
    if not cdm.facilities:
        if is_demo:
            warnings.append("Missing facilities - will be auto-generated")
        else:
            errors.append("Missing facilities")
    else:
        facility = cdm.facilities[0]
        if not facility.facility_name:
            if is_demo:
                facility.facility_name = "Term Loan Facility"
                warnings.append("Facility missing name - auto-filled")
            else:
                errors.append("Facility missing name")
        if not facility.commitment_amount:
            if is_demo:
                from app.models.cdm import Money, Currency
                facility.commitment_amount = Money(amount=Decimal("1000000"), currency=Currency.USD)
                warnings.append("Facility missing commitment_amount - auto-filled")
            else:
                errors.append("Facility missing commitment_amount")
        elif facility.commitment_amount.amount <= 0:
            if is_demo:
                facility.commitment_amount.amount = Decimal("1000000")
                warnings.append("Facility commitment_amount fixed to positive value")
            else:
                errors.append("Facility commitment_amount must be positive")
        if not facility.maturity_date:
            if is_demo:
                facility.maturity_date = date.today() + timedelta(days=365*5)
                warnings.append("Facility missing maturity_date - auto-filled")
            else:
                errors.append("Facility missing maturity_date")
        if not facility.interest_terms:
            if is_demo:
                from app.models.cdm import InterestRatePayout, FloatingRateOption, Frequency, PeriodEnum
                facility.interest_terms = InterestRatePayout(
                    rate_option=FloatingRateOption(benchmark="SOFR", spread_bps=250.0),
                    payment_frequency=Frequency(period=PeriodEnum.MONTHLY, period_multiplier=1)
                )
                warnings.append("Facility missing interest_terms - auto-filled")
            else:
                errors.append("Facility missing interest_terms")
        elif not facility.interest_terms.rate_option:
            if is_demo:
                facility.interest_terms.rate_option = FloatingRateOption(benchmark="SOFR", spread_bps=250.0)
                warnings.append("Facility missing rate_option - auto-filled")
            else:
                errors.append("Facility missing rate_option")
        elif not facility.interest_terms.rate_option.benchmark:
            if is_demo:
                facility.interest_terms.rate_option.benchmark = "SOFR"
                warnings.append("Facility missing benchmark - auto-filled")
            else:
                errors.append("Facility missing benchmark")
    
    if not cdm.agreement_date:
        if is_demo:
            cdm.agreement_date = date.today() - timedelta(days=30)
            warnings.append("Missing agreement_date - auto-filled")
        else:
            errors.append("Missing agreement_date")
    elif cdm.agreement_date > date.today():
        if is_demo:
            cdm.agreement_date = date.today() - timedelta(days=30)
            warnings.append("agreement_date was in future - fixed to past date")
        else:
            errors.append("agreement_date must be in the past")
    
    if not cdm.governing_law:
        if is_demo:
            cdm.governing_law = "NY"
            warnings.append("Missing governing_law - auto-filled")
        else:
            errors.append("Missing governing_law")
    
    # Validate date relationships
    if cdm.agreement_date and cdm.facilities:
        for facility in cdm.facilities:
            if facility.maturity_date and facility.maturity_date <= cdm.agreement_date:
                if is_demo:
                    facility.maturity_date = cdm.agreement_date + timedelta(days=365*5)
                    warnings.append(f"Facility {facility.facility_name} maturity_date fixed to be after agreement_date")
                else:
                    errors.append(f"Facility {facility.facility_name} maturity_date must be after agreement_date")
    
    # Log warnings in demo mode
    if is_demo and warnings:
        logger.info(f"Demo mode auto-fixes applied: {', '.join(warnings)}")
    
    # Only raise errors for critical issues that can't be auto-fixed
    if errors:
        raise ValueError(f"CDM validation failed: {', '.join(errors)}")


def generate_lei() -> str:
    """
    Generate a realistic LEI (Legal Entity Identifier).
    
    Format: 20 alphanumeric characters, uppercase
    
    Returns:
        20-character alphanumeric LEI string
    """
    import string
    chars = string.ascii_uppercase + string.digits
    # Start with common LEI prefix pattern (4 digits, 2 letters)
    prefix = ''.join(random.choices(string.digits, k=4)) + ''.join(random.choices(string.ascii_uppercase, k=2))
    # Rest is random alphanumeric
    suffix = ''.join(random.choices(chars, k=14))
    return prefix + suffix


def generate_company_name(industry: str) -> str:
    """
    Generate a realistic company name for the given industry.
    
    Args:
        industry: Industry sector
        
    Returns:
        Company name string
    """
    suffixes = ["Corp", "Corporation", "LLC", "Inc", "Ltd", "Group", "Holdings", "Partners"]
    industry_words = {
        "Technology": ["Tech", "Digital", "Software", "Systems", "Solutions", "Innovations"],
        "Manufacturing": ["Manufacturing", "Industries", "Production", "Works", "Fabrication"],
        "Energy": ["Energy", "Power", "Utilities", "Resources", "Renewables"],
        "Healthcare": ["Health", "Medical", "Care", "Wellness", "Pharmaceuticals"],
        "Agriculture": ["Farms", "Agriculture", "Crops", "Harvest", "Agri"],
        "Real Estate": ["Properties", "Realty", "Developments", "Estates", "Homes"],
        "Retail": ["Retail", "Stores", "Commerce", "Merchants", "Trading"]
    }
    
    words = industry_words.get(industry, ["Business", "Enterprises", "Ventures"])
    word = random.choice(words)
    suffix = random.choice(suffixes)
    
    # Add location or descriptive prefix
    locations = ["Pacific", "Global", "National", "United", "American", "International", "Continental"]
    prefix = random.choice(locations)
    
    return f"{prefix} {word} {suffix}"
