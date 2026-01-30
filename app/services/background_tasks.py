"""
Background Tasks for Filing, Signature, and Loan Recovery Management.

This module contains scheduled background tasks for:
1. Deadline monitoring (daily at 9 AM)
2. Signature status updates (hourly)
3. Filing status verification (daily)
4. Loan default detection (daily at 9 AM)
5. Recovery action processing (hourly)
"""

import logging
from datetime import date, datetime, time
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.db import get_db
from app.agents.deadline_verifier import DeadlineVerifier
from app.agents.signature_verifier import SignatureVerifier
from app.agents.filing_verifier import FilingVerifier
from app.services.loan_recovery_service import LoanRecoveryService
from app.services.asset_amortization_service import AssetAmortizationService
from app.services.alpaca_account_service import sync_all_pending_alpaca_accounts

logger = logging.getLogger(__name__)


async def monitor_filing_deadlines() -> Dict[str, Any]:
    """
    Background task to monitor filing deadlines.
    
    Runs daily at 9 AM to check for approaching deadlines and generate alerts.
    
    Returns:
        Task execution result
    """
    logger.info("Starting deadline monitoring task")
    
    try:
        db = next(get_db())
        verifier = DeadlineVerifier(db)
        
        # Check deadlines for next 7 days
        result = verifier.check_approaching_deadlines(days_ahead=7)
        
        # Get critical deadlines
        critical = verifier.get_critical_deadlines(hours_ahead=24)
        
        # Escalate critical deadlines
        escalated = verifier.escalate_critical_deadlines()
        
        logger.info(
            f"Deadline monitoring completed: {result['total_alerts']} alerts, "
            f"{critical['critical_count']} critical, {escalated['escalated_count']} escalated"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "alerts": result,
            "critical": critical,
            "escalated": escalated
        }
    except Exception as e:
        logger.error(f"Error in deadline monitoring task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


async def update_signature_statuses() -> Dict[str, Any]:
    """
    Background task to update signature statuses.
    
    Runs hourly to check DigiSigner API for signature status updates.
    
    Returns:
        Task execution result
    """
    logger.info("Starting signature status update task")
    
    try:
        db = next(get_db())
        verifier = SignatureVerifier(db)
        
        # Check for expiring signatures
        expiring = verifier.verify_expired_signatures(hours_ahead=24)
        
        # Update statuses for pending signatures
        from app.db.models import DocumentSignature
        
        pending_signatures = db.query(DocumentSignature).filter(
            DocumentSignature.signature_status == "pending"
        ).limit(100).all()  # Limit to avoid timeout
        
        updated_count = 0
        for signature in pending_signatures:
            try:
                result = verifier.verify_signature_status(signature.id)
                if result.get("status") == "success":
                    updated_count += 1
            except Exception as e:
                logger.warning(f"Error updating signature {signature.id}: {e}")
        
        logger.info(
            f"Signature status update completed: {updated_count} signatures updated, "
            f"{expiring['expiring_count']} expiring soon"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "updated_count": updated_count,
            "expiring": expiring
        }
    except Exception as e:
        logger.error(f"Error in signature status update task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


async def verify_filing_statuses() -> Dict[str, Any]:
    """
    Background task to verify filing statuses.
    
    Runs daily to verify filing compliance and check status with external authorities.
    
    Returns:
        Task execution result
    """
    logger.info("Starting filing status verification task")
    
    try:
        db = next(get_db())
        verifier = FilingVerifier(db)
        
        # Get pending filings
        from app.db.models import DocumentFiling
        
        pending_filings = db.query(DocumentFiling).filter(
            DocumentFiling.filing_status == "pending"
        ).limit(100).all()  # Limit to avoid timeout
        
        verified_count = 0
        compliance_issues = []
        
        for filing in pending_filings:
            try:
                result = verifier.verify_filing_submission(filing.id)
                if result.get("status") == "success":
                    verified_count += 1
                elif result.get("status") == "warning":
                    compliance_issues.append({
                        "filing_id": filing.id,
                        "issue": result.get("message")
                    })
            except Exception as e:
                logger.warning(f"Error verifying filing {filing.id}: {e}")
        
        # Also verify document-level compliance
        from app.db.models import Document
        
        documents_with_filings = db.query(Document).join(DocumentFiling).distinct().limit(50).all()
        
        compliance_results = []
        for document in documents_with_filings:
            try:
                result = verifier.verify_document_filings(document.id, check_deadlines=True)
                if result.get("compliance_status") != "compliant":
                    compliance_results.append({
                        "document_id": document.id,
                        "compliance_status": result.get("compliance_status"),
                        "issues": result.get("missing_filings", []) + result.get("compliance_issues", [])
                    })
            except Exception as e:
                logger.warning(f"Error verifying document {document.id} filings: {e}")
        
        logger.info(
            f"Filing status verification completed: {verified_count} filings verified, "
            f"{len(compliance_results)} documents with compliance issues"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "verified_count": verified_count,
            "compliance_issues": compliance_issues,
            "compliance_results": compliance_results
        }
    except Exception as e:
        logger.error(f"Error in filing status verification task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


async def detect_loan_defaults_task() -> Dict[str, Any]:
    """
    Background task to detect loan defaults and covenant breaches.
    
    Runs daily at 9 AM to check for payment defaults and covenant breaches,
    creating LoanDefault records and triggering recovery actions.
    
    Returns:
        Task execution result with counts of detected defaults
    """
    logger.info("Starting loan default detection task")
    
    try:
        db = next(get_db())
        recovery_service = LoanRecoveryService(db)
        
        # Detect payment defaults
        payment_defaults = recovery_service.detect_payment_defaults()
        payment_count = len(payment_defaults)
        
        # Detect covenant breaches
        covenant_breaches = recovery_service.detect_covenant_breaches()
        covenant_count = len(covenant_breaches)
        
        total_defaults = payment_count + covenant_count
        
        logger.info(
            f"Loan default detection completed: {payment_count} payment defaults, "
            f"{covenant_count} covenant breaches, {total_defaults} total"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "payment_defaults": payment_count,
            "covenant_breaches": covenant_count,
            "total_defaults": total_defaults
        }
    except Exception as e:
        logger.error(f"Error in loan default detection task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
    finally:
        db.close()


async def process_recovery_actions_task() -> Dict[str, Any]:
    """
    Background task to process scheduled recovery actions.
    
    Runs hourly to execute recovery actions that are scheduled and due,
    sending SMS/voice messages via Twilio.
    
    Returns:
        Task execution result with counts of processed actions
    """
    logger.info("Starting recovery action processing task")
    
    try:
        db = next(get_db())
        recovery_service = LoanRecoveryService(db)
        
        # Process scheduled actions
        result = recovery_service.process_scheduled_actions()
        
        processed_count = result.get("processed_count", 0)
        
        logger.info(
            f"Recovery action processing completed: {processed_count} actions processed"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "processed_count": processed_count,
            **result
        }
    except Exception as e:
        logger.error(f"Error in recovery action processing task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
    finally:
        db.close()


async def monitor_asset_amortization() -> Dict[str, Any]:
    """
    Background task to monitor asset amortization and maturity (Trading Phase 3).
    Creates in-app AssetAlerts for upcoming maturities and amortization payments.
    """
    logger.info("Starting asset amortization monitoring task")
    try:
        db = next(get_db())
        svc = AssetAmortizationService(db)
        items = svc.check_upcoming_payments(days_ahead=7, user_id=None)
        created = 0
        for x in items:
            asset = x.get("asset")
            if not asset:
                continue
            try:
                d = None
                if isinstance(x.get("due_date"), str):
                    d = date.fromisoformat(x["due_date"])
                msg = x.get("message") or "Payment due"
                al = svc.create_maturity_alert(asset, d or date.today(), x.get("type") or "maturity", msg)
                if al:
                    created += 1
            except Exception as e:
                logger.warning("Asset alert create failed for asset %s: %s", getattr(asset, "id", None), e)
        logger.info("Asset amortization monitoring: %s upcoming, %s alerts created", len(items), created)
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "upcoming_count": len(items),
            "alerts_created": created,
        }
    except Exception as e:
        logger.error("Error in asset amortization monitoring: %s", e, exc_info=True)
        return {"status": "error", "timestamp": datetime.utcnow().isoformat(), "error": str(e)}
    finally:
        try:
            db.close()
        except Exception:
            pass


async def check_price_alerts() -> Dict[str, Any]:
    """
    Background task to check price alerts and trigger notifications.
    
    Runs hourly to check active price alerts against current market prices.
    
    Returns:
        Task execution result with triggered alerts count
    """
    logger.info("Starting price alerts monitoring task")
    
    try:
        from app.db.models import PriceAlert
        from app.api.trading_routes import get_trading_api_service
        from app.services.trading_api_service import TradingAPIService
        from decimal import Decimal
        
        db = next(get_db())
        
        # Get all active alerts
        active_alerts = db.query(PriceAlert).filter(
            PriceAlert.is_active == True,
            PriceAlert.triggered_at.is_(None)  # Only check untriggered alerts
        ).all()
        
        if not active_alerts:
            logger.debug("No active price alerts to check")
            return {
                "status": "success",
                "timestamp": datetime.utcnow().isoformat(),
                "checked": 0,
                "triggered": 0,
            }
        
        # Get trading API service for market data
        trading_service: TradingAPIService = get_trading_api_service()
        
        triggered_count = 0
        symbols_to_check = list(set([alert.symbol for alert in active_alerts]))
        
        # Get current prices for all symbols
        symbol_prices: Dict[str, float] = {}
        for symbol in symbols_to_check:
            try:
                market_data = trading_service.get_market_data(symbol, db=db)
                # Calculate mid price from bid/ask
                bid = float(market_data.get("bid_price") or 0)
                ask = float(market_data.get("ask_price") or 0)
                if bid and ask:
                    symbol_prices[symbol] = (bid + ask) / 2
                elif bid:
                    symbol_prices[symbol] = bid
                elif ask:
                    symbol_prices[symbol] = ask
            except Exception as e:
                logger.warning(f"Failed to get market data for {symbol}: {e}")
                continue
        
        # Check each alert
        for alert in active_alerts:
            current_price = symbol_prices.get(alert.symbol)
            if not current_price:
                continue
            
            should_trigger = False
            
            if alert.alert_type == "above" and alert.target_price:
                should_trigger = current_price >= float(alert.target_price)
            elif alert.alert_type == "below" and alert.target_price:
                should_trigger = current_price <= float(alert.target_price)
            elif alert.alert_type == "change_percent" and alert.change_percent:
                # For change_percent, we'd need previous price - simplified for now
                # In production, would track price history
                pass
            
            if should_trigger:
                alert.is_active = False
                alert.triggered_at = datetime.utcnow()
                alert.triggered_price = Decimal(str(current_price))
                db.commit()
                triggered_count += 1
                
                logger.info(
                    f"Price alert triggered: {alert.symbol} {alert.alert_type} "
                    f"{alert.target_price} at {current_price}"
                )
                
                # TODO: Send notifications (email, in-app) based on alert.notify_email and alert.notify_in_app
        
        logger.info(
            f"Price alerts monitoring completed: {len(active_alerts)} checked, "
            f"{triggered_count} triggered"
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "checked": len(active_alerts),
            "triggered": triggered_count,
        }
    except Exception as e:
        logger.error(f"Error in price alerts monitoring task: {e}", exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
    finally:
        try:
            db.close()
        except Exception:
            pass


async def sync_alpaca_account_statuses_task() -> Dict[str, Any]:
    """
    Background task to poll Alpaca Broker API for account status updates.
    Runs hourly; syncs AlpacaCustomerAccount records that are not yet ACTIVE or REJECTED.
    """
    logger.info("Starting Alpaca account status sync task")
    db = None
    try:
        db = next(get_db())
        result = sync_all_pending_alpaca_accounts(db)
        logger.info(
            "Alpaca account status sync completed: %s pending, %s synced, %s errors",
            result.get("pending_count", 0),
            result.get("synced", 0),
            result.get("errors", 0),
        )
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            **result,
        }
    except Exception as e:
        logger.error("Error in Alpaca account status sync task: %s", e, exc_info=True)
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
        }
    finally:
        try:
            if db is not None:
                db.close()
        except Exception:
            pass


# Task schedule configuration
TASK_SCHEDULE = {
    "deadline_monitoring": {
        "task": monitor_filing_deadlines,
        "schedule": "daily",
        "time": time(9, 0),  # 9 AM
        "enabled": True
    },
    "signature_status_updates": {
        "task": update_signature_statuses,
        "schedule": "hourly",
        "enabled": True
    },
    "filing_status_verification": {
        "task": verify_filing_statuses,
        "schedule": "daily",
        "time": time(10, 0),  # 10 AM
        "enabled": True
    },
    "loan_default_detection": {
        "task": detect_loan_defaults_task,
        "schedule": "daily",
        "time": time(9, 0),  # 9 AM
        "enabled": True
    },
    "recovery_action_processing": {
        "task": process_recovery_actions_task,
        "schedule": "hourly",
        "enabled": True
    },
    "asset_amortization_monitoring": {
        "task": monitor_asset_amortization,
        "schedule": "daily",
        "time": time(8, 0),  # 8 AM
        "enabled": True
    },
    "price_alerts_monitoring": {
        "task": check_price_alerts,
        "schedule": "hourly",
        "enabled": True
    },
    "alpaca_account_status_sync": {
        "task": sync_alpaca_account_statuses_task,
        "schedule": "hourly",
        "enabled": True
    }
}
