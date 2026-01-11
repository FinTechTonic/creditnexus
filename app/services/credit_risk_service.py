"""
Credit Risk Calculation Service for CreditNexus.

Implements Basel III capital requirements, IRB approach calculations,
and credit risk metrics including RWA, PD, LGD, EAD.
"""

import logging
import math
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime

logger = logging.getLogger(__name__)


class CreditRiskService:
    """
    Service for calculating credit risk metrics per Basel III framework.
    
    Supports:
    - Risk-Weighted Assets (RWA) calculation
    - Capital requirements (Basel III)
    - Probability of Default (PD) estimation
    - Loss Given Default (LGD) calculation
    - Exposure at Default (EAD) calculation
    - IRB (Internal Ratings-Based) approach
    - Standardized approach
    """
    
    # Basel III constants
    MIN_CAPITAL_RATIO = Decimal("0.08")  # 8% minimum capital ratio
    MIN_TIER1_RATIO = Decimal("0.06")  # 6% minimum Tier 1 capital ratio
    MIN_LEVERAGE_RATIO = Decimal("0.03")  # 3% minimum leverage ratio
    MIN_LCR = Decimal("1.0")  # 100% minimum liquidity coverage ratio
    
    # Asset class risk weights (Standardized Approach)
    RISK_WEIGHTS = {
        "sovereign_aaa": Decimal("0.00"),  # 0%
        "sovereign_aa": Decimal("0.20"),  # 20%
        "sovereign_a": Decimal("0.50"),  # 50%
        "sovereign_bbb": Decimal("1.00"),  # 100%
        "sovereign_bb": Decimal("1.00"),  # 100%
        "sovereign_b": Decimal("1.50"),  # 150%
        "sovereign_ccc": Decimal("1.50"),  # 150%
        "corporate_aaa": Decimal("0.20"),  # 20%
        "corporate_aa": Decimal("0.20"),  # 20%
        "corporate_a": Decimal("0.50"),  # 50%
        "corporate_bbb": Decimal("1.00"),  # 100%
        "corporate_bb": Decimal("1.00"),  # 100%
        "corporate_b": Decimal("1.50"),  # 150%
        "corporate_ccc": Decimal("1.50"),  # 150%
        "retail": Decimal("0.75"),  # 75%
        "residential_mortgage": Decimal("0.35"),  # 35%
        "commercial_real_estate": Decimal("1.00"),  # 100%
        "default": Decimal("1.00"),  # 100% default
    }
    
    def __init__(self):
        """Initialize credit risk service."""
        pass
    
    def calculate_rwa(
        self,
        exposure: Decimal,
        pd: float,
        lgd: float,
        maturity: float = 1.0,
        asset_class: str = "corporate",
        approach: str = "irb"
    ) -> Decimal:
        """
        Calculate Risk-Weighted Assets (RWA) per Basel III.
        
        For IRB approach:
        RWA = EAD × K × 12.5
        K = LGD × N[(1-R)^-0.5 × G(PD) + (R/(1-R))^0.5 × G(0.999)] - PD × LGD
        
        For Standardized approach:
        RWA = EAD × Risk Weight
        
        Args:
            exposure: Exposure at Default (EAD)
            pd: Probability of Default (0-1)
            lgd: Loss Given Default (0-1)
            maturity: Maturity in years (default: 1.0)
            asset_class: Asset class (corporate, retail, sovereign, etc.)
            approach: Calculation approach ("irb" or "standardized")
            
        Returns:
            Risk-weighted assets as Decimal
        """
        if approach.lower() == "irb":
            # IRB approach calculation
            k = self._calculate_capital_requirement_k(pd, lgd, maturity, asset_class)
            rwa = exposure * Decimal(str(k)) * Decimal("12.5")
        else:
            # Standardized approach
            risk_weight = self._get_risk_weight(asset_class, pd)
            rwa = exposure * risk_weight
        
        return rwa.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def _calculate_capital_requirement_k(
        self,
        pd: float,
        lgd: float,
        maturity: float,
        asset_class: str
    ) -> float:
        """
        Calculate capital requirement K per Basel III IRB formula.
        
        K = LGD × N[(1-R)^-0.5 × G(PD) + (R/(1-R))^0.5 × G(0.999)] - PD × LGD
        
        Where:
        - N(x) is the cumulative standard normal distribution
        - G(x) is the inverse cumulative standard normal distribution
        - R is the correlation factor (depends on asset class and PD)
        
        Args:
            pd: Probability of Default (0-1)
            lgd: Loss Given Default (0-1)
            maturity: Maturity in years
            asset_class: Asset class (corporate, retail, etc.)
            
        Returns:
            Capital requirement K (0-1)
        """
        # Correlation factor R (simplified formula per Basel III)
        if asset_class.lower() == "retail":
            r = 0.04  # Retail correlation
        else:
            # Corporate correlation (depends on PD)
            r = 0.12 * (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)) + 0.24 * (1 - (1 - math.exp(-50 * pd)) / (1 - math.exp(-50)))
        
        # Maturity adjustment (b)
        b = (0.11852 - 0.05478 * math.log(pd)) ** 2
        
        # Maturity adjustment factor
        maturity_adj = (1 + (maturity - 2.5) * b) / (1 - 1.5 * b)
        
        # Calculate N[(1-R)^-0.5 × G(PD) + (R/(1-R))^0.5 × G(0.999)]
        # Using approximation for normal distribution
        g_pd = self._inverse_normal_cdf(pd)
        g_999 = self._inverse_normal_cdf(0.999)
        
        inner_term = (1 - r) ** -0.5 * g_pd + (r / (1 - r)) ** 0.5 * g_999
        n_term = self._normal_cdf(inner_term)
        
        # Calculate K
        k = lgd * n_term - pd * lgd
        
        # Apply maturity adjustment
        k = k * maturity_adj
        
        # Ensure K is non-negative
        k = max(0.0, k)
        
        return k
    
    def _normal_cdf(self, x: float) -> float:
        """Cumulative standard normal distribution (approximation)."""
        # Abramowitz and Stegun approximation
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911
        
        sign = 1
        if x < 0:
            sign = -1
        x = abs(x) / math.sqrt(2.0)
        
        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
        
        return 0.5 * (1.0 + sign * y)
    
    def _inverse_normal_cdf(self, p: float) -> float:
        """Inverse cumulative standard normal distribution (approximation)."""
        # Beasley-Springer-Moro algorithm approximation
        if p <= 0 or p >= 1:
            raise ValueError("p must be between 0 and 1")
        
        # Approximation for inverse normal CDF
        if p < 0.5:
            return -self._inverse_normal_cdf_approx(1 - p)
        else:
            return self._inverse_normal_cdf_approx(p)
    
    def _inverse_normal_cdf_approx(self, p: float) -> float:
        """Approximation for inverse normal CDF (p >= 0.5)."""
        # Winitzki approximation
        c0 = 2.515517
        c1 = 0.802853
        c2 = 0.010328
        d1 = 1.432788
        d2 = 0.189269
        d3 = 0.001308
        
        t = math.sqrt(-2 * math.log(1 - p))
        x = t - (c0 + c1 * t + c2 * t * t) / (1 + d1 * t + d2 * t * t + d3 * t * t * t)
        return x
    
    def _get_risk_weight(self, asset_class: str, pd: Optional[float] = None) -> Decimal:
        """
        Get risk weight for standardized approach.
        
        Args:
            asset_class: Asset class identifier
            pd: Optional probability of default for rating-based lookup
            
        Returns:
            Risk weight as Decimal
        """
        # Map PD to rating if provided
        if pd is not None:
            if pd <= 0.0001:  # AAA
                rating = "aaa"
            elif pd <= 0.0005:  # AA
                rating = "aa"
            elif pd <= 0.002:  # A
                rating = "a"
            elif pd <= 0.01:  # BBB
                rating = "bbb"
            elif pd <= 0.05:  # BB
                rating = "bb"
            elif pd <= 0.15:  # B
                rating = "b"
            else:  # CCC or below
                rating = "ccc"
            
            key = f"{asset_class}_{rating}"
            if key in self.RISK_WEIGHTS:
                return self.RISK_WEIGHTS[key]
        
        # Default risk weight
        return self.RISK_WEIGHTS.get(asset_class.lower(), self.RISK_WEIGHTS["default"])
    
    def calculate_capital_requirement(
        self,
        rwa: Decimal,
        capital_ratio: Optional[Decimal] = None
    ) -> Decimal:
        """
        Calculate minimum capital requirement (Basel III).
        
        Capital Requirement = RWA × Capital Ratio (default: 8%)
        
        Args:
            rwa: Risk-weighted assets
            capital_ratio: Capital ratio (default: 8% = 0.08)
            
        Returns:
            Minimum capital requirement as Decimal
        """
        if capital_ratio is None:
            capital_ratio = self.MIN_CAPITAL_RATIO
        
        capital_requirement = rwa * capital_ratio
        return capital_requirement.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def calculate_tier1_capital_requirement(
        self,
        rwa: Decimal
    ) -> Decimal:
        """
        Calculate minimum Tier 1 capital requirement (6% of RWA).
        
        Args:
            rwa: Risk-weighted assets
            
        Returns:
            Minimum Tier 1 capital requirement as Decimal
        """
        return (rwa * self.MIN_TIER1_RATIO).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    def calculate_leverage_ratio(
        self,
        tier1_capital: Decimal,
        total_exposure: Decimal
    ) -> Decimal:
        """
        Calculate leverage ratio (Tier 1 Capital / Total Exposure).
        
        Args:
            tier1_capital: Tier 1 capital amount
            total_exposure: Total exposure amount
            
        Returns:
            Leverage ratio as Decimal (e.g., 0.03 for 3%)
        """
        if total_exposure == 0:
            return Decimal("0")
        
        leverage_ratio = tier1_capital / total_exposure
        return leverage_ratio.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    
    def assess_creditworthiness(
        self,
        credit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess creditworthiness using internal rating model.
        
        Args:
            credit_data: Dictionary with credit metrics (credit_score, financial_ratios, etc.)
            
        Returns:
            Dictionary with rating, score, and rationale
        """
        # Extract metrics
        credit_score = credit_data.get("credit_score", 0)
        dscr = credit_data.get("debt_service_coverage_ratio", 0)
        leverage = credit_data.get("leverage_ratio", 0)
        net_worth = credit_data.get("net_worth", 0)
        cash_flow = credit_data.get("free_cash_flow", 0)
        
        # Calculate composite credit score (0-100)
        score = 0
        
        # Credit score component (40% weight)
        if credit_score >= 750:
            score += 40
        elif credit_score >= 700:
            score += 35
        elif credit_score >= 650:
            score += 30
        elif credit_score >= 600:
            score += 25
        else:
            score += 15
        
        # DSCR component (25% weight)
        if dscr >= 2.0:
            score += 25
        elif dscr >= 1.5:
            score += 20
        elif dscr >= 1.25:
            score += 15
        elif dscr >= 1.0:
            score += 10
        else:
            score += 5
        
        # Leverage component (20% weight)
        if leverage <= 0.30:
            score += 20
        elif leverage <= 0.50:
            score += 15
        elif leverage <= 0.70:
            score += 10
        else:
            score += 5
        
        # Financial strength component (15% weight)
        if net_worth > 0 and cash_flow > 0:
            score += 15
        elif net_worth > 0:
            score += 10
        else:
            score += 5
        
        # Map score to rating
        if score >= 90:
            rating = "AAA"
            internal_rating = 1
        elif score >= 80:
            rating = "AA"
            internal_rating = 2
        elif score >= 70:
            rating = "A"
            internal_rating = 3
        elif score >= 60:
            rating = "BBB"
            internal_rating = 4
        elif score >= 50:
            rating = "BB"
            internal_rating = 5
        elif score >= 40:
            rating = "B"
            internal_rating = 6
        elif score >= 30:
            rating = "CCC"
            internal_rating = 7
        elif score >= 20:
            rating = "CC"
            internal_rating = 8
        elif score >= 10:
            rating = "C"
            internal_rating = 9
        else:
            rating = "D"
            internal_rating = 10
        
        # Estimate PD from rating
        pd_estimates = {
            "AAA": 0.0001, "AA": 0.0005, "A": 0.002, "BBB": 0.01,
            "BB": 0.05, "B": 0.15, "CCC": 0.30, "CC": 0.50, "C": 0.75, "D": 1.0
        }
        estimated_pd = pd_estimates.get(rating, 0.01)
        
        return {
            "rating": rating,
            "internal_rating": internal_rating,
            "credit_score": score,
            "estimated_pd": estimated_pd,
            "rationale": f"Composite score: {score}/100 based on credit score, DSCR, leverage, and financial strength"
        }
    
    def validate_collateral(
        self,
        collateral_data: Dict[str, Any],
        facility_amount: Decimal
    ) -> Dict[str, Any]:
        """
        Validate collateral adequacy.
        
        Args:
            collateral_data: Dictionary with collateral information
            facility_amount: Facility amount to be secured
            
        Returns:
            Dictionary with validation results
        """
        collateral_value = Decimal(str(collateral_data.get("collateral_value", 0)))
        collateral_type = collateral_data.get("collateral_type", "unknown")
        valuation_date = collateral_data.get("valuation_date")
        valuation_age_months = collateral_data.get("valuation_age_months", 0)
        
        # Calculate collateral coverage ratio
        if facility_amount > 0:
            coverage_ratio = collateral_value / facility_amount
        else:
            coverage_ratio = Decimal("0")
        
        # Validation results
        is_adequate = coverage_ratio >= Decimal("1.20")  # 120% minimum coverage
        is_valuation_current = valuation_age_months <= 12  # Within 12 months
        is_eligible_type = collateral_type not in ["intangible_assets", "goodwill", "speculative_investments"]
        
        # Calculate volatility adjustment if provided
        volatility = collateral_data.get("collateral_value_volatility", 0)
        adjusted_coverage = coverage_ratio * (1 - volatility) if volatility > 0 else coverage_ratio
        
        return {
            "is_adequate": is_adequate,
            "coverage_ratio": float(coverage_ratio),
            "adjusted_coverage_ratio": float(adjusted_coverage),
            "is_valuation_current": is_valuation_current,
            "is_eligible_type": is_eligible_type,
            "collateral_value": float(collateral_value),
            "facility_amount": float(facility_amount),
            "validation_status": "pass" if (is_adequate and is_valuation_current and is_eligible_type) else "fail",
            "issues": [
                "Insufficient collateral coverage" if not is_adequate else None,
                "Outdated collateral valuation" if not is_valuation_current else None,
                "Ineligible collateral type" if not is_eligible_type else None
            ]
        }
    
    def calculate_portfolio_concentration(
        self,
        portfolio: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate portfolio concentration metrics.
        
        Args:
            portfolio: List of facility dictionaries with sector, amount, etc.
            
        Returns:
            Dictionary with concentration metrics
        """
        total_exposure = Decimal("0")
        sector_exposures = {}
        borrower_exposures = {}
        
        for facility in portfolio:
            amount = Decimal(str(facility.get("amount", 0)))
            total_exposure += amount
            
            sector = facility.get("sector", "unknown")
            sector_exposures[sector] = sector_exposures.get(sector, Decimal("0")) + amount
            
            borrower_id = facility.get("borrower_id", "unknown")
            borrower_exposures[borrower_id] = borrower_exposures.get(borrower_id, Decimal("0")) + amount
        
        # Calculate sector concentrations
        sector_concentrations = {}
        for sector, exposure in sector_exposures.items():
            if total_exposure > 0:
                concentration = exposure / total_exposure
                sector_concentrations[sector] = float(concentration)
        
        # Calculate borrower concentrations
        borrower_concentrations = {}
        for borrower_id, exposure in borrower_exposures.items():
            if total_exposure > 0:
                concentration = exposure / total_exposure
                borrower_concentrations[borrower_id] = float(concentration)
        
        # Find maximum concentrations
        max_sector_concentration = max(sector_concentrations.values()) if sector_concentrations else 0
        max_borrower_concentration = max(borrower_concentrations.values()) if borrower_concentrations else 0
        
        return {
            "total_exposure": float(total_exposure),
            "sector_concentrations": sector_concentrations,
            "borrower_concentrations": borrower_concentrations,
            "max_sector_concentration": max_sector_concentration,
            "max_borrower_concentration": max_borrower_concentration,
            "sector_count": len(sector_concentrations),
            "borrower_count": len(borrower_concentrations)
        }
