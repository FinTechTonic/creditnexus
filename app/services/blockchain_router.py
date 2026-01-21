"""BlockchainRouter: resolve contract address by organization and deployment type.
Falls back to global settings when organization_id is None or no org-specific deployment.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import OrganizationBlockchainDeployment

logger = logging.getLogger(__name__)


def get_contract_address(
    db: Session,
    deployment_type: str,
    *,
    organization_id: Optional[int] = None,
    chain_id: Optional[int] = None,
) -> Optional[str]:
    """Return contract address for deployment_type, optionally scoped to organization and chain.
    If organization_id is set, look up OrganizationBlockchainDeployment (is_primary or by chain_id).
    Otherwise fall back to settings (e.g. SECURITIZATION_NOTARIZATION_CONTRACT for notarization).
    """
    if organization_id is not None:
        q = (
            db.query(OrganizationBlockchainDeployment)
            .filter(
                OrganizationBlockchainDeployment.organization_id == organization_id,
                OrganizationBlockchainDeployment.deployment_type == deployment_type,
            )
        )
        if chain_id is not None:
            q = q.filter(OrganizationBlockchainDeployment.chain_id == chain_id)
        # Prefer is_primary
        row = q.order_by(OrganizationBlockchainDeployment.is_primary.desc()).first()
        if row and row.contract_address:
            return row.contract_address

    # Fallback to global config
    m = {
        "notarization": getattr(settings, "SECURITIZATION_NOTARIZATION_CONTRACT", None),
        "token": getattr(settings, "SECURITIZATION_TOKEN_CONTRACT", None),
        "router": getattr(settings, "SECURITIZATION_PAYMENT_ROUTER_CONTRACT", None),
    }
    return m.get(deployment_type)
