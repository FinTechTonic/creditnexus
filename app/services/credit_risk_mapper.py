"""
Credit Risk Field Mapper for CreditNexus.

Maps CDM fields to credit risk metrics for policy evaluation.
Supports RWA calculations, PD/LGD/EAD inputs, and Basel III compliance.
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import date, datetime

from app.models.cdm import CreditAgreement

logger = logging.getLogger(__name__)


class CreditRiskMapper:
    """Maps CDM fields to credit risk metrics for policy evaluation."""
    
    # Default values for credit risk calculations
    DEFAULT_PD = 0.01  # 1% default probability of default
    DEFAULT_LGD = 0.45  # 45% default loss given default
    DEFAULT_MATURITY = 1.0  # 1 year default maturity
    DEFAULT_CAPITAL_RATIO = 0.08  # 8% Basel III minimum capital ratio
    
    def __init__(self):
        """Initialize credit risk mapper."""
        pass
    
    def map_cdm_to_credit_risk_fields(
        self,
        credit_agreement: CreditAgreement,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Map CDM CreditAgreement to credit risk policy transaction fields.
        
        Args:
            credit_agreement: CDM CreditAgreement model
            additional_context: Optional additional context (deal data, borrower financials, etc.)
            
        Returns:
            Dictionary with credit risk fields for policy evaluation
        """
        risk_fields = {}
        
        # Extract basic facility information
        risk_fields.update(self._extract_facility_info(credit_agreement))
        
        # Extract borrower information
        risk_fields.update(self._extract_borrower_info(credit_agreement, additional_context))
        
        # Extract financial metrics
        risk_fields.update(self._extract_financial_metrics(credit_agreement, additional_context))
        
        # Extract collateral information
        risk_fields.update(self._extract_collateral_info(credit_agreement, additional_context))
        
        # Extract risk ratings
        risk_fields.update(self._extract_risk_ratings(credit_agreement, additional_context))
        
        # Calculate derived metrics
        risk_fields.update(self._calculate_derived_metrics(risk_fields, additional_context))
        
        return risk_fields
    
    def _extract_facility_info(self, credit_agreement: CreditAgreement) -> Dict[str, Any]:
        """Extract facility-level information."""
        fields = {}
        
        # Total commitment amount (EAD - Exposure at Default)
        total_commitment = Decimal("0")
        if credit_agreement.facilities:
            for facility in credit_agreement.facilities:
                if facility.commitment_amount:
                    total_commitment += facility.commitment_amount.amount
        
        fields["facility_amount"] = float(total_commitment)
        fields["exposure_at_default"] = float(total_commitment)  # EAD = commitment for undrawn facilities
        
        # Currency
        currency = "USD"
        if credit_agreement.facilities and credit_agreement.facilities[0].commitment_amount:
            currency = credit_agreement.facilities[0].commitment_amount.currency.value
        fields["currency"] = currency
        
        # Facility type
        if credit_agreement.facilities:
            fields["facility_type"] = credit_agreement.facilities[0].facility_name
        else:
            fields["facility_type"] = "Unknown"
        
        # Maturity date (calculate maturity in years)
        if credit_agreement.facilities and credit_agreement.facilities[0].maturity_date:
            maturity_date = credit_agreement.facilities[0].maturity_date
            if isinstance(maturity_date, str):
                maturity_date = date.fromisoformat(maturity_date)
            today = date.today()
            maturity_years = (maturity_date - today).days / 365.25
            fields["maturity_years"] = max(0.0, maturity_years)
        else:
            fields["maturity_years"] = self.DEFAULT_MATURITY
        
        return fields
    
    def _extract_borrower_info(
        self,
        credit_agreement: CreditAgreement,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract borrower information and creditworthiness metrics."""
        fields = {}
        
        # Find borrower from parties
        borrower = next(
            (p for p in (credit_agreement.parties or []) if "borrower" in p.role.lower()),
            None
        )
        
        if borrower:
            fields["borrower_id"] = borrower.id
            fields["borrower_name"] = borrower.name
            fields["borrower_lei"] = borrower.lei
        
        # Extract from additional context if available
        if additional_context:
            # Credit score
            if "credit_score" in additional_context:
                fields["borrower_credit_score"] = additional_context["credit_score"]
            
            # Net worth
            if "net_worth" in additional_context:
                fields["borrower_net_worth"] = additional_context["net_worth"]
            
            # Debt service coverage ratio
            if "debt_service_coverage_ratio" in additional_context:
                fields["debt_service_coverage_ratio"] = additional_context["debt_service_coverage_ratio"]
            
            # Leverage ratio
            if "leverage_ratio" in additional_context:
                fields["borrower_leverage_ratio"] = additional_context["leverage_ratio"]
            
            # Free cash flow
            if "free_cash_flow" in additional_context:
                fields["borrower_free_cash_flow"] = additional_context["free_cash_flow"]
            
            # Default history
            if "default_history" in additional_context:
                fields["borrower_default_history"] = additional_context["default_history"]
            
            # Rating trend
            if "rating_trend" in additional_context:
                fields["borrower_rating_trend"] = additional_context["rating_trend"]
        
        return fields
    
    def _extract_financial_metrics(
        self,
        credit_agreement: CreditAgreement,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract financial metrics for credit risk assessment."""
        fields = {}
        
        # Extract from additional context
        if additional_context:
            # Probability of Default (PD)
            if "probability_of_default" in additional_context:
                fields["probability_of_default"] = additional_context["probability_of_default"]
            elif "pd" in additional_context:
                fields["probability_of_default"] = additional_context["pd"]
            else:
                fields["probability_of_default"] = self.DEFAULT_PD
            
            # Loss Given Default (LGD)
            if "loss_given_default" in additional_context:
                fields["loss_given_default"] = additional_context["loss_given_default"]
            elif "lgd" in additional_context:
                fields["loss_given_default"] = additional_context["lgd"]
            else:
                fields["loss_given_default"] = self.DEFAULT_LGD
            
            # Risk model approach
            if "risk_model_approach" in additional_context:
                fields["risk_model_approach"] = additional_context["risk_model_approach"]
            else:
                fields["risk_model_approach"] = "standardized"  # Default to standardized approach
            
            # Rating history
            if "rating_history_years" in additional_context:
                fields["rating_history_years"] = additional_context["rating_history_years"]
        
        else:
            # Use defaults if no additional context
            fields["probability_of_default"] = self.DEFAULT_PD
            fields["loss_given_default"] = self.DEFAULT_LGD
            fields["risk_model_approach"] = "standardized"
        
        return fields
    
    def _extract_collateral_info(
        self,
        credit_agreement: CreditAgreement,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract collateral information."""
        fields = {}
        
        if additional_context:
            # Collateral coverage ratio
            if "collateral_coverage_ratio" in additional_context:
                fields["collateral_coverage_ratio"] = additional_context["collateral_coverage_ratio"]
            
            # Collateral valuation date
            if "collateral_valuation_date" in additional_context:
                fields["collateral_valuation_date"] = additional_context["collateral_valuation_date"]
            
            # Collateral valuation age (in months)
            if "collateral_valuation_age_months" in additional_context:
                fields["collateral_valuation_age_months"] = additional_context["collateral_valuation_age_months"]
            
            # Collateral type
            if "collateral_type" in additional_context:
                fields["collateral_type"] = additional_context["collateral_type"]
            
            # Collateral concentration
            if "collateral_concentration_ratio" in additional_context:
                fields["collateral_concentration_ratio"] = additional_context["collateral_concentration_ratio"]
            
            # Collateral value volatility
            if "collateral_value_volatility" in additional_context:
                fields["collateral_value_volatility"] = additional_context["collateral_value_volatility"]
        
        return fields
    
    def _extract_risk_ratings(
        self,
        credit_agreement: CreditAgreement,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract risk rating information."""
        fields = {}
        
        if additional_context:
            # Borrower risk rating
            if "borrower_risk_rating" in additional_context:
                fields["borrower_risk_rating"] = additional_context["borrower_risk_rating"]
            
            # Rating type (internal/external)
            if "rating_type" in additional_context:
                fields["rating_type"] = additional_context["rating_type"]
            
            # Rating age (in months)
            if "rating_age_months" in additional_context:
                fields["rating_age_months"] = additional_context["rating_age_months"]
            
            # Rating agency count
            if "rating_agency_count" in additional_context:
                fields["rating_agency_count"] = additional_context["rating_agency_count"]
            
            # Rating consensus
            if "rating_consensus" in additional_context:
                fields["rating_consensus"] = additional_context["rating_consensus"]
            
            # Model calibration status
            if "rating_model_calibrated" in additional_context:
                fields["rating_model_calibrated"] = additional_context["rating_model_calibrated"]
        
        return fields
    
    def _calculate_derived_metrics(
        self,
        risk_fields: Dict[str, Any],
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate derived credit risk metrics."""
        fields = {}
        
        # Risk-weighted assets (RWA) - placeholder calculation
        # Full RWA calculation requires CreditRiskService
        if "exposure_at_default" in risk_fields:
            ead = risk_fields["exposure_at_default"]
            pd = risk_fields.get("probability_of_default", self.DEFAULT_PD)
            lgd = risk_fields.get("loss_given_default", self.DEFAULT_LGD)
            
            # Simplified RWA calculation (will be replaced by full Basel III formula)
            # RWA = EAD × Risk Weight
            # Risk Weight = f(PD, LGD, Maturity) per Basel III
            # For now, use a simplified approximation
            risk_weight = pd * lgd * 12.5  # Simplified risk weight
            fields["risk_weighted_assets"] = ead * risk_weight
        
        # Capital requirement (8% of RWA)
        if "risk_weighted_assets" in fields:
            rwa = fields["risk_weighted_assets"]
            capital_ratio = additional_context.get("capital_ratio", self.DEFAULT_CAPITAL_RATIO) if additional_context else self.DEFAULT_CAPITAL_RATIO
            fields["calculated_capital_requirement"] = rwa * capital_ratio
        
        # Available capital (from additional context)
        if additional_context and "available_tier1_capital" in additional_context:
            fields["available_tier1_capital"] = additional_context["available_tier1_capital"]
        
        # Tier 1 capital ratio
        if "available_tier1_capital" in fields and "risk_weighted_assets" in fields:
            tier1_capital = fields["available_tier1_capital"]
            rwa = fields["risk_weighted_assets"]
            if rwa > 0:
                fields["tier1_capital_ratio"] = tier1_capital / rwa
        
        # Leverage ratio (Tier 1 Capital / Total Exposure)
        if "available_tier1_capital" in fields and "exposure_at_default" in risk_fields:
            tier1_capital = fields["available_tier1_capital"]
            total_exposure = risk_fields["exposure_at_default"]
            if total_exposure > 0:
                fields["leverage_ratio"] = (tier1_capital / total_exposure) * 100  # As percentage
        
        # Sector concentration (from additional context)
        if additional_context and "sector_concentration" in additional_context:
            fields["sector_concentration"] = additional_context["sector_concentration"]
        
        # Liquidity coverage ratio (from additional context)
        if additional_context and "liquidity_coverage_ratio" in additional_context:
            fields["liquidity_coverage_ratio"] = additional_context["liquidity_coverage_ratio"]
        
        return fields


def get_credit_risk_fields(
    credit_agreement: CreditAgreement,
    additional_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function to get credit risk fields from CDM agreement.
    
    Args:
        credit_agreement: CDM CreditAgreement model
        additional_context: Optional additional context (deal data, borrower financials, etc.)
        
    Returns:
        Dictionary with credit risk fields for policy evaluation
    """
    mapper = CreditRiskMapper()
    return mapper.map_cdm_to_credit_risk_fields(credit_agreement, additional_context)
