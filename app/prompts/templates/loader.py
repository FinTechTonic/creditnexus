"""
Prompt loader for LMA template prompts.

Dynamically loads prompt templates based on template category.
"""

import logging
from typing import Dict, Optional
from langchain_core.prompts import ChatPromptTemplate

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Loads prompt templates for different LMA template categories.
    
    Maps template categories to prompt modules and provides
    access to section-specific prompts.
    """
    
    # Mapping of template categories to prompt modules
    PROMPT_MODULE_MAP = {
        "Facility Agreement": "app.prompts.templates.facility_agreement",
        "Term Sheet": "app.prompts.templates.term_sheet",
        "Confidentiality Agreement": "app.prompts.templates.confidentiality",
        "Secondary Trading": "app.prompts.templates.secondary_trading",
        "Security & Intercreditor": "app.prompts.templates.security_intercreditor",
        "Origination Documents": "app.prompts.templates.origination",
        "Sustainable Finance": "app.prompts.templates.sustainable_finance",
        "Regional Documents": "app.prompts.templates.regional",
        "Regulatory": "app.prompts.templates.regulatory",
        "Restructuring": "app.prompts.templates.restructuring",
        "Supporting Documents": "app.prompts.templates.supporting",
        "Filing": "app.prompts.templates.filing",
        "Signature": "app.prompts.templates.signature",
    }
    
    
    # Mapping of section names to prompt variable names
    SECTION_PROMPT_MAP = {
        "Facility Agreement": {
            "representations_and_warranties": "REPRESENTATIONS_PROMPT",
            "conditions_precedent": "CONDITIONS_PRECEDENT_PROMPT",
            "covenants": "COVENANTS_PROMPT",
            "esg_spt": "ESG_SPT_PROMPT",
            "events_of_default": "EVENTS_OF_DEFAULT_PROMPT",
            "governing_law_clause": "GOVERNING_LAW_PROMPT",
            # REF (Real Estate Finance) prompts
            "property_description": "PROPERTY_DESCRIPTION_PROMPT",
            "security_package": "SECURITY_PACKAGE_PROMPT",
            "valuation_requirements": "VALUATION_REQUIREMENTS_PROMPT",
            "ltv_covenants": "LTV_COVENANTS_PROMPT",
            # SLL (Sustainability-Linked Loan) prompts
            "spt_measurement_methodology": "SPT_MEASUREMENT_METHODOLOGY_PROMPT",
            "margin_adjustment_mechanism": "MARGIN_ADJUSTMENT_MECHANISM_PROMPT",
            "reporting_requirements": "REPORTING_REQUIREMENTS_PROMPT",
            "verification_process": "VERIFICATION_PROCESS_PROMPT",
            # Bridge Loan prompts
            "bridge_loan_provisions": "BRIDGE_LOAN_PROVISIONS_PROMPT",
            "refinancing_obligations": "REFINANCING_OBLIGATIONS_PROMPT",
            "prepayment_terms": "PREPAYMENT_TERMS_PROMPT",
            # Mezzanine Finance prompts
            "mezzanine_provisions": "MEZZANINE_PROVISIONS_PROMPT",
            "equity_participation_rights": "EQUITY_PARTICIPATION_RIGHTS_PROMPT",
            "subordination_agreement": "SUBORDINATION_AGREEMENT_PROMPT",
            "conversion_rights": "CONVERSION_RIGHTS_PROMPT",
            # Project Finance prompts
            "project_specific_provisions": "PROJECT_SPECIFIC_PROVISIONS_PROMPT",
            "offtake_agreement_provisions": "OFFTAKE_AGREEMENT_PROVISIONS_PROMPT",
            "construction_phase_covenants": "CONSTRUCTION_PHASE_COVENANTS_PROMPT",
            "operational_phase_covenants": "OPERATIONAL_PHASE_COVENANTS_PROMPT",
            # Acquisition Finance prompts
            "acquisition_provisions": "ACQUISITION_PROVISIONS_PROMPT",
            "target_company_representations": "TARGET_COMPANY_REPRESENTATIONS_PROMPT",
            "equity_funding_conditions": "EQUITY_FUNDING_CONDITIONS_PROMPT",
            "post_acquisition_covenants": "POST_ACQUISITION_COVENANTS_PROMPT",
            # Working Capital prompts
            "working_capital_provisions": "WORKING_CAPITAL_PROVISIONS_PROMPT",
            "revolving_credit_terms": "REVOLVING_CREDIT_TERMS_PROMPT",
            "drawdown_mechanics": "DRAWDOWN_MECHANICS_PROMPT",
            "utilization_covenants": "UTILIZATION_COVENANTS_PROMPT",
            # Trade Finance prompts
            "trade_finance_provisions": "TRADE_FINANCE_PROVISIONS_PROMPT",
            "letter_of_credit_terms": "LETTER_OF_CREDIT_TERMS_PROMPT",
            "documentary_requirements": "DOCUMENTARY_REQUIREMENTS_PROMPT",
            "shipping_document_provisions": "SHIPPING_DOCUMENT_PROVISIONS_PROMPT",
            # Leveraged Finance prompts
            "leverage_covenants": "LEVERAGE_COVENANTS_PROMPT",
            "ebitda_definitions": "EBITDA_DEFINITIONS_PROMPT",
            "financial_covenants": "FINANCIAL_COVENANTS_PROMPT",
            "incurrence_based_covenants": "INCURRENCE_BASED_COVENANTS_PROMPT",
            # Asset-Based Lending prompts
            "asset_based_provisions": "ASSET_BASED_PROVISIONS_PROMPT",
            "collateral_monitoring": "COLLATERAL_MONITORING_PROMPT",
            "advance_rate_calculations": "ADVANCE_RATE_CALCULATIONS_PROMPT",
            "field_examiner_rights": "FIELD_EXAMINER_RIGHTS_PROMPT",
            # Infrastructure Finance prompts
            "infrastructure_provisions": "INFRASTRUCTURE_PROVISIONS_PROMPT",
            "regulatory_compliance": "REGULATORY_COMPLIANCE_PROMPT",
            "concession_agreement_provisions": "CONCESSION_AGREEMENT_PROVISIONS_PROMPT",
            "long_term_operational_covenants": "LONG_TERM_OPERATIONAL_COVENANTS_PROMPT",
            # Sovereign Lending prompts
            "sovereign_immunity_waiver": "SOVEREIGN_IMMUNITY_WAIVER_PROMPT",
            "political_risk_provisions": "POLITICAL_RISK_PROVISIONS_PROMPT",
            "sovereign_representations": "SOVEREIGN_REPRESENTATIONS_PROMPT",
            "enforcement_provisions": "ENFORCEMENT_PROVISIONS_PROMPT",
        },
        "Term Sheet": {
            "purpose": "PURPOSE_PROMPT",
            "conditions_precedent": "CONDITIONS_PRECEDENT_PROMPT",
            "representations": "REPRESENTATIONS_PROMPT",
            "fees": "FEES_PROMPT",
        },
        "Confidentiality Agreement": {
            "confidentiality_obligations": "CONFIDENTIALITY_OBLIGATIONS_PROMPT",
            "no_front_running_undertaking": "NO_FRONT_RUNNING_UNDERTAKING_PROMPT",
            "permitted_disclosures": "PERMITTED_DISCLOSURES_PROMPT",
        },
        "Secondary Trading": {
            "assignment_clause": "ASSIGNMENT_CLAUSE_PROMPT",
            "transfer_restrictions": "TRANSFER_RESTRICTIONS_PROMPT",
            "participation_agreement": "PARTICIPATION_AGREEMENT_PROMPT",
            "collateral_obligations": "COLLATERAL_OBLIGATIONS_PROMPT",
            "margin_calculation": "MARGIN_CALCULATION_PROMPT",
            "transfer_provisions": "TRANSFER_PROVISIONS_PROMPT",
            "dispute_resolution": "DISPUTE_RESOLUTION_PROMPT",
        },
        "Security & Intercreditor": {
            "security_package_description": "SECURITY_PACKAGE_DESCRIPTION_PROMPT",
            "intercreditor_arrangements": "INTERCREDITOR_ARRANGEMENTS_PROMPT",
            "subordination_provisions": "SUBORDINATION_PROVISIONS_PROMPT",
            "enforcement_rights": "ENFORCEMENT_RIGHTS_PROMPT",
            "priority_provisions": "PRIORITY_PROVISIONS_PROMPT",
            "voting_mechanisms": "VOTING_MECHANISMS_PROMPT",
            "standstill_provisions": "STANDSTILL_PROVISIONS_PROMPT",
        },
        "Origination Documents": {
            "commitment_letter": "COMMITMENT_LETTER_PROMPT",
            "underwriting_terms": "UNDERWRITING_TERMS_PROMPT",
            "syndication_terms": "SYNDICATION_TERMS_PROMPT",
            "aml_certification": "AML_CERTIFICATION_PROMPT",
            "source_of_funds": "SOURCE_OF_FUNDS_PROMPT",
            "ongoing_obligations": "ONGOING_OBLIGATIONS_PROMPT",
        },
        "Sustainable Finance": {
            "green_loan_framework": "GREEN_LOAN_FRAMEWORK_PROMPT",
            "esg_reporting_framework": "ESG_REPORTING_FRAMEWORK_PROMPT",
            "sustainability_certification": "SUSTAINABILITY_CERTIFICATION_PROMPT",
            "sustainability_provisions": "SUSTAINABILITY_PROVISIONS_PROMPT",
            "kpi_monitoring_clause": "KPI_MONITORING_CLAUSE_PROMPT",
            "margin_adjustment_mechanism": "MARGIN_ADJUSTMENT_MECHANISM_PROMPT",
            "reporting_obligations": "REPORTING_OBLIGATIONS_PROMPT",
        },
        "Regional Documents": {
            "regional_compliance": "REGIONAL_COMPLIANCE_PROMPT",
            "jurisdiction_specific_provisions": "JURISDICTION_SPECIFIC_PROVISIONS_PROMPT",
        },
        "Regulatory": {
            "regulatory_compliance": "REGULATORY_COMPLIANCE_PROMPT",
            "mica_compliance": "MICA_COMPLIANCE_PROMPT",
            "basel_iii_compliance": "BASEL_III_COMPLIANCE_PROMPT",
            "fatf_compliance": "FATF_COMPLIANCE_PROMPT",
            "fatf_compliance_statement": "FATF_COMPLIANCE_STATEMENT_PROMPT",
            "cdd_obligations": "CDD_OBLIGATIONS_PROMPT",
            "suspicious_transaction_reporting": "SUSPICIOUS_TRANSACTION_REPORTING_PROMPT",
            "sanctions_compliance": "SANCTIONS_COMPLIANCE_PROMPT",
            "capital_adequacy_certification": "CAPITAL_ADEQUACY_CERTIFICATION_PROMPT",
            "risk_weighting_disclosure": "RISK_WEIGHTING_DISCLOSURE_PROMPT",
            "regulatory_capital_requirements": "REGULATORY_CAPITAL_REQUIREMENTS_PROMPT",
        },
        "Restructuring": {
            "restructuring_terms": "RESTRUCTURING_TERMS_PROMPT",
            "workout_agreement": "WORKOUT_AGREEMENT_PROMPT",
            "forbearance_provisions": "FORBEARANCE_PROVISIONS_PROMPT",
            "debt_compromise": "DEBT_COMPROMISE_PROMPT",
        },
        "Supporting Documents": {
            "legal_opinion": "LEGAL_OPINION_PROMPT",
            "compliance_certificate": "COMPLIANCE_CERTIFICATE_PROMPT",
            "authorization_resolution": "AUTHORIZATION_RESOLUTION_PROMPT",
        },
    }
    
    @classmethod
    def load_prompts_for_template(cls, template_category: str) -> Dict[str, ChatPromptTemplate]:
        """
        Load all prompts for a template category.
        
        Args:
            template_category: Template category (e.g., "Facility Agreement", "Term Sheet")
            
        Returns:
            Dictionary mapping section names to ChatPromptTemplate instances
            
        Raises:
            ImportError: If prompt module cannot be imported
            KeyError: If template category is not supported
        """
        if template_category not in cls.PROMPT_MODULE_MAP:
            raise KeyError(f"Template category '{template_category}' not supported. Available: {list(cls.PROMPT_MODULE_MAP.keys())}")
        
        module_path = cls.PROMPT_MODULE_MAP[template_category]
        
        try:
            # Dynamic import
            module = __import__(module_path, fromlist=[""])
            
            # Get prompts dictionary from module
            # Try category-specific dictionary names
            category_prompts_name = template_category.upper().replace(' ', '_').replace('&', '').replace('-', '_') + "_PROMPTS"
            if hasattr(module, category_prompts_name):
                prompts_dict = getattr(module, category_prompts_name)
            elif hasattr(module, "FACILITY_AGREEMENT_PROMPTS"):
                prompts_dict = getattr(module, "FACILITY_AGREEMENT_PROMPTS")
            elif hasattr(module, "TERM_SHEET_PROMPTS"):
                prompts_dict = getattr(module, "TERM_SHEET_PROMPT")
            elif hasattr(module, "CONFIDENTIALITY_AGREEMENT_PROMPTS"):
                prompts_dict = getattr(module, "CONFIDENTIALITY_AGREEMENT_PROMPTS")
            elif hasattr(module, "SECONDARY_TRADING_PROMPTS"):
                prompts_dict = getattr(module, "SECONDARY_TRADING_PROMPTS")
            elif hasattr(module, "SECURITY_INTERCREDITOR_PROMPTS"):
                prompts_dict = getattr(module, "SECURITY_INTERCREDITOR_PROMPTS")
            elif hasattr(module, "ORIGINATION_PROMPTS"):
                prompts_dict = getattr(module, "ORIGINATION_PROMPTS")
            elif hasattr(module, "SUSTAINABLE_FINANCE_PROMPTS"):
                prompts_dict = getattr(module, "SUSTAINABLE_FINANCE_PROMPTS")
            elif hasattr(module, "REGIONAL_PROMPTS"):
                prompts_dict = getattr(module, "REGIONAL_PROMPTS")
            elif hasattr(module, "REGULATORY_PROMPTS"):
                prompts_dict = getattr(module, "REGULATORY_PROMPTS")
            elif hasattr(module, "RESTRUCTURING_PROMPTS"):
                prompts_dict = getattr(module, "RESTRUCTURING_PROMPTS")
            elif hasattr(module, "SUPPORTING_PROMPTS"):
                prompts_dict = getattr(module, "SUPPORTING_PROMPTS")
            elif hasattr(module, "PROMPTS"):
                prompts_dict = getattr(module, "PROMPTS")
            else:
                # Try to find all ChatPromptTemplate instances
                prompts_dict = {
                    name: value
                    for name, value in vars(module).items()
                    if isinstance(value, ChatPromptTemplate) and name.endswith("_PROMPT")
                }
                # Convert to lowercase keys
                prompts_dict = {
                    name.lower().replace("_prompt", ""): value
                    for name, value in prompts_dict.items()
                }
            
            logger.debug(f"Loaded {len(prompts_dict)} prompt(s) for category '{template_category}'")
            return prompts_dict
            
        except ImportError as e:
            logger.error(f"Failed to import prompt module '{module_path}': {e}")
            raise ImportError(f"Could not import prompt module for category '{template_category}': {e}") from e
    
    @classmethod
    def get_prompt_for_section(
        cls, 
        template_category: str, 
        section_name: str
    ) -> Optional[ChatPromptTemplate]:
        """
        Get a specific prompt for a section.
        
        Args:
            template_category: Template category
            section_name: Section name (e.g., "representations_and_warranties")
            
        Returns:
            ChatPromptTemplate instance or None if not found
        """
        try:
            prompts = cls.load_prompts_for_template(template_category)
            
            # Try direct lookup
            if section_name in prompts:
                return prompts[section_name]
            
            # Try normalized lookup
            normalized_name = section_name.lower().replace(" ", "_").replace("-", "_")
            if normalized_name in prompts:
                return prompts[normalized_name]
            
            # Try section mapping
            if template_category in cls.SECTION_PROMPT_MAP:
                section_map = cls.SECTION_PROMPT_MAP[template_category]
                if section_name in section_map:
                    prompt_var = section_map[section_name]
                    prompts = cls.load_prompts_for_template(template_category)
                    # The prompts dict should have the section name as key
                    if section_name in prompts:
                        return prompts[section_name]
            
            logger.warning(f"Prompt not found for section '{section_name}' in category '{template_category}'")
            return None
            
        except (KeyError, ImportError) as e:
            logger.error(f"Error loading prompt for section '{section_name}': {e}")
            return None
    
    @classmethod
    def list_available_sections(cls, template_category: str) -> list:
        """
        List available sections for a template category.
        
        Args:
            template_category: Template category
            
        Returns:
            List of available section names
        """
        try:
            prompts = cls.load_prompts_for_template(template_category)
            return list(prompts.keys())
        except (KeyError, ImportError):
            return []
















