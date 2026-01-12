"""
Policy Service Layer for CreditNexus.

Provides CDM-compliant interfaces to the policy engine, handling transaction
mapping and result interpretation. This service layer bridges CDM models and
the vendor-agnostic policy engine interface.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal
from functools import lru_cache
import asyncio

from app.models.cdm import CreditAgreement
from app.models.loan_asset import LoanAsset
from app.models.cdm_events import generate_cdm_policy_evaluation
from app.services.policy_engine_interface import PolicyEngineInterface
from app.services.credit_risk_service import CreditRiskService
from app.services.credit_risk_mapper import CreditRiskMapper

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    """Result of policy evaluation."""
    decision: str  # "ALLOW", "BLOCK", "FLAG"
    rule_applied: Optional[str]  # Name of rule that triggered decision
    trace_id: str  # Unique trace identifier for audit
    trace: List[Dict[str, Any]]  # Full evaluation trace
    matched_rules: List[str]  # All matching rules (for audit)
    metadata: Dict[str, Any]  # Additional context (document_id, loan_asset_id, etc.)


class PolicyService:
    """
    Service layer for policy engine integration.
    
    Provides CDM-compliant interfaces to the policy engine,
    handling transaction mapping and result interpretation.
    """
    
    def __init__(self, policy_engine: PolicyEngineInterface):
        """
        Initialize with policy engine instance.
        
        Args:
            policy_engine: Vendor-agnostic policy engine interface
        """
        self.engine = policy_engine
        self.credit_risk_service = CreditRiskService()
        self.credit_risk_mapper = CreditRiskMapper()
        # Cache for credit risk calculations (key: transaction_id, value: credit_risk_metrics)
        self._credit_risk_cache: Dict[str, Dict[str, Any]] = {}
    
    def evaluate_facility_creation(
        self,
        credit_agreement: CreditAgreement,
        document_id: Optional[int] = None
    ) -> PolicyDecision:
        """
        Evaluate a new loan facility for compliance.
        
        Args:
            credit_agreement: Extracted CDM CreditAgreement
            document_id: Optional document ID for audit trail
            
        Returns:
            PolicyDecision with ALLOW/BLOCK/FLAG
        """
        # Convert CDM to policy transaction
        tx = self._cdm_to_policy_transaction(
            credit_agreement=credit_agreement,
            transaction_type="facility_creation"
        )
        
        # Evaluate
        result = self.engine.evaluate(tx)
        
        return PolicyDecision(
            decision=result["decision"],
            rule_applied=result.get("rule"),
            trace_id=f"facility_{document_id}_{datetime.utcnow().isoformat()}" if document_id else f"facility_{datetime.utcnow().isoformat()}",
            trace=result.get("trace", []),
            matched_rules=result.get("matched_rules", []),
            metadata={"document_id": document_id}
        )
    
    def evaluate_trade_execution(
        self,
        cdm_event: Dict[str, Any],
        credit_agreement: Optional[CreditAgreement] = None
    ) -> PolicyDecision:
        """
        Evaluate a trade execution for compliance.
        
        Args:
            cdm_event: CDM TradeExecution event dictionary
            credit_agreement: Optional source credit agreement
            
        Returns:
            PolicyDecision
        """
        tx = self._cdm_trade_event_to_policy_transaction(cdm_event, credit_agreement)
        result = self.engine.evaluate(tx)
        
        # Extract trade ID from CDM event
        trade_id = "unknown"
        try:
            trade = cdm_event.get("trade", {})
            trade_identifier = trade.get("tradeIdentifier", {})
            assigned_ids = trade_identifier.get("assignedIdentifier", [])
            if assigned_ids:
                trade_id = assigned_ids[0].get("identifier", {}).get("value", "unknown")
        except (KeyError, IndexError, AttributeError):
            pass
        
        return PolicyDecision(
            decision=result["decision"],
            rule_applied=result.get("rule"),
            trace_id=f"trade_{trade_id}_{datetime.utcnow().isoformat()}",
            trace=result.get("trace", []),
            matched_rules=result.get("matched_rules", []),
            metadata={"cdm_event_type": "TradeExecution", "trade_id": trade_id}
        )
    
    def evaluate_loan_asset(
        self,
        loan_asset: LoanAsset,
        credit_agreement: Optional[CreditAgreement] = None
    ) -> PolicyDecision:
        """
        Evaluate loan asset securitization for compliance.
        
        Args:
            loan_asset: LoanAsset model instance
            credit_agreement: Optional source credit agreement
            
        Returns:
            PolicyDecision
        """
        tx = self._loan_asset_to_policy_transaction(loan_asset, credit_agreement)
        result = self.engine.evaluate(tx)
        
        return PolicyDecision(
            decision=result["decision"],
            rule_applied=result.get("rule"),
            trace_id=f"asset_{loan_asset.loan_id}_{datetime.utcnow().isoformat()}",
            trace=result.get("trace", []),
            matched_rules=result.get("matched_rules", []),
            metadata={"loan_asset_id": loan_asset.id, "loan_id": loan_asset.loan_id}
        )
    
    def evaluate_terms_change(
        self,
        trade_id: str,
        current_rate: float,
        proposed_rate: float,
        reason: str
    ) -> PolicyDecision:
        """
        Evaluate interest rate change for compliance.
        
        Args:
            trade_id: Trade identifier
            current_rate: Current interest rate
            proposed_rate: Proposed new rate
            reason: Reason for change
            
        Returns:
            PolicyDecision
        """
        tx = {
            "transaction_id": f"terms_change_{trade_id}",
            "transaction_type": "terms_change",
            "timestamp": datetime.utcnow().isoformat(),
            "current_rate": current_rate,
            "proposed_rate": proposed_rate,
            "rate_delta": proposed_rate - current_rate,
            "reason": reason,
            "context": "InterestRateAdjustment"
        }
        
        result = self.engine.evaluate(tx)
        
        return PolicyDecision(
            decision=result["decision"],
            rule_applied=result.get("rule"),
            trace_id=f"terms_{trade_id}_{datetime.utcnow().isoformat()}",
            trace=result.get("trace", []),
            matched_rules=result.get("matched_rules", []),
            metadata={"trade_id": trade_id}
        )
    
    # Private helper methods for CDM mapping
    def _cdm_to_policy_transaction(
        self,
        credit_agreement: CreditAgreement,
        transaction_type: str
    ) -> Dict[str, Any]:
        """Convert CDM CreditAgreement to policy transaction format."""
        # Find borrower from parties list
        borrower = next(
            (p for p in (credit_agreement.parties or []) if "borrower" in p.role.lower()),
            None
        )
        
        # Calculate total commitment from all facilities
        total_commitment = Decimal("0")
        if credit_agreement.facilities:
            for facility in credit_agreement.facilities:
                if facility.commitment_amount:
                    total_commitment += facility.commitment_amount.amount
        
        # Extract currency from first facility (assume all facilities use same currency)
        currency = "USD"  # Default
        if credit_agreement.facilities and credit_agreement.facilities[0].commitment_amount:
            currency = credit_agreement.facilities[0].commitment_amount.currency.value
        
        # Extract ESG KPI targets
        esg_kpi_targets = []
        if credit_agreement.esg_kpi_targets:
            for kpi in credit_agreement.esg_kpi_targets:
                esg_kpi_targets.append({
                    "kpi_type": kpi.kpi_type.value if hasattr(kpi.kpi_type, 'value') else str(kpi.kpi_type),
                    "target_value": kpi.target_value,
                    "unit": kpi.unit
                })
        
        return {
            "transaction_id": credit_agreement.deal_id or credit_agreement.loan_identification_number or "unknown",
            "transaction_type": transaction_type,
            "timestamp": datetime.utcnow().isoformat(),
            "originator": {
                "id": borrower.id if borrower else "unknown",
                "name": borrower.name if borrower else "unknown",
                "role": borrower.role if borrower else "Borrower",
                "lei": borrower.lei,
                "kyc_status": True,  # Assume KYC'd if in CDM
                "jurisdiction": credit_agreement.governing_law.value if hasattr(credit_agreement.governing_law, 'value') else str(credit_agreement.governing_law) if credit_agreement.governing_law else "Unknown"
            },
            "amount": float(total_commitment),
            "currency": currency,
            "facility_name": credit_agreement.facilities[0].facility_name if credit_agreement.facilities else None,
            "facility_type": "SyndicatedLoan",
            "sustainability_linked": credit_agreement.sustainability_linked or False,
            "esg_kpi_targets": esg_kpi_targets,
            "governing_law": credit_agreement.governing_law.value if hasattr(credit_agreement.governing_law, 'value') else str(credit_agreement.governing_law) if credit_agreement.governing_law else "Unknown",
            "regulatory_framework": self._infer_regulatory_framework(credit_agreement),
            "context": "CreditAgreement_Creation"
        }
        
        # Add green finance metrics if available from loan assets
        if credit_agreement.loan_assets:
            # Get enhanced metrics from first loan asset with location
            for loan_asset in credit_agreement.loan_assets:
                if hasattr(loan_asset, 'geo_lat') and loan_asset.geo_lat and loan_asset.geo_lon:
                    # Get green finance metrics from loan asset
                    if hasattr(loan_asset, 'green_finance_metrics') and loan_asset.green_finance_metrics:
                        green_metrics = loan_asset.green_finance_metrics
                        tx.update({
                            "location_type": green_metrics.get("location_type") or loan_asset.location_type if hasattr(loan_asset, 'location_type') else None,
                            "air_quality_index": green_metrics.get("air_quality_index") or loan_asset.air_quality_index if hasattr(loan_asset, 'air_quality_index') else None,
                            "composite_sustainability_score": green_metrics.get("composite_sustainability_score") or loan_asset.composite_sustainability_score if hasattr(loan_asset, 'composite_sustainability_score') else None,
                            "road_density": green_metrics.get("osm_metrics", {}).get("road_density"),
                            "building_density": green_metrics.get("osm_metrics", {}).get("building_density"),
                            "green_infrastructure_coverage": green_metrics.get("osm_metrics", {}).get("green_infrastructure_coverage"),
                            "pm25": green_metrics.get("air_quality", {}).get("pm25"),
                            "pm10": green_metrics.get("air_quality", {}).get("pm10"),
                            "no2": green_metrics.get("air_quality", {}).get("no2"),
                            "sustainability_components": green_metrics.get("sustainability_components")
                        })
                    elif hasattr(loan_asset, 'location_type'):
                        # Fallback to direct fields if green_finance_metrics not populated
                        tx.update({
                            "location_type": loan_asset.location_type,
                            "air_quality_index": loan_asset.air_quality_index if hasattr(loan_asset, 'air_quality_index') else None,
                            "composite_sustainability_score": loan_asset.composite_sustainability_score if hasattr(loan_asset, 'composite_sustainability_score') else None
                        })
                    break
    
    def _cdm_trade_event_to_policy_transaction(
        self,
        cdm_event: Dict[str, Any],
        credit_agreement: Optional[CreditAgreement] = None
    ) -> Dict[str, Any]:
        """Convert CDM TradeExecution event to policy transaction."""
        trade = cdm_event.get("trade", {})
        tradable_product = trade.get("tradableProduct", {})
        counterparties = tradable_product.get("counterparty", [])
        economic_terms = tradable_product.get("economicTerms", {})
        notional = economic_terms.get("notional", {})
        
        # Extract originator (first counterparty)
        originator_id = "unknown"
        if counterparties:
            originator = counterparties[0]
            party_ref = originator.get("partyReference", {})
            originator_id = party_ref.get("globalReference", "unknown")
        
        # Extract beneficiary (second counterparty if exists)
        beneficiary_id = None
        if len(counterparties) > 1:
            beneficiary = counterparties[1]
            party_ref = beneficiary.get("partyReference", {})
            beneficiary_id = party_ref.get("globalReference")
        
        # Extract amount and currency
        amount = 0.0
        currency = "USD"
        if notional:
            amount_obj = notional.get("amount", {})
            amount = float(amount_obj.get("value", 0.0))
            currency_obj = notional.get("currency", {})
            currency = currency_obj.get("value", "USD")
        
        # Extract trade identifier
        trade_id = "unknown"
        trade_identifier = trade.get("tradeIdentifier", {})
        assigned_ids = trade_identifier.get("assignedIdentifier", [])
        if assigned_ids:
            trade_id = assigned_ids[0].get("identifier", {}).get("value", "unknown")
        
        return {
            "transaction_id": trade_id,
            "transaction_type": "trade_execution",
            "timestamp": cdm_event.get("eventDate", datetime.utcnow().isoformat()),
            "originator": {
                "id": originator_id,
                "kyc_status": True,  # Assume KYC'd for CDM events
                "jurisdiction": "Unknown"
            },
            "beneficiary": {
                "id": beneficiary_id,
                "kyc_status": True
            } if beneficiary_id else None,
            "amount": amount,
            "currency": currency,
            "interest_rate": self._extract_rate_from_cdm(cdm_event),
            "context": "TradeExecution"
        }
    
    def _loan_asset_to_policy_transaction(
        self,
        loan_asset: LoanAsset,
        credit_agreement: Optional[CreditAgreement] = None
    ) -> Dict[str, Any]:
        """Convert LoanAsset to policy transaction."""
        return {
            "transaction_id": loan_asset.loan_id,
            "transaction_type": "loan_asset_securitization",
            "timestamp": loan_asset.created_at.isoformat() if loan_asset.created_at else datetime.utcnow().isoformat(),
            "amount": 0,  # Not applicable for asset verification
            "currency": "USD",  # Default
            "spt_threshold": loan_asset.spt_threshold,
            "ndvi_score": loan_asset.last_verified_score,
            "risk_status": loan_asset.risk_status,
            "collateral_address": loan_asset.collateral_address,
            "geo_lat": loan_asset.geo_lat,
            "geo_lon": loan_asset.geo_lon,
            "context": "LoanAsset_Securitization"
        }
    
    def _infer_regulatory_framework(self, credit_agreement: CreditAgreement) -> List[str]:
        """Infer applicable regulatory frameworks from credit agreement."""
        frameworks = []
        
        # ESG compliance
        if credit_agreement.sustainability_linked:
            frameworks.append("ESG_Compliance")
        
        # US regulations based on jurisdiction
        governing_law = credit_agreement.governing_law
        if governing_law:
            gov_law_str = governing_law.value if hasattr(governing_law, 'value') else str(governing_law)
            if gov_law_str in ["NY", "Delaware", "California"]:
                frameworks.append("US_Regulations")
        
        # MiCA (Markets in Crypto-Assets) for EUR transactions
        if credit_agreement.facilities:
            for facility in credit_agreement.facilities:
                if facility.commitment_amount:
                    currency = facility.commitment_amount.currency
                    currency_str = currency.value if hasattr(currency, 'value') else str(currency)
                    if "EUR" in currency_str:
                        frameworks.append("MiCA")
                        break
        
        # Basel III (applies to all large financial institutions)
        # Could add logic here to check if parties are banks
        
        # FATF (Financial Action Task Force) - applies globally
        frameworks.append("FATF")
        
        return frameworks
    
    # Credit Risk Evaluation Methods
    
    def evaluate_credit_risk(
        self,
        credit_agreement: CreditAgreement,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform full credit risk assessment.
        
        Args:
            credit_agreement: CDM CreditAgreement
            additional_context: Optional additional context (borrower financials, etc.)
            
        Returns:
            Dictionary with credit risk assessment results
        """
        # Map CDM to credit risk fields
        credit_risk_fields = self.credit_risk_mapper.map_cdm_to_credit_risk_fields(
            credit_agreement=credit_agreement,
            additional_context=additional_context
        )
        
        # Calculate RWA and capital requirements
        if "exposure_at_default" in credit_risk_fields:
            ead = Decimal(str(credit_risk_fields["exposure_at_default"]))
            pd = credit_risk_fields.get("probability_of_default", 0.01)
            lgd = credit_risk_fields.get("loss_given_default", 0.45)
            maturity = credit_risk_fields.get("maturity_years", 1.0)
            asset_class = credit_risk_fields.get("asset_class", "corporate")
            approach = credit_risk_fields.get("risk_model_approach", "standardized")
            
            # Calculate RWA
            rwa = self.credit_risk_service.calculate_rwa(
                exposure=ead,
                pd=pd,
                lgd=lgd,
                maturity=maturity,
                asset_class=asset_class,
                approach=approach
            )
            credit_risk_fields["risk_weighted_assets"] = float(rwa)
            
            # Calculate capital requirements
            capital_requirement = self.credit_risk_service.calculate_capital_requirement(rwa)
            credit_risk_fields["capital_requirement"] = float(capital_requirement)
            
            tier1_requirement = self.credit_risk_service.calculate_tier1_capital_requirement(rwa)
            credit_risk_fields["tier1_capital_requirement"] = float(tier1_requirement)
        
        # Assess creditworthiness if borrower data available
        if additional_context:
            borrower_data = {
                "credit_score": additional_context.get("credit_score"),
                "debt_service_coverage_ratio": additional_context.get("debt_service_coverage_ratio"),
                "leverage_ratio": additional_context.get("leverage_ratio"),
                "net_worth": additional_context.get("net_worth"),
                "free_cash_flow": additional_context.get("free_cash_flow"),
            }
            if any(borrower_data.values()):
                creditworthiness = self.credit_risk_service.assess_creditworthiness(borrower_data)
                credit_risk_fields.update(creditworthiness)
        
        return credit_risk_fields
    
    def calculate_capital_requirements(
        self,
        rwa: Decimal,
        capital_ratio: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """
        Calculate capital requirements for given RWA.
        
        Args:
            rwa: Risk-weighted assets
            capital_ratio: Optional capital ratio (default: 8%)
            
        Returns:
            Dictionary with capital requirement breakdown
        """
        capital_requirement = self.credit_risk_service.calculate_capital_requirement(
            rwa=rwa,
            capital_ratio=capital_ratio
        )
        
        tier1_requirement = self.credit_risk_service.calculate_tier1_capital_requirement(rwa)
        
        return {
            "risk_weighted_assets": float(rwa),
            "capital_requirement": float(capital_requirement),
            "tier1_capital_requirement": float(tier1_requirement),
            "capital_ratio": float(capital_ratio) if capital_ratio else 0.08,
            "tier1_ratio": float(tier1_requirement / rwa) if rwa > 0 else 0.0
        }
    
    def assess_creditworthiness(
        self,
        credit_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Assess borrower creditworthiness.
        
        Args:
            credit_data: Dictionary with credit metrics (credit_score, financial_ratios, etc.)
            
        Returns:
            Dictionary with rating, score, and rationale
        """
        return self.credit_risk_service.assess_creditworthiness(credit_data)
    
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
        return self.credit_risk_service.validate_collateral(collateral_data, facility_amount)
    
    def _extract_rate_from_cdm(self, cdm_event: Dict[str, Any]) -> Optional[float]:
        """Extract interest rate from CDM event (helper method)."""
        try:
            trade = cdm_event.get("trade", {})
            tradable_product = trade.get("tradableProduct", {})
            economic_terms = tradable_product.get("economicTerms", {})
            
            # Try to extract rate from various possible locations
            # This is a simplified extraction - may need adjustment based on actual CDM structure
            rate_schedule = economic_terms.get("rateSchedule", {})
            if rate_schedule:
                # Extract first rate value if available
                pass  # Implementation depends on CDM rate structure
            
            return None  # Return None if rate cannot be extracted
        except (KeyError, AttributeError, TypeError):
            return None
    
    def evaluate_with_cdm_process(
        self,
        cdm_event: Dict[str, Any],
        credit_agreement: Optional[CreditAgreement] = None
    ) -> Dict[str, Any]:
        """
        CDM-compliant policy evaluation following CDM process model.
        
        CDM Process Model:
        1. VALIDATION: Validate CDM event structure
        2. CALCULATION: Evaluate policy rules
        3. EVENT CREATION: Create PolicyEvaluation CDM event
        
        This method ensures full CDM compliance by:
        - Validating event structure before processing
        - Following deterministic evaluation process
        - Creating machine-readable and machine-executable CDM events
        
        Args:
            cdm_event: CDM event dictionary (TradeExecution, Observation, TermsChange, etc.)
            credit_agreement: Optional source credit agreement for context
            
        Returns:
            Dictionary containing:
            {
                "policy_evaluation_event": CDM PolicyEvaluation event,
                "decision": "ALLOW" | "BLOCK" | "FLAG",
                "rule_applied": Optional[str],
                "matched_rules": List[str],
                "trace": List[Dict[str, Any]]
            }
            
        Raises:
            ValueError: If CDM event structure is invalid
        """
        # STEP 1: VALIDATION (CDM principle)
        self._validate_cdm_event(cdm_event)
        
        # STEP 2: CALCULATION (Policy evaluation)
        # Convert CDM event to policy transaction format
        policy_transaction = self._cdm_trade_event_to_policy_transaction(cdm_event, credit_agreement)
        
        # Evaluate using policy engine
        evaluation_result = self.engine.evaluate(policy_transaction)
        
        # STEP 3: EVENT CREATION (CDM event model)
        # Extract transaction identifier from CDM event
        transaction_id = self._extract_transaction_id_from_cdm(cdm_event)
        transaction_type = self._infer_transaction_type(cdm_event)
        
        # Build related event identifiers
        related_event_identifiers = []
        if "meta" in cdm_event and "globalKey" in cdm_event["meta"]:
            related_event_identifiers.append({
                "eventIdentifier": {
                    "issuer": "CreditNexus",
                    "assignedIdentifier": [{
                        "identifier": {
                            "value": cdm_event["meta"]["globalKey"]
                        }
                    }]
                }
            })
        
        # Create CDM PolicyEvaluation event
        policy_event = generate_cdm_policy_evaluation(
            transaction_id=transaction_id,
            transaction_type=transaction_type,
            decision=evaluation_result["decision"],
            rule_applied=evaluation_result.get("rule"),
            related_event_identifiers=related_event_identifiers,
            evaluation_trace=evaluation_result.get("trace", []),
            matched_rules=evaluation_result.get("matched_rules", [])
        )
        
        return {
            "policy_evaluation_event": policy_event,
            "decision": evaluation_result["decision"],
            "rule_applied": evaluation_result.get("rule"),
            "matched_rules": evaluation_result.get("matched_rules", []),
            "trace": evaluation_result.get("trace", [])
        }
    
    def _validate_cdm_event(self, cdm_event: Dict[str, Any]) -> None:
        """
        Validate CDM event structure (CDM compliance requirement).
        
        Ensures the event follows CDM event model:
        - eventType: Required string
        - eventDate: Required ISO 8601 timestamp
        - meta.globalKey: Required unique identifier
        - Event-specific structure based on eventType
        
        Args:
            cdm_event: CDM event dictionary to validate
            
        Raises:
            ValueError: If event structure is invalid
        """
        if not isinstance(cdm_event, dict):
            raise ValueError("CDM event must be a dictionary")
        
        # Validate required top-level fields
        if "eventType" not in cdm_event:
            raise ValueError("CDM event missing required field: eventType")
        
        if "eventDate" not in cdm_event:
            raise ValueError("CDM event missing required field: eventDate")
        
        # Validate eventDate format (should be ISO 8601)
        try:
            from datetime import datetime
            # Try to parse the date
            datetime.fromisoformat(cdm_event["eventDate"].replace("Z", "+00:00"))
        except (ValueError, AttributeError, TypeError):
            raise ValueError(
                f"CDM event eventDate must be ISO 8601 format, got: {cdm_event.get('eventDate')}"
            )
        
        # Validate meta.globalKey (required for CDM compliance)
        if "meta" not in cdm_event:
            raise ValueError("CDM event missing required field: meta")
        
        if not isinstance(cdm_event["meta"], dict):
            raise ValueError("CDM event meta must be a dictionary")
        
        if "globalKey" not in cdm_event["meta"]:
            raise ValueError("CDM event meta missing required field: globalKey")
        
        # Validate eventType-specific structure
        event_type = cdm_event["eventType"]
        
        if event_type == "TradeExecution":
            if "trade" not in cdm_event:
                raise ValueError("TradeExecution event missing required field: trade")
        
        elif event_type == "Observation":
            if "observation" not in cdm_event:
                raise ValueError("Observation event missing required field: observation")
        
        elif event_type == "TermsChange":
            if "tradeState" not in cdm_event:
                raise ValueError("TermsChange event missing required field: tradeState")
        
        elif event_type == "PolicyEvaluation":
            if "policyEvaluation" not in cdm_event:
                raise ValueError("PolicyEvaluation event missing required field: policyEvaluation")
        
        # Additional validation could be added for other event types
        logger.debug(f"CDM event validation passed for eventType: {event_type}")
    
    def _extract_transaction_id_from_cdm(self, cdm_event: Dict[str, Any]) -> str:
        """Extract transaction ID from CDM event."""
        event_type = cdm_event.get("eventType", "")
        
        if event_type == "TradeExecution":
            trade = cdm_event.get("trade", {})
            trade_identifier = trade.get("tradeIdentifier", {})
            assigned_ids = trade_identifier.get("assignedIdentifier", [])
            if assigned_ids:
                return assigned_ids[0].get("identifier", {}).get("value", "unknown")
        
        elif event_type == "Observation":
            observation = cdm_event.get("observation", {})
            related_trade_ids = observation.get("relatedTradeIdentifier", [])
            if related_trade_ids:
                return related_trade_ids[0].get("identifier", {}).get("value", "unknown")
        
        elif event_type == "TermsChange":
            trade_state = cdm_event.get("tradeState", {})
            trade_identifiers = trade_state.get("tradeIdentifier", [])
            if trade_identifiers:
                return trade_identifiers[0].get("identifier", {}).get("value", "unknown")
        
        # Fallback to globalKey if available
        if "meta" in cdm_event and "globalKey" in cdm_event["meta"]:
            return cdm_event["meta"]["globalKey"]
        
        return "unknown"
    
    def _infer_transaction_type(self, cdm_event: Dict[str, Any]) -> str:
        """Infer transaction type from CDM event."""
        event_type = cdm_event.get("eventType", "")
        
        # Map CDM event types to policy transaction types
        event_type_map = {
            "TradeExecution": "trade_execution",
            "Observation": "observation",
            "TermsChange": "terms_change",
            "PolicyEvaluation": "policy_evaluation"
        }
        
        return event_type_map.get(event_type, "unknown")
    
    # Green Finance Evaluation Methods
    
    def evaluate_green_finance_compliance(
        self,
        credit_agreement: CreditAgreement,
        loan_asset: Optional[LoanAsset] = None,
        document_id: Optional[int] = None
    ) -> PolicyDecision:
        """
        Evaluate green finance compliance for a credit agreement.
        
        Loads all green finance policy rules and evaluates against enhanced
        satellite metrics (OSM, air quality, sustainability score).
        
        Args:
            credit_agreement: CDM CreditAgreement
            loan_asset: Optional LoanAsset with enhanced metrics
            document_id: Optional document ID for audit trail
            
        Returns:
            PolicyDecision with comprehensive compliance assessment
        """
        # Get enhanced metrics from loan asset if available
        enhanced_metrics = {}
        if loan_asset and hasattr(loan_asset, 'green_finance_metrics') and loan_asset.green_finance_metrics:
            enhanced_metrics = loan_asset.green_finance_metrics
        
        # Convert CDM to policy transaction with green finance metrics
        tx = self._cdm_to_policy_transaction(
            credit_agreement=credit_agreement,
            transaction_type="facility_creation"
        )
        
        # Add green finance metrics if available
        if enhanced_metrics:
            tx.update({
                "location_type": enhanced_metrics.get("location_type"),
                "air_quality_index": enhanced_metrics.get("air_quality_index"),
                "composite_sustainability_score": enhanced_metrics.get("composite_sustainability_score"),
                "road_density": enhanced_metrics.get("osm_metrics", {}).get("road_density"),
                "building_density": enhanced_metrics.get("osm_metrics", {}).get("building_density"),
                "green_infrastructure_coverage": enhanced_metrics.get("osm_metrics", {}).get("green_infrastructure_coverage"),
                "pm25": enhanced_metrics.get("air_quality", {}).get("pm25") if isinstance(enhanced_metrics.get("air_quality"), dict) else None,
                "pm10": enhanced_metrics.get("air_quality", {}).get("pm10") if isinstance(enhanced_metrics.get("air_quality"), dict) else None,
                "no2": enhanced_metrics.get("air_quality", {}).get("no2") if isinstance(enhanced_metrics.get("air_quality"), dict) else None
            })
        
        # Evaluate against all policy rules (including green finance)
        result = self.engine.evaluate(tx)
        
        return PolicyDecision(
            decision=result["decision"],
            rule_applied=result.get("rule"),
            trace_id=f"green_finance_{document_id}_{datetime.utcnow().isoformat()}" if document_id else f"green_finance_{datetime.utcnow().isoformat()}",
            trace=result.get("trace", []),
            matched_rules=result.get("matched_rules", []),
            metadata={
                "document_id": document_id,
                "green_finance_assessment": True,
                "enhanced_metrics_used": bool(enhanced_metrics)
            }
        )
    
    async def assess_urban_sustainability(
        self,
        location_lat: float,
        location_lon: float,
        osm_data: Optional[Dict[str, Any]] = None,
        air_quality: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Assess urban sustainability for a location.
        
        Args:
            location_lat: Location latitude
            location_lon: Location longitude
            osm_data: Optional pre-fetched OSM data
            air_quality: Optional pre-fetched air quality data
            
        Returns:
            Dictionary with sustainability metrics and compliance status
        """
        from app.services.osm_service import OSMService
        from app.services.location_classifier import LocationClassifier
        from app.services.air_quality_service import AirQualityService
        
        osm_service = OSMService()
        location_classifier = LocationClassifier()
        air_quality_service = AirQualityService()
        
        # Get OSM data if not provided
        if osm_data is None:
            osm_data = await osm_service.get_osm_features(location_lat, location_lon)
        
        # Classify location
        location_type, confidence = await location_classifier.classify(location_lat, location_lon, osm_data)
        
        # Get air quality if not provided
        if air_quality is None:
            air_quality = await air_quality_service.get_air_quality(location_lat, location_lon)
        
        # Calculate urban sustainability score
        road_density = osm_data.get("road_density", 0.0)
        building_density = osm_data.get("building_density", 0.0)
        green_coverage = osm_data.get("green_coverage", 0.0)
        aqi = air_quality.get("aqi", 50.0)
        
        # Urban sustainability scoring (0.0-1.0)
        # Factors: green infrastructure, air quality, moderate activity
        green_score = green_coverage * 0.4
        aqi_score = max(0.0, 1.0 - (aqi / 200.0)) * 0.3
        activity_score = min(1.0, (road_density + building_density) / 10.0) * 0.3
        
        urban_sustainability_score = green_score + aqi_score + activity_score
        
        return {
            "location_type": location_type,
            "location_confidence": confidence,
            "urban_sustainability_score": urban_sustainability_score,
            "metrics": {
                "road_density": road_density,
                "building_density": building_density,
                "green_coverage": green_coverage,
                "air_quality_index": aqi
            },
            "compliance_status": "compliant" if urban_sustainability_score >= 0.6 else "needs_improvement"
        }
    
    async def monitor_emissions_compliance(
        self,
        location_lat: float,
        location_lon: float,
        air_quality: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Monitor emissions and air quality compliance.
        
        Args:
            location_lat: Location latitude
            location_lon: Location longitude
            air_quality: Optional pre-fetched air quality data
            
        Returns:
            Dictionary with compliance status and violation details
        """
        from app.services.air_quality_service import AirQualityService
        
        air_quality_service = AirQualityService()
        
        # Get air quality if not provided
        if air_quality is None:
            air_quality = await air_quality_service.get_air_quality(location_lat, location_lon)
        
        aqi = air_quality.get("aqi", 50.0)
        pm25 = air_quality.get("pm25", 0.0)
        pm10 = air_quality.get("pm10", 0.0)
        no2 = air_quality.get("no2", 0.0)
        
        # EU Air Quality Directive limits
        violations = []
        compliance_status = "compliant"
        
        if pm25 and pm25 > 25:  # EU annual limit: 25 µg/m³
            violations.append({"parameter": "PM2.5", "value": pm25, "limit": 25, "unit": "µg/m³"})
            compliance_status = "non_compliant"
        elif pm25 and pm25 > 20:  # WHO guideline: 20 µg/m³
            violations.append({"parameter": "PM2.5", "value": pm25, "limit": 20, "unit": "µg/m³ (WHO guideline)"})
            compliance_status = "warning"
        
        if pm10 and pm10 > 40:  # EU annual limit: 40 µg/m³
            violations.append({"parameter": "PM10", "value": pm10, "limit": 40, "unit": "µg/m³"})
            compliance_status = "non_compliant"
        
        if no2 and no2 > 200:  # EU hourly limit: 200 µg/m³
            violations.append({"parameter": "NO2", "value": no2, "limit": 200, "unit": "µg/m³"})
            compliance_status = "non_compliant"
        
        if aqi > 150:  # Unhealthy AQI
            violations.append({"parameter": "AQI", "value": aqi, "limit": 150, "unit": "AQI"})
            compliance_status = "non_compliant"
        elif aqi > 100:  # Unhealthy for Sensitive Groups
            violations.append({"parameter": "AQI", "value": aqi, "limit": 100, "unit": "AQI (sensitive groups)"})
            if compliance_status == "compliant":
                compliance_status = "warning"
        
        return {
            "compliance_status": compliance_status,
            "air_quality_index": aqi,
            "violations": violations,
            "measurements": {
                "pm25": pm25,
                "pm10": pm10,
                "no2": no2
            }
        }
    
    def evaluate_sdg_alignment(
        self,
        location_lat: float,
        location_lon: float,
        sustainability_components: Optional[Dict[str, float]] = None,
        green_finance_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate SDG alignment for a location.
        
        Maps environmental metrics to SDG targets and calculates alignment scores.
        
        Args:
            location_lat: Location latitude
            location_lon: Location longitude
            sustainability_components: Optional sustainability component scores
            green_finance_metrics: Optional comprehensive green finance metrics
            
        Returns:
            Dictionary with SDG alignment scores per goal and overall alignment
        """
        # Map to relevant SDGs
        sdg_scores = {}
        
        if sustainability_components:
            # SDG 11: Sustainable Cities and Communities
            # Based on urban activity, green infrastructure
            urban_activity = sustainability_components.get("urban_activity", 0.5)
            green_infra = sustainability_components.get("green_infrastructure", 0.5)
            sdg_scores["SDG_11"] = (urban_activity + green_infra) / 2.0
            
            # SDG 13: Climate Action
            # Based on air quality, pollution levels
            air_quality = sustainability_components.get("air_quality", 0.5)
            pollution = sustainability_components.get("pollution_levels", 0.5)
            sdg_scores["SDG_13"] = (air_quality + pollution) / 2.0
            
            # SDG 15: Life on Land
            # Based on vegetation health
            vegetation = sustainability_components.get("vegetation_health", 0.5)
            sdg_scores["SDG_15"] = vegetation
        
        if green_finance_metrics:
            # Additional SDG mapping from comprehensive metrics
            osm_metrics = green_finance_metrics.get("osm_metrics", {})
            green_coverage = osm_metrics.get("green_infrastructure_coverage", 0.0)
            
            # SDG 11: Enhance with green coverage
            if "SDG_11" not in sdg_scores:
                sdg_scores["SDG_11"] = green_coverage
            else:
                sdg_scores["SDG_11"] = (sdg_scores["SDG_11"] + green_coverage) / 2.0
        
        # Calculate overall SDG alignment (average of all SDG scores)
        overall_alignment = sum(sdg_scores.values()) / len(sdg_scores) if sdg_scores else 0.0
        
        return {
            "sdg_alignment": sdg_scores,
            "overall_alignment": overall_alignment,
            "aligned_goals": [goal for goal, score in sdg_scores.items() if score >= 0.7],
            "needs_improvement": [goal for goal, score in sdg_scores.items() if score < 0.5]
        }

