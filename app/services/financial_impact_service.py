"""Financial Impact Service for CreditNexus.

This service wraps the financial_engine.py functions to provide a clean
service layer interface for calculating financial impacts of sustainability
covenant breaches and margin ratchets.
"""

import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from app.financial_engine import (
    calculate_breach_impact,
    calculate_margin_ratchet,
    generate_spread_schedule_cdm
)

logger = logging.getLogger(__name__)


class FinancialImpactService:
    """Service for calculating financial impacts of sustainability covenant breaches."""

    def calculate_breach_impact(
        self,
        principal: float,
        base_spread_bps: int,
        penalty_spread_bps: int
    ) -> Dict[str, Any]:
        """
        Calculate the financial impact of a sustainability breach.
        
        This method wraps the financial_engine.calculate_breach_impact function
        to provide a service layer interface.
        
        Args:
            principal: The loan principal amount in dollars
            base_spread_bps: The base interest rate spread in basis points
            penalty_spread_bps: The penalty spread after breach in basis points
        
        Returns:
            Dictionary with financial impact details including annualized penalty cost
        
        Raises:
            ValueError: If inputs are invalid
        """
        try:
            logger.info(
                f"Calculating breach impact: principal=${principal:,.0f}, "
                f"base={base_spread_bps}bps, penalty={penalty_spread_bps}bps"
            )
            
            result = calculate_breach_impact(
                principal=principal,
                base_spread_bps=base_spread_bps,
                penalty_spread_bps=penalty_spread_bps
            )
            
            logger.info(
                f"Breach impact calculated: annualized_penalty=${result.get('annualized_penalty', 0):,.2f}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating breach impact: {e}")
            raise ValueError(f"Failed to calculate breach impact: {str(e)}")

    def calculate_margin_ratchet(
        self,
        ndvi_score: float,
        spt_threshold: float,
        principal: float,
        base_spread_bps: int = 200,
        step_bps: int = 25
    ) -> Dict[str, Any]:
        """
        Calculate margin ratchet based on NDVI verification result.
        
        This method wraps the financial_engine.calculate_margin_ratchet function
        to provide a service layer interface.
        
        Args:
            ndvi_score: The verified NDVI score from satellite imagery (0.0 to 1.0)
            spt_threshold: The Sustainability Performance Target threshold (0.0 to 1.0)
            principal: The loan principal amount in dollars
            base_spread_bps: Base spread in basis points (default 200 = 2.00%)
            step_bps: Penalty increment per threshold breach tier (default 25 bps)
        
        Returns:
            Dictionary with margin ratchet calculation results
        
        Raises:
            ValueError: If inputs are invalid
        """
        try:
            logger.info(
                f"Calculating margin ratchet: ndvi={ndvi_score:.3f}, "
                f"spt={spt_threshold:.3f}, principal=${principal:,.0f}, "
                f"base={base_spread_bps}bps"
            )
            
            result = calculate_margin_ratchet(
                ndvi_score=ndvi_score,
                spt_threshold=spt_threshold,
                principal=principal,
                base_spread_bps=base_spread_bps,
                step_bps=step_bps
            )
            
            logger.info(
                f"Margin ratchet calculated: status={result.get('compliance_status')}, "
                f"penalty={result.get('penalty_bps', 0)}bps"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating margin ratchet: {e}")
            raise ValueError(f"Failed to calculate margin ratchet: {str(e)}")

    def generate_spread_schedule_cdm(
        self,
        base_spread_bps: int,
        performance_data: list,
        ratchet_threshold_pct: float = 0.95,
        max_penalty_bps: int = 50
    ) -> Dict[str, Any]:
        """
        Generate CDM-compliant spread schedule based on performance data.
        
        This method wraps the financial_engine.generate_spread_schedule_cdm function
        to provide a service layer interface.
        
        Args:
            base_spread_bps: The base interest rate spread in basis points
            performance_data: List of performance records with 'date' and 'performance_pct' keys
            ratchet_threshold_pct: Performance threshold below which ratchet applies (default 0.95)
            max_penalty_bps: Maximum penalty spread in basis points (default 50)
        
        Returns:
            Dictionary with CDM-compliant spread schedule
        
        Raises:
            ValueError: If inputs are invalid
        """
        try:
            logger.info(
                f"Generating spread schedule CDM: base={base_spread_bps}bps, "
                f"performance_records={len(performance_data)}"
            )
            
            result = generate_spread_schedule_cdm(
                base_spread_bps=base_spread_bps,
                performance_data=performance_data,
                ratchet_threshold_pct=ratchet_threshold_pct,
                max_penalty_bps=max_penalty_bps
            )
            
            logger.info("Spread schedule CDM generated successfully")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating spread schedule CDM: {e}")
            raise ValueError(f"Failed to generate spread schedule CDM: {str(e)}")


# Global service instance
_financial_impact_service: Optional[FinancialImpactService] = None


def get_financial_impact_service() -> FinancialImpactService:
    """Get or create the global FinancialImpactService instance.
    
    Returns:
        FinancialImpactService instance
    """
    global _financial_impact_service
    if _financial_impact_service is None:
        _financial_impact_service = FinancialImpactService()
    return _financial_impact_service
