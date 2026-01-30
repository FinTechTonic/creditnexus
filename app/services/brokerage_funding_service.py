"""
Brokerage funding: link bank (Plaid processor token → Alpaca ACH), fund, withdraw.

- link_bank_for_funding: exchange public_token → processor_token → Alpaca ACH relationship; persist BrokerageAchRelationship.
- list_linked_banks: return user's ACH relationships (optionally sync status from Alpaca).
- fund_account: create Alpaca transfer INCOMING.
- withdraw_from_account: create Alpaca transfer OUTGOING.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AlpacaCustomerAccount, BrokerageAchRelationship, AuditAction
from app.services.alpaca_broker_service import get_broker_client, AlpacaBrokerAPIError
from app.services.plaid_service import (
    exchange_public_token,
    create_processor_token,
)
from app.utils.audit import log_audit_action

logger = logging.getLogger(__name__)


class BrokerageFundingServiceError(Exception):
    """Raised when funding/link/withdraw fails."""
    pass


def _resolve_alpaca_account(db: Session, user_id: int) -> Optional[AlpacaCustomerAccount]:
    """Return ACTIVE Alpaca customer account for user, or None."""
    acc = (
        db.query(AlpacaCustomerAccount)
        .filter(
            AlpacaCustomerAccount.user_id == user_id,
            AlpacaCustomerAccount.status == "ACTIVE",
        )
        .first()
    )
    return acc


def link_bank_for_funding(
    db: Session,
    user_id: int,
    public_token: str,
    plaid_account_id: str,
    nickname: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Link a bank for brokerage funding: exchange token → processor token → Alpaca ACH → persist.
    Returns {"relationship_id": str, "status": str} or raises / returns {"error": str}.
    """
    acc = _resolve_alpaca_account(db, user_id)
    if not acc:
        return {"error": "No active brokerage account. Complete account opening first."}

    client = get_broker_client()
    if not client:
        return {"error": "Broker API not configured"}

    exchanged = exchange_public_token(public_token)
    if "error" in exchanged:
        return {"error": exchanged["error"]}
    access_token = exchanged.get("access_token")
    if not access_token:
        return {"error": "Failed to exchange Plaid token"}

    proc = create_processor_token(access_token, plaid_account_id, "alpaca")
    if "error" in proc:
        return {"error": proc["error"]}
    processor_token = proc.get("processor_token")
    if not processor_token:
        return {"error": "Failed to create processor token"}

    try:
        ach = client.create_ach_relationship_with_processor_token(
            acc.alpaca_account_id,
            processor_token,
        )
    except AlpacaBrokerAPIError as e:
        logger.warning("Alpaca ACH (processor token) failed: %s", e)
        return {"error": str(e)}

    rel_id = ach.get("id") or ach.get("relationship_id")
    if not rel_id:
        rel_id = str(ach.get("id")) if ach.get("id") is not None else None
    if not rel_id:
        return {"error": "Alpaca did not return relationship id"}

    status = (ach.get("status") or "").strip() or None

    existing = (
        db.query(BrokerageAchRelationship)
        .filter(
            BrokerageAchRelationship.user_id == user_id,
            BrokerageAchRelationship.alpaca_account_id == acc.alpaca_account_id,
            BrokerageAchRelationship.alpaca_relationship_id == str(rel_id),
        )
        .first()
    )
    if existing:
        if nickname is not None:
            existing.nickname = nickname
        existing.status = status
        db.commit()
        db.refresh(existing)
        log_audit_action(
            db=db,
            action=AuditAction.UPDATE,
            target_type="brokerage_ach_relationship",
            target_id=existing.id,
            user_id=user_id,
            metadata={
                "alpaca_account_id": acc.alpaca_account_id,
                "alpaca_relationship_id": str(rel_id),
                "brokerage_event": "link_bank_for_funding",
            },
        )
        return {"relationship_id": str(rel_id), "status": status or "unknown"}

    rec = BrokerageAchRelationship(
        user_id=user_id,
        alpaca_account_id=acc.alpaca_account_id,
        alpaca_relationship_id=str(rel_id),
        plaid_account_id=plaid_account_id,
        nickname=nickname,
        status=status,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    log_audit_action(
        db=db,
        action=AuditAction.CREATE,
        target_type="brokerage_ach_relationship",
        target_id=rec.id,
        user_id=user_id,
        metadata={
            "alpaca_account_id": acc.alpaca_account_id,
            "alpaca_relationship_id": str(rel_id),
            "brokerage_event": "link_bank_for_funding",
        },
    )
    return {"relationship_id": str(rel_id), "status": status or "unknown"}


def list_linked_banks(db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Return list of linked ACH relationships for user. Optionally sync status from Alpaca."""
    acc = _resolve_alpaca_account(db, user_id)
    rels = (
        db.query(BrokerageAchRelationship)
        .filter(BrokerageAchRelationship.user_id == user_id)
        .order_by(BrokerageAchRelationship.created_at.desc())
        .all()
    )
    out: List[Dict[str, Any]] = []
    client = get_broker_client() if acc else None
    for r in rels:
        status = r.status
        if client and acc and acc.alpaca_account_id == r.alpaca_account_id:
            try:
                list_ach = client.list_ach_relationships(acc.alpaca_account_id)
                for a in list_ach:
                    if str(a.get("id")) == r.alpaca_relationship_id:
                        status = a.get("status") or status
                        break
            except AlpacaBrokerAPIError:
                pass
        out.append({
            "relationship_id": r.alpaca_relationship_id,
            "nickname": r.nickname,
            "status": status,
            "alpaca_account_id": r.alpaca_account_id,
        })
    return out


def _parse_amount(amount: str) -> Decimal:
    """Parse amount string to Decimal; raise ValueError if invalid."""
    try:
        v = Decimal(str(amount).strip())
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    except Exception as e:
        raise ValueError(f"Invalid amount: {e}") from e


def fund_account(
    db: Session,
    user_id: int,
    amount: str,
    relationship_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fund brokerage account (ACH INCOMING). If relationship_id omitted, use first approved relationship.
    Returns {"transfer_id": str, "status": str} or {"error": str}.
    """
    amount_decimal = _parse_amount(amount)
    acc = _resolve_alpaca_account(db, user_id)
    if not acc:
        return {"error": "No active brokerage account."}

    client = get_broker_client()
    if not client:
        return {"error": "Broker API not configured"}

    rels = (
        db.query(BrokerageAchRelationship)
        .filter(
            BrokerageAchRelationship.user_id == user_id,
            BrokerageAchRelationship.alpaca_account_id == acc.alpaca_account_id,
        )
        .order_by(BrokerageAchRelationship.created_at.desc())
        .all()
    )
    if not rels:
        return {"error": "No linked bank. Link a bank for funding first."}

    rel = None
    if relationship_id:
        for r in rels:
            if r.alpaca_relationship_id == relationship_id:
                rel = r
                break
        if not rel:
            return {"error": "Linked bank not found."}
    else:
        rel = rels[0]

    max_single = getattr(settings, "BROKERAGE_MAX_SINGLE_TRANSFER", None)
    if max_single is not None:
        try:
            max_d = Decimal(str(max_single))
            if amount_decimal > max_d:
                return {"error": f"Amount exceeds maximum single transfer ({max_d})."}
        except Exception:
            pass

    try:
        result = client.create_transfer(
            account_id=acc.alpaca_account_id,
            transfer_type="ach",
            relationship_id=rel.alpaca_relationship_id,
            amount=str(amount_decimal),
            direction="INCOMING",
        )
    except AlpacaBrokerAPIError as e:
        logger.warning("Alpaca create_transfer INCOMING failed: %s", e)
        return {"error": str(e)}

    transfer_id = result.get("id") or result.get("transfer_id")
    status = result.get("status") or "unknown"
    log_audit_action(
        db=db,
        action=AuditAction.CREATE,
        target_type="brokerage_transfer",
        target_id=None,
        user_id=user_id,
        metadata={
            "alpaca_account_id": acc.alpaca_account_id,
            "relationship_id": rel.alpaca_relationship_id,
            "direction": "INCOMING",
            "amount": str(amount_decimal),
            "transfer_id": str(transfer_id) if transfer_id else None,
        },
    )
    return {"transfer_id": str(transfer_id) if transfer_id else None, "status": status}


def withdraw_from_account(
    db: Session,
    user_id: int,
    amount: str,
    relationship_id: str,
) -> Dict[str, Any]:
    """
    Withdraw from brokerage to linked bank (ACH OUTGOING).
    Returns {"transfer_id": str, "status": str} or {"error": str}.
    """
    amount_decimal = _parse_amount(amount)
    if not relationship_id or not str(relationship_id).strip():
        return {"error": "relationship_id is required for withdraw."}

    acc = _resolve_alpaca_account(db, user_id)
    if not acc:
        return {"error": "No active brokerage account."}

    client = get_broker_client()
    if not client:
        return {"error": "Broker API not configured"}

    rel = (
        db.query(BrokerageAchRelationship)
        .filter(
            BrokerageAchRelationship.user_id == user_id,
            BrokerageAchRelationship.alpaca_account_id == acc.alpaca_account_id,
            BrokerageAchRelationship.alpaca_relationship_id == str(relationship_id).strip(),
        )
        .first()
    )
    if not rel:
        return {"error": "Linked bank not found."}

    try:
        result = client.create_transfer(
            account_id=acc.alpaca_account_id,
            transfer_type="ach",
            relationship_id=rel.alpaca_relationship_id,
            amount=str(amount_decimal),
            direction="OUTGOING",
        )
    except AlpacaBrokerAPIError as e:
        logger.warning("Alpaca create_transfer OUTGOING failed: %s", e)
        return {"error": str(e)}

    transfer_id = result.get("id") or result.get("transfer_id")
    status = result.get("status") or "unknown"
    log_audit_action(
        db=db,
        action=AuditAction.CREATE,
        target_type="brokerage_transfer",
        target_id=None,
        user_id=user_id,
        metadata={
            "alpaca_account_id": acc.alpaca_account_id,
            "relationship_id": rel.alpaca_relationship_id,
            "direction": "OUTGOING",
            "amount": str(amount_decimal),
            "transfer_id": str(transfer_id) if transfer_id else None,
        },
    )
    return {"transfer_id": str(transfer_id) if transfer_id else None, "status": status}
