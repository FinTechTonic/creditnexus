"""
Vendored Plaid (plaid-python) for standalone: link token, exchange, SQLite storage.
Uses server/vendored/db for implementations and plaid_connections.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

try:
    from server.vendored.db import get_connection, init_db
except ImportError:
    from demo_mcp.server.vendored.db import get_connection, init_db

logger = logging.getLogger(__name__)

_plaid_api = None
_plaid_error: Optional[str] = None


def _get_plaid_client():
    """Lazy-init Plaid API. Returns (api, None) or (None, error_msg)."""
    global _plaid_api, _plaid_error
    if _plaid_error is not None:
        return None, _plaid_error
    if _plaid_api is not None:
        return _plaid_api, None
    cid = os.getenv("PLAID_CLIENT_ID", "").strip()
    secret = os.getenv("PLAID_SECRET", "").strip()
    if not cid or not secret:
        _plaid_error = "PLAID_CLIENT_ID and PLAID_SECRET are required"
        return None, _plaid_error
    env = (os.getenv("PLAID_ENV", "sandbox") or "sandbox").lower()
    try:
        import plaid
        from plaid.api import plaid_api
    except ImportError as e:
        _plaid_error = f"plaid-python not installed: {e}"
        return None, _plaid_error
    try:
        host = getattr(plaid, "Environment", None)
        if host is not None:
            if env == "production":
                host = host.Production
            elif env == "development":
                host = host.Development
            else:
                host = host.Sandbox
        else:
            hosts = {
                "production": "https://production.plaid.com",
                "development": "https://development.plaid.com",
            }
            host = hosts.get(env, "https://sandbox.plaid.com")
        if hasattr(plaid, "Configuration"):
            cfg = plaid.Configuration(host=host, api_key={"clientId": cid, "secret": secret})
            api_client = plaid.ApiClient(cfg)
            _plaid_api = plaid_api.PlaidApi(api_client)
            return _plaid_api, None
        _plaid_error = "Plaid SDK Configuration not found"
        return None, _plaid_error
    except Exception as e:
        _plaid_error = str(e)
        return None, _plaid_error


def ensure_plaid_implementation() -> int:
    """Return implementation id for name=plaid; insert if missing."""
    init_db()
    conn = get_connection()
    try:
        cur = conn.execute("SELECT id FROM implementations WHERE name = ? AND is_active = 1", ("plaid",))
        row = cur.fetchone()
        if row:
            return int(row["id"])
        cur = conn.execute("INSERT INTO implementations (name, is_active) VALUES (?, 1)", ("plaid",))
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def create_link_token(user_id: str) -> dict:
    """Return {\"link_token\": str} or {\"error\": str}."""
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.link_token_create_request import LinkTokenCreateRequest
        from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
        from plaid.model.country_code import CountryCode
        from plaid.model.products import Products
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    user = LinkTokenCreateRequestUser(client_user_id=user_id)
    products = [Products("transactions")]
    country_codes = [CountryCode("US")]
    req = LinkTokenCreateRequest(
        user=user,
        client_name="CreditNexus MCP",
        products=products,
        country_codes=country_codes,
        language="en",
    )
    try:
        resp = api.link_token_create(req)
        return {"link_token": resp.link_token}
    except Exception as e:
        logger.warning("Plaid link_token_create failed: %s", e)
        return {"error": str(e)}


def exchange_public_token(public_token: str, agent_wallet: Optional[str] = None) -> dict:
    """Exchange public_token; store in plaid_connections. Return {\"status\": \"connected\", \"connection_id\": int} or {\"error\": str}."""
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    try:
        req = ItemPublicTokenExchangeRequest(public_token=public_token)
        resp = api.item_public_token_exchange(req)
    except Exception as e:
        logger.warning("Plaid item_public_token_exchange failed: %s", e)
        return {"error": str(e)}
    impl_id = ensure_plaid_implementation()
    connection_data = {"access_token": resp.access_token, "item_id": resp.item_id}
    if agent_wallet and agent_wallet.strip():
        connection_data["agent_wallet"] = agent_wallet.strip()
    created_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            """INSERT INTO plaid_connections (implementation_id, user_id, connection_data, is_active, created_at)
               VALUES (?, ?, ?, 1, ?)""",
            (impl_id, "mcp-demo", json.dumps(connection_data), created_at),
        )
        conn.commit()
        return {"status": "connected", "connection_id": cur.lastrowid}
    finally:
        conn.close()


def get_plaid_connection_by_agent_wallet(agent_wallet: str) -> Optional[dict]:
    """Return first active plaid_connection whose connection_data.agent_wallet matches (case-insensitive), or None."""
    if not agent_wallet or not agent_wallet.strip():
        return None
    target = agent_wallet.strip().lower()
    init_db()
    conn = get_connection()
    try:
        cur = conn.execute(
            """SELECT pc.id, pc.connection_data FROM plaid_connections pc
               JOIN implementations i ON i.id = pc.implementation_id
               WHERE i.name = 'plaid' AND pc.is_active = 1"""
        )
        for row in cur.fetchall():
            try:
                data = json.loads(row["connection_data"]) if isinstance(row["connection_data"], str) else row["connection_data"]
            except (TypeError, json.JSONDecodeError):
                continue
            if (data.get("agent_wallet") or "").strip().lower() == target:
                return dict(row)
        return None
    finally:
        conn.close()
