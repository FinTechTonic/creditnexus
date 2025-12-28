"""
FINOS CDM Event Generator for 'Kill Shot' Demo (Deep Tech Implementation)
Generates machine-executable JSON structures for Sustainbility-Linked Loans (SLL).
"""

from typing import Dict, Any, List
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

def generate_cdm_terms_change(trade_id: str, current_rate: float, status: str) -> Dict[str, Any]:
    """
    Generates the TermsChange event (TradeState v2).
    Mathematically updates the spread based on the Observation.
    """
    
    # Financial Logic: "The Contract is Code"
    # Base = 5.00%
    # Penalty = +1.50% (150 bps) if BREACH
    base_spread = 5.00
    penalty = 1.50 if status == "BREACH" else 0.00
    new_spread = base_spread + penalty
    
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
