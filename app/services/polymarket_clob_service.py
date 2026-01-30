"""
Polymarket CLOB order placement: forward client-signed orders with user L2 + builder headers.

- place_order: accept signed order + order_type; add user L2 auth and builder headers; POST to CLOB.
- L2 auth per Polymarket docs: POLY_ADDRESS, POLY_SIGNATURE (HMAC-SHA256), POLY_TIMESTAMP, POLY_API_KEY, POLY_PASSPHRASE.
- Builder headers from polymarket_builder_signing_service for order attribution.
"""

import base64
import hmac
import hashlib
import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.services.polymarket_account_service import get_user_l2_creds
from app.services.polymarket_builder_signing_service import build_builder_headers

logger = logging.getLogger(__name__)


def _build_l2_signature(secret: str, timestamp: str, method: str, request_path: str, body: Optional[str] = None) -> str:
    """L2 HMAC per py-clob-client: base64-decode secret; message = timestamp + method + path + body (single→double quotes); return base64 HMAC-SHA256."""
    try:
        base64_secret = base64.urlsafe_b64decode(secret)
    except Exception:
        logger.warning("Polymarket L2 secret not valid base64")
        return ""
    message = str(timestamp) + str(method) + str(request_path)
    if body:
        message += str(body).replace("'", '"')
    h = hmac.new(base64_secret, message.encode("utf-8"), hashlib.sha256)
    return (base64.urlsafe_b64encode(h.digest())).decode("utf-8")


def place_order(
    user_id: int,
    db: Any,
    signed_order: Dict[str, Any],
    order_type: str = "GTC",
    post_only: bool = False,
) -> Dict[str, Any]:
    """
    Post a client-signed order to Polymarket CLOB with user L2 auth and builder headers.

    signed_order: order object as created/signed by client (salt, maker, signer, taker, tokenId, etc.).
    order_type: GTC, FOK, or GTD.
    Returns CLOB response (success, orderId, orderHashes, errorMsg, status) or error dict.
    """
    creds = get_user_l2_creds(user_id, db)
    if not creds or not creds.get("api_key") or not creds.get("secret") or not creds.get("passphrase"):
        return {"ok": False, "error": "polymarket_not_linked", "message": "Link Polymarket account (BYOK) first."}
    funder = creds.get("funder_address")
    if not funder:
        return {"ok": False, "error": "funder_required", "message": "Link Polymarket with funder_address for orders."}

    clob_url = (getattr(settings, "POLYMARKET_API_URL", None) or "https://clob.polymarket.com").rstrip("/")
    path = "/order"
    body = {
        "order": signed_order,
        "owner": creds["api_key"],
        "orderType": order_type,
        "postOnly": post_only,
    }
    body_str = json.dumps(body, separators=(",", ":"))

    import time
    timestamp = str(int(time.time()))
    l2_sig = _build_l2_signature(creds["secret"], timestamp, "POST", path, body_str)
    if not l2_sig:
        return {"ok": False, "error": "l2_signature_failed", "message": "Invalid L2 secret."}

    headers = {
        "Content-Type": "application/json",
        "POLY_ADDRESS": funder,
        "POLY_SIGNATURE": l2_sig,
        "POLY_TIMESTAMP": timestamp,
        "POLY_API_KEY": creds["api_key"],
        "POLY_PASSPHRASE": creds["passphrase"],
    }
    builder_headers = build_builder_headers("POST", path, body_str)
    if builder_headers:
        headers.update(builder_headers)

    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.post(f"{clob_url}{path}", content=body_str, headers=headers)
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if not r.is_success:
            return {
                "ok": False,
                "error": "clob_error",
                "status_code": r.status_code,
                "message": data.get("errorMsg", r.text or "CLOB request failed"),
                "clob_response": data,
            }
        return {
            "ok": True,
            "success": data.get("success", True),
            "orderId": data.get("orderId"),
            "orderHashes": data.get("orderHashes", []),
            "status": data.get("status"),
            "errorMsg": data.get("errorMsg"),
            "clob_response": data,
        }
    except Exception as e:
        logger.warning("Polymarket CLOB place_order failed: %s", e)
        return {"ok": False, "error": "request_failed", "message": str(e)}
