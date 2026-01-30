"""
FINOS CDM Event Generator for 'Kill Shot' Demo (Deep Tech Implementation)
Generates machine-executable JSON structures for Sustainbility-Linked Loans (SLL).
"""

from typing import Dict, Any, List, Optional
import datetime
import uuid

def generate_cdm_trade_execution(trade_id: str, borrower: str, amount: float, rate: float) -> Dict[str, Any]:
    """Generates the initial TradeExecution event JSON (TradeState v1)."""
    return {
        "eventType": "TradeExecution",
        "eventDate": datetime.date.today().isoformat(),
        "trade": {
            "tradeIdentifier": {
                "issuer": "CreditNexus_System",
                "assignedIdentifier": [{"identifier": {"value": trade_id}}]
            },
            "tradeDate": {"date": datetime.date.today().isoformat()},
            "tradableProduct": {
                "productType": "SustainabilityLinkedLoan",
                "counterparty": [
                    {"partyReference": {"globalReference": "US_BANK_NA"}},
                    {"partyReference": {"globalReference": borrower.upper().replace(" ", "_")}}
                ],
                "economicTerms": {
                    "notional": {
                        "currency": {"value": "USD"},
                        "amount": {"value": amount}
                    },
                    "effectiveDate": {"date": datetime.date.today().isoformat()},
                    "terminationDate": {"date": (datetime.date.today() + datetime.timedelta(days=365*5)).isoformat()},
                    "payout": {
                        "interestRatePayout": {
                            "payerReceiver": {
                                "payerPartyReference": {"globalReference": borrower.upper().replace(" ", "_")},
                                "receiverPartyReference": {"globalReference": "US_BANK_NA"}
                            },
                            "rateSpecification": {
                                "floatingRate": {
                                    "rateOption": {"value": "USD-SOFR-COMPOUND"},
                                    "spreadSchedule": {
                                        "initialValue": {"value": rate, "unit": "PERCENT"},
                                        "type": "SustainabilityLinkedSpread",
                                        "condition": "LAND_USE_COMPLIANCE_INDEX"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_Originator_v2",
            "version": 1
        }
    }

def generate_cdm_observation(trade_id: str, satellite_hash: str, ndvi_score: float, status: str) -> Dict[str, Any]:
    """Generates the Observation event from the Satellite (The 'Oracle')."""
    return {
        "eventType": "Observation",
        "eventDate": datetime.datetime.now().isoformat(),
        "observation": {
            "relatedTradeIdentifier": [{"identifier": {"value": trade_id}}],
            "observationDate": {"date": datetime.date.today().isoformat()},
            "observedValue": {
                "value": status,
                "unit": "LAND_USE_COMPLIANCE_STATUS",
                "numericValue": ndvi_score,
                "context": {
                     "classification": "AnnualCrop" if status == "BREACH" else "Forest",
                     "confidence": 0.9423
                }
            },
            "informationSource": {
                "sourceProvider": "CreditNexus_TorchGeo_Sentinel2_Model_v1",
                "sourceType": "EarthObservation",
                "reference": {
                    "hash": satellite_hash,
                    "satellite": "Sentinel-2B",
                    "bands": ["B02", "B03", "B04", "B08", "B11", "B12"],
                    "processingLevel": "L2A_BOA_REFLECTANCE"
                }
            }
        }
    }

def generate_cdm_terms_change(
    trade_id: str,
    current_rate: float,
    status: str,
    policy_service=None  # Optional policy service for compliance evaluation
) -> Optional[Dict[str, Any]]:
    """
    Generates the TermsChange event (TradeState v2).
    Mathematically updates the spread based on the Observation.
    
    If policy_service is provided, evaluates the rate change against compliance
    policies before generating the event. Returns None if policy evaluation BLOCKS
    the rate change.
    
    Args:
        trade_id: Trade identifier
        current_rate: Current interest rate
        status: Compliance status (BREACH, COMPLIANT, etc.)
        policy_service: Optional policy service for compliance evaluation
        
    Returns:
        CDM TermsChange event dictionary, or None if blocked by policy
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Financial Logic: "The Contract is Code"
    # Base = 5.00%
    # Penalty = +1.50% (150 bps) if BREACH
    base_spread = 5.00
    penalty = 1.50 if status == "BREACH" else 0.00
    new_spread = base_spread + penalty
    proposed_rate = new_spread
    
    # Policy evaluation before rate change (if enabled)
    if policy_service:
        try:
            # Evaluate terms change for compliance
            policy_result = policy_service.evaluate_terms_change(
                trade_id=trade_id,
                current_rate=current_rate,
                proposed_rate=proposed_rate,
                reason="SustainabilityPerformanceTarget_Breach" if status == "BREACH" else "SustainabilityPerformanceTarget_Maintenance"
            )
            
            # Handle BLOCK decision - prevent rate change
            if policy_result.decision == "BLOCK":
                logger.warning(
                    f"Policy evaluation BLOCKED terms change: "
                    f"trade_id={trade_id}, current_rate={current_rate}, "
                    f"proposed_rate={proposed_rate}, rule={policy_result.rule_applied}, "
                    f"trace_id={policy_result.trace_id}"
                )
                # Return None to indicate rate change was blocked
                return None
            
            # Handle FLAG decision - allow but log for review
            elif policy_result.decision == "FLAG":
                logger.info(
                    f"Policy evaluation FLAGGED terms change: "
                    f"trade_id={trade_id}, rule={policy_result.rule_applied}, "
                    f"trace_id={policy_result.trace_id}"
                )
                # Continue with rate change but it's flagged
            
            # ALLOW decision - proceed normally
            else:
                logger.debug(
                    f"Policy evaluation ALLOWED terms change: "
                    f"trade_id={trade_id}, trace_id={policy_result.trace_id}"
                )
        
        except Exception as e:
            # Log policy evaluation errors but don't block rate change
            logger.error(f"Policy evaluation failed for terms change: {e}", exc_info=True)
            # Continue with rate change even if policy evaluation fails
    
    return {
        "eventType": "TermsChange",
        "eventDate": datetime.datetime.now().isoformat(),
        "tradeState": {
            "tradeIdentifier": [{"identifier": {"value": trade_id}}],
            "change": {
                "reason": "SustainabilityPerformanceTarget_Breach" if status == "BREACH" else "SustainabilityPerformanceTarget_Maintenance",
                "effectiveDate": {"date": datetime.date.today().isoformat()}
            },
            "updatedEconomicTerms": {
                "payout": {
                    "interestRatePayout": {
                        "rateSpecification": {
                            "floatingRate": {
                                "spreadSchedule": {
                                    "initialValue": {"value": new_spread, "unit": "PERCENT"},
                                    "delta": {"value": penalty, "unit": "BASIS_POINTS"},
                                    "calculationNote": f"Base {base_spread:.2f}% + Penalty {penalty:.2f}% due to {status} status."
                                }
                            }
                        }
                    }
                }
            }
        },
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_SmartContract_Engine",
            "previousEventReference": "OBSERVATION-001",
            "version": 2
        }
    }

def generate_cdm_credit_risk_assessment(
    transaction_id: str,
    risk_rating: str,
    probability_of_default: float,
    loss_given_default: float,
    exposure_at_default: float,
    risk_weighted_assets: float,
    capital_requirement: float,
    related_event_identifiers: List[Dict[str, Any]] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates CDM-compliant CreditRiskAssessment event.
    
    This event represents a credit risk assessment following CDM event model:
    - eventType: "CreditRiskAssessment"
    - eventDate: Timestamp
    - assessment: Risk ratings, PD/LGD/EAD, RWA, capital requirements
    - relatedEventIdentifier: Links to PolicyEvaluation, TradeExecution, etc.
    
    Args:
        transaction_id: Transaction/deal identifier
        risk_rating: Risk rating (AAA-D or 1-10)
        probability_of_default: PD (0-1)
        loss_given_default: LGD (0-1)
        exposure_at_default: EAD amount
        risk_weighted_assets: RWA amount
        capital_requirement: Capital requirement amount
        related_event_identifiers: List of related event identifiers
        additional_metrics: Optional additional credit risk metrics
        
    Returns:
        CDM-compliant CreditRiskAssessment event dictionary
    """
    if related_event_identifiers is None:
        related_event_identifiers = []
    if additional_metrics is None:
        additional_metrics = {}
    
    return {
        "eventType": "CreditRiskAssessment",
        "eventDate": datetime.datetime.now().isoformat(),
        "creditRiskAssessment": {
            "transactionIdentifier": {
                "issuer": "CreditNexus_CreditRiskService",
                "assignedIdentifier": [{"identifier": {"value": transaction_id}}]
            },
            "assessmentDate": {"date": datetime.date.today().isoformat()},
            "riskRating": {
                "value": risk_rating,
                "ratingAgency": additional_metrics.get("rating_agency", "Internal"),
                "ratingType": additional_metrics.get("rating_type", "internal")
            },
            "probabilityOfDefault": {
                "value": probability_of_default,
                "unit": "PROBABILITY",
                "calculationMethod": additional_metrics.get("pd_calculation_method", "IRB")
            },
            "lossGivenDefault": {
                "value": loss_given_default,
                "unit": "PROBABILITY",
                "calculationMethod": additional_metrics.get("lgd_calculation_method", "IRB")
            },
            "exposureAtDefault": {
                "value": exposure_at_default,
                "currency": additional_metrics.get("currency", {"value": "USD"}),
                "unit": "MONETARY_AMOUNT"
            },
            "riskWeightedAssets": {
                "value": risk_weighted_assets,
                "currency": additional_metrics.get("currency", {"value": "USD"}),
                "unit": "MONETARY_AMOUNT",
                "calculationApproach": additional_metrics.get("risk_model_approach", "IRB")
            },
            "capitalRequirement": {
                "value": capital_requirement,
                "currency": additional_metrics.get("currency", {"value": "USD"}),
                "unit": "MONETARY_AMOUNT",
                "capitalRatio": additional_metrics.get("capital_ratio", 0.08)
            },
            "tier1CapitalRequirement": additional_metrics.get("tier1_capital_requirement"),
            "leverageRatio": additional_metrics.get("leverage_ratio"),
            "liquidityCoverageRatio": additional_metrics.get("liquidity_coverage_ratio"),
            "creditScore": additional_metrics.get("credit_score"),
            "debtServiceCoverageRatio": additional_metrics.get("debt_service_coverage_ratio"),
            "collateralCoverageRatio": additional_metrics.get("collateral_coverage_ratio"),
            "assessmentRationale": additional_metrics.get("assessment_rationale")
        },
        "relatedEventIdentifier": related_event_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_CreditRiskService_v1",
            "version": 1
        }
    }


def generate_cdm_kyc_evaluation(
    profile_id: str,
    profile_type: str,  # "individual" or "business"
    profile_name: str,
    decision: str,  # "ALLOW", "BLOCK", "FLAG"
    rule_applied: Optional[str] = None,
    matched_rules: Optional[List[str]] = None,
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None,
    kyc_metrics: Optional[Dict[str, Any]] = None,
    deal_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates CDM-compliant KYC (Know Your Customer) evaluation event.
    
    This event represents a KYC compliance check following CDM event model:
    - eventType: "PolicyEvaluation" (reusing existing type)
    - eventDate: Timestamp
    - policyEvaluation: KYC decision, rules applied, metrics
    - relatedEventIdentifier: Links to profile creation, deal events
    
    Args:
        profile_id: Profile identifier (individual or business)
        profile_type: Type of profile ("individual" or "business")
        profile_name: Name of the individual or business
        decision: Policy decision ("ALLOW", "BLOCK", "FLAG")
        rule_applied: Name of rule that triggered the decision
        matched_rules: List of all matching rules
        related_event_identifiers: List of related event identifiers
        kyc_metrics: Optional KYC-specific metrics (risk scores, confidence, etc.)
        deal_id: Optional deal ID for context
        
    Returns:
        CDM-compliant PolicyEvaluation event dictionary for KYC
    """
    if related_event_identifiers is None:
        related_event_identifiers = []
    if matched_rules is None:
        matched_rules = []
    if kyc_metrics is None:
        kyc_metrics = {}
    
    return {
        "eventType": "PolicyEvaluation",
        "eventDate": datetime.datetime.now().isoformat(),
        "policyEvaluation": {
            "transactionIdentifier": {
                "issuer": "CreditNexus_KYCService",
                "assignedIdentifier": [{"identifier": {"value": f"kyc_{profile_type}_{profile_id}"}}]
            },
            "evaluationDate": {"date": datetime.date.today().isoformat()},
            "policyDecision": {
                "value": decision,
                "decisionType": "KYC_COMPLIANCE_CHECK"
            },
            "ruleApplied": rule_applied,
            "matchedRules": matched_rules,
            "evaluationContext": {
                "profileType": profile_type,
                "profileName": profile_name,
                "profileId": profile_id,
                "dealId": deal_id,
                **kyc_metrics
            },
            "evaluationTrace": kyc_metrics.get("trace", []),
            "evaluationRationale": kyc_metrics.get("rationale", f"KYC compliance check for {profile_type} profile: {profile_name}")
        },
        "relatedEventIdentifier": related_event_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_KYCService_v1",
            "version": 1
        }
    }


def generate_cdm_policy_evaluation(
    transaction_id: str,
    transaction_type: str,
    decision: str,  # "ALLOW", "BLOCK", "FLAG"
    rule_applied: str = None,
    related_event_identifiers: List[Dict[str, Any]] = None,
    evaluation_trace: List[Dict[str, Any]] = None,
    matched_rules: List[str] = None
) -> Dict[str, Any]:
    """
    Generates CDM-compliant PolicyEvaluation event.
    
    This event represents a policy engine decision following CDM event model:
    - eventType: "PolicyEvaluation"
    - eventDate: Timestamp
    - policyEvaluation: Policy evaluation details
    - relatedEventIdentifier: Links to TradeExecution, Observation, TermsChange, etc.
    
    Follows CDM principles:
    - Machine-readable and machine-executable format
    - Event relationships via relatedEventIdentifier
    - Full audit trail in evaluationTrace
    - Metadata for source system tracking
    
    Args:
        transaction_id: Unique identifier for the transaction being evaluated
        transaction_type: Type of transaction ("facility_creation", "trade_execution", etc.)
        decision: Policy decision ("ALLOW", "BLOCK", "FLAG")
        rule_applied: Name of the rule that triggered the decision
        related_event_identifiers: List of related CDM event identifiers
        evaluation_trace: Full evaluation trace for auditability
        matched_rules: List of all rules that matched during evaluation
        
    Returns:
        CDM-compliant PolicyEvaluation event dictionary
    """
    if related_event_identifiers is None:
        related_event_identifiers = []
    if evaluation_trace is None:
        evaluation_trace = []
    if matched_rules is None:
        matched_rules = []
    
    return {
        "eventType": "PolicyEvaluation",
        "eventDate": datetime.datetime.now().isoformat(),
        "policyEvaluation": {
            "transactionIdentifier": {
                "issuer": "CreditNexus_PolicyEngine",
                "assignedIdentifier": [{"identifier": {"value": transaction_id}}]
            },
            "transactionType": transaction_type,
            "decision": {
                "value": decision,
                "unit": "POLICY_DECISION",
                "enumeration": ["ALLOW", "BLOCK", "FLAG"]
            },
            "ruleApplied": rule_applied,
            "matchedRules": matched_rules,
            "evaluationTrace": evaluation_trace,
            "evaluationDate": {"date": datetime.date.today().isoformat()},
            "evaluationTimestamp": datetime.datetime.now().isoformat()
        },
        "relatedEventIdentifier": related_event_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_PolicyEngine_v1",
            "version": 1
        }
    }


def generate_green_finance_assessment(
    transaction_id: str,
    location_lat: float,
    location_lon: float,
    location_type: str,
    air_quality_index: float,
    composite_sustainability_score: float,
    sustainability_components: Dict[str, float],
    sdg_alignment: Optional[Dict[str, float]] = None,
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None,
    additional_metrics: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate CDM-compliant GreenFinanceAssessment event.
    
    This event represents a green finance assessment following CDM event model:
    - eventType: "GreenFinanceAssessment"
    - eventDate: Timestamp
    - greenFinanceAssessment: Environmental metrics, sustainability scores, SDG alignment
    - relatedEventIdentifier: Links to PolicyEvaluation, TradeExecution, etc.
    
    Args:
        transaction_id: Transaction/deal identifier
        location_lat: Location latitude
        location_lon: Location longitude
        location_type: Location classification ("urban", "suburban", "rural")
        air_quality_index: Air Quality Index (AQI) value
        composite_sustainability_score: Composite sustainability score (0.0-1.0)
        sustainability_components: Dictionary of component scores
        sdg_alignment: Optional SDG alignment scores per goal
        related_event_identifiers: List of related event identifiers
        additional_metrics: Optional additional green finance metrics
        
    Returns:
        CDM-compliant GreenFinanceAssessment event dictionary
    """
    if related_event_identifiers is None:
        related_event_identifiers = []
    if sdg_alignment is None:
        sdg_alignment = {}
    if additional_metrics is None:
        additional_metrics = {}
    
    return {
        "eventType": "GreenFinanceAssessment",
        "eventDate": datetime.datetime.now().isoformat(),
        "greenFinanceAssessment": {
            "transactionIdentifier": {
                "issuer": "CreditNexus_GreenFinanceService",
                "assignedIdentifier": [{"identifier": {"value": transaction_id}}]
            },
            "assessmentDate": {"date": datetime.date.today().isoformat()},
            "location": {
                "latitude": location_lat,
                "longitude": location_lon,
                "locationType": location_type
            },
            "environmentalMetrics": {
                "airQualityIndex": air_quality_index,
                "compositeSustainabilityScore": composite_sustainability_score,
                "sustainabilityComponents": sustainability_components,
                "pm25": additional_metrics.get("pm25"),
                "pm10": additional_metrics.get("pm10"),
                "no2": additional_metrics.get("no2")
            },
            "sdgAlignment": sdg_alignment,
            "osmMetrics": additional_metrics.get("osm_metrics", {}),
            "greenInfrastructureCoverage": additional_metrics.get("green_infrastructure_coverage")
        },
        "relatedEventIdentifier": related_event_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_GreenFinanceService_v1",
            "version": 1
        }
    }


def generate_cdm_filing_requirement(
    transaction_id: str,
    filing_requirement: Any,  # FilingRequirement dataclass
    credit_agreement: Optional[Any] = None,
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate CDM event for filing requirement.
    
    Args:
        transaction_id: Deal/transaction identifier
        filing_requirement: FilingRequirement object (from PolicyService)
        credit_agreement: Optional source credit agreement
        related_event_identifiers: Related CDM events
        
    Returns:
        CDM FilingRequirement event dictionary
    """
    if related_event_identifiers is None:
        related_event_identifiers = []
    
    return {
        "eventType": "FilingRequirement",
        "eventDate": datetime.datetime.now().isoformat(),
        "meta": {
            "globalKey": {
                "issuer": "CreditNexus",
                "assignedIdentifier": [{
                    "identifier": {
                        "value": f"filing_req_{transaction_id}_{datetime.datetime.now().timestamp()}"
                    }
                }]
            }
        },
        "transactionIdentifier": {
            "issuer": "CreditNexus",
            "assignedIdentifier": [{
                "identifier": {
                    "value": transaction_id
                }
            }]
        },
        "filingRequirement": {
            "authority": filing_requirement.authority,
            "filingSystem": filing_requirement.filing_system,
            "deadline": filing_requirement.deadline.isoformat() if hasattr(filing_requirement.deadline, 'isoformat') else str(filing_requirement.deadline),
            "requiredFields": filing_requirement.required_fields,
            "apiAvailable": filing_requirement.api_available,
            "apiEndpoint": filing_requirement.api_endpoint,
            "penalty": filing_requirement.penalty,
            "jurisdiction": filing_requirement.jurisdiction or "Unknown",
            "agreementType": filing_requirement.agreement_type or "Unknown",
            "formType": filing_requirement.form_type,
            "priority": filing_requirement.priority,
            "languageRequirement": filing_requirement.language_requirement
        },
        "relatedEventIdentifier": related_event_identifiers
    }


def generate_cdm_filing_submission(
    transaction_id: str,
    filing_id: int,
    filing_status: str,
    filing_reference: Optional[str] = None,
    filing_authority: Optional[str] = None,
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate CDM event for filing submission.
    
    Args:
        transaction_id: Deal/transaction identifier
        filing_id: DocumentFiling ID
        filing_status: "pending", "submitted", "accepted", "rejected"
        filing_reference: External filing reference (if available)
        filing_authority: Filing authority name
        related_event_identifiers: Related CDM events
        
    Returns:
        CDM FilingSubmission event dictionary
    """
    if related_event_identifiers is None:
        related_event_identifiers = []
    
    return {
        "eventType": "FilingSubmission",
        "eventDate": datetime.datetime.now().isoformat(),
        "meta": {
            "globalKey": {
                "issuer": "CreditNexus",
                "assignedIdentifier": [{
                    "identifier": {
                        "value": f"filing_sub_{filing_id}_{datetime.datetime.now().timestamp()}"
                    }
                }]
            }
        },
        "transactionIdentifier": {
            "issuer": "CreditNexus",
            "assignedIdentifier": [{
                "identifier": {
                    "value": transaction_id
                }
            }]
        },
        "filingSubmission": {
            "filingId": filing_id,
            "filingStatus": filing_status,
            "filingReference": filing_reference,
            "filingAuthority": filing_authority,
            "submittedAt": datetime.datetime.now().isoformat()
        },
        "relatedEventIdentifier": related_event_identifiers
    }


def generate_cdm_securitization_creation(
    pool_id: str,
    pool_name: str,
    pool_type: str,
    originator: str,
    trustee: str,
    total_pool_value: float,
    currency: str,
    underlying_assets: List[Dict[str, Any]],
    tranches: List[Dict[str, Any]],
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Generate CDM-compliant SecuritizationCreation event."""
    if related_event_identifiers is None:
        related_event_identifiers = []
    
    return {
        "eventType": "SecuritizationCreation",
        "eventDate": datetime.datetime.now().isoformat(),
        "securitizationCreation": {
            "poolIdentifier": {
                "issuer": "CreditNexus_SecuritizationService",
                "assignedIdentifier": [{"identifier": {"value": pool_id}}]
            },
            "poolName": pool_name,
            "poolType": pool_type,
            "originator": {"partyReference": {"globalReference": originator}},
            "trustee": {"partyReference": {"globalReference": trustee}},
            "totalPoolValue": {
                "currency": {"value": currency},
                "amount": {"value": float(total_pool_value)}
            },
            "underlyingAssets": underlying_assets,
            "tranches": tranches,
            "creationDate": {"date": datetime.date.today().isoformat()}
        },
        "relatedEventIdentifier": related_event_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_SecuritizationService_v1",
            "version": 1
        }
    }


def generate_cdm_notarization_event(
    notarization_id: str,
    deal_id: str,
    signers: List[Dict[str, Any]],
    notarization_hash: str,
    blockchain_tx_hash: Optional[str] = None
) -> Dict[str, Any]:
    """Generate CDM-compliant Notarization event for deal notarization.
    
    Args:
        notarization_id: Notarization record ID
        deal_id: Deal ID (can be None for securitization pools)
        signers: List of signer dictionaries with wallet_address and signature
        notarization_hash: Hash of the notarization payload
        blockchain_tx_hash: Optional blockchain transaction hash
        
    Returns:
        CDM-compliant Notarization event dictionary
    """
    return {
        "eventType": "Notarization",
        "eventDate": datetime.datetime.now().isoformat(),
        "notarization": {
            "notarizationIdentifier": {
                "issuer": "CreditNexus_NotarizationService",
                "assignedIdentifier": [{"identifier": {"value": f"NOTARIZATION_{notarization_id}"}}]
            },
            "dealIdentifier": {
                "issuer": "CreditNexus_DealService",
                "assignedIdentifier": [{"identifier": {"value": deal_id}}]
            } if deal_id and deal_id != "" else None,
            "notarizationHash": notarization_hash,
            "signers": signers,
            "blockchainTransactionHash": blockchain_tx_hash,
            "notarizationDate": {"date": datetime.date.today().isoformat()}
        },
        "meta": {
            "globalKey": {
                "issuer": "CreditNexus",
                "assignedIdentifier": [{"identifier": {"value": str(uuid.uuid4())}}]
            },
            "sourceSystem": "CreditNexus_NotarizationService_v1",
            "version": 1
        }
    }


def generate_cdm_signature_event(
    signature_id: str,
    document_id: int,
    deal_id: Optional[int],
    signer_name: str,
    signature_status: str,
    signature_method: str = "digital"
) -> Dict[str, Any]:
    """Generate CDM-compliant signature event.
    
    Args:
        signature_id: Signature record ID
        document_id: Document ID that was signed
        deal_id: Optional deal ID
        signer_name: Name/email of the signer
        signature_status: Status of the signature (completed, pending, etc.)
        signature_method: Method of signature (digital, electronic, etc.)
        
    Returns:
        CDM-compliant Signature event dictionary
    """
    return {
        "eventType": "SignatureEvent",
        "eventDate": datetime.datetime.now().isoformat(),
        "signature": {
            "signatureIdentifier": {
                "issuer": "CreditNexus_DealSignatureService",
                "assignedIdentifier": [{"identifier": {"value": f"SIG_{signature_id}"}}]
            },
            "documentIdentifier": {
                "issuer": "CreditNexus_DocumentService",
                "assignedIdentifier": [{"identifier": {"value": str(document_id)}}]
            },
            "dealIdentifier": {
                "issuer": "CreditNexus_DealService",
                "assignedIdentifier": [{"identifier": {"value": str(deal_id)}}]
            } if deal_id else None,
            "signerName": signer_name,
            "signatureStatus": signature_status,
            "signatureMethod": signature_method,
            "signatureDate": {"date": datetime.date.today().isoformat()}
        },
        "meta": {
            "globalKey": {
                "issuer": "CreditNexus",
                "assignedIdentifier": [{"identifier": {"value": str(uuid.uuid4())}}]
            },
            "sourceSystem": "CreditNexus_DealSignatureService_v1",
            "version": 1
        }
    }


def generate_cdm_documentation_event(
    document_id: int,
    deal_id: Optional[int],
    document_type: str,
    document_category: str,
    documentation_status: str,
    action: str = "added"  # added, updated, completed
) -> Dict[str, Any]:
    """Generate CDM-compliant documentation event.
    
    Args:
        document_id: Document ID
        deal_id: Optional deal ID
        document_type: Type of document
        document_category: Category of document
        documentation_status: Status of documentation (complete, pending, etc.)
        action: Action taken (added, updated, completed)
        
    Returns:
        CDM-compliant Documentation event dictionary
    """
    return {
        "eventType": "DocumentationEvent",
        "eventDate": datetime.datetime.now().isoformat(),
        "documentation": {
            "documentIdentifier": {
                "issuer": "CreditNexus_DocumentService",
                "assignedIdentifier": [{"identifier": {"value": str(document_id)}}]
            },
            "dealIdentifier": {
                "issuer": "CreditNexus_DealService",
                "assignedIdentifier": [{"identifier": {"value": str(deal_id)}}]
            } if deal_id else None,
            "documentType": document_type,
            "documentCategory": document_category,
            "documentationStatus": documentation_status,
            "action": action,
            "eventDate": {"date": datetime.date.today().isoformat()}
        },
        "meta": {
            "globalKey": {
                "issuer": "CreditNexus",
                "assignedIdentifier": [{"identifier": {"value": str(uuid.uuid4())}}]
            },
            "sourceSystem": "CreditNexus_DealSignatureService_v1",
            "version": 1
        }
    }


def generate_cdm_securitization_notarization(
    pool_id: str,
    notarization_hash: str,
    signers: List[Dict[str, Any]],
    blockchain_tx_hash: Optional[str] = None
) -> Dict[str, Any]:
    """Generate CDM-compliant SecuritizationNotarization event."""
    return {
        "eventType": "SecuritizationNotarization",
        "eventDate": datetime.datetime.now().isoformat(),
        "securitizationNotarization": {
            "poolIdentifier": {
                "issuer": "CreditNexus_SecuritizationService",
                "assignedIdentifier": [{"identifier": {"value": pool_id}}]
            },
            "notarizationHash": notarization_hash,
            "signers": signers,
            "blockchainTransactionHash": blockchain_tx_hash,
            "notarizationDate": {"date": datetime.date.today().isoformat()}
        },
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_NotarizationService_v1",
            "version": 1
        }
    }


def generate_cdm_loan_default(
    default_id: str,
    loan_id: Optional[str],
    deal_id: Optional[str],
    default_type: str,
    default_date: datetime.datetime,
    amount_overdue: Optional[float] = None,
    days_past_due: int = 0,
    severity: str = "low",
    default_reason: Optional[str] = None,
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate CDM-compliant Observation event for loan default.
    
    Args:
        default_id: Unique identifier for the default
        loan_id: Loan identifier (optional)
        deal_id: Deal identifier (optional)
        default_type: Type of default (payment_default, covenant_breach, infraction)
        default_date: Date when default occurred
        amount_overdue: Amount overdue (if payment default)
        days_past_due: Number of days past due
        severity: Severity level (low, medium, high, critical)
        default_reason: Reason for default (optional)
        related_event_identifiers: List of related event identifiers
        
    Returns:
        CDM-compliant Observation event dictionary
    """
    observation_value = {
        "value": default_type.upper(),
        "unit": "LOAN_DEFAULT_TYPE",
        "numericValue": days_past_due,
        "context": {
            "severity": severity,
            "daysPastDue": days_past_due
        }
    }
    
    if amount_overdue is not None:
        observation_value["context"]["amountOverdue"] = amount_overdue
    
    if default_reason:
        observation_value["context"]["reason"] = default_reason
    
    related_identifiers = related_event_identifiers or []
    
    # Add loan/facility identifier if provided
    if loan_id:
        related_identifiers.append({
            "eventIdentifier": {
                "issuer": "CreditNexus_LoanService",
                "assignedIdentifier": [{"identifier": {"value": loan_id}}]
            }
        })
    
    # Add deal identifier if provided
    if deal_id:
        related_identifiers.append({
            "eventIdentifier": {
                "issuer": "CreditNexus_DealService",
                "assignedIdentifier": [{"identifier": {"value": deal_id}}]
            }
        })
    
    return {
        "eventType": "Observation",
        "eventDate": default_date.isoformat() if isinstance(default_date, datetime.datetime) else default_date,
        "observation": {
            "observationType": "LoanDefault",
            "observationDate": {
                "date": default_date.date().isoformat() if isinstance(default_date, datetime.datetime) else default_date
            },
            "observedValue": observation_value,
            "informationSource": {
                "sourceProvider": "CreditNexus_RecoveryService",
                "sourceType": "LoanMonitoring",
                "reference": {
                    "defaultId": default_id,
                    "detectionMethod": "automated"
                }
            }
        },
        "relatedEventIdentifier": related_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_RecoveryService_v1",
            "version": 1
        }
    }


def generate_cdm_recovery_action(
    action_id: str,
    loan_default_id: str,
    action_type: str,
    communication_method: str,
    message_content: str,
    status: str = "pending",
    twilio_message_sid: Optional[str] = None,
    twilio_call_sid: Optional[str] = None,
    sent_at: Optional[datetime.datetime] = None,
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate CDM-compliant Observation event for recovery action.
    
    Args:
        action_id: Unique identifier for the recovery action
        loan_default_id: ID of the related loan default
        action_type: Type of action (sms_reminder, voice_call, email, escalation, legal_notice)
        communication_method: Method used (sms, voice, email)
        message_content: Content of the message sent
        status: Status of the action (pending, sent, delivered, failed, responded)
        twilio_message_sid: Twilio message SID (if SMS)
        twilio_call_sid: Twilio call SID (if voice)
        sent_at: Timestamp when action was sent (optional)
        related_event_identifiers: List of related event identifiers
        
    Returns:
        CDM-compliant Observation event dictionary
    """
    observation_value = {
        "value": action_type.upper(),
        "unit": "RECOVERY_ACTION_TYPE",
        "context": {
            "communicationMethod": communication_method,
            "status": status,
            "messageLength": len(message_content)
        }
    }
    
    if twilio_message_sid:
        observation_value["context"]["twilioMessageSid"] = twilio_message_sid
    
    if twilio_call_sid:
        observation_value["context"]["twilioCallSid"] = twilio_call_sid
    
    related_identifiers = related_event_identifiers or []
    
    # Add loan default identifier
    related_identifiers.append({
        "eventIdentifier": {
            "issuer": "CreditNexus_RecoveryService",
            "assignedIdentifier": [{"identifier": {"value": f"LOAN_DEFAULT_{loan_default_id}"}}]
        }
    })
    
    event_date = sent_at if sent_at else datetime.datetime.now()
    
    return {
        "eventType": "Observation",
        "eventDate": event_date.isoformat() if isinstance(event_date, datetime.datetime) else event_date,
        "observation": {
            "observationType": "RecoveryAction",
            "observationDate": {
                "date": event_date.date().isoformat() if isinstance(event_date, datetime.datetime) else datetime.date.today().isoformat()
            },
            "observedValue": observation_value,
            "informationSource": {
                "sourceProvider": "CreditNexus_RecoveryService",
                "sourceType": "LoanRecovery",
                "reference": {
                    "actionId": action_id,
                    "communicationProvider": "Twilio" if communication_method in ["sms", "voice"] else "Email"
                }
            }
        },
        "relatedEventIdentifier": related_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_RecoveryService_v1",
            "version": 1
        }
    }


def generate_cdm_research_query(
    query_id: str,
    query_text: str,
    query_type: str = "research",
    metadata: Optional[Dict[str, Any]] = None,
    related_event_identifiers: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Generate CDM-compliant Observation event for research query.
    
    Args:
        query_id: Unique identifier for the research query
        query_text: The research query text
        query_type: Type of research (e.g., "company_analysis", "market_analysis", "loan_application_analysis")
        metadata: Optional metadata about the query
        related_event_identifiers: List of related event identifiers
        
    Returns:
        CDM-compliant Observation event dictionary
    """
    if metadata is None:
        metadata = {}
    if related_event_identifiers is None:
        related_event_identifiers = []
    
    return {
        "eventType": "Observation",
        "eventDate": datetime.datetime.now().isoformat(),
        "observation": {
            "observationType": "ResearchQuery",
            "observationDate": {
                "date": datetime.date.today().isoformat()
            },
            "observedValue": {
                "value": query_text,
                "unit": "RESEARCH_QUERY",
                "context": {
                    "queryType": query_type,
                    "queryId": query_id,
                    **metadata
                }
            },
            "informationSource": {
                "sourceProvider": "CreditNexus_LangAlpha",
                "sourceType": "QuantitativeAnalysis",
                "reference": {
                    "queryId": query_id
                }
            }
        },
        "relatedEventIdentifier": related_event_identifiers,
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_LangAlpha_v1",
            "version": 1
        }
    }


def generate_cdm_sharing_event(
    event_id: str,
    event_type: str,  # "send" or "receive"
    sender_user_id: Optional[int],
    receiver_user_id: Optional[int],
    receiver_email: Optional[str],
    receiver_wallet_address: Optional[str],
    file_hash: str,
    workflow_id: Optional[str] = None,
    deal_id: Optional[str] = None,
    blockchain_tx_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate CDM-compliant Sharing event.

    Args:
        event_id: Sharing event ID
        event_type: "send" or "receive"
        sender_user_id: Sender user ID
        receiver_user_id: Receiver user ID
        receiver_email: Receiver email
        receiver_wallet_address: Receiver wallet address
        file_hash: SHA-256 hash of shared file
        workflow_id: Optional workflow ID
        deal_id: Optional deal ID
        blockchain_tx_hash: Optional blockchain transaction hash

    Returns:
        CDM-compliant Sharing event dictionary
    """
    return {
        "eventType": "Sharing",
        "eventDate": datetime.datetime.now().isoformat(),
        "sharing": {
            "sharingIdentifier": {
                "issuer": "CreditNexus_SharingService",
                "assignedIdentifier": [{"identifier": {"value": f"SHARING_{event_id}"}}]
            },
            "eventType": event_type,  # send or receive
            "senderPartyReference": {
                "globalReference": str(sender_user_id) if sender_user_id else None
            } if sender_user_id else None,
            "receiverPartyReference": {
                "globalReference": str(receiver_user_id) if receiver_user_id else None,
                "email": receiver_email,
                "walletAddress": receiver_wallet_address,
            } if receiver_user_id or receiver_email or receiver_wallet_address else None,
            "fileHash": file_hash,
            "workflowIdentifier": {
                "assignedIdentifier": [{"identifier": {"value": workflow_id}}]
            } if workflow_id else None,
            "dealIdentifier": {
                "assignedIdentifier": [{"identifier": {"value": deal_id}}]
            } if deal_id else None,
            "blockchainTransactionHash": blockchain_tx_hash,
            "sharingDate": {"date": datetime.date.today().isoformat()}
        },
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_SharingService_v1",
            "version": 1
        }
    }