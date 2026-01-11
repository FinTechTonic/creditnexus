"""
Credit Risk Data Models for CreditNexus.

Defines Pydantic models for credit risk assessments, ratings, and metrics.
"""

from decimal import Decimal
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class RiskRating(str, Enum):
    """External risk rating scale (S&P, Moody's, Fitch style)."""
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    BB_PLUS = "BB+"
    BB = "BB"
    BB_MINUS = "BB-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    CCC_PLUS = "CCC+"
    CCC = "CCC"
    CCC_MINUS = "CCC-"
    CC = "CC"
    C = "C"
    D = "D"


class InternalRating(int, Enum):
    """Internal risk rating scale (1-10)."""
    RATING_1 = 1  # AAA equivalent
    RATING_2 = 2  # AA equivalent
    RATING_3 = 3  # A equivalent
    RATING_4 = 4  # BBB equivalent
    RATING_5 = 5  # BB equivalent
    RATING_6 = 6  # B equivalent
    RATING_7 = 7  # CCC equivalent
    RATING_8 = 8  # CC equivalent
    RATING_9 = 9  # C equivalent
    RATING_10 = 10  # D equivalent


class RatingAgency(str, Enum):
    """Credit rating agency."""
    STANDARD_AND_POORS = "S&P"
    MOODYS = "Moody's"
    FITCH = "Fitch"
    INTERNAL = "Internal"
    OTHER = "Other"


class RiskModelApproach(str, Enum):
    """Credit risk model approach."""
    STANDARDIZED = "standardized"
    IRB_FOUNDATION = "irb_foundation"
    IRB_ADVANCED = "irb_advanced"
    INTERNAL = "internal"


class CreditRiskAssessment(BaseModel):
    """Credit risk assessment result."""
    
    # Assessment metadata
    assessment_id: str = Field(..., description="Unique assessment identifier")
    transaction_id: str = Field(..., description="Transaction/deal identifier")
    assessment_date: datetime = Field(default_factory=datetime.utcnow, description="Assessment timestamp")
    assessed_by: Optional[str] = Field(None, description="User/system that performed assessment")
    
    # Risk ratings
    external_rating: Optional[RiskRating] = Field(None, description="External credit rating (AAA-D)")
    internal_rating: Optional[InternalRating] = Field(None, description="Internal credit rating (1-10)")
    rating_agency: Optional[RatingAgency] = Field(None, description="Rating agency")
    rating_date: Optional[date] = Field(None, description="Date of rating assignment")
    
    # Probability metrics
    probability_of_default: float = Field(..., ge=0.0, le=1.0, description="Probability of default (0-1)")
    loss_given_default: float = Field(..., ge=0.0, le=1.0, description="Loss given default (0-1)")
    exposure_at_default: Decimal = Field(..., ge=0, description="Exposure at default amount")
    
    # Risk-weighted assets and capital
    risk_weighted_assets: Decimal = Field(..., ge=0, description="Risk-weighted assets (RWA)")
    capital_requirement: Decimal = Field(..., ge=0, description="Minimum capital requirement (8% of RWA)")
    tier1_capital_requirement: Decimal = Field(..., ge=0, description="Tier 1 capital requirement (6% of RWA)")
    
    # Leverage and liquidity
    leverage_ratio: Optional[Decimal] = Field(None, ge=0, description="Leverage ratio (Tier 1 / Total Exposure)")
    liquidity_coverage_ratio: Optional[Decimal] = Field(None, ge=0, description="Liquidity coverage ratio")
    
    # Creditworthiness metrics
    credit_score: Optional[float] = Field(None, ge=0, le=100, description="Composite credit score (0-100)")
    debt_service_coverage_ratio: Optional[float] = Field(None, ge=0, description="Debt service coverage ratio")
    borrower_leverage_ratio: Optional[float] = Field(None, ge=0, description="Borrower leverage ratio")
    
    # Collateral information
    collateral_coverage_ratio: Optional[float] = Field(None, ge=0, description="Collateral coverage ratio")
    collateral_type: Optional[str] = Field(None, description="Type of collateral")
    collateral_valuation_date: Optional[date] = Field(None, description="Collateral valuation date")
    
    # Model information
    risk_model_approach: RiskModelApproach = Field(
        default=RiskModelApproach.STANDARDIZED,
        description="Risk model approach used"
    )
    model_validation_status: Optional[str] = Field(None, description="Model validation status")
    model_version: Optional[str] = Field(None, description="Model version identifier")
    
    # Assessment results
    assessment_status: str = Field(default="completed", description="Assessment status")
    assessment_rationale: Optional[str] = Field(None, description="Assessment rationale and notes")
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional assessment metadata")


class CreditRiskModelInterface:
    """
    Abstract interface for credit risk models.
    
    This interface allows CreditNexus to support multiple credit risk models:
    - Internal rating models
    - External rating mappings (S&P, Moody's, Fitch)
    - Custom proprietary models
    """
    
    def calculate_pd(
        self,
        borrower_data: Dict[str, Any],
        facility_data: Dict[str, Any]
    ) -> float:
        """
        Calculate probability of default.
        
        Args:
            borrower_data: Borrower financial and credit data
            facility_data: Facility-specific data
            
        Returns:
            Probability of default (0-1)
        """
        raise NotImplementedError
    
    def calculate_lgd(
        self,
        collateral_data: Dict[str, Any],
        facility_data: Dict[str, Any]
    ) -> float:
        """
        Calculate loss given default.
        
        Args:
            collateral_data: Collateral information
            facility_data: Facility-specific data
            
        Returns:
            Loss given default (0-1)
        """
        raise NotImplementedError
    
    def assign_rating(
        self,
        credit_data: Dict[str, Any]
    ) -> str:
        """
        Assign credit rating.
        
        Args:
            credit_data: Credit assessment data
            
        Returns:
            Credit rating (AAA-D or 1-10)
        """
        raise NotImplementedError


class InternalRatingModel(CreditRiskModelInterface):
    """Internal rating model implementation."""
    
    def __init__(self, credit_risk_service: Any):
        """
        Initialize internal rating model.
        
        Args:
            credit_risk_service: CreditRiskService instance
        """
        self.credit_risk_service = credit_risk_service
    
    def calculate_pd(
        self,
        borrower_data: Dict[str, Any],
        facility_data: Dict[str, Any]
    ) -> float:
        """Calculate PD using internal model."""
        # Use creditworthiness assessment to estimate PD
        creditworthiness = self.credit_risk_service.assess_creditworthiness(borrower_data)
        return creditworthiness.get("estimated_pd", 0.01)
    
    def calculate_lgd(
        self,
        collateral_data: Dict[str, Any],
        facility_data: Dict[str, Any]
    ) -> float:
        """Calculate LGD using internal model."""
        # Default LGD based on collateral coverage
        collateral_coverage = collateral_data.get("collateral_coverage_ratio", 0)
        if collateral_coverage >= 1.5:
            return 0.25  # 25% LGD with strong collateral
        elif collateral_coverage >= 1.2:
            return 0.35  # 35% LGD with adequate collateral
        else:
            return 0.45  # 45% LGD with insufficient collateral
    
    def assign_rating(
        self,
        credit_data: Dict[str, Any]
    ) -> str:
        """Assign internal rating (1-10)."""
        creditworthiness = self.credit_risk_service.assess_creditworthiness(credit_data)
        internal_rating = creditworthiness.get("internal_rating", 5)
        return str(internal_rating)


class ExternalRatingMapper(CreditRiskModelInterface):
    """Maps external ratings (S&P, Moody's, Fitch) to PD/LGD."""
    
    # PD mapping from external ratings
    RATING_TO_PD = {
        "AAA": 0.0001, "AA+": 0.0002, "AA": 0.0005, "AA-": 0.001,
        "A+": 0.0015, "A": 0.002, "A-": 0.003,
        "BBB+": 0.005, "BBB": 0.01, "BBB-": 0.015,
        "BB+": 0.02, "BB": 0.05, "BB-": 0.08,
        "B+": 0.10, "B": 0.15, "B-": 0.20,
        "CCC+": 0.25, "CCC": 0.30, "CCC-": 0.40,
        "CC": 0.50, "C": 0.75, "D": 1.0
    }
    
    # LGD mapping (varies by asset class and rating)
    RATING_TO_LGD = {
        "AAA": 0.20, "AA": 0.25, "A": 0.30,
        "BBB": 0.35, "BB": 0.40, "B": 0.45,
        "CCC": 0.50, "CC": 0.60, "C": 0.70, "D": 1.0
    }
    
    def __init__(self, rating_agency: RatingAgency = RatingAgency.STANDARD_AND_POORS):
        """
        Initialize external rating mapper.
        
        Args:
            rating_agency: Rating agency to use
        """
        self.rating_agency = rating_agency
    
    def calculate_pd(
        self,
        borrower_data: Dict[str, Any],
        facility_data: Dict[str, Any]
    ) -> float:
        """Calculate PD from external rating."""
        rating = borrower_data.get("external_rating")
        if not rating:
            return 0.01  # Default PD
        
        # Normalize rating (remove +/- modifiers for lookup)
        base_rating = rating.replace("+", "").replace("-", "")
        return self.RATING_TO_PD.get(base_rating, 0.01)
    
    def calculate_lgd(
        self,
        collateral_data: Dict[str, Any],
        facility_data: Dict[str, Any]
    ) -> float:
        """Calculate LGD from external rating and collateral."""
        rating = facility_data.get("borrower_rating", "BBB")
        base_rating = rating.replace("+", "").replace("-", "")
        base_lgd = self.RATING_TO_LGD.get(base_rating, 0.45)
        
        # Adjust for collateral
        collateral_coverage = collateral_data.get("collateral_coverage_ratio", 0)
        if collateral_coverage >= 1.5:
            base_lgd *= 0.7  # Reduce LGD by 30% with strong collateral
        elif collateral_coverage >= 1.2:
            base_lgd *= 0.85  # Reduce LGD by 15% with adequate collateral
        
        return min(1.0, base_lgd)
    
    def assign_rating(
        self,
        credit_data: Dict[str, Any]
    ) -> str:
        """Return external rating."""
        return credit_data.get("external_rating", "BBB")
