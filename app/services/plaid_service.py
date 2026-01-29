"""
Plaid bank integration (Trading Phase 1).

- create_link_token: for Plaid Link UI
- exchange_public_token: store access_token in UserImplementationConnection
- get_accounts, get_balances, get_transactions

Expanded (Portfolio-First / Plaid-First):
- investments, liabilities, identity
- income / assets / consumer report (Plaid Check) / statements (where available)
- (future) identity verification + monitor/beacon + transfer/payment initiation + layer
"""

import logging
from datetime import date, timedelta
import json
import os
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import UserImplementationConnection, VerifiedImplementation

logger = logging.getLogger(__name__)

# Lazy Plaid imports (plaid-python)
_plaid_api = None
_plaid_config = None


def _agent_debug_log(*, hypothesisId: str, location: str, message: str, data: Dict[str, Any]) -> None:
    """
    Debug-mode NDJSON logger (no secrets / no PII).
    Writes to workspace debug log path.
    """
    try:
        path = r"c:\Users\MeMyself\creditnexus\.cursor\debug.log"
        payload = {
            "sessionId": "debug-session",
            "runId": "pre-fix",
            "hypothesisId": hypothesisId,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(__import__("time").time() * 1000),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Never break runtime on debug logging
        pass


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


def create_link_token_for_brokerage(user_id: int) -> Dict[str, Any]:
    """
    Create a Plaid Link token for brokerage onboarding (link-for-brokerage).
    Uses auth + identity products for account verification and form prefill.
    Returns {"link_token": str} or {"error": str}.
    """
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

    user = LinkTokenCreateRequestUser(client_user_id=str(user_id))
    # Auth (routing/account verification) + Identity (name, address) for brokerage prefill
    products = [Products("auth"), Products("identity")]
    country_codes = [CountryCode("US")]
    req = LinkTokenCreateRequest(
        user=user,
        client_name="CreditNexus Brokerage",
        products=products,
        country_codes=country_codes,
        language="en",
    )
    try:
        resp = api.link_token_create(req)
        return {"link_token": resp.link_token}
    except Exception as e:
        logger.warning("Plaid link_token_create (brokerage) failed: %s", e)
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


def get_identity(access_token: str) -> Dict[str, Any]:
    """
    Fetch identity for linked accounts (Identity product).
    Returns {"accounts":[...]} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.identity_get_request import IdentityGetRequest
        req = IdentityGetRequest(access_token=access_token)
        resp = api.identity_get(req)
        accounts = [a.to_dict() if hasattr(a, "to_dict") else _plaid_obj_to_dict(a) for a in resp.accounts]
        return {"accounts": accounts, "item": _plaid_obj_to_dict(resp.item) if getattr(resp, "item", None) else None}
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid identity_get failed: %s", e)
        return {"error": str(e)}


def get_liabilities(access_token: str) -> Dict[str, Any]:
    """
    Fetch liabilities (Liabilities product).
    Returns {"liabilities": {...}, "accounts":[...]} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.liabilities_get_request import LiabilitiesGetRequest
        req = LiabilitiesGetRequest(access_token=access_token)
        resp = api.liabilities_get(req)
        out = {
            "liabilities": _plaid_obj_to_dict(getattr(resp, "liabilities", None)),
            "accounts": [a.to_dict() if hasattr(a, "to_dict") else _plaid_obj_to_dict(a) for a in getattr(resp, "accounts", [])],
            "item": _plaid_obj_to_dict(resp.item) if getattr(resp, "item", None) else None,
        }
        return out
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid liabilities_get failed: %s", e)
        return {"error": str(e)}


def get_investments_holdings(access_token: str) -> Dict[str, Any]:
    """
    Fetch investment holdings (Investments product).
    Returns {"holdings":[...], "securities":[...], "accounts":[...]} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
        req = InvestmentsHoldingsGetRequest(access_token=access_token)
        resp = api.investments_holdings_get(req)
        return {
            "holdings": [h.to_dict() if hasattr(h, "to_dict") else _plaid_obj_to_dict(h) for h in getattr(resp, "holdings", [])],
            "securities": [s.to_dict() if hasattr(s, "to_dict") else _plaid_obj_to_dict(s) for s in getattr(resp, "securities", [])],
            "accounts": [a.to_dict() if hasattr(a, "to_dict") else _plaid_obj_to_dict(a) for a in getattr(resp, "accounts", [])],
            "item": _plaid_obj_to_dict(resp.item) if getattr(resp, "item", None) else None,
        }
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid investments_holdings_get failed: %s", e)
        return {"error": str(e)}


def get_investments_transactions(
    access_token: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    account_id: Optional[str] = None,
    count: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    """
    Fetch investment transactions (Investments product).
    Returns {"investment_transactions":[...], "securities":[...], "accounts":[...], "total_investment_transactions": int} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=30))
    try:
        from plaid.model.investments_transactions_get_request import InvestmentsTransactionsGetRequest
        from plaid.model.investments_transactions_get_request_options import InvestmentsTransactionsGetRequestOptions
        opt = InvestmentsTransactionsGetRequestOptions(
            account_ids=[account_id] if account_id else None,
            count=count,
            offset=offset,
        )
        req = InvestmentsTransactionsGetRequest(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            options=opt,
        )
        resp = api.investments_transactions_get(req)
        txs = [
            t.to_dict() if hasattr(t, "to_dict") else _plaid_obj_to_dict(t)
            for t in getattr(resp, "investment_transactions", [])
        ]
        return {
            "investment_transactions": txs,
            "securities": [s.to_dict() if hasattr(s, "to_dict") else _plaid_obj_to_dict(s) for s in getattr(resp, "securities", [])],
            "accounts": [a.to_dict() if hasattr(a, "to_dict") else _plaid_obj_to_dict(a) for a in getattr(resp, "accounts", [])],
            "total_investment_transactions": getattr(resp, "total_investment_transactions", len(txs)),
            "item": _plaid_obj_to_dict(resp.item) if getattr(resp, "item", None) else None,
        }
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid investments_transactions_get failed: %s", e)
        return {"error": str(e)}


def get_income(access_token: str) -> Dict[str, Any]:
    """
    Fetch income information (Income product / legacy).
    NOTE: Plaid Check Consumer Report is recommended for underwriting in many cases.
    Returns {"income": {...}} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.income_get_request import IncomeGetRequest
        req = IncomeGetRequest(access_token=access_token)
        resp = api.income_get(req)
        return {"income": _plaid_obj_to_dict(getattr(resp, "income", None))}
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid income_get failed: %s", e)
        return {"error": str(e)}


def get_assets(access_token: str) -> Dict[str, Any]:
    """
    Create an Assets report (Assets product).
    Returns {"assets_report_token": str, "asset_report_id": str} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.asset_report_create_request import AssetReportCreateRequest
        from plaid.model.asset_report_create_request_options import AssetReportCreateRequestOptions
        # Default to 30 days (common baseline); callers can adjust later as needed.
        options = AssetReportCreateRequestOptions()
        req = AssetReportCreateRequest(access_token=access_token, days_requested=30, options=options)
        resp = api.asset_report_create(req)
        return {
            "assets_report_token": getattr(resp, "asset_report_token", None),
            "asset_report_id": getattr(resp, "asset_report_id", None),
        }
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid asset_report_create failed: %s", e)
        return {"error": str(e)}


def get_assets_report(assets_report_token: str) -> Dict[str, Any]:
    """
    Fetch an Assets report by token.
    Returns {"report": {...}} or {"error": str}.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        from plaid.model.asset_report_get_request import AssetReportGetRequest
        req = AssetReportGetRequest(asset_report_token=assets_report_token)
        resp = api.asset_report_get(req)
        return {"report": _plaid_obj_to_dict(getattr(resp, "report", None))}
    except ImportError as e:
        return {"error": f"Plaid models: {e}"}
    except Exception as e:
        logger.warning("Plaid asset_report_get failed: %s", e)
        return {"error": str(e)}


def get_statements(access_token: str) -> Dict[str, Any]:
    """
    Statements product: currently varies by Plaid availability.
    This wrapper is intentionally conservative and returns a helpful error if unsupported.
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}
    try:
        # Not all plaid-python versions expose statements endpoints/models.
        from plaid.model.statements_list_request import StatementsListRequest  # type: ignore
        req = StatementsListRequest(access_token=access_token)
        resp = api.statements_list(req)  # type: ignore[attr-defined]
        return {"statements": _plaid_obj_to_dict(resp)}
    except ImportError:
        return {"error": "Plaid statements models not available in current SDK"}
    except Exception as e:
        logger.warning("Plaid statements_list failed: %s", e)
        return {"error": str(e)}


def get_consumer_report(*_: Any, **__: Any) -> Dict[str, Any]:
    """
    Plaid Check (Consumer Report) integration placeholder.
    Pricing and availability are not public; implementation requires product enablement and API contract.
    """
    return {"error": "consumer_report_not_implemented"}


def initiate_identity_verification(*_: Any, **__: Any) -> Dict[str, Any]:
    """Plaid Identity Verification placeholder (minimal integration planned)."""
    return {"error": "identity_verification_not_implemented"}


def monitor_aml_screening(*_: Any, **__: Any) -> Dict[str, Any]:
    """Plaid Monitor / AML screening placeholder (minimal integration planned)."""
    return {"error": "monitor_not_implemented"}


# Transfer billing: Plaid charges per transfer (see https://plaid.com/pricing).
# Callers (e.g. brokerage fund/withdraw) should record transfer usage for billing/credits
# via BillingService or RollingCreditsService when BROKERAGE_ONBOARDING_FEE or transfer fees apply.


def create_transfer(
    *,
    access_token: str,
    amount: str,
    currency: str = "USD",
    account_id: Optional[str] = None,
    transfer_type: str = "debit",
    description: str = "CreditNexus transfer",
) -> Dict[str, Any]:
    """
    Plaid Transfer (US) implementation.

    Official flow (per Plaid docs):
      1) POST /transfer/authorization/create
      2) POST /transfer/create (using authorization)

    Billing: Plaid charges per transfer; record usage for billing/credits when applicable.

    Returns:
      - {"authorization": {...}, "transfer": {...}} on success
      - {"error": "..."} on failure
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}

    # #region agent log
    _agent_debug_log(
        hypothesisId="H1",
        location="app/services/plaid_service.py:create_transfer:entry",
        message="create_transfer called",
        data={"has_account_id": bool(account_id), "currency": currency, "transfer_type": transfer_type},
    )
    # #endregion

    try:
        from decimal import Decimal
        from plaid.model.transfer_authorization_create_request import TransferAuthorizationCreateRequest
        from plaid.model.transfer_create_request import TransferCreateRequest
        from plaid.model.transfer_user_in_request import TransferUserInRequest
    except Exception as e:
        return {"error": f"Plaid transfer models unavailable: {e}"}

    try:
        # If caller didn't supply account_id, choose first eligible depository account.
        if not account_id:
            acct = get_accounts(access_token)
            if "error" in acct:
                return {"error": acct["error"]}
            accounts = acct.get("accounts") or []
            chosen = None
            for a in accounts:
                # best-effort: pick a depository/checking first
                try:
                    if (a.get("type") == "depository") and (a.get("subtype") in ("checking", "savings", None)):
                        chosen = a
                        break
                except Exception:
                    continue
            if not chosen and accounts:
                chosen = accounts[0]
            account_id = (chosen or {}).get("account_id")
            if not account_id:
                return {"error": "No eligible Plaid account_id found for transfer"}

        # Authorization
        # IMPORTANT: do not log amount; it can be sensitive for some orgs
        user = TransferUserInRequest(legal_name="CreditNexus User")
        auth_req = TransferAuthorizationCreateRequest(
            access_token=access_token,
            account_id=account_id,
            type=transfer_type,  # debit or credit
            network="ach",
            amount=Decimal(str(amount)),
            ach_class="ppd",
            user=user,
        )
        auth_resp = api.transfer_authorization_create(auth_req)
        auth = auth_resp.to_dict() if hasattr(auth_resp, "to_dict") else _plaid_obj_to_dict(auth_resp)

        # #region agent log
        _agent_debug_log(
            hypothesisId="H1",
            location="app/services/plaid_service.py:create_transfer:auth",
            message="transfer authorization result",
            data={
                "decision": auth.get("decision") or auth.get("authorization", {}).get("decision"),
                "rationale": auth.get("rationale") or auth.get("authorization", {}).get("rationale"),
            },
        )
        # #endregion

        # Decision handling
        decision = (auth.get("decision") or auth.get("authorization", {}).get("decision") or "").lower()
        if decision and decision not in ("approved",):
            return {"error": "transfer_authorization_not_approved", "authorization": auth}

        # Create transfer
        auth_id = auth.get("authorization", {}).get("id") or auth.get("id")
        if not auth_id:
            return {"error": "transfer_authorization_missing_id", "authorization": auth}

        create_req = TransferCreateRequest(
            access_token=access_token,
            account_id=account_id,
            authorization_id=auth_id,
            description=description,
        )
        create_resp = api.transfer_create(create_req)
        transfer = create_resp.to_dict() if hasattr(create_resp, "to_dict") else _plaid_obj_to_dict(create_resp)

        # #region agent log
        _agent_debug_log(
            hypothesisId="H1",
            location="app/services/plaid_service.py:create_transfer:created",
            message="transfer created",
            data={"has_transfer_id": bool((transfer.get("transfer") or {}).get("id") or transfer.get("id"))},
        )
        # #endregion

        return {"authorization": auth, "transfer": transfer}
    except Exception as e:
        logger.warning("Plaid transfer flow failed: %s", e)
        # #region agent log
        _agent_debug_log(
            hypothesisId="H1",
            location="app/services/plaid_service.py:create_transfer:exception",
            message="transfer flow exception",
            data={"error": str(e)[:300]},
        )
        # #endregion
        return {"error": str(e)}


def create_payment_initiation(
    *,
    access_token: str,
    amount: str,
    currency: str = "USD",
    payment_type: str = "bank_payment",
    # Optional Payment Initiation (UK/EU) recipient details:
    recipient_name: Optional[str] = None,
    iban: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Initiate a bank payment via Plaid.

    Strategy:
    - If recipient details (recipient_name + iban) are provided, attempt Plaid Payment Initiation
      (UK/EU) using recipient/create + payment/create.
    - Otherwise default to Plaid Transfer (US) as the practical path for linked US accounts.

    Returns a normalized structure:
      - {"mode": "transfer", "transfer": {...}, "authorization": {...}}
      - {"mode": "payment_initiation", "recipient": {...}, "payment": {...}}
      - {"error": "..."}
    """
    # #region agent log
    _agent_debug_log(
        hypothesisId="H2",
        location="app/services/plaid_service.py:create_payment_initiation:entry",
        message="create_payment_initiation called",
        data={"has_recipient": bool(recipient_name and iban), "currency": currency, "payment_type": payment_type},
    )
    # #endregion

    # UK/EU Payment Initiation path (requires recipient info)
    if recipient_name and iban:
        api, err = _get_plaid_client()
        if err:
            return {"error": err}
        try:
            from decimal import Decimal
            from plaid.model.payment_initiation_recipient_create_request import PaymentInitiationRecipientCreateRequest
            from plaid.model.payment_initiation_payment_create_request import PaymentInitiationPaymentCreateRequest
            from plaid.model.payment_initiation_address import PaymentInitiationAddress
        except Exception as e:
            return {"error": f"Plaid payment initiation models unavailable: {e}"}

        try:
            # Recipient create
            recipient_req = PaymentInitiationRecipientCreateRequest(
                name=recipient_name,
                iban=iban,
                address=PaymentInitiationAddress(
                    street=["N/A"],
                    city="N/A",
                    postal_code="N/A",
                    country="GB",
                ),
            )
            recipient_resp = api.payment_initiation_recipient_create(recipient_req)
            recipient = recipient_resp.to_dict() if hasattr(recipient_resp, "to_dict") else _plaid_obj_to_dict(recipient_resp)

            recipient_id = recipient.get("recipient_id") or recipient.get("id")
            if not recipient_id:
                return {"error": "payment_initiation_recipient_missing_id", "recipient": recipient}

            # Payment create (authorization happens in Link in PI flows; this just creates the intent)
            payment_req = PaymentInitiationPaymentCreateRequest(
                recipient_id=recipient_id,
                reference=f"CreditNexus:{payment_type}",
                amount=Decimal(str(amount)),
                currency=currency,
            )
            payment_resp = api.payment_initiation_payment_create(payment_req)
            payment = payment_resp.to_dict() if hasattr(payment_resp, "to_dict") else _plaid_obj_to_dict(payment_resp)

            # #region agent log
            _agent_debug_log(
                hypothesisId="H2",
                location="app/services/plaid_service.py:create_payment_initiation:pi_created",
                message="payment initiation recipient+payment created",
                data={"has_recipient_id": True, "has_payment_id": bool(payment.get("payment_id") or payment.get("id"))},
            )
            # #endregion

            return {"mode": "payment_initiation", "recipient": recipient, "payment": payment}
        except Exception as e:
            logger.warning("Plaid payment initiation flow failed: %s", e)
            # #region agent log
            _agent_debug_log(
                hypothesisId="H2",
                location="app/services/plaid_service.py:create_payment_initiation:pi_exception",
                message="payment initiation exception",
                data={"error": str(e)[:300]},
            )
            # #endregion
            return {"error": str(e)}

    # Default: US Transfer path
    out = create_transfer(access_token=access_token, amount=amount, currency=currency, transfer_type="debit")
    if "error" in out:
        return {"error": out["error"], "mode": "transfer", "details": out.get("authorization")}
    return {"mode": "transfer", **out}


def create_layer_session(*, template_id: str, client_user_id: str) -> Dict[str, Any]:
    """
    Plaid Layer session token creation.

    Per Plaid Layer docs, this is created via Layer's session/token/create
    and returns a Link token to start the Layer flow.

    Returns:
      - {"link_token": "..."} or {"error": "..."}
    """
    api, err = _get_plaid_client()
    if err:
        return {"error": err}

    # #region agent log
    _agent_debug_log(
        hypothesisId="H3",
        location="app/services/plaid_service.py:create_layer_session:entry",
        message="create_layer_session called",
        data={"has_template_id": bool(template_id), "has_client_user_id": bool(client_user_id)},
    )
    # #endregion

    try:
        # Not all plaid-python versions include Layer models/methods; use getattr defensively.
        from plaid.model.session_token_create_request import SessionTokenCreateRequest  # type: ignore
    except Exception as e:
        return {"error": f"Plaid Layer models unavailable: {e}"}

    try:
        req = SessionTokenCreateRequest(
            template_id=template_id,
            client_user_id=client_user_id,
        )
        fn = getattr(api, "session_token_create", None)
        if not fn:
            return {"error": "Plaid Layer session_token_create not available in current SDK"}
        resp = fn(req)
        d = resp.to_dict() if hasattr(resp, "to_dict") else _plaid_obj_to_dict(resp)
        link_token = d.get("link_token") or d.get("session_token") or d.get("token")
        if not link_token:
            return {"error": "Plaid Layer did not return link token", "response": d}
        return {"link_token": link_token, "raw": d}
    except Exception as e:
        logger.warning("Plaid layer session token create failed: %s", e)
        # #region agent log
        _agent_debug_log(
            hypothesisId="H3",
            location="app/services/plaid_service.py:create_layer_session:exception",
            message="layer session exception",
            data={"error": str(e)[:300]},
        )
        # #endregion
        return {"error": str(e)}


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
