"""
Plaid Transfer API: authorization, create, get.

- create_transfer_authorization: POST /transfer/authorization/create
- create_transfer: POST /transfer/create (after authorization)
- get_transfer: GET /transfer/get

Uses PLAID_TRANSFER_ENABLED, PLAID_TRANSFER_ORIGINATION_ACCOUNT_ID (optional),
and PLAID_CLIENT_ID, PLAID_SECRET, PLAID_ENV from settings.
Never log full account numbers or transfer ids in production.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, Optional

from app.core.config import settings
from app.services.plaid_service import _get_plaid_client

logger = logging.getLogger(__name__)


def _transfer_enabled() -> bool:
    return getattr(settings, "PLAID_TRANSFER_ENABLED", False)


def create_transfer_authorization(
    access_token: str,
    account_id: str,
    amount: str,
    direction: str,
    counterparty: Optional[Dict[str, Any]] = None,
    transfer_type: str = "debit",
    network: str = "ach",
    ach_class: str = "ppd",
) -> Dict[str, Any]:
    """
    Call Plaid POST /transfer/authorization/create.
    direction: "debit" (pull from user account) or "credit" (push to user account).
    Returns {"authorization": {...}, "decision": "approved"|...} or {"error": str}.
    """
    if not _transfer_enabled():
        return {"error": "Plaid Transfer is disabled (PLAID_TRANSFER_ENABLED=false)"}
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.transfer_authorization_create_request import TransferAuthorizationCreateRequest
        from plaid.model.transfer_user_in_request import TransferUserInRequest
    except Exception as e:
        return {"error": f"Plaid transfer models unavailable: {e}"}
    try:
        user = TransferUserInRequest(legal_name=(counterparty or {}).get("legal_name", "CreditNexus User"))
        # direction "debit" = pull from user account; "credit" = push to user account
        t_type = (direction or transfer_type or "debit").lower()
        if t_type not in ("debit", "credit"):
            t_type = "debit"
        auth_req = TransferAuthorizationCreateRequest(
            access_token=access_token,
            account_id=account_id,
            type=t_type,
            network=network,
            amount=Decimal(str(amount)),
            ach_class=ach_class,
            user=user,
        )
        auth_resp = api.transfer_authorization_create(auth_req)
        auth = auth_resp.to_dict() if hasattr(auth_resp, "to_dict") else {}
        if not isinstance(auth, dict):
            auth = {"authorization": auth, "decision": getattr(auth_resp, "decision", None)}
        return auth
    except Exception as e:
        logger.warning("Plaid transfer_authorization_create failed: %s", e)
        return {"error": str(e)}


def create_transfer(
    authorization_id: str,
    idempotency_key: str,
    access_token: str,
    account_id: str,
    description: str = "CreditNexus transfer",
) -> Dict[str, Any]:
    """
    Call Plaid POST /transfer/create after authorization.
    Returns {"transfer": {...}} or {"error": str}.
    """
    if not _transfer_enabled():
        return {"error": "Plaid Transfer is disabled (PLAID_TRANSFER_ENABLED=false)"}
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.transfer_create_request import TransferCreateRequest
    except Exception as e:
        return {"error": f"Plaid transfer models unavailable: {e}"}
    try:
        create_req = TransferCreateRequest(
            access_token=access_token,
            account_id=account_id,
            authorization_id=authorization_id,
            description=description,
        )
        if idempotency_key and hasattr(create_req, "idempotency_key"):
            create_req.idempotency_key = idempotency_key
        create_resp = api.transfer_create(create_req)
        transfer = create_resp.to_dict() if hasattr(create_resp, "to_dict") else {}
        if not isinstance(transfer, dict):
            transfer = {"transfer": transfer}
        return {"transfer": transfer} if "transfer" not in transfer else transfer
    except Exception as e:
        logger.warning("Plaid transfer_create failed: %s", e)
        return {"error": str(e)}


def get_transfer(transfer_id: str) -> Dict[str, Any]:
    """
    Call Plaid GET /transfer/get.
    Returns {"transfer": {...}} or {"error": str}.
    """
    if not _transfer_enabled():
        return {"error": "Plaid Transfer is disabled (PLAID_TRANSFER_ENABLED=false)"}
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.transfer_get_request import TransferGetRequest
    except Exception as e:
        return {"error": f"Plaid transfer models unavailable: {e}"}
    try:
        req = TransferGetRequest(transfer_id=transfer_id)
        resp = api.transfer_get(req)
        transfer = resp.to_dict() if hasattr(resp, "to_dict") else {}
        if not isinstance(transfer, dict):
            transfer = {"transfer": transfer}
        return {"transfer": transfer} if "transfer" not in transfer else transfer
    except Exception as e:
        logger.warning("Plaid transfer_get failed: %s", e)
        return {"error": str(e)}
