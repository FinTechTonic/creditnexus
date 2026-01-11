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
from app.services.policy_service import PolicyService

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
    db_session=None,  # Optional SQLAlchemy session for persistence
    policy_service: Optional[PolicyService] = None,  # Optional policy service for compliance evaluation
    credit_agreement=None,  # Optional CreditAgreement for policy context
    deal_id: Optional[int] = None  # Optional deal ID to update with verification results
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
        
        # Handle SPT extraction (gracefully handle None if rate limited)
        if legal_result.spt:
            try:
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
            except Exception as e:
                logger.warning(f"Failed to process SPT data: {e}")
                result.stages_failed.append("legal_analysis")
        else:
            result.stages_failed.append("legal_analysis")
            logger.warning("No SPT extracted from document (may be due to rate limiting or missing data)")
        
        # Handle address extraction (gracefully handle None if rate limited)
        if legal_result.collateral_address:
            try:
                loan_asset.collateral_address = legal_result.collateral_address.full_address
                result.stages_completed.append("address_extraction")
            except Exception as e:
                logger.warning(f"Failed to process address data: {e}")
                result.stages_failed.append("address_extraction")
        else:
            result.stages_failed.append("address_extraction")
            logger.warning("No address extracted from document (may be due to rate limiting or missing data)")
            
    except Exception as e:
        logger.error(f"Legal analysis failed: {e}")
        result.stages_failed.append("legal_analysis")
        if "address_extraction" not in result.stages_failed:
            result.stages_failed.append("address_extraction")
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
                # Store previous risk status to detect changes
                previous_risk_status = loan_asset.risk_status
                previous_rate = loan_asset.current_interest_rate or loan_asset.base_interest_rate or 5.0
                
                loan_asset.update_verification(ndvi_score)
                result.stages_completed.append("satellite_verification")
                
                # Update deal with verification results if deal_id provided
                if deal_id and db_session:
                    try:
                        from app.services.deal_service import DealService
                        deal_service = DealService(db_session)
                        deal_service.update_deal_on_verification(
                            deal_id=deal_id,
                            verification_result={
                                "ndvi_score": ndvi_score,
                                "risk_status": loan_asset.risk_status,
                                "threshold": loan_asset.spt_threshold or 0.8,
                                "verified_at": verification.get("verified_at", datetime.utcnow().isoformat()),
                                "data_source": verification.get("data_source", "unknown"),
                                "success": True
                            },
                            loan_asset_id=loan_asset.id if hasattr(loan_asset, 'id') and loan_asset.id else None,
                            user_id=None  # Will use deal applicant_id
                        )
                        logger.info(f"Updated deal {deal_id} with verification results")
                    except Exception as e:
                        logger.warning(f"Failed to update deal {deal_id} with verification results: {e}")
                        # Don't fail the audit if deal update fails
                
                # Policy evaluation after satellite verification (if enabled)
                if policy_service:
                    try:
                        from app.models.cdm_events import generate_cdm_observation, generate_cdm_policy_evaluation, generate_cdm_terms_change
                        from app.db.models import PolicyDecision as PolicyDecisionModel
                        
                        # Create CDM Observation event for satellite verification
                        satellite_hash = verification.get("hash", "")
                        # risk_status is already a string (RiskStatus is a class with string constants, not an Enum)
                        # Ensure we have a string value
                        risk_status_str = loan_asset.risk_status
                        if not isinstance(risk_status_str, str):
                            # If it's somehow not a string, convert it
                            risk_status_str = str(risk_status_str)
                        observation_event = generate_cdm_observation(
                            trade_id=loan_id,
                            satellite_hash=satellite_hash,
                            ndvi_score=ndvi_score,
                            status=risk_status_str
                        )
                        
                        # Get observation event ID for linking
                        observation_event_id = observation_event.get("meta", {}).get("globalKey", "")
                        
                        # Evaluate loan asset securitization for compliance
                        policy_result = policy_service.evaluate_loan_asset(
                            loan_asset=loan_asset,
                            credit_agreement=credit_agreement
                        )
                        
                        # Create CDM PolicyEvaluation event
                        policy_evaluation_event = generate_cdm_policy_evaluation(
                            transaction_id=loan_id,
                            transaction_type="loan_asset_securitization",
                            decision=policy_result.decision,
                            rule_applied=policy_result.rule_applied,
                            related_event_identifiers=[{
                                "eventIdentifier": {
                                    "issuer": "CreditNexus",
                                    "assignedIdentifier": [{
                                        "identifier": {"value": observation_event_id}
                                    }]
                                }
                            }],
                            evaluation_trace=policy_result.trace,
                            matched_rules=policy_result.matched_rules
                        )
                        
                        # Create TermsChange event if breach detected and rate changed
                        terms_change_event = None
                        if loan_asset.risk_status == RiskStatus.BREACH and previous_risk_status != RiskStatus.BREACH:
                            # Breach just detected - trigger TermsChange event
                            logger.info(
                                f"Breach detected for loan {loan_id}: "
                                f"NDVI={ndvi_score:.4f}, threshold={loan_asset.spt_threshold}, "
                                f"rate change: {previous_rate}% -> {loan_asset.current_interest_rate}%"
                            )
                            
                            terms_change_event = generate_cdm_terms_change(
                                trade_id=loan_id,
                                current_rate=previous_rate,
                                status=risk_status_str,
                                policy_service=policy_service
                            )
                            
                            if terms_change_event:
                                # Link TermsChange to Observation event
                                terms_change_event["relatedEventIdentifier"] = [{
                                    "eventIdentifier": {
                                        "issuer": "CreditNexus",
                                        "assignedIdentifier": [{
                                            "identifier": {"value": observation_event_id}
                                        }]
                                    }
                                }]
                                
                                logger.info(f"Generated TermsChange event for loan {loan_id} breach")
                            else:
                                logger.warning(f"TermsChange event was blocked by policy for loan {loan_id}")
                        
                        # Also trigger TermsChange if status changed from BREACH to COMPLIANT (penalty removed)
                        elif previous_risk_status == RiskStatus.BREACH and loan_asset.risk_status == RiskStatus.COMPLIANT:
                            logger.info(
                                f"Compliance restored for loan {loan_id}: "
                                f"NDVI={ndvi_score:.4f}, rate change: {previous_rate}% -> {loan_asset.current_interest_rate}%"
                            )
                            
                            terms_change_event = generate_cdm_terms_change(
                                trade_id=loan_id,
                                current_rate=previous_rate,
                                status=risk_status_str,
                                policy_service=policy_service
                            )
                            
                            if terms_change_event:
                                # Link TermsChange to Observation event
                                terms_change_event["relatedEventIdentifier"] = [{
                                    "eventIdentifier": {
                                        "issuer": "CreditNexus",
                                        "assignedIdentifier": [{
                                            "identifier": {"value": observation_event_id}
                                        }]
                                    }
                                }]
                                
                                logger.info(f"Generated TermsChange event for loan {loan_id} compliance restoration")
                        
                        # Handle BLOCK decision - prevent securitization
                        if policy_result.decision == "BLOCK":
                            logger.warning(
                                f"Policy evaluation BLOCKED loan asset securitization: "
                                f"loan_id={loan_id}, rule={policy_result.rule_applied}, "
                                f"trace_id={policy_result.trace_id}"
                            )
                            
                            loan_asset.risk_status = RiskStatus.ERROR
                            loan_asset.verification_error = (
                                f"Policy violation: {policy_result.rule_applied}. "
                                f"Securitization blocked by compliance policy."
                            )
                            result.stages_failed.append("policy_evaluation")
                            
                            # Store policy decision info to create after loan_asset is persisted
                            # (loan_asset.id doesn't exist yet, and foreign key requires the table to exist)
                            if db_session:
                                if not hasattr(loan_asset, '_pending_policy_decisions'):
                                    loan_asset._pending_policy_decisions = []
                                cdm_events = [policy_evaluation_event]
                                if terms_change_event:
                                    cdm_events.append(terms_change_event)
                                loan_asset._pending_policy_decisions.append({
                                    "transaction_id": loan_id,
                                    "transaction_type": "loan_asset_securitization",
                                    "decision": policy_result.decision,
                                    "rule_applied": policy_result.rule_applied,
                                    "trace_id": policy_result.trace_id,
                                    "trace": policy_result.trace,
                                    "matched_rules": policy_result.matched_rules,
                                    "cdm_events": cdm_events
                                })
                        
                        # Handle FLAG decision - allow but mark for review
                        elif policy_result.decision == "FLAG":
                            logger.info(
                                f"Policy evaluation FLAGGED loan asset securitization: "
                                f"loan_id={loan_id}, rule={policy_result.rule_applied}, "
                                f"trace_id={policy_result.trace_id}"
                            )
                            
                            loan_asset.risk_status = RiskStatus.WARNING
                            # Add policy metadata to loan asset
                            if not hasattr(loan_asset, 'asset_metadata') or loan_asset.asset_metadata is None:
                                loan_asset.asset_metadata = {}
                            loan_asset.asset_metadata["policy_flag"] = {
                                "rule_applied": policy_result.rule_applied,
                                "trace_id": policy_result.trace_id,
                                "requires_review": True
                            }
                            
                            # Store policy decision info to create after loan_asset is persisted
                            if db_session:
                                if not hasattr(loan_asset, '_pending_policy_decisions'):
                                    loan_asset._pending_policy_decisions = []
                                cdm_events = [policy_evaluation_event]
                                if terms_change_event:
                                    cdm_events.append(terms_change_event)
                                loan_asset._pending_policy_decisions.append({
                                    "transaction_id": loan_id,
                                    "transaction_type": "loan_asset_securitization",
                                    "decision": policy_result.decision,
                                    "rule_applied": policy_result.rule_applied,
                                    "trace_id": policy_result.trace_id,
                                    "trace": policy_result.trace,
                                    "matched_rules": policy_result.matched_rules,
                                    "cdm_events": cdm_events,
                                    "metadata": {"requires_review": True}
                                })
                        
                        # Handle ALLOW decision - log for audit
                        else:
                            logger.debug(
                                f"Policy evaluation ALLOWED loan asset securitization: "
                                f"loan_id={loan_id}, trace_id={policy_result.trace_id}"
                            )
                            
                            # Store policy decision info to create after loan_asset is persisted
                            if db_session:
                                if not hasattr(loan_asset, '_pending_policy_decisions'):
                                    loan_asset._pending_policy_decisions = []
                                cdm_events = [policy_evaluation_event]
                                if terms_change_event:
                                    cdm_events.append(terms_change_event)
                                loan_asset._pending_policy_decisions.append({
                                    "transaction_id": loan_id,
                                    "transaction_type": "loan_asset_securitization",
                                    "decision": policy_result.decision,
                                    "rule_applied": policy_result.rule_applied,
                                    "trace_id": policy_result.trace_id,
                                    "trace": policy_result.trace,
                                    "matched_rules": policy_result.matched_rules,
                                    "cdm_events": cdm_events
                                })
                    
                    except Exception as e:
                        # Log policy evaluation errors but don't block audit
                        logger.error(f"Policy evaluation failed for loan {loan_id}: {e}", exc_info=True)
                        # Continue with audit even if policy evaluation fails
                else:
                    # Even without policy_service, create Observation and TermsChange events if breach detected
                    try:
                        from app.models.cdm_events import generate_cdm_observation, generate_cdm_terms_change
                        
                        # Create CDM Observation event for satellite verification
                        satellite_hash = verification.get("hash", "")
                        risk_status_str = loan_asset.risk_status
                        if not isinstance(risk_status_str, str):
                            risk_status_str = str(risk_status_str)
                        
                        observation_event = generate_cdm_observation(
                            trade_id=loan_id,
                            satellite_hash=satellite_hash,
                            ndvi_score=ndvi_score,
                            status=risk_status_str
                        )
                        observation_event_id = observation_event.get("meta", {}).get("globalKey", "")
                        
                        # Create TermsChange event if breach detected and rate changed
                        terms_change_event = None
                        if loan_asset.risk_status == RiskStatus.BREACH and previous_risk_status != RiskStatus.BREACH:
                            logger.info(
                                f"Breach detected for loan {loan_id}: "
                                f"NDVI={ndvi_score:.4f}, threshold={loan_asset.spt_threshold}, "
                                f"rate change: {previous_rate}% -> {loan_asset.current_interest_rate}%"
                            )
                            
                            terms_change_event = generate_cdm_terms_change(
                                trade_id=loan_id,
                                current_rate=previous_rate,
                                status=risk_status_str,
                                policy_service=None  # No policy service available
                            )
                            
                            if terms_change_event:
                                # Link TermsChange to Observation event
                                terms_change_event["relatedEventIdentifier"] = [{
                                    "eventIdentifier": {
                                        "issuer": "CreditNexus",
                                        "assignedIdentifier": [{
                                            "identifier": {"value": observation_event_id}
                                        }]
                                    }
                                }]
                                
                                logger.info(f"Generated TermsChange event for loan {loan_id} breach")
                        
                        # Also trigger TermsChange if status changed from BREACH to COMPLIANT
                        elif previous_risk_status == RiskStatus.BREACH and loan_asset.risk_status == RiskStatus.COMPLIANT:
                            logger.info(
                                f"Compliance restored for loan {loan_id}: "
                                f"NDVI={ndvi_score:.4f}, rate change: {previous_rate}% -> {loan_asset.current_interest_rate}%"
                            )
                            
                            terms_change_event = generate_cdm_terms_change(
                                trade_id=loan_id,
                                current_rate=previous_rate,
                                status=risk_status_str,
                                policy_service=None
                            )
                            
                            if terms_change_event:
                                # Link TermsChange to Observation event
                                terms_change_event["relatedEventIdentifier"] = [{
                                    "eventIdentifier": {
                                        "issuer": "CreditNexus",
                                        "assignedIdentifier": [{
                                            "identifier": {"value": observation_event_id}
                                        }]
                                    }
                                }]
                                
                                logger.info(f"Generated TermsChange event for loan {loan_id} compliance restoration")
                        
                        # Store events for later persistence (if db_session available)
                        if db_session:
                            if not hasattr(loan_asset, '_pending_cdm_events'):
                                loan_asset._pending_cdm_events = []
                            event_data = {"observation": observation_event}
                            if terms_change_event:
                                event_data["terms_change"] = terms_change_event
                            loan_asset._pending_cdm_events.append(event_data)
                    except Exception as e:
                        logger.warning(f"Failed to generate CDM events (no policy service): {e}")
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
            db_session.flush()  # Flush to get the ID without committing
            db_session.refresh(loan_asset)
            
            # Now create policy decisions with the loan_asset_id
            # Note: loan_assets table exists in DB (via Alembic), but LoanAsset is a SQLModel
            # so it's not in Base.metadata. The foreign key will work at DB level.
            if hasattr(loan_asset, '_pending_policy_decisions') and loan_asset._pending_policy_decisions:
                for policy_data in loan_asset._pending_policy_decisions:
                    try:
                        # Create policy decision with loan_asset_id set
                        # SQLAlchemy may warn about foreign key validation, but it will work at DB level
                        policy_decision_db = PolicyDecisionModel(
                            transaction_id=policy_data["transaction_id"],
                            transaction_type=policy_data["transaction_type"],
                            decision=policy_data["decision"],
                            rule_applied=policy_data["rule_applied"],
                            trace_id=policy_data["trace_id"],
                            trace=policy_data["trace"],
                            matched_rules=policy_data["matched_rules"],
                            additional_metadata=policy_data.get("metadata", {}),
                            cdm_events=policy_data["cdm_events"],
                            loan_asset_id=loan_asset.id if loan_asset.id else None
                        )
                        db_session.add(policy_decision_db)
                    except Exception as e:
                        # Log warning but continue - policy decision is for audit trail
                        # The loan_asset itself is more important than the policy decision record
                        logger.warning(
                            f"Failed to create policy decision for loan {loan_asset.loan_id}: {e}. "
                            f"Policy decision will be logged in loan_asset metadata instead."
                        )
                        # Store policy decision info in loan_asset metadata as fallback
                        if not loan_asset.asset_metadata:
                            loan_asset.asset_metadata = {}
                        if "policy_decisions" not in loan_asset.asset_metadata:
                            loan_asset.asset_metadata["policy_decisions"] = []
                        loan_asset.asset_metadata["policy_decisions"].append({
                            "transaction_id": policy_data["transaction_id"],
                            "decision": policy_data["decision"],
                            "rule_applied": policy_data["rule_applied"],
                            "trace_id": policy_data["trace_id"]
                        })
                        continue
            
            db_session.commit()
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
