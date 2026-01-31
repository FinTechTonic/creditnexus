"""add_organization_and_deployment_columns (Phase 8)

Revision ID: p8org001
Revises: h4a5b6c7d8e0
Create Date: 2026-01-30

Adds Organization (legal_name, registration_number, tax_id, lei, industry, country,
website, email, blockchain_*, bridge_*, status, approved_by/at, subscription_tier/expires_at,
metadata) and OrganizationBlockchainDeployment (network_name, rpc_url, notarization_contract,
token_contract, payment_router_contract, bridge_contract, status, deployed_at, deployed_by,
deployment_metadata, updated_at) columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "p8org001"
down_revision: Union[str, None] = "h4a5b6c7d8e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organization: registration and legal
    op.add_column("organizations", sa.Column("legal_name", sa.String(500), nullable=True))
    op.add_column("organizations", sa.Column("registration_number", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("tax_id", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("lei", sa.String(255), nullable=True))
    op.add_column("organizations", sa.Column("industry", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("country", sa.String(2), nullable=True))
    op.add_column("organizations", sa.Column("website", sa.String(500), nullable=True))
    op.add_column("organizations", sa.Column("email", sa.String(255), nullable=True))
    # Organization: blockchain
    op.add_column("organizations", sa.Column("blockchain_type", sa.String(50), nullable=True))
    op.add_column("organizations", sa.Column("blockchain_network", sa.String(100), nullable=True))
    op.add_column("organizations", sa.Column("blockchain_rpc_url", sa.String(500), nullable=True))
    op.add_column("organizations", sa.Column("blockchain_chain_id", sa.Integer(), nullable=True))
    op.add_column("organizations", sa.Column("blockchain_contract_addresses", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("organizations", sa.Column("bridge_contract_address", sa.String(66), nullable=True))
    op.add_column("organizations", sa.Column("bridge_status", sa.String(50), server_default="pending", nullable=False))
    # Organization: lifecycle
    op.add_column("organizations", sa.Column("status", sa.String(50), server_default="pending", nullable=False))
    op.add_column("organizations", sa.Column("registration_date", sa.DateTime(), nullable=True))
    op.add_column("organizations", sa.Column("approved_by", sa.Integer(), nullable=True))
    op.add_column("organizations", sa.Column("approved_at", sa.DateTime(), nullable=True))
    op.add_column("organizations", sa.Column("subscription_tier", sa.String(50), server_default="free", nullable=False))
    op.add_column("organizations", sa.Column("subscription_expires_at", sa.DateTime(), nullable=True))
    op.add_column("organizations", sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index(op.f("ix_organizations_status"), "organizations", ["status"], unique=False)
    op.create_index(op.f("ix_organizations_registration_number"), "organizations", ["registration_number"], unique=True)
    op.create_index(op.f("ix_organizations_lei"), "organizations", ["lei"], unique=True)
    op.create_foreign_key("fk_organizations_approved_by", "organizations", "users", ["approved_by"], ["id"], ondelete="SET NULL")

    # OrganizationBlockchainDeployment
    op.add_column("organization_blockchain_deployments", sa.Column("network_name", sa.String(100), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("rpc_url", sa.String(500), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("notarization_contract", sa.String(66), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("token_contract", sa.String(66), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("payment_router_contract", sa.String(66), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("bridge_contract", sa.String(66), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("status", sa.String(50), server_default="pending", nullable=False))
    op.add_column("organization_blockchain_deployments", sa.Column("deployed_at", sa.DateTime(), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("deployed_by", sa.Integer(), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("deployment_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("organization_blockchain_deployments", sa.Column("updated_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_org_blockchain_deployments_deployed_by", "organization_blockchain_deployments", "users", ["deployed_by"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_org_blockchain_deployments_deployed_by", "organization_blockchain_deployments", type_="foreignkey")
    op.drop_column("organization_blockchain_deployments", "updated_at")
    op.drop_column("organization_blockchain_deployments", "deployment_metadata")
    op.drop_column("organization_blockchain_deployments", "deployed_by")
    op.drop_column("organization_blockchain_deployments", "deployed_at")
    op.drop_column("organization_blockchain_deployments", "status")
    op.drop_column("organization_blockchain_deployments", "bridge_contract")
    op.drop_column("organization_blockchain_deployments", "payment_router_contract")
    op.drop_column("organization_blockchain_deployments", "token_contract")
    op.drop_column("organization_blockchain_deployments", "notarization_contract")
    op.drop_column("organization_blockchain_deployments", "rpc_url")
    op.drop_column("organization_blockchain_deployments", "network_name")

    op.drop_constraint("fk_organizations_approved_by", "organizations", type_="foreignkey")
    op.drop_index(op.f("ix_organizations_lei"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_registration_number"), table_name="organizations")
    op.drop_index(op.f("ix_organizations_status"), table_name="organizations")
    op.drop_column("organizations", "metadata")
    op.drop_column("organizations", "subscription_expires_at")
    op.drop_column("organizations", "subscription_tier")
    op.drop_column("organizations", "approved_at")
    op.drop_column("organizations", "approved_by")
    op.drop_column("organizations", "registration_date")
    op.drop_column("organizations", "status")
    op.drop_column("organizations", "bridge_status")
    op.drop_column("organizations", "bridge_contract_address")
    op.drop_column("organizations", "blockchain_contract_addresses")
    op.drop_column("organizations", "blockchain_chain_id")
    op.drop_column("organizations", "blockchain_rpc_url")
    op.drop_column("organizations", "blockchain_network")
    op.drop_column("organizations", "blockchain_type")
    op.drop_column("organizations", "email")
    op.drop_column("organizations", "website")
    op.drop_column("organizations", "country")
    op.drop_column("organizations", "industry")
    op.drop_column("organizations", "lei")
    op.drop_column("organizations", "tax_id")
    op.drop_column("organizations", "registration_number")
    op.drop_column("organizations", "legal_name")
