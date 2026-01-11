"""
Credit Risk API Routes for CreditNexus.

Provides endpoints for credit risk assessment, capital requirements,
portfolio analysis, and stress testing.
"""

import logging
from typing import Dict, Any, Optional, List
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.auth.jwt_auth import require_auth, get_current_user
from app.db.models import User, Deal, Document
from app.services.credit_risk_service import CreditRiskService
from app.services.credit_risk_mapper import CreditRiskMapper
from app.services.policy_service import PolicyService
from app.services.policy_engine_factory import get_policy_engine
from app.models.cdm import CreditAgreement
from app.models.credit_risk import CreditRiskAssessment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/credit-risk", tags=["credit-risk"])


# Request/Response Models

class CreditRiskAssessRequest(BaseModel):
    """Request model for credit risk assessment."""
    deal_id: Optional[int] = Field(None, description="Deal ID to assess")
    document_id: Optional[int] = Field(None, description="Document ID with CDM data")
    credit_agreement: Optional[Dict[str, Any]] = Field(None, description="CDM CreditAgreement data (optional)")
    additional_context: Optional[Dict[str, Any]] = Field(None, description="Additional context (borrower financials, etc.)")


class CapitalRequirementsRequest(BaseModel):
    """Request model for capital requirements calculation."""
    risk_weighted_assets: float = Field(..., ge=0, description="Risk-weighted assets")
    capital_ratio: Optional[float] = Field(0.08, ge=0, le=1, description="Capital ratio (default: 8%)")


class PortfolioSummaryRequest(BaseModel):
    """Request model for portfolio summary."""
    deal_ids: Optional[List[int]] = Field(None, description="List of deal IDs (optional, uses all deals if not provided)")
    user_id: Optional[int] = Field(None, description="Filter by user ID")


class StressTestRequest(BaseModel):
    """Request model for stress testing."""
    deal_id: int = Field(..., description="Deal ID to stress test")
    stress_scenario: str = Field(..., description="Stress scenario name (e.g., 'recession', 'market_crash')")
    pd_shock: Optional[float] = Field(None, ge=0, le=1, description="PD shock multiplier (e.g., 1.5 for 50% increase)")
    lgd_shock: Optional[float] = Field(None, ge=0, le=1, description="LGD shock multiplier")
    market_value_shock: Optional[float] = Field(None, description="Market value shock (percentage, e.g., -0.2 for 20% decrease)")


# API Endpoints

@router.post("/assess", response_model=Dict[str, Any])
async def assess_credit_risk(
    request: CreditRiskAssessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Assess credit risk for a deal or credit agreement.
    
    Args:
        request: CreditRiskAssessRequest with deal_id, document_id, or credit_agreement
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Credit risk assessment results including ratings, PD/LGD/EAD, RWA, capital requirements
    """
    try:
        credit_risk_service = CreditRiskService()
        credit_risk_mapper = CreditRiskMapper()
        policy_service = PolicyService(get_policy_engine())
        
        credit_agreement = None
        additional_context = request.additional_context or {}
        
        # Load credit agreement from various sources
        if request.deal_id:
            deal = db.query(Deal).filter(Deal.id == request.deal_id).first()
            if not deal:
                raise HTTPException(status_code=404, detail=f"Deal {request.deal_id} not found")
            
            # Check user access
            if deal.applicant_id != current_user.id and current_user.role != "admin":
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            # Get document with CDM data
            document = db.query(Document).filter(
                Document.deal_id == request.deal_id,
                Document.source_cdm_data.isnot(None)
            ).first()
            
            if document and document.source_cdm_data:
                credit_agreement = CreditAgreement(**document.source_cdm_data)
                additional_context.update({
                    "deal_id": deal.deal_id,
                    "deal_type": deal.deal_type,
                    "status": deal.status
                })
            else:
                # Use deal data as context
                additional_context.update(deal.deal_data or {})
                additional_context.update({
                    "deal_id": deal.deal_id,
                    "deal_type": deal.deal_type,
                    "status": deal.status
                })
        
        elif request.document_id:
            document = db.query(Document).filter(Document.id == request.document_id).first()
            if not document:
                raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found")
            
            # Check user access
            if document.uploaded_by != current_user.id and current_user.role != "admin":
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            if document.source_cdm_data:
                credit_agreement = CreditAgreement(**document.source_cdm_data)
            else:
                raise HTTPException(status_code=400, detail="Document does not contain CDM data")
        
        elif request.credit_agreement:
            credit_agreement = CreditAgreement(**request.credit_agreement)
        
        else:
            raise HTTPException(status_code=400, detail="Must provide deal_id, document_id, or credit_agreement")
        
        # Perform credit risk assessment
        assessment = policy_service.evaluate_credit_risk(
            credit_agreement=credit_agreement,
            additional_context=additional_context
        )
        
        # Generate CDM event
        from app.models.cdm_events import generate_cdm_credit_risk_assessment
        
        cdm_event = generate_cdm_credit_risk_assessment(
            transaction_id=additional_context.get("deal_id") or credit_agreement.deal_id or "unknown",
            risk_rating=assessment.get("rating", "BBB"),
            probability_of_default=assessment.get("probability_of_default", 0.01),
            loss_given_default=assessment.get("loss_given_default", 0.45),
            exposure_at_default=assessment.get("exposure_at_default", 0.0),
            risk_weighted_assets=assessment.get("risk_weighted_assets", 0.0),
            capital_requirement=assessment.get("capital_requirement", 0.0),
            additional_metrics={
                "currency": assessment.get("currency", "USD"),
                "rating_agency": "Internal",
                "rating_type": "internal",
                "risk_model_approach": assessment.get("risk_model_approach", "standardized"),
                "capital_ratio": 0.08,
                "tier1_capital_requirement": assessment.get("tier1_capital_requirement"),
                "leverage_ratio": assessment.get("leverage_ratio"),
                "credit_score": assessment.get("credit_score"),
                "assessment_rationale": assessment.get("rationale")
            }
        )
        
        return {
            "status": "success",
            "assessment": assessment,
            "cdm_event": cdm_event
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assessing credit risk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error assessing credit risk: {str(e)}")


@router.post("/capital-requirements", response_model=Dict[str, Any])
async def calculate_capital_requirements(
    request: CapitalRequirementsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Calculate capital requirements for given RWA.
    
    Args:
        request: CapitalRequirementsRequest with RWA and optional capital ratio
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Capital requirement breakdown
    """
    try:
        credit_risk_service = CreditRiskService()
        
        rwa = Decimal(str(request.risk_weighted_assets))
        capital_ratio = Decimal(str(request.capital_ratio)) if request.capital_ratio else None
        
        requirements = credit_risk_service.calculate_capital_requirement(
            rwa=rwa,
            capital_ratio=capital_ratio
        )
        
        tier1_requirement = credit_risk_service.calculate_tier1_capital_requirement(rwa)
        
        return {
            "status": "success",
            "risk_weighted_assets": float(rwa),
            "capital_requirement": float(requirements),
            "tier1_capital_requirement": float(tier1_requirement),
            "capital_ratio": float(capital_ratio) if capital_ratio else 0.08,
            "tier1_ratio": float(tier1_requirement / rwa) if rwa > 0 else 0.0
        }
    
    except Exception as e:
        logger.error(f"Error calculating capital requirements: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculating capital requirements: {str(e)}")


@router.post("/portfolio-summary", response_model=Dict[str, Any])
async def get_portfolio_summary(
    request: PortfolioSummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Get portfolio-level credit risk summary.
    
    Args:
        request: PortfolioSummaryRequest with optional deal_ids and user_id filters
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Portfolio summary with concentration metrics, total RWA, capital requirements
    """
    try:
        credit_risk_service = CreditRiskService()
        
        # Get deals
        query = db.query(Deal)
        
        if request.user_id:
            query = query.filter(Deal.applicant_id == request.user_id)
        elif current_user.role != "admin":
            # Non-admins only see their own deals
            query = query.filter(Deal.applicant_id == current_user.id)
        
        if request.deal_ids:
            query = query.filter(Deal.id.in_(request.deal_ids))
        
        deals = query.all()
        
        # Build portfolio data
        portfolio = []
        total_rwa = Decimal("0")
        total_capital_requirement = Decimal("0")
        
        for deal in deals:
            # Get documents with CDM data
            document = db.query(Document).filter(
                Document.deal_id == deal.id,
                Document.source_cdm_data.isnot(None)
            ).first()
            
            if document and document.source_cdm_data:
                try:
                    credit_agreement = CreditAgreement(**document.source_cdm_data)
                    
                    # Calculate RWA for this deal
                    credit_risk_mapper = CreditRiskMapper()
                    risk_fields = credit_risk_mapper.map_cdm_to_credit_risk_fields(
                        credit_agreement=credit_agreement,
                        additional_context=deal.deal_data or {}
                    )
                    
                    if "exposure_at_default" in risk_fields:
                        ead = Decimal(str(risk_fields["exposure_at_default"]))
                        pd = risk_fields.get("probability_of_default", 0.01)
                        lgd = risk_fields.get("loss_given_default", 0.45)
                        maturity = risk_fields.get("maturity_years", 1.0)
                        asset_class = risk_fields.get("asset_class", "corporate")
                        approach = risk_fields.get("risk_model_approach", "standardized")
                        
                        rwa = credit_risk_service.calculate_rwa(
                            exposure=ead,
                            pd=pd,
                            lgd=lgd,
                            maturity=maturity,
                            asset_class=asset_class,
                            approach=approach
                        )
                        
                        capital_req = credit_risk_service.calculate_capital_requirement(rwa)
                        
                        portfolio.append({
                            "deal_id": deal.deal_id,
                            "deal_type": deal.deal_type,
                            "amount": float(ead),
                            "rwa": float(rwa),
                            "capital_requirement": float(capital_req),
                            "sector": deal.deal_data.get("sector", "unknown") if deal.deal_data else "unknown",
                            "borrower_id": deal.applicant_id
                        })
                        
                        total_rwa += rwa
                        total_capital_requirement += capital_req
                except Exception as e:
                    logger.warning(f"Failed to process deal {deal.id} for portfolio summary: {e}")
                    continue
        
        # Calculate concentration metrics
        concentration = credit_risk_service.calculate_portfolio_concentration(portfolio)
        
        return {
            "status": "success",
            "portfolio": {
                "total_deals": len(portfolio),
                "total_exposure": concentration.get("total_exposure", 0.0),
                "total_rwa": float(total_rwa),
                "total_capital_requirement": float(total_capital_requirement),
                "concentration": {
                    "max_sector_concentration": concentration.get("max_sector_concentration", 0.0),
                    "max_borrower_concentration": concentration.get("max_borrower_concentration", 0.0),
                    "sector_count": concentration.get("sector_count", 0),
                    "borrower_count": concentration.get("borrower_count", 0)
                }
            },
            "deals": portfolio[:100]  # Limit to first 100 deals
        }
    
    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting portfolio summary: {str(e)}")


@router.post("/stress-test", response_model=Dict[str, Any])
async def run_stress_test(
    request: StressTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth)
):
    """
    Run stress test scenario on a deal.
    
    Args:
        request: StressTestRequest with deal_id and stress scenario parameters
        db: Database session
        current_user: Authenticated user
        
    Returns:
        Stress test results with shocked PD/LGD, RWA, capital requirements
    """
    try:
        deal = db.query(Deal).filter(Deal.id == request.deal_id).first()
        if not deal:
            raise HTTPException(status_code=404, detail=f"Deal {request.deal_id} not found")
        
        # Check user access
        if deal.applicant_id != current_user.id and current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get document with CDM data
        document = db.query(Document).filter(
            Document.deal_id == request.deal_id,
            Document.source_cdm_data.isnot(None)
        ).first()
        
        if not document or not document.source_cdm_data:
            raise HTTPException(status_code=400, detail="Deal does not have CDM data for stress testing")
        
        credit_agreement = CreditAgreement(**document.source_cdm_data)
        credit_risk_service = CreditRiskService()
        credit_risk_mapper = CreditRiskMapper()
        policy_service = PolicyService(get_policy_engine())
        
        # Get baseline assessment
        additional_context = deal.deal_data.copy() if deal.deal_data else {}
        baseline = policy_service.evaluate_credit_risk(
            credit_agreement=credit_agreement,
            additional_context=additional_context
        )
        
        # Apply stress shocks
        baseline_pd = baseline.get("probability_of_default", 0.01)
        baseline_lgd = baseline.get("loss_given_default", 0.45)
        baseline_ead = Decimal(str(baseline.get("exposure_at_default", 0.0)))
        
        # Apply PD shock
        stressed_pd = baseline_pd
        if request.pd_shock:
            stressed_pd = min(1.0, baseline_pd * request.pd_shock)
        
        # Apply LGD shock
        stressed_lgd = baseline_lgd
        if request.lgd_shock:
            stressed_lgd = min(1.0, baseline_lgd * request.lgd_shock)
        
        # Apply market value shock (affects EAD for undrawn facilities)
        stressed_ead = baseline_ead
        if request.market_value_shock:
            stressed_ead = baseline_ead * (1 + Decimal(str(request.market_value_shock)))
        
        # Recalculate RWA with stressed parameters
        maturity = baseline.get("maturity_years", 1.0)
        asset_class = baseline.get("asset_class", "corporate")
        approach = baseline.get("risk_model_approach", "standardized")
        
        stressed_rwa = credit_risk_service.calculate_rwa(
            exposure=stressed_ead,
            pd=stressed_pd,
            lgd=stressed_lgd,
            maturity=maturity,
            asset_class=asset_class,
            approach=approach
        )
        
        stressed_capital_req = credit_risk_service.calculate_capital_requirement(stressed_rwa)
        
        # Calculate impact
        baseline_rwa = Decimal(str(baseline.get("risk_weighted_assets", 0.0)))
        baseline_capital_req = Decimal(str(baseline.get("capital_requirement", 0.0)))
        
        rwa_impact = float(stressed_rwa - baseline_rwa)
        capital_impact = float(stressed_capital_req - baseline_capital_req)
        rwa_impact_pct = float((stressed_rwa - baseline_rwa) / baseline_rwa * 100) if baseline_rwa > 0 else 0.0
        
        return {
            "status": "success",
            "stress_scenario": request.stress_scenario,
            "baseline": {
                "pd": baseline_pd,
                "lgd": baseline_lgd,
                "ead": float(baseline_ead),
                "rwa": float(baseline_rwa),
                "capital_requirement": float(baseline_capital_req)
            },
            "stressed": {
                "pd": stressed_pd,
                "lgd": stressed_lgd,
                "ead": float(stressed_ead),
                "rwa": float(stressed_rwa),
                "capital_requirement": float(stressed_capital_req)
            },
            "impact": {
                "rwa_impact": rwa_impact,
                "rwa_impact_pct": rwa_impact_pct,
                "capital_impact": capital_impact,
                "capital_impact_pct": float((stressed_capital_req - baseline_capital_req) / baseline_capital_req * 100) if baseline_capital_req > 0 else 0.0
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running stress test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error running stress test: {str(e)}")
