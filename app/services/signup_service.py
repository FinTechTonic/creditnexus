"""
Signup post-creation tasks: populate dashboard from Plaid and person search.

After user (and optionally org) creation, enqueue:
1. populate_dashboard_from_plaid – fetch accounts/transactions/investments for linked Plaid items.
2. person_search – use PeopleHub research for the user's display_name; store results for admin.

Both run in parallel (e.g. via asyncio.gather) in a single background task.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db import get_db
from app.db.models import User

logger = logging.getLogger(__name__)


def _populate_dashboard_from_plaid_sync(db: Session, user_id: int) -> None:
    """Fetch Plaid-backed portfolio for user and store a minimal prefill summary. No-op if no Plaid link."""
    try:
        from app.services.portfolio_aggregation_service import get_unified_portfolio

        overview = get_unified_portfolio(db, user_id)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
        if not isinstance(user.profile_data, dict):
            user.profile_data = {}
        user.profile_data["dashboard_prefill"] = {
            "populated_at": datetime.utcnow().isoformat(),
            "account_count": len((overview.get("account_info") or {}).get("accounts") or []),
            "total_equity": overview.get("total_equity"),
        }
        db.commit()
    except Exception as e:
        logger.warning("Signup populate_dashboard_from_plaid failed for user_id=%s: %s", user_id, e)


async def _person_search_async(db: Session, user_id: int) -> None:
    """Run PeopleHub research for user's display_name and store result in profile_data for admin."""
    try:
        from app.workflows.peoplehub_research_graph import execute_peoplehub_research

        user = db.query(User).filter(User.id == user_id).first()
        if not user or not (getattr(user, "display_name", None) or "").strip():
            return
        person_name = (user.display_name or "").strip()
        result = await execute_peoplehub_research(person_name=person_name, linkedin_url=None)
        if not isinstance(user.profile_data, dict):
            user.profile_data = {}
        user.profile_data["person_search_result"] = {
            "person_name": person_name,
            "searched_at": datetime.utcnow().isoformat(),
            "report": result.get("final_report"),
            "status": result.get("status"),
        }
        db.commit()
    except Exception as e:
        logger.warning("Signup person_search failed for user_id=%s: %s", user_id, e)


async def run_post_signup_tasks(user_id: int) -> None:
    """
    Run populate_dashboard_from_plaid and person_search in parallel.
    Uses a new DB session; call from a background task after user creation.
    """
    gen = get_db()
    try:
        db = next(gen)
    except StopIteration:
        return
    try:
        loop = asyncio.get_event_loop()
        await asyncio.gather(
            loop.run_in_executor(None, _populate_dashboard_from_plaid_sync, db, user_id),
            _person_search_async(db, user_id),
        )
    except Exception as e:
        logger.warning("Signup post-signup tasks failed for user_id=%s: %s", user_id, e)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
