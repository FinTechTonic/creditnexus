"""
Plaid bank integration (Trading Phase 1).

- create_link_token: for Plaid Link UI
- exchange_public_token: store access_token in UserImplementationConnection
- get_accounts, get_balances, get_transactions
"""

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import UserImplementationConnection, VerifiedImplementation

logger = logging.getLogger(__name__)

# Lazy Plaid imports (plaid-python)
_plaid_api = None
_plaid_config = None


def _get_plaid_client():
    """Lazy-init Plaid API client. Returns (api, None) or (None, error_msg)."""
    global _plaid_api, _plaid_config
    if not getattr(settings, "PLAID_ENABLED", False):
        return None, "Plaid is disabled (PLAID_ENABLED=false)"
    cid = getattr(settings, "PLAID_CLIENT_ID", None)
    secret = getattr(settings, "PLAID_SECRET", None)
    if not cid or not secret:
        return None, "PLAID_CLIENT_ID and PLAID_SECRET are required"
    cid = cid.get_secret_value() if hasattr(cid, "get_secret_value") else cid
    secret = secret.get_secret_value() if hasattr(secret, "get_secret_value") else secret

    try:
        import plaid
        from plaid.api import plaid_api
    except ImportError as e:
        return None, f"plaid-python not installed: {e}"

    env = (getattr(settings, "PLAID_ENV", None) or "sandbox").lower()
    host = getattr(plaid, "Environment", None)
    if host is not None:
        if env == "production":
            host = host.Production
        elif env == "development":
            host = host.Development
        else:
            host = host.Sandbox
    else:
        hosts = {"production": "https://production.plaid.com", "development": "https://development.plaid.com"}
        host = hosts.get(env, "https://sandbox.plaid.com")

    try:
        if hasattr(plaid, "Configuration"):
            cfg = plaid.Configuration(host=host, api_key={"clientId": cid, "secret": secret})
            api_client = plaid.ApiClient(cfg)
            _plaid_api = plaid_api.PlaidApi(api_client)
        else:
            return None, "Plaid SDK Configuration not found"
        return _plaid_api, None
    except Exception as e:
        return None, str(e)


def create_link_token(user_id: int) -> Dict[str, Any]:
    """
    Create a Plaid Link token for the frontend.
    Returns {"link_token": str} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}

    try:
        import plaid
        from plaid.model.link_token_create_request import LinkTokenCreateRequest
        from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
        from plaid.model.country_code import CountryCode
        from plaid.model.products import Products
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}

    user = LinkTokenCreateRequestUser(client_user_id=str(user_id))
    products = [Products("transactions")]
    country_codes = [CountryCode("US")]
    req = LinkTokenCreateRequest(
        user=user,
        client_name="CreditNexus",
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


def exchange_public_token(public_token: str) -> Dict[str, Any]:
    """
    Exchange public_token for access_token and item_id.
    Returns {"access_token": str, "item_id": str} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}

    try:
        from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
        req = ItemPublicTokenExchangeRequest(public_token=public_token)
        resp = api.item_public_token_exchange(req)
        return {"access_token": resp.access_token, "item_id": resp.item_id}
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid item_public_token_exchange failed: %s", e)
        return {"error": str(e)}


def get_accounts(access_token: str) -> Dict[str, Any]:
    """Fetch accounts for an access_token. Returns {"accounts": [...]} or {"error": str}."""
    api, err = _get_plaid_client()
    if err:
        return {"error": err}

    try:
        from plaid.model.accounts_get_request import AccountsGetRequest
        req = AccountsGetRequest(access_token=access_token)
        resp = api.accounts_get(req)
        accounts = [a.to_dict() if hasattr(a, "to_dict") else _plaid_obj_to_dict(a) for a in resp.accounts]
        return {"accounts": accounts, "item": _plaid_obj_to_dict(resp.item) if resp.item else None}
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid accounts_get failed: %s", e)
        return {"error": str(e)}


def get_balances(access_token: str) -> Dict[str, Any]:
    """Fetch balances. Returns {"accounts": [{"account_id","balances":{...}}]} or {"error": str}."""
    api, err = _get_plaid_client()
    if err:
        return {"error": err}

    try:
        from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
        req = AccountsBalanceGetRequest(access_token=access_token)
        resp = api.accounts_balance_get(req)
        accounts = [a.to_dict() if hasattr(a, "to_dict") else _plaid_obj_to_dict(a) for a in resp.accounts]
        return {"accounts": accounts}
    except ImportError:
        return {"error": "Plaid models for balance not available"}
    except Exception as e:
        logger.warning("Plaid accounts_balance_get failed: %s", e)
        return {"error": str(e)}


def get_transactions(
    access_token: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_id: Optional[str] = None,
    count: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """Fetch transactions. Returns {"transactions": [...], "total_transactions": int} or {"error": str}."""
    api, err = _get_plaid_client()
    if err:
        return {"error": err}

    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))

    try:
        from plaid.model.transactions_get_request import TransactionsGetRequest
        from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
        opt = TransactionsGetRequestOptions(
            account_ids=[account_id] if account_id else None,
            count=count,
            offset=offset,
        )
        req = TransactionsGetRequest(access_token=access_token, start_date=start_date, end_date=end_date, options=opt)
        resp = api.transactions_get(req)
        txs = [t.to_dict() if hasattr(t, "to_dict") else _plaid_obj_to_dict(t) for t in resp.transactions]
        return {"transactions": txs, "total_transactions": getattr(resp, "total_transactions", len(txs))}
    except ImportError:
        return {"error": "Plaid models for transactions not available"}
    except Exception as e:
        logger.warning("Plaid transactions_get failed: %s", e)
        return {"error": str(e)}


def _plaid_obj_to_dict(obj: Any) -> dict:
    if obj is None:
        return {}
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    return {"raw": str(obj)}


def get_plaid_connection(db: Session, user_id: int) -> Optional[UserImplementationConnection]:
    """Return the user's Plaid UserImplementationConnection if any."""
    impl = db.query(VerifiedImplementation).filter(
        VerifiedImplementation.name == "plaid",
        VerifiedImplementation.is_active == True,
    ).first()
    if not impl:
        return None
    return db.query(UserImplementationConnection).filter(
        UserImplementationConnection.user_id == user_id,
        UserImplementationConnection.implementation_id == impl.id,
        UserImplementationConnection.is_active == True,
    ).first()


def ensure_plaid_implementation(db: Session) -> Optional[VerifiedImplementation]:
    """Create VerifiedImplementation for 'plaid' if missing. Return it."""
    impl = db.query(VerifiedImplementation).filter(VerifiedImplementation.name == "plaid").first()
    if impl:
        return impl
    impl = VerifiedImplementation(
        name="plaid",
        display_name="Plaid",
        category="banking",
        is_active=True,
    )
    db.add(impl)
    db.commit()
    db.refresh(impl)
    return impl
