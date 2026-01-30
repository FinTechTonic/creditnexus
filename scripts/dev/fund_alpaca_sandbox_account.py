#!/usr/bin/env python
"""
Fund an Alpaca Broker sandbox account via ACH transfer (paper trading).

Uses Alpaca Broker API:
1. List or create an ACH relationship for the account (sandbox test bank details).
2. Create an INCOMING transfer to credit the account.

In sandbox, the transfer is effective immediately. Use only with Broker sandbox
(ALPACA_BROKER_BASE_URL=https://broker-api.sandbox.alpaca.markets).

Usage:
    From project root:
        python scripts/fund_alpaca_sandbox_account.py
    Or with explicit account/amount:
        ACCOUNT_ID=61341496-2272-425d-9f3e-acdcb980e9ce AMOUNT=100000 python scripts/fund_alpaca_sandbox_account.py

Requires .env (or env) with:
    ALPACA_BROKER_API_KEY, ALPACA_BROKER_API_SECRET, ALPACA_BROKER_BASE_URL (sandbox)
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Project root on path so "app" resolves
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Defaults: your account and $100,000 for paper trading
DEFAULT_ACCOUNT_ID = "61341496-2272-425d-9f3e-acdcb980e9ce"
DEFAULT_ACCOUNT_NUMBER = "162368041"
DEFAULT_AMOUNT = "100000"

# Sandbox test ACH fixture (from Alpaca docs / dev/alpaca.md)
SANDBOX_ACH = {
    "account_owner_name": "Sandbox Account Owner",
    "bank_account_type": "CHECKING",
    "bank_account_number": "32131231abc",
    "bank_routing_number": "123103716",
    "nickname": "Sandbox Checking",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fund an Alpaca Broker sandbox account via ACH (paper trading)."
    )
    parser.add_argument(
        "--account-id",
        default=DEFAULT_ACCOUNT_ID,
        help=f"Alpaca account ID (default: {DEFAULT_ACCOUNT_ID})",
    )
    parser.add_argument(
        "--amount",
        default=DEFAULT_AMOUNT,
        help=f"Amount to deposit in USD (default: {DEFAULT_AMOUNT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be done; do not call the API",
    )
    args = parser.parse_args()

    account_id = args.account_id.strip()
    amount = str(args.amount).strip()

    if args.dry_run:
        logger.info("Dry run: would fund account_id=%s with amount=%s", account_id, amount)
        logger.info("Would ensure ACH relationship then POST transfer INCOMING.")
        return 0

    # Load config and get broker client
    from app.core.config import settings
    from app.services.alpaca_broker_service import get_broker_client, AlpacaBrokerAPIError

    client = get_broker_client()
    if not client:
        logger.error(
            "Alpaca Broker API not configured. Set ALPACA_BROKER_API_KEY, "
            "ALPACA_BROKER_API_SECRET, and ALPACA_BROKER_BASE_URL (sandbox) in .env"
        )
        return 1

    base_url = getattr(settings, "ALPACA_BROKER_BASE_URL", "") or ""
    if "sandbox" not in base_url.lower():
        logger.warning("ALPACA_BROKER_BASE_URL does not look like sandbox. Use sandbox for this script.")

    # 1) Get or create ACH relationship
    try:
        relationships = client.list_ach_relationships(account_id)
    except AlpacaBrokerAPIError as e:
        logger.error("Failed to list ACH relationships: %s", e)
        if getattr(e, "response", None):
            logger.error("Response: %s", e.response)
        return 1

    approved = [r for r in relationships if (r.get("status") or "").upper() == "APPROVED"]
    if approved:
        rel = approved[0]
        relationship_id = rel.get("id")
        logger.info("Using existing ACH relationship: %s (%s)", relationship_id, rel.get("nickname"))
    else:
        # Create sandbox ACH relationship
        logger.info("No approved ACH relationship; creating one with sandbox test data...")
        try:
            rel = client.create_ach_relationship(
                account_id=account_id,
                account_owner_name=SANDBOX_ACH["account_owner_name"],
                bank_account_type=SANDBOX_ACH["bank_account_type"],
                bank_account_number=SANDBOX_ACH["bank_account_number"],
                bank_routing_number=SANDBOX_ACH["bank_routing_number"],
                nickname=SANDBOX_ACH["nickname"],
            )
            relationship_id = rel.get("id")
            status = rel.get("status", "")
            logger.info("Created ACH relationship: %s (status=%s)", relationship_id, status)
            if (status or "").upper() == "QUEUED":
                logger.info("Waiting up to 90s for ACH relationship to become APPROVED...")
                for _ in range(18):
                    time.sleep(5)
                    relationships = client.list_ach_relationships(account_id)
                    approved = [r for r in relationships if (r.get("status") or "").upper() == "APPROVED"]
                    if approved and approved[0].get("id") == relationship_id:
                        logger.info("ACH relationship is APPROVED.")
                        break
                else:
                    # Use it anyway; sandbox may still accept the transfer
                    logger.warning("ACH relationship still not APPROVED; attempting transfer anyway.")
        except AlpacaBrokerAPIError as e:
            logger.error("Failed to create ACH relationship: %s", e)
            if getattr(e, "response", None):
                logger.error("Response: %s", e.response)
            return 1

    if not relationship_id:
        logger.error("No relationship_id available.")
        return 1

    # 2) Create INCOMING transfer
    try:
        transfer = client.create_transfer(
            account_id=account_id,
            transfer_type="ach",
            relationship_id=relationship_id,
            amount=amount,
            direction="INCOMING",
        )
        logger.info("Transfer created: %s", transfer.get("id"))
        logger.info("  status=%s amount=%s direction=%s", transfer.get("status"), transfer.get("amount"), transfer.get("direction"))
        logger.info("Account %s (number %s) funded with $%s for paper trading.", account_id, DEFAULT_ACCOUNT_NUMBER, amount)
        return 0
    except AlpacaBrokerAPIError as e:
        logger.error("Failed to create transfer: %s", e)
        if getattr(e, "response", None):
            logger.error("Response: %s", e.response)
        return 1


if __name__ == "__main__":
    sys.exit(main())
