"""Audit Workflow Orchestration for Ground Truth Protocol.

This module combines legal and geospatial verification into a single
"Securitize & Verify" workflow.
"""

import logging
from datetime import datetime
from typing import Optional

from app.agents.analyzer import analyze_legal_document, generate_legal_vector
from app.agents.verifier import geocode_address, verify_asset_location
from app.models.loan_asset import LoanAsset, RiskStatus
from app.models.spt_schema import SustainabilityPerformanceTarget

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditResult:
    """Result of a complete audit workflow."""
    
    def __init__(self):
        self.success: bool = False
        self.loan_asset: Optional[LoanAsset] = None
        self.error: Optional[str] = None
        self.stages_completed: list[str] = []
        self.stages_failed: list[str] = []
    
    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "loan_asset": self.loan_asset.to_dict() if self.loan_asset else None,
            "error": self.error,
            "stages_completed": self.stages_completed,
            "stages_failed": self.stages_failed,
        }


async def run_full_audit(
    loan_id: str,
    document_text: str,
    db_session=None  # Optional SQLAlchemy session for persistence
) -> AuditResult:
    """
    Execute the complete "Securitize & Verify" workflow.
    
    Stages:
    1. Legal Analysis - Extract SPT and collateral address
    2. Geocoding - Convert address to coordinates
    3. Satellite Verification - Fetch imagery and calculate NDVI
    4. Status Determination - Compare against SPT threshold
    5. (Optional) Database Persistence
    
    Args:
        loan_id: External loan identifier
        document_text: Raw text from loan agreement
        db_session: Optional database session for persistence
        
    Returns:
        AuditResult with loan asset and status
    """
    result = AuditResult()
    
    # Initialize loan asset
    loan_asset = LoanAsset(
        loan_id=loan_id,
        original_text=document_text[:5000],  # Store first 5000 chars
        risk_status=RiskStatus.PENDING,
        created_at=datetime.utcnow()
    )
    
    logger.info(f"Starting full audit for loan {loan_id}")
    
    # --- Stage 1: Legal Analysis ---
    try:
        logger.info("Stage 1: Legal document analysis")
        legal_result = await analyze_legal_document(document_text)
        
        if legal_result.spt:
            # Store SPT data as JSON
            loan_asset.spt_data = {
                "resource_target": {
                    "metric": legal_result.spt.resource_target.metric,
                    "unit": legal_result.spt.resource_target.unit,
                    "threshold": legal_result.spt.resource_target.threshold,
                    "direction": legal_result.spt.resource_target.direction.value
                },
                "financial_consequence": {
                    "type": legal_result.spt.financial_consequence.type.value,
                    "penalty_bps": legal_result.spt.financial_consequence.penalty_bps,
                    "trigger_mechanism": legal_result.spt.financial_consequence.trigger_mechanism.value
                }
            }
            # Update penalty from SPT
            loan_asset.penalty_bps = legal_result.spt.financial_consequence.penalty_bps
            loan_asset.spt_threshold = legal_result.spt.resource_target.threshold
            result.stages_completed.append("legal_analysis")
        else:
            result.stages_failed.append("legal_analysis")
            logger.warning("No SPT extracted from document")
        
        if legal_result.collateral_address:
            loan_asset.collateral_address = legal_result.collateral_address.full_address
            result.stages_completed.append("address_extraction")
        else:
            result.stages_failed.append("address_extraction")
            
    except Exception as e:
        logger.error(f"Legal analysis failed: {e}")
        result.stages_failed.append("legal_analysis")
        result.error = f"Legal analysis error: {str(e)}"
    
    # --- Stage 2: Generate Legal Vector ---
    try:
        logger.info("Stage 2: Generating legal text embedding")
        legal_vector = await generate_legal_vector(document_text[:8000])
        if legal_vector:
            loan_asset.legal_vector = legal_vector
            result.stages_completed.append("legal_embedding")
    except Exception as e:
        logger.warning(f"Legal embedding failed: {e}")
        result.stages_failed.append("legal_embedding")
    
    # --- Stage 3: Geocoding ---
    if loan_asset.collateral_address:
        try:
            logger.info("Stage 3: Geocoding collateral address")
            coords = await geocode_address(loan_asset.collateral_address)
            
            if coords:
                loan_asset.geo_lat, loan_asset.geo_lon = coords
                result.stages_completed.append("geocoding")
            else:
                result.stages_failed.append("geocoding")
                logger.warning("Geocoding returned no results")
                
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")
            result.stages_failed.append("geocoding")
    else:
        logger.warning("Skipping geocoding - no address available")
        result.stages_failed.append("geocoding")
    
    # --- Stage 4: Satellite Verification ---
    if loan_asset.geo_lat and loan_asset.geo_lon:
        try:
            logger.info("Stage 4: Satellite verification")
            verification = await verify_asset_location(
                lat=loan_asset.geo_lat,
                lon=loan_asset.geo_lon,
                threshold=loan_asset.spt_threshold or 0.8
            )
            
            if verification.get("success"):
                ndvi_score = verification["ndvi_score"]
                loan_asset.update_verification(ndvi_score)
                result.stages_completed.append("satellite_verification")
            else:
                loan_asset.risk_status = RiskStatus.ERROR
                loan_asset.verification_error = verification.get("error", "Unknown error")
                result.stages_failed.append("satellite_verification")
                
        except Exception as e:
            logger.error(f"Satellite verification failed: {e}")
            loan_asset.risk_status = RiskStatus.ERROR
            loan_asset.verification_error = str(e)
            result.stages_failed.append("satellite_verification")
    else:
        logger.warning("Skipping satellite verification - no coordinates available")
        result.stages_failed.append("satellite_verification")
    
    # --- Stage 5: Database Persistence (if session provided) ---
    if db_session:
        try:
            logger.info("Stage 5: Persisting to database")
            db_session.add(loan_asset)
            db_session.commit()
            db_session.refresh(loan_asset)
            result.stages_completed.append("database_persistence")
        except Exception as e:
            logger.error(f"Database persistence failed: {e}")
            db_session.rollback()
            result.stages_failed.append("database_persistence")
    
    # --- Finalize ---
    result.loan_asset = loan_asset
    result.success = (
        "legal_analysis" in result.stages_completed
        and "geocoding" in result.stages_completed
        and "satellite_verification" in result.stages_completed
    )
    
    logger.info(f"Audit complete. Success: {result.success}")
    logger.info(f"Stages completed: {result.stages_completed}")
    logger.info(f"Stages failed: {result.stages_failed}")
    
    return result


# Demo covenant text for testing
DEMO_COVENANT = """
SUSTAINABILITY-LINKED CREDIT AGREEMENT

This Credit Agreement dated December 15, 2024, between GreenForest Holdings LLC 
("Borrower") and First National Bank ("Lender").

ARTICLE VII - SUSTAINABILITY COVENANTS

Section 7.1 - Forest Conservation Target

The Borrower covenants that the vegetation coverage on the Collateral Property 
located at 2847 Timber Ridge Road, Paradise, California 95969, as measured by 
the Normalized Difference Vegetation Index (NDVI) from satellite imagery, shall 
be maintained at a level of at least Eighty Percent (80%) of the baseline 
measurement established at loan origination.

Section 7.2 - Margin Adjustment

Upon a verified Sustainability Target Breach, the Applicable Margin shall 
automatically increase by Fifty (50) basis points. Such increase shall remain 
in effect until the next annual verification confirms compliance.

Section 7.3 - Verification

Verification shall be performed annually using Sentinel-2 satellite imagery 
or equivalent earth observation data of equivalent or greater resolution.
"""


async def demo_audit():
    """Demo the full audit workflow."""
    print("=" * 70)
    print("CreditNexus Ground Truth Protocol - Full Audit Demo")
    print("=" * 70)
    
    result = await run_full_audit(
        loan_id="DEMO-2024-001",
        document_text=DEMO_COVENANT
    )
    
    print(f"\nAudit Success: {result.success}")
    print(f"\nStages Completed: {', '.join(result.stages_completed)}")
    print(f"Stages Failed: {', '.join(result.stages_failed)}")
    
    if result.loan_asset:
        asset = result.loan_asset
        print(f"\n{'='*40}")
        print("LOAN ASSET DETAILS")
        print(f"{'='*40}")
        print(f"Loan ID: {asset.loan_id}")
        print(f"Address: {asset.collateral_address}")
        print(f"Coordinates: ({asset.geo_lat}, {asset.geo_lon})")
        print(f"NDVI Score: {asset.last_verified_score}")
        print(f"Risk Status: {asset.risk_status}")
        print(f"Base Rate: {asset.base_interest_rate}%")
        print(f"Current Rate: {asset.current_interest_rate}%")
        if asset.spt_data:
            print(f"\nSPT Threshold: {asset.spt_threshold}")
            print(f"Penalty: {asset.penalty_bps} bps")
    
    return result
