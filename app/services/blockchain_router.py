"""BlockchainRouter: resolve contract address by organization and deployment type.
Falls back to global settings when organization_id is None or no org-specific deployment.
Phase 8: BlockchainRouterService with get_user_blockchain, get_web3_connection, route_notarization.
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Organization, OrganizationBlockchainDeployment, User

logger = logging.getLogger(__name__)

# Simple in-process cache for Web3 by (org_id, chain_id)
_web3_cache: Dict[tuple, Any] = {}


class BlockchainRouterService:
    """Resolve user's org blockchain config, Web3 connection, and notarization contract."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_user_blockchain(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Return org blockchain config from User.organization_id → Organization → OrganizationBlockchainDeployment."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or not getattr(user, "organization_id", None):
            return None
        org = self.db.query(Organization).filter(Organization.id == user.organization_id).first()
        if not org:
            return None
        deployment = (
            self.db.query(OrganizationBlockchainDeployment)
            .filter(OrganizationBlockchainDeployment.organization_id == org.id)
            .order_by(OrganizationBlockchainDeployment.is_primary.desc())
            .first()
        )
        if not deployment:
            return None
        return {
            "organization_id": org.id,
            "chain_id": deployment.chain_id,
            "network_name": deployment.network_name,
            "rpc_url": getattr(deployment, "rpc_url", None),
            "notarization_contract": deployment.notarization_contract,
            "token_contract": deployment.token_contract,
            "payment_router_contract": deployment.payment_router_contract,
            "bridge_contract": deployment.bridge_contract,
            "contract_address": deployment.contract_address,
            "deployment_type": deployment.deployment_type,
        }

    def get_web3_connection(self, organization_id: int, chain_id: int) -> Optional[Any]:
        """Return cached Web3 for org RPC URL from OrganizationBlockchainDeployment."""
        key = (organization_id, chain_id)
        if key in _web3_cache:
            return _web3_cache[key]
        deployment = (
            self.db.query(OrganizationBlockchainDeployment)
            .filter(
                OrganizationBlockchainDeployment.organization_id == organization_id,
                OrganizationBlockchainDeployment.chain_id == chain_id,
            )
            .first()
        )
        if not deployment or not getattr(deployment, "rpc_url", None):
            return None
        try:
            from web3 import Web3
            w3 = Web3(Web3.HTTPProvider(deployment.rpc_url))
            _web3_cache[key] = w3
            return w3
        except Exception as e:
            logger.warning("get_web3_connection failed: %s", e)
            return None

    def route_notarization(self, user_id: int, payload: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Resolve org notarization contract address for user; return address for caller to use."""
        config = self.get_user_blockchain(user_id)
        if config and (config.get("notarization_contract") or config.get("contract_address")):
            return config.get("notarization_contract") or config.get("contract_address")
        return get_contract_address(self.db, "notarization", organization_id=None, chain_id=None)


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
