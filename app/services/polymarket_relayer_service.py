"""
Polymarket relayer: gasless Safe/proxy deploy and CTF execute via builder HMAC auth.

- deploy_safe: POST to relayer to deploy Safe for user (EOA/signer from request).
- execute_transactions: POST to relayer to execute batch of { to, data, value }.
- get_transaction: GET transaction state by id.

Builder auth required; POLYMARKET_RELAYER_URL default https://relayer-v2.polymarket.com/
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.services.polymarket_builder_signing_service import build_builder_headers

logger = logging.getLogger(__name__)

# Polygon contract addresses (Polymarket docs)
USDCe_POLYGON = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
CTF_POLYGON = "0x4d97dcd97ec945f40cf65f87097ace5ea0476045"
CTF_EXCHANGE_POLYGON = "0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E"
NEG_RISK_CTF_EXCHANGE_POLYGON = "0xC5d563A36AE78145C45a50134d48A1215220f80a"
NEG_RISK_ADAPTER_POLYGON = "0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296"


def _relayer_url() -> str:
    return (getattr(settings, "POLYMARKET_RELAYER_URL", None) or "https://relayer-v2.polymarket.com/").rstrip("/")


def _request(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send request to relayer with builder HMAC headers. path should start with /."""
    url = _relayer_url() + path
    body_str = json.dumps(body) if body else ""
    headers = {"Content-Type": "application/json"}
    builder = build_builder_headers(method, path, body_str)
    if not builder:
        return {"ok": False, "error": "builder_not_configured", "message": "POLY_BUILDER_* not set"}
    headers.update(builder)
    try:
        with httpx.Client(timeout=30.0) as client:
            if method == "GET":
                r = client.get(url, headers=headers)
            else:
                r = client.request(method, url, content=body_str, headers=headers)
        data = r.json() if r.headers.get("content-type", "").strip().startswith("application/json") else {}
        if not r.is_success:
            return {
                "ok": False,
                "status_code": r.status_code,
                "error": data.get("error", "relayer_error"),
                "message": data.get("message", r.text or "Relayer request failed"),
                "response": data,
            }
        return {"ok": True, "data": data, "response": data}
    except Exception as e:
        logger.warning("Polymarket relayer request failed: %s", e)
        return {"ok": False, "error": "request_failed", "message": str(e)}


def deploy_safe(
    user_id: int,
    db: Any,
    funder_address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Deploy Safe/proxy for user via relayer. funder_address: user's EOA or existing proxy.
    Returns { ok, proxy_address?, transaction_id?, transaction_hash?, ... } or error.
    """
    # Relayer deploy typically expects POST /deploy with signer/funder; exact body from builder-relayer-client
    body = {}
    if funder_address:
        body["funder_address"] = funder_address
    out = _request("POST", "/deploy", body=body if body else None)
    if not out.get("ok"):
        return out
    data = out.get("data") or out.get("response") or {}
    return {
        "ok": True,
        "proxy_address": data.get("proxyAddress") or data.get("proxy_address"),
        "transaction_id": data.get("transactionID") or data.get("transaction_id"),
        "transaction_hash": data.get("transactionHash") or data.get("transaction_hash"),
        "response": data,
    }


def execute_transactions(
    user_id: int,
    db: Any,
    proxy_address: str,
    transactions: List[Dict[str, Any]],
    description: str = "",
) -> Dict[str, Any]:
    """
    Execute batch of transactions via relayer for proxy_address.
    transactions: list of { to, data, value }.
    Returns { ok, transaction_id?, transaction_hash?, ... } or error.
    """
    if not transactions:
        return {"ok": False, "error": "no_transactions", "message": "transactions list is empty"}
    body = {
        "proxy_address": proxy_address,
        "transactions": [{"to": t.get("to"), "data": t.get("data", "0x"), "value": t.get("value", "0")} for t in transactions],
        "metadata": description or "CreditNexus execute",
    }
    out = _request("POST", "/execute", body=body)
    if not out.get("ok"):
        return out
    data = out.get("data") or out.get("response") or {}
    return {
        "ok": True,
        "transaction_id": data.get("transactionID") or data.get("transaction_id"),
        "transaction_hash": data.get("transactionHash") or data.get("transaction_hash"),
        "state": data.get("state"),
        "response": data,
    }


def get_transaction(transaction_id: str) -> Dict[str, Any]:
    """Get relayer transaction state by id. Returns { ok, state, transaction_hash?, ... }."""
    out = _request("GET", f"/transaction/{transaction_id}")
    if not out.get("ok"):
        return out
    data = out.get("data") or out.get("response") or {}
    return {
        "ok": True,
        "transaction_id": transaction_id,
        "state": data.get("state"),
        "transaction_hash": data.get("transactionHash") or data.get("transaction_hash"),
        "proxy_address": data.get("proxyAddress") or data.get("proxy_address"),
        "response": data,
    }


def _addr_to_hex(addr: str) -> str:
    """Normalize address to 0x-prefixed 40-char hex (no 0x prefix stripped for calldata)."""
    a = (addr or "").strip()
    if a.startswith("0x"):
        a = a[2:]
    return "0x" + a.lower().zfill(40)[-40:]


def _erc20_approve_calldata(spender: str, amount_hex: str = "0xff" * 32) -> str:
    """Build ERC20 approve(spender, amount) calldata. amount_hex default = max uint256."""
    # approve(address,uint256) selector
    selector = "0x095ea7b3"
    spender_padded = _addr_to_hex(spender)
    # uint256: 32 bytes = 64 hex chars
    if not amount_hex.startswith("0x"):
        amount_hex = "0x" + amount_hex
    amount_padded = amount_hex[2:].zfill(64)[-64:]
    return f"{selector}{spender_padded[2:]}{amount_padded}"


def approve_usdce_for_ctf(proxy_address: str) -> Dict[str, Any]:
    """
    Build ERC20 approve(CTF, maxUint256) for USDCe so proxy can use USDCe with CTF.
    Returns transaction dict { to, data, value } for relayer execute.
    """
    # USDCe.approve(CTF_POLYGON, type(uint256).max)
    return {
        "to": USDCe_POLYGON,
        "data": _erc20_approve_calldata(CTF_POLYGON),
        "value": "0",
    }


def approve_ctf_for_exchange(proxy_address: str) -> Dict[str, Any]:
    """
    Build CTF (outcome token) approve(CTF_EXCHANGE, maxUint256) so proxy can trade.
    Returns transaction dict { to, data, value } for relayer execute.
    """
    return {
        "to": CTF_POLYGON,
        "data": _erc20_approve_calldata(CTF_EXCHANGE_POLYGON),
        "value": "0",
    }


def ensure_user_approvals(
    user_id: int,
    db: Any,
    proxy_address: str,
) -> List[Dict[str, Any]]:
    """
    Return list of approval transactions for first-time setup: approve USDCe for CTF,
    approve CTF for exchange. Frontend or backend can submit these via relayer execute.
    Does not check on-chain state; returns both so client can run them.
    """
    return [
        approve_usdce_for_ctf(proxy_address),
        approve_ctf_for_exchange(proxy_address),
    ]
