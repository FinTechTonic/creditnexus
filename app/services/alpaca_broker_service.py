"""
Alpaca Broker API client for multiuser brokerage.

- Account CRUD: create_account, get_account, update_account
- Trading per account: create_order, get_order, cancel_order, list_orders, get_positions
- Documents: upload_document (for ACTION_REQUIRED)
- Events: account status updates (poll or SSE)

Broker API uses HTTP Basic auth: base64(API_KEY:API_SECRET).
See: https://docs.alpaca.markets/docs/authentication
"""

from __future__ import annotations

import base64
import logging
from typing import Any, BinaryIO, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class AlpacaBrokerAPIError(Exception):
    """Raised when Alpaca Broker API returns an error."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class AlpacaBrokerClient:
    """HTTP client for Alpaca Broker API (accounts, orders, positions, documents)."""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: Optional[str] = None,
    ):
        self.base_url = (base_url or "https://broker-api.sandbox.alpaca.markets").rstrip("/")
        credentials = f"{api_key}:{api_secret}"
        self._auth_header = "Basic " + base64.b64encode(credentials.encode()).decode()
        self._session = requests.Session()
        self._session.headers["Authorization"] = self._auth_header
        self._session.headers["Content-Type"] = "application/json"

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.request(
                method,
                url,
                params=params,
                json=json,
                data=data,
                files=files,
                timeout=30,
            )
            if resp.status_code >= 400:
                try:
                    err_body = resp.json()
                except Exception:
                    err_body = {"message": resp.text or str(resp.status_code)}
                raise AlpacaBrokerAPIError(
                    err_body.get("message") or err_body.get("error") or resp.text or f"HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    response=err_body,
                )
            if resp.status_code == 204 or not resp.content:
                return {}
            return resp.json()
        except AlpacaBrokerAPIError:
            raise
        except requests.RequestException as e:
            logger.warning("Alpaca Broker API request failed: %s", e)
            raise AlpacaBrokerAPIError(str(e))

    # -------------------------------------------------------------------------
    # Account API
    # -------------------------------------------------------------------------

    def create_account(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /v1/accounts — Create a new customer account (KYC submitted to Alpaca).
        Returns account id and status (e.g. SUBMITTED).
        """
        return self._request("POST", "/v1/accounts", json=payload)

    def get_account(self, account_id: str) -> Dict[str, Any]:
        """GET /v1/accounts/{account_id} — Get account details."""
        return self._request("GET", f"/v1/accounts/{account_id}")

    def update_account(self, account_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """PATCH /v1/accounts/{account_id} — Update account (e.g. contact, identity)."""
        return self._request("PATCH", f"/v1/accounts/{account_id}", json=payload)

    # -------------------------------------------------------------------------
    # Trading API (per account)
    # -------------------------------------------------------------------------

    def create_order(self, account_id: str, order_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /v1/trading/accounts/{account_id}/orders — Submit order for account.
        order_request: symbol, qty or notional, side, type, time_in_force, limit_price, stop_price, etc.
        """
        return self._request("POST", f"/v1/trading/accounts/{account_id}/orders", json=order_request)

    def get_order(self, account_id: str, order_id: str) -> Dict[str, Any]:
        """GET /v1/trading/accounts/{account_id}/orders/{order_id}."""
        return self._request("GET", f"/v1/trading/accounts/{account_id}/orders/{order_id}")

    def cancel_order(self, account_id: str, order_id: str) -> Dict[str, Any]:
        """DELETE /v1/trading/accounts/{account_id}/orders/{order_id}."""
        return self._request("DELETE", f"/v1/trading/accounts/{account_id}/orders/{order_id}")

    def list_orders(
        self,
        account_id: str,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/trading/accounts/{account_id}/orders."""
        params: Dict[str, Any] = {}
        if status:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if after:
            params["after"] = after
        data = self._request("GET", f"/v1/trading/accounts/{account_id}/orders", params=params or None)
        return data.get("orders") if isinstance(data.get("orders"), list) else []

    def get_positions(self, account_id: str) -> List[Dict[str, Any]]:
        """GET /v1/trading/accounts/{account_id}/positions. API may return list or { positions: [] }."""
        data = self._request("GET", f"/v1/trading/accounts/{account_id}/positions")
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        return data.get("positions") if isinstance(data.get("positions"), list) else []

    def get_account_portfolio(self, account_id: str) -> Dict[str, Any]:
        """GET /v1/trading/accounts/{account_id}/account — Equity, cash, buying power."""
        return self._request("GET", f"/v1/trading/accounts/{account_id}/account")

    # -------------------------------------------------------------------------
    # Documents (for ACTION_REQUIRED)
    # -------------------------------------------------------------------------

    def upload_document(
        self,
        account_id: str,
        document_type: str,
        file_content: BinaryIO,
        filename: str,
        content_type: str = "application/pdf",
    ) -> Dict[str, Any]:
        """
        Upload a document for an account (e.g. utility bill for address verification).
        Alpaca Document API: POST /v1/accounts/{account_id}/documents/upload
        """
        files = {"document": (filename, file_content, content_type)}
        data = {"document_type": document_type}
        # Many APIs expect multipart/form-data with file + fields
        url = f"{self.base_url}/v1/accounts/{account_id}/documents/upload"
        headers = {"Authorization": self._auth_header}
        # Do not set Content-Type; requests sets it with boundary for multipart
        r = self._session.post(url, files=files, data=data, timeout=60)
        if r.status_code >= 400:
            try:
                err_body = r.json()
            except Exception:
                err_body = {"message": r.text or str(r.status_code)}
            raise AlpacaBrokerAPIError(
                err_body.get("message") or err_body.get("error") or r.text or f"HTTP {r.status_code}",
                status_code=r.status_code,
                response=err_body,
            )
        if r.status_code == 204 or not r.content:
            return {}
        return r.json()

    # -------------------------------------------------------------------------
    # ACH & Transfers (funding)
    # -------------------------------------------------------------------------

    def list_ach_relationships(self, account_id: str) -> List[Dict[str, Any]]:
        """
        GET /v1/accounts/{account_id}/ach_relationships — List ACH relationships.
        In sandbox, relationships move from QUEUED to APPROVED after ~1 minute.
        """
        data = self._request("GET", f"/v1/accounts/{account_id}/ach_relationships")
        return data if isinstance(data, list) else data.get("ach_relationships") or []

    def create_ach_relationship(
        self,
        account_id: str,
        account_owner_name: str,
        bank_account_type: str,
        bank_account_number: str,
        bank_routing_number: str,
        nickname: str,
    ) -> Dict[str, Any]:
        """
        POST /v1/accounts/{account_id}/ach_relationships — Create ACH relationship.
        Sandbox accepts test values (e.g. bank_account_number "32131231abc", routing "123103716").
        """
        payload = {
            "account_owner_name": account_owner_name,
            "bank_account_type": bank_account_type,
            "bank_account_number": bank_account_number,
            "bank_routing_number": bank_routing_number,
            "nickname": nickname,
        }
        return self._request("POST", f"/v1/accounts/{account_id}/ach_relationships", json=payload)

    def create_ach_relationship_with_processor_token(
        self,
        account_id: str,
        processor_token: str,
    ) -> Dict[str, Any]:
        """
        POST /v1/accounts/{account_id}/ach_relationships — Create ACH relationship using
        Plaid processor token (no raw account/routing stored). Returns full response
        (id = relationship_id, status, etc.).
        """
        payload = {"processor_token": processor_token}
        return self._request("POST", f"/v1/accounts/{account_id}/ach_relationships", json=payload)

    def get_transfer(self, account_id: str, transfer_id: str) -> Dict[str, Any]:
        """GET /v1/accounts/{account_id}/transfers/{transfer_id} — Get transfer status."""
        return self._request("GET", f"/v1/accounts/{account_id}/transfers/{transfer_id}")

    def list_transfers(
        self,
        account_id: str,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """GET /v1/accounts/{account_id}/transfers — List transfers."""
        params: Dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if after:
            params["after"] = after
        if direction:
            params["direction"] = direction
        data = self._request(
            "GET",
            f"/v1/accounts/{account_id}/transfers",
            params=params if params else None,
        )
        return data.get("transfers") if isinstance(data.get("transfers"), list) else []

    def create_transfer(
        self,
        account_id: str,
        transfer_type: str,
        relationship_id: str,
        amount: str,
        direction: str,
    ) -> Dict[str, Any]:
        """
        POST /v1/accounts/{account_id}/transfers — Create transfer (deposit/withdrawal).
        Sandbox: credit/debit is effective immediately.
        direction: INCOMING (deposit) or OUTGOING (withdrawal).
        """
        payload = {
            "transfer_type": transfer_type,
            "relationship_id": relationship_id,
            "amount": amount,
            "direction": direction,
        }
        return self._request("POST", f"/v1/accounts/{account_id}/transfers", json=payload)

    # -------------------------------------------------------------------------
    # CIP (fully-disclosed broker-dealer only)
    # -------------------------------------------------------------------------

    def submit_cip(self, account_id: str, cip_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST /v1/accounts/{account_id}/cip — Submit CIP after your KYC (fully-disclosed BD).
        Only used when Alpaca relies on your KYC; otherwise Account API submission is enough.
        """
        return self._request("POST", f"/v1/accounts/{account_id}/cip", json=cip_payload)


def get_broker_client() -> Optional[AlpacaBrokerClient]:
    """Build AlpacaBrokerClient from settings if Broker API is configured."""
    from app.core.config import settings

    key = getattr(settings, "ALPACA_BROKER_API_KEY", None)
    secret = getattr(settings, "ALPACA_BROKER_API_SECRET", None)
    base_url = getattr(settings, "ALPACA_BROKER_BASE_URL", None)
    if not key or not secret:
        return None
    k = key.get_secret_value() if hasattr(key, "get_secret_value") else str(key)
    s = secret.get_secret_value() if hasattr(secret, "get_secret_value") else str(secret)
    return AlpacaBrokerClient(api_key=k, api_secret=s, base_url=base_url)


def validate_alpaca_user_key(api_key: str, api_secret: str, paper: bool) -> bool:
    """
    Validate user-provided Alpaca Trading API key by calling GET /v2/account.
    Used for BYOK: user's key unlocks trading. Do not log raw secret.
    """
    base_url = (
        "https://paper-api.alpaca.markets"
        if paper
        else "https://api.alpaca.markets"
    )
    url = f"{base_url.rstrip('/')}/v2/account"
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": api_secret,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            logger.info("BYOK Alpaca key validated (paper=%s)", paper)
            return True
        logger.debug("BYOK Alpaca key validation failed: status %s", resp.status_code)
        return False
    except requests.RequestException as e:
        logger.warning("BYOK Alpaca key validation request failed: %s", e)
        return False
