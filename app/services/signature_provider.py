"""Signature provider abstraction for pluggable signature engines.

Phase 2 goal:
- Default provider: InternalSignatureService (native signatures)
- Optional provider: DigiSigner (if configured and desired)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DocumentSignature, User
from app.services.internal_signature_service import InternalSignatureService, SignatureCoordinates
from app.services.signature_service import SignatureService

logger = logging.getLogger(__name__)


@dataclass
class SignatureRequestContext:
    """Context passed to signature providers."""

    document_id: int
    signers: Optional[List[Dict[str, str]]] = None
    auto_detect_signers: bool = True
    expires_in_days: int = 30
    subject: Optional[str] = None
    message: Optional[str] = None
    urgency: str = "standard"
    requested_by_user_id: Optional[int] = None


class SignatureProvider(Protocol):
    """Provider interface for requesting signatures."""

    async def request_signature(self, ctx: SignatureRequestContext) -> DocumentSignature:
        ...


class DigiSignerSignatureProvider(SignatureProvider):
    """Adapter around existing DigiSigner-based SignatureService."""

    def __init__(self, db: Session) -> None:
        self.service = SignatureService(db)

    async def request_signature(self, ctx: SignatureRequestContext) -> DocumentSignature:
        # Underlying DigiSigner service is synchronous; wrap in async interface.
        return self.service.request_signature(
            document_id=ctx.document_id,
            signers=ctx.signers,
            auto_detect_signers=ctx.auto_detect_signers,
            expires_in_days=ctx.expires_in_days,
            subject=ctx.subject,
            message=ctx.message,
            urgency=ctx.urgency,
        )


class InternalSignatureProvider(SignatureProvider):
    """Internal provider backed by InternalSignatureService."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.service = InternalSignatureService(db)

    def _pick_signer_email(self, ctx: SignatureRequestContext) -> str:
        if ctx.signers:
            first = ctx.signers[0] or {}
            email = first.get("email")
            if not email:
                raise ValueError("First signer is missing email")
            return email

        if ctx.requested_by_user_id is not None:
            user = self.db.query(User).filter(User.id == ctx.requested_by_user_id).first()
            if user and user.email:
                return user.email

        raise ValueError("At least one signer with email is required for internal signatures")

    async def request_signature(self, ctx: SignatureRequestContext) -> DocumentSignature:
        signer_email = self._pick_signer_email(ctx)

        coords = SignatureCoordinates(page=0, x=50, y=50, width=200, height=80)

        signature = await self.service.create_signature_request(
            document_id=ctx.document_id,
            signer_email=signer_email,
            coordinates=coords,
            expires_in_days=ctx.expires_in_days,
            require_metamask=False,
        )

        return signature


def get_signature_provider(db: Session) -> SignatureProvider:
    """Select signature provider based on configuration."""
    provider_choice = (getattr(settings, "SIGNATURE_PROVIDER", "internal") or "internal").lower()
    digisigner_configured = bool(settings.DIGISIGNER_API_KEY)

    # #region agent log
    try:
        import json, time as _time

        with open(
            "c:\\Users\\MeMyself\\creditnexus\\.cursor\\debug.log", "a", encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(
                    {
                        "sessionId": "debug-session",
                        "runId": "pre-fix",
                        "hypothesisId": "P1",
                        "location": "app/services/signature_provider.py:get_signature_provider",
                        "message": "Selecting signature provider",
                        "data": {
                            "provider_choice": provider_choice,
                            "digisigner_configured": digisigner_configured,
                        },
                        "timestamp": _time.time(),
                    }
                )
                + "\n"
            )
    except Exception:
        pass
    # #endregion

    if provider_choice == "digisigner" and digisigner_configured:
        logger.info("Using DigiSignerSignatureProvider")
        return DigiSignerSignatureProvider(db)

    logger.info("Using InternalSignatureProvider (default)")
    return InternalSignatureProvider(db)


