"""Financial Impact Calculation Engine for CreditNexus.

Calculates the real-world monetary consequences of sustainability covenant breaches,
linking satellite-verified risk directly to P&L impact through margin ratchets.
"""

from typing import Dict, Any, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


def calculate_breach_impact(
    principal: float,
    base_spread_bps: int,
    penalty_spread_bps: int
) -> Dict[str, Any]:
    """
    Calculates the financial impact of a sustainability breach.
    
    This is the "Money Shot" - showing exactly how much the borrower loses
    when a covenant is breached, linking satellite data directly to P&L.
    
    Args:
        principal: The loan principal amount in dollars
        base_spread_bps: The base interest rate spread in basis points
        penalty_spread_bps: The penalty spread after breach in basis points
    
    Returns:
        Dictionary with financial impact details including annualized penalty cost
    """
    spread_diff_bps = penalty_spread_bps - base_spread_bps
    
    # Convert BPS to decimal (1 bp = 0.0001 = 0.01%)
    annual_cost_increase = principal * (spread_diff_bps * 0.0001)
    
    # Monthly and daily breakdown for granularity
    monthly_cost_increase = annual_cost_increase / 12
    daily_cost_increase = annual_cost_increase / 365
    
    return {
        "status": "BREACH",
        "spread_adjustment_bps": spread_diff_bps,
        "spread_adjustment_display": f"+{spread_diff_bps} bps",
        "base_spread_bps": base_spread_bps,
        "new_spread_bps": penalty_spread_bps,
        "base_rate_pct": base_spread_bps / 100,
        "new_rate_pct": penalty_spread_bps / 100,
        "annualized_penalty": round(annual_cost_increase, 2),
        "monthly_penalty": round(monthly_cost_increase, 2),
        "daily_penalty": round(daily_cost_increase, 2),
        "principal": principal,
        "message": f"Covenant Breach triggers automatic +{spread_diff_bps} bps margin ratchet."
    }


def calculate_margin_ratchet(
    ndvi_score: float,
    spt_threshold: float,
    principal: float,
    base_spread_bps: int = 200,  # Default 2.00%
    step_bps: int = 25  # Default penalty step: 25 bps
) -> Dict[str, Any]:
    """
    Full margin ratchet calculation based on NDVI verification result.
    
    The margin ratchet mechanism adjusts interest rates based on
    sustainability performance relative to agreed thresholds.
    
    Args:
        ndvi_score: The verified NDVI score (0.0 to 1.0)
        spt_threshold: The Sustainability Performance Target threshold
        principal: Loan principal amount
        base_spread_bps: Base spread in basis points (default 200 = 2%)
        step_bps: Penalty increment per threshold breach (default 25 bps)
    
    Returns:
        Complete margin ratchet calculation including financial impact
    """
    # Determine compliance status
    breach_margin = spt_threshold - ndvi_score
    
    if ndvi_score >= spt_threshold:
        # Compliant - no penalty, possible discount
        compliance_status = "COMPLIANT"
        penalty_bps = 0
        
        # Optional: Provide discount for exceeding threshold
        if ndvi_score >= spt_threshold + 0.1:
            penalty_bps = -step_bps  # Discount!
            compliance_status = "EXCEEDS_TARGET"
            
    elif ndvi_score >= spt_threshold - 0.1:
        # Warning zone - minor penalty
        compliance_status = "WARNING"
        penalty_bps = step_bps
    else:
        # Full breach - major penalty
        compliance_status = "BREACH"
        # Calculate penalty tiers based on severity
        severity_levels = int((spt_threshold - ndvi_score) / 0.1)
        penalty_bps = min(step_bps * severity_levels, step_bps * 4)  # Cap at 4x
    
    # Calculate new spread
    new_spread_bps = base_spread_bps + penalty_bps
    
    # Calculate financial impact
    annualized_change = principal * (penalty_bps * 0.0001)
    
    result = {
        "compliance_status": compliance_status,
        "ndvi_score": round(ndvi_score, 4),
        "spt_threshold": spt_threshold,
        "breach_margin": round(breach_margin, 4),
        "base_spread_bps": base_spread_bps,
        "penalty_bps": penalty_bps,
        "new_spread_bps": new_spread_bps,
        "base_rate_pct": f"{base_spread_bps / 100:.2f}%",
        "new_rate_pct": f"{new_spread_bps / 100:.2f}%",
        "spread_adjustment_display": f"{'+' if penalty_bps >= 0 else ''}{penalty_bps} bps",
        "annualized_impact": round(annualized_change, 2),
        "monthly_impact": round(annualized_change / 12, 2),
        "principal": principal,
        "is_breach": compliance_status in ["BREACH", "WARNING"],
        "is_penalty": penalty_bps > 0,
        "is_discount": penalty_bps < 0,
    }
    
    # Add human-readable message
    if compliance_status == "COMPLIANT":
        result["message"] = "Asset meets sustainability performance targets. No margin adjustment."
    elif compliance_status == "EXCEEDS_TARGET":
        result["message"] = f"Asset exceeds SPT by {round(ndvi_score - spt_threshold, 2)}. Discount of {abs(penalty_bps)} bps applied."
    elif compliance_status == "WARNING":
        result["message"] = f"Asset near threshold. Warning zone penalty of +{penalty_bps} bps applied."
    else:
        result["message"] = f"Covenant Breach: NDVI {ndvi_score:.2f} < {spt_threshold}. Penalty of +{penalty_bps} bps triggered."
    
    return result


def generate_spread_schedule_cdm(
    base_spread_bps: int,
    penalty_spread_bps: int,
    trigger_event: str = "ESG_BREACH"
) -> Dict[str, Any]:
    """
    Generate CDM-compliant spread schedule for audit trail.
    
    Returns the Before/After state for the smart contract visualization.
    """
    before_state = {
        "spreadSchedule": {
            "initialValue": base_spread_bps / 10000,  # Convert to decimal (2.00% = 0.0200)
            "type": "SustainabilityLinked",
            "effectiveDate": None,
            "step": None
        }
    }
    
    after_state = {
        "spreadSchedule": {
            "initialValue": penalty_spread_bps / 10000,  # e.g., 2.25% = 0.0225
            "type": "SustainabilityLinked",
            "effectiveDate": "T+2",  # Settlement convention
            "step": {
                "triggerEvent": trigger_event,
                "adjustmentBps": penalty_spread_bps - base_spread_bps,
                "evidence": {
                    "source": "Sentinel-2_MSI",
                    "metric": "NDVI",
                    "verified": True
                }
            }
        }
    }
    
    return {
        "before": before_state,
        "after": after_state,
        "diff": {
            "field": "spreadSchedule.initialValue",
            "oldValue": base_spread_bps / 10000,
            "newValue": penalty_spread_bps / 10000,
            "changeType": "INCREASE",
            "trigger": trigger_event
        }
    }
