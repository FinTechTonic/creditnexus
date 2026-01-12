"""Green Finance API Routes.

This module provides API endpoints for green finance functionality:
- Green finance assessments
- Urban sustainability evaluation
- Emissions compliance monitoring
- SDG alignment evaluation
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import GreenFinanceAssessment, Deal
from app.models.loan_asset import LoanAsset
from app.auth.dependencies import get_current_user
from app.models.green_finance import GreenFinanceAssessment as GreenFinanceAssessmentModel
from app.services.policy_service import PolicyService
from app.services.policy_engine_factory import get_policy_engine
from app.models.cdm_events import generate_green_finance_assessment
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/green-finance", tags=["green-finance"])


@router.post("/assess", response_model=Dict[str, Any])
async def assess_green_finance(
    location_lat: float = Query(..., description="Location latitude"),
    location_lon: float = Query(..., description="Location longitude"),
    transaction_id: Optional[str] = Query(None, description="Transaction/deal ID"),
    deal_id: Optional[int] = Query(None, description="Deal ID"),
    loan_asset_id: Optional[int] = Query(None, description="Loan asset ID"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    policy_service: PolicyService = Depends(lambda: PolicyService(get_policy_engine()))
):
    """
    Perform comprehensive green finance assessment for a location.
    
    This endpoint:
    1. Fetches OSM data, air quality, and satellite metrics
    2. Calculates composite sustainability score
    3. Evaluates SDG alignment
    4. Performs policy compliance evaluation
    5. Stores assessment in database
    """
    if not settings.ENHANCED_SATELLITE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Enhanced satellite verification is disabled"
        )
    
    try:
        from app.agents.verifier import verify_asset_location
        from app.services.sustainability_scorer import SustainabilityScorer
        from app.services.policy_service import PolicyService
        from app.services.policy_engine_factory import get_policy_engine
        
        # Perform enhanced verification
        verification_result = await verify_asset_location(
            lat=location_lat,
            lon=location_lon,
            include_enhanced=True
        )
        
        if not verification_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Verification failed: {verification_result.get('error')}"
            )
        
        # Extract metrics
        location_type = verification_result.get("location_type", "unknown")
        air_quality_index = verification_result.get("air_quality_index", 50.0)
        composite_sustainability_score = verification_result.get("composite_sustainability_score", 0.5)
        sustainability_components = verification_result.get("sustainability_components", {})
        osm_metrics = verification_result.get("osm_metrics", {})
        air_quality = verification_result.get("air_quality", {})
        
        # Evaluate SDG alignment
        policy_service = PolicyService(get_policy_engine())
        sdg_result = policy_service.evaluate_sdg_alignment(
            location_lat=location_lat,
            location_lon=location_lon,
            sustainability_components=sustainability_components,
            green_finance_metrics={
                "location_type": location_type,
                "air_quality_index": air_quality_index,
                "composite_sustainability_score": composite_sustainability_score,
                "osm_metrics": osm_metrics
            }
        )
        
        # Get loan asset if provided
        loan_asset = None
        if loan_asset_id:
            loan_asset = db.query(LoanAsset).filter(LoanAsset.id == loan_asset_id).first()
            if not loan_asset:
                raise HTTPException(status_code=404, detail=f"Loan asset {loan_asset_id} not found")
        
        # Get deal if provided
        deal = None
        if deal_id:
            deal = db.query(Deal).filter(Deal.id == deal_id).first()
            if not deal:
                raise HTTPException(status_code=404, detail=f"Deal {deal_id} not found")
        
        # Use transaction_id from deal or loan_asset if not provided
        if not transaction_id:
            if deal:
                transaction_id = deal.deal_id
            elif loan_asset:
                transaction_id = loan_asset.loan_id
            else:
                transaction_id = f"ASSESSMENT_{location_lat}_{location_lon}"
        
        # Create CDM event
        cdm_event = generate_green_finance_assessment(
            transaction_id=transaction_id,
            location_lat=location_lat,
            location_lon=location_lon,
            location_type=location_type,
            air_quality_index=air_quality_index,
            composite_sustainability_score=composite_sustainability_score,
            sustainability_components=sustainability_components,
            sdg_alignment=sdg_result.get("sdg_alignment", {}),
            related_event_identifiers=[],
            additional_metrics={
                "pm25": air_quality.get("pm25"),
                "pm10": air_quality.get("pm10"),
                "no2": air_quality.get("no2"),
                "osm_metrics": osm_metrics,
                "green_infrastructure_coverage": osm_metrics.get("green_infrastructure_coverage")
            }
        )
        
        # Store assessment in database
        assessment = GreenFinanceAssessment(
            transaction_id=transaction_id,
            deal_id=deal_id,
            loan_asset_id=loan_asset_id,
            location_lat=location_lat,
            location_lon=location_lon,
            location_type=location_type,
            location_confidence=verification_result.get("location_confidence", 0.5),
            environmental_metrics={
                "air_quality_index": air_quality_index,
                "pm25": air_quality.get("pm25"),
                "pm10": air_quality.get("pm10"),
                "no2": air_quality.get("no2")
            },
            urban_activity_metrics=osm_metrics,
            sustainability_score=composite_sustainability_score,
            sustainability_components=sustainability_components,
            sdg_alignment=sdg_result,
            cdm_events=[cdm_event]
        )
        
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
        
        return {
            "assessment_id": assessment.id,
            "transaction_id": transaction_id,
            "location": {
                "lat": location_lat,
                "lon": location_lon,
                "type": location_type
            },
            "sustainability_score": composite_sustainability_score,
            "sustainability_components": sustainability_components,
            "air_quality_index": air_quality_index,
            "sdg_alignment": sdg_result,
            "cdm_event": cdm_event,
            "assessed_at": assessment.assessed_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Green finance assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Assessment failed: {str(e)}"
        )


@router.get("/assessments", response_model=List[Dict[str, Any]])
def list_assessments(
    deal_id: Optional[int] = Query(None, description="Filter by deal ID"),
    loan_asset_id: Optional[int] = Query(None, description="Filter by loan asset ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """List green finance assessments with optional filtering."""
    query = db.query(GreenFinanceAssessment)
    
    if deal_id:
        query = query.filter(GreenFinanceAssessment.deal_id == deal_id)
    if loan_asset_id:
        query = query.filter(GreenFinanceAssessment.loan_asset_id == loan_asset_id)
    
    # Pagination
    offset = (page - 1) * limit
    assessments = query.order_by(GreenFinanceAssessment.assessed_at.desc()).offset(offset).limit(limit).all()
    
    return [assessment.to_dict() for assessment in assessments]


@router.get("/assessments/{assessment_id}", response_model=Dict[str, Any])
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific green finance assessment by ID."""
    assessment = db.query(GreenFinanceAssessment).filter(GreenFinanceAssessment.id == assessment_id).first()
    
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Assessment {assessment_id} not found")
    
    return assessment.to_dict()


@router.post("/urban-sustainability", response_model=Dict[str, Any])
async def assess_urban_sustainability(
    location_lat: float = Query(..., description="Location latitude"),
    location_lon: float = Query(..., description="Location longitude"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    policy_service: PolicyService = Depends(lambda: PolicyService(get_policy_engine()))
):
    """Assess urban sustainability for a location."""
    if not settings.ENHANCED_SATELLITE_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Enhanced satellite verification is disabled"
        )
    
    try:
        result = await policy_service.assess_urban_sustainability(
            location_lat=location_lat,
            location_lon=location_lon
        )
        return result
    except Exception as e:
        logger.error(f"Urban sustainability assessment failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Assessment failed: {str(e)}"
        )


@router.post("/emissions-compliance", response_model=Dict[str, Any])
async def monitor_emissions_compliance(
    location_lat: float = Query(..., description="Location latitude"),
    location_lon: float = Query(..., description="Location longitude"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    policy_service: PolicyService = Depends(lambda: PolicyService(get_policy_engine()))
):
    """Monitor emissions and air quality compliance."""
    if not settings.AIR_QUALITY_ENABLED:
        raise HTTPException(
            status_code=503,
            detail="Air quality monitoring is disabled"
        )
    
    try:
        result = await policy_service.monitor_emissions_compliance(
            location_lat=location_lat,
            location_lon=location_lon
        )
        return result
    except Exception as e:
        logger.error(f"Emissions compliance monitoring failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Monitoring failed: {str(e)}"
        )


@router.post("/sdg-alignment", response_model=Dict[str, Any])
def evaluate_sdg_alignment(
    location_lat: float = Query(..., description="Location latitude"),
    location_lon: float = Query(..., description="Location longitude"),
    sustainability_components: Optional[Dict[str, float]] = None,
    green_finance_metrics: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
    policy_service: PolicyService = Depends(lambda: PolicyService(get_policy_engine()))
):
    """Evaluate SDG alignment for a location."""
    try:
        result = policy_service.evaluate_sdg_alignment(
            location_lat=location_lat,
            location_lon=location_lon,
            sustainability_components=sustainability_components,
            green_finance_metrics=green_finance_metrics
        )
        return result
    except Exception as e:
        logger.error(f"SDG alignment evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Evaluation failed: {str(e)}"
        )
