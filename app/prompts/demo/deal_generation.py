"""
Deal Generation Prompt Templates for Demo Data.

This module provides scenario-specific and industry-specific prompt templates
for generating realistic credit agreement scenarios using LLMs.
All generated deals must be CDM-compliant.
"""

from typing import List, Dict, Any
from langchain_core.prompts import ChatPromptTemplate


# Required CDM fields that must always be present
REQUIRED_FIELDS = [
    "parties[role='Borrower'].name",
    "parties[role='Borrower'].lei",  # 20-char alphanumeric
    "facilities[0].facility_name",
    "facilities[0].commitment_amount.amount",  # 100K - 50M
    "facilities[0].commitment_amount.currency",  # USD, EUR, GBP
    "facilities[0].maturity_date",  # ISO 8601, future date
    "facilities[0].interest_terms.rate_option.benchmark",  # SOFR, LIBOR, EURIBOR
    "facilities[0].interest_terms.rate_option.spread_bps",  # 100-500 bps
    "agreement_date",  # ISO 8601, past date (30-180 days ago)
    "governing_law"  # NY, English, DE, CA
]

# Optional CDM fields (include 70% of time)
OPTIONAL_FIELDS = [
    "parties[role='Administrative Agent'].name",
    "parties[role='Lender'].name",
    "sustainability_linked",  # 30% true
    "esg_kpi_targets",  # If sustainability_linked
    "deal_id",
    "loan_identification_number"
]


# ============================================================================
# Scenario-Specific System Prompts
# ============================================================================

def get_corporate_lending_system_prompt(industry: str) -> str:
    """Get system prompt for corporate lending scenario."""
    industry_context = get_industry_context(industry)
    
    return f"""You are an expert Credit Analyst generating realistic corporate lending credit agreement scenarios for demo purposes.

INDUSTRY CONTEXT: {industry}
{industry_context}

Your task is to generate a complete, CDM-compliant CreditAgreement for a standard corporate term loan or revolving credit facility.

SCENARIO: Corporate Lending
- Standard term loans or revolving facilities
- Typical loan sizes: $1M - $25M
- Terms: 3-7 years
- Interest: SOFR + 200-400 bps
- No sustainability-linked provisions

CRITICAL REQUIREMENTS:
1. All required fields MUST be present and valid
2. Borrower must be a realistic {industry} company
3. Generate company name appropriate for {industry} sector
4. Loan purpose should align with {industry} business needs
5. Use standard corporate lending terms and structures

Generate a realistic corporate lending scenario that demonstrates typical {industry} financing needs."""


def get_sustainability_linked_system_prompt(industry: str) -> str:
    """Get system prompt for sustainability-linked loan scenario."""
    industry_context = get_industry_context(industry)
    
    return f"""You are an expert Credit Analyst generating realistic sustainability-linked loan scenarios for demo purposes.

INDUSTRY CONTEXT: {industry}
{industry_context}

Your task is to generate a complete, CDM-compliant CreditAgreement for a sustainability-linked loan with ESG KPI targets.

SCENARIO: Sustainability-Linked Loan
- Loan sizes: $2M - $30M
- Terms: 3-7 years
- Interest: SOFR + 250-450 bps
- MUST include sustainability_linked = true
- MUST include esg_kpi_targets with NDVI vegetation index
- NDVI threshold: 0.70-0.85
- Measurement frequency: Quarterly
- Penalty structure: 25-50 bps if threshold not met

CRITICAL REQUIREMENTS:
1. All required fields MUST be present and valid
2. Set sustainability_linked = true
3. Include esg_kpi_targets array with at least one NDVI target
4. Borrower must be a realistic {industry} company with sustainability focus
5. Loan purpose should relate to environmental/sustainability initiatives
6. Generate company name appropriate for {industry} sector with green/sustainable focus

Generate a realistic sustainability-linked loan scenario that demonstrates ESG financing in the {industry} sector."""


def get_refinancing_system_prompt(industry: str) -> str:
    """Get system prompt for refinancing scenario."""
    industry_context = get_industry_context(industry)
    
    return f"""You are an expert Credit Analyst generating realistic loan refinancing scenarios for demo purposes.

INDUSTRY CONTEXT: {industry}
{industry_context}

Your task is to generate a complete, CDM-compliant CreditAgreement for a refinancing transaction with improved terms.

SCENARIO: Refinancing
- Loan sizes: $5M - $40M (typically larger, existing loans)
- Terms: 3-10 years
- Interest: SOFR + 150-350 bps (lower than original, improved terms)
- Borrower has existing credit facility being refinanced
- Improved terms reflect better credit profile or market conditions

CRITICAL REQUIREMENTS:
1. All required fields MUST be present and valid
2. Borrower must be a realistic {industry} company with established operations
3. Loan terms should reflect improved credit profile (lower rates)
4. Generate company name appropriate for {industry} sector
5. Loan purpose should indicate refinancing of existing debt

Generate a realistic refinancing scenario that demonstrates improved terms for an established {industry} company."""


def get_restructuring_system_prompt(industry: str) -> str:
    """Get system prompt for restructuring scenario."""
    industry_context = get_industry_context(industry)
    
    return f"""You are an expert Credit Analyst generating realistic loan restructuring scenarios for demo purposes.

INDUSTRY CONTEXT: {industry}
{industry_context}

Your task is to generate a complete, CDM-compliant CreditAgreement for a distressed borrower restructuring.

SCENARIO: Restructuring
- Loan sizes: $3M - $20M
- Terms: 5-10 years (extended maturities)
- Interest: SOFR + 300-500 bps (higher rates, distressed pricing)
- Borrower is experiencing financial difficulties
- Extended maturities and modified terms to support recovery

CRITICAL REQUIREMENTS:
1. All required fields MUST be present and valid
2. Borrower must be a realistic {industry} company facing financial challenges
3. Loan terms should reflect distressed credit profile (higher rates, longer terms)
4. Generate company name appropriate for {industry} sector
5. Loan purpose should indicate restructuring or turnaround financing

Generate a realistic restructuring scenario that demonstrates workout financing for a distressed {industry} company."""


# ============================================================================
# Industry-Specific Context
# ============================================================================

def get_industry_context(industry: str) -> str:
    """Get industry-specific context for prompts."""
    contexts = {
        "Technology": """Technology companies typically:
- Require financing for R&D, product development, scaling operations
- Have high growth potential but may have limited tangible assets
- Use financing for working capital, equipment, expansion
- Common loan purposes: Software development, infrastructure, acquisitions""",
        
        "Manufacturing": """Manufacturing companies typically:
- Require financing for equipment, facilities, inventory, working capital
- Have tangible assets (machinery, real estate) for collateral
- Use financing for expansion, modernization, seasonal working capital
- Common loan purposes: Equipment purchase, facility expansion, inventory financing""",
        
        "Energy": """Energy companies typically:
- Require financing for infrastructure, exploration, development projects
- Have long project timelines and capital-intensive operations
- Use financing for renewable energy projects, oil & gas development, infrastructure
- Common loan purposes: Project finance, equipment, development capital""",
        
        "Healthcare": """Healthcare companies typically:
- Require financing for facilities, equipment, expansion, working capital
- Have regulatory compliance requirements
- Use financing for medical equipment, facility expansion, working capital
- Common loan purposes: Equipment purchase, facility expansion, operational needs""",
        
        "Agriculture": """Agriculture companies typically:
- Require financing for land, equipment, seasonal working capital, sustainability projects
- Have seasonal cash flow patterns
- Use financing for crop production, equipment, land acquisition, sustainability initiatives
- Common loan purposes: Equipment, land, working capital, sustainable farming practices""",
        
        "Real Estate": """Real Estate companies typically:
- Require financing for property acquisition, development, refinancing
- Have real estate assets as collateral
- Use financing for acquisitions, development, refinancing existing properties
- Common loan purposes: Property acquisition, development, refinancing""",
        
        "Retail": """Retail companies typically:
- Require financing for inventory, expansion, working capital, turnaround
- Have seasonal cash flow patterns
- Use financing for inventory, store expansion, working capital, restructuring
- Common loan purposes: Inventory financing, expansion, working capital, turnaround"""
    }
    
    return contexts.get(industry, "Standard business financing needs.")


# ============================================================================
# Prompt Template Creation
# ============================================================================

def create_deal_generation_prompt(deal_type: str, scenario: str, industry: str) -> ChatPromptTemplate:
    """
    Create a scenario-specific and industry-specific prompt template.
    
    Args:
        deal_type: Type of deal (loan_application, refinancing, restructuring)
        scenario: Scenario template (corporate_lending, sustainability_linked, refinancing, restructuring)
        industry: Industry sector (Technology, Manufacturing, Energy, etc.)
        
    Returns:
        ChatPromptTemplate for deal generation
    """
    # Get scenario-specific system prompt
    if scenario == "corporate_lending":
        system_prompt = get_corporate_lending_system_prompt(industry)
    elif scenario == "sustainability_linked":
        system_prompt = get_sustainability_linked_system_prompt(industry)
    elif scenario == "refinancing":
        system_prompt = get_refinancing_system_prompt(industry)
    elif scenario == "restructuring":
        system_prompt = get_restructuring_system_prompt(industry)
    else:
        system_prompt = get_corporate_lending_system_prompt(industry)
    
    # Get scenario configuration
    scenario_config = get_scenario_config(scenario)
    
    user_prompt_template = """Generate a {deal_type} credit agreement with the following specifications:

Scenario: {scenario}
Industry: {industry}
Loan Size Range: {loan_size_range}
Term Range: {term_range}
Interest Rate Range: {interest_range}
{sustainability_note}

Required Fields (MUST be present):
- Borrower name and LEI (20-char alphanumeric, format: 5493000X0ABCDEFGH12)
- At least one facility with complete terms (name, commitment amount, currency, maturity date)
- Agreement date (ISO 8601, past date, 30-180 days ago)
- Governing law (NY, English, Delaware, California)
- Interest terms with benchmark (SOFR, LIBOR, EURIBOR) and spread in basis points (100-500 bps)

Optional Fields (include if applicable):
- Administrative Agent (50% chance)
- Multiple Lenders (60% chance, 1-5 lenders)
- Sustainability-linked provisions (if scenario is sustainability_linked)
- ESG KPI targets (if sustainability_linked, MUST include NDVI target with threshold 0.70-0.85)

Data Validation:
- LEI: Exactly 20 alphanumeric characters, uppercase
- Amounts: Positive Decimal, reasonable for {industry} sector ({loan_size_range})
- Dates: Valid ISO 8601 (YYYY-MM-DD), agreement_date < maturity_date
- Spread: Basis points (e.g., 3.5% = 350.0 bps)
- Currencies: ISO 3-letter codes (USD, EUR, GBP, JPY)

Generate a complete, valid CreditAgreement that is CDM-compliant and ready for use in demo scenarios.
The borrower should be a realistic {industry} company with an appropriate name and business profile."""

    # Format sustainability note
    sustainability_note = ""
    if scenario == "sustainability_linked":
        sustainability_note = "Sustainability-Linked: YES - Must include ESG KPI targets with NDVI vegetation index"
    else:
        sustainability_note = "Sustainability-Linked: NO"
    
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", user_prompt_template)
    ])


def get_scenario_config(scenario: str) -> Dict[str, Any]:
    """
    Get configuration for a specific scenario.
    
    Args:
        scenario: Scenario name (corporate_lending, sustainability_linked, refinancing, restructuring)
        
    Returns:
        Dictionary with scenario configuration
    """
    scenarios = {
        "corporate_lending": {
            "industries": ["Technology", "Manufacturing", "Energy", "Healthcare"],
            "loan_size_range": "$1M - $25M",
            "term_range": "3-7 years",
            "interest_range": "SOFR + 200-400 bps",
            "sustainability_linked": False
        },
        "sustainability_linked": {
            "industries": ["Agriculture", "Energy", "Manufacturing", "Real Estate"],
            "loan_size_range": "$2M - $30M",
            "term_range": "3-7 years",
            "interest_range": "SOFR + 250-450 bps",
            "sustainability_linked": True,
            "esg_targets": {
                "ndvi_threshold": (0.70, 0.85),
                "penalty_bps": (25, 50),
                "frequency": "Quarterly"
            }
        },
        "refinancing": {
            "industries": ["Technology", "Manufacturing", "Healthcare"],
            "loan_size_range": "$5M - $40M",
            "term_range": "3-10 years",
            "interest_range": "SOFR + 150-350 bps",
            "sustainability_linked": False,
            "note": "Improved terms, lower interest rates"
        },
        "restructuring": {
            "industries": ["Manufacturing", "Retail", "Energy"],
            "loan_size_range": "$3M - $20M",
            "term_range": "5-10 years",
            "interest_range": "SOFR + 300-500 bps",
            "sustainability_linked": False,
            "note": "Distressed borrower, extended maturities"
        }
    }
    
    return scenarios.get(scenario, scenarios["corporate_lending"])


def get_industry_weights() -> Dict[str, float]:
    """Get industry distribution weights for deal generation."""
    return {
        "Technology": 0.25,
        "Manufacturing": 0.20,
        "Energy": 0.15,
        "Healthcare": 0.15,
        "Agriculture": 0.10,
        "Real Estate": 0.10,
        "Retail": 0.05
    }
