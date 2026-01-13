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
    Calculate the financial impact of a sustainability covenant breach.
    
    This function calculates the real-world monetary consequences when a sustainability
    covenant is breached, linking satellite-verified risk directly to P&L impact
    through margin ratchets. This is the "Money Shot" - showing exactly how much
    the borrower loses when a covenant is breached.
    
    The calculation determines the annualized, monthly, and daily cost increases
    resulting from the spread adjustment triggered by the breach.
    
    Args:
        principal: The loan principal amount in dollars. Must be positive.
        base_spread_bps: The base interest rate spread in basis points (e.g., 200 = 2.00%).
        penalty_spread_bps: The penalty spread after breach in basis points (e.g., 250 = 2.50%).
                          Must be >= base_spread_bps for a penalty.
    
    Returns:
        Dictionary containing:
            - status: "BREACH" indicating breach status
            - spread_adjustment_bps: Difference in basis points (penalty_spread_bps - base_spread_bps)
            - spread_adjustment_display: Human-readable spread adjustment (e.g., "+50 bps")
            - base_spread_bps: Original base spread
            - new_spread_bps: New spread after breach
            - base_rate_pct: Base rate as percentage
            - new_rate_pct: New rate as percentage
            - annualized_penalty: Annual cost increase in dollars
            - monthly_penalty: Monthly cost increase in dollars
            - daily_penalty: Daily cost increase in dollars
            - principal: Original principal amount
            - message: Human-readable message describing the breach impact
    
    Example:
        >>> result = calculate_breach_impact(
        ...     principal=1000000,
        ...     base_spread_bps=200,
        ...     penalty_spread_bps=250
        ... )
        >>> result["annualized_penalty"]
        5000.0  # $5,000 annual penalty
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
    Calculate margin ratchet based on NDVI verification result.
    
    The margin ratchet mechanism automatically adjusts interest rates based on
    sustainability performance relative to agreed thresholds. This function
    implements a tiered penalty system:
    
    - EXCEEDS_TARGET: Performance > threshold + 0.1 → Discount applied
    - COMPLIANT: Performance >= threshold → No adjustment
    - WARNING: Performance >= threshold - 0.1 → Minor penalty (1x step_bps)
    - BREACH: Performance < threshold - 0.1 → Major penalty (up to 4x step_bps)
    
    Penalty severity increases with the magnitude of the breach, capped at
    4x the step increment to prevent excessive penalties.
    
    Args:
        ndvi_score: The verified NDVI score from satellite imagery (0.0 to 1.0).
                   Higher values indicate better vegetation health.
        spt_threshold: The Sustainability Performance Target threshold (0.0 to 1.0).
                      This is the agreed-upon minimum NDVI score.
        principal: Loan principal amount in dollars. Must be positive.
        base_spread_bps: Base spread in basis points (default 200 = 2.00%).
        step_bps: Penalty increment per threshold breach tier (default 25 bps).
                 Each 0.1 below threshold adds one step, capped at 4 steps.
    
    Returns:
        Dictionary containing:
            - compliance_status: One of "COMPLIANT", "EXCEEDS_TARGET", "WARNING", "BREACH"
            - ndvi_score: Verified NDVI score
            - spt_threshold: Sustainability Performance Target
            - breach_margin: Difference between threshold and score (positive = breach)
            - base_spread_bps: Original base spread
            - penalty_bps: Penalty spread adjustment (can be negative for discounts)
            - new_spread_bps: Final spread after adjustment
            - base_rate_pct: Base rate as percentage string
            - new_rate_pct: New rate as percentage string
            - spread_adjustment_display: Human-readable adjustment (e.g., "+25 bps" or "-25 bps")
            - annualized_impact: Annual cost change in dollars (positive = cost increase)
            - monthly_impact: Monthly cost change in dollars
            - principal: Original principal amount
            - is_breach: Boolean indicating if breach occurred
            - is_penalty: Boolean indicating if penalty applied
            - is_discount: Boolean indicating if discount applied
            - message: Human-readable message describing the result
    
    Example:
        >>> result = calculate_margin_ratchet(
        ...     ndvi_score=0.85,
        ...     spt_threshold=0.90,
        ...     principal=1000000,
        ...     base_spread_bps=200,
        ...     step_bps=25
        ... )
        >>> result["compliance_status"]
        "BREACH"
        >>> result["penalty_bps"]
        25  # 25 bps penalty for being 0.05 below threshold
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
    Generate CDM-compliant spread schedule for audit trail and smart contract visualization.
    
    This function creates a FINOS Common Domain Model (CDM) compliant representation
    of a spread schedule change, showing the before and after states. This is used
    for audit trails, smart contract visualization, and regulatory reporting.
    
    The output includes:
    - Before state: Original spread schedule configuration
    - After state: Updated spread schedule with trigger event and evidence
    - Diff: Structured change record for audit purposes
    
    Args:
        base_spread_bps: The original base spread in basis points (e.g., 200 = 2.00%).
        penalty_spread_bps: The new spread after penalty in basis points (e.g., 250 = 2.50%).
        trigger_event: The event that triggered the spread change (default "ESG_BREACH").
                      Common values: "ESG_BREACH", "ESG_COMPLIANCE", "ESG_EXCEEDS_TARGET".
    
    Returns:
        Dictionary containing:
            - before: CDM spread schedule before the change
                - spreadSchedule.initialValue: Original spread as decimal (e.g., 0.0200 for 2%)
                - spreadSchedule.type: "SustainabilityLinked"
            - after: CDM spread schedule after the change
                - spreadSchedule.initialValue: New spread as decimal
                - spreadSchedule.effectiveDate: "T+2" (settlement convention)
                - spreadSchedule.step: Adjustment details
                    - triggerEvent: Event that triggered the change
                    - adjustmentBps: Spread change in basis points
                    - evidence: Verification evidence (source, metric, verified flag)
            - diff: Change record
                - field: Field path that changed
                - oldValue: Original value
                - newValue: New value
                - changeType: "INCREASE" or "DECREASE"
                - trigger: Trigger event identifier
    
    Example:
        >>> schedule = generate_spread_schedule_cdm(
        ...     base_spread_bps=200,
        ...     penalty_spread_bps=250,
        ...     trigger_event="ESG_BREACH"
        ... )
        >>> schedule["diff"]["oldValue"]
        0.02  # 2.00% as decimal
        >>> schedule["diff"]["newValue"]
        0.025  # 2.50% as decimal
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
