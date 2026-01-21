"""organizations, organization_blockchain_deployments, users.organization_id (org_1)

Revision ID: e2024org_org
Revises: c2024sp_mpl
Create Date: 2026-01-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e2024org_org"
down_revision: Union[str, Sequence[str], None] = "c2024sp_mpl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "organizations" not in existing:
        op.create_table(
            "organizations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=100), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_organizations_name", "organizations", ["name"])
        op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    if "organization_blockchain_deployments" not in existing:
        op.create_table(
            "organization_blockchain_deployments",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("organization_id", sa.Integer(), nullable=False),
            sa.Column("chain_id", sa.Integer(), nullable=False),
            sa.Column("deployment_type", sa.String(length=50), nullable=False),
            sa.Column("contract_address", sa.String(length=66), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_organization_blockchain_deployments_organization_id", "organization_blockchain_deployments", ["organization_id"])
        op.create_index("ix_organization_blockchain_deployments_chain_id", "organization_blockchain_deployments", ["chain_id"])
        op.create_index("ix_organization_blockchain_deployments_deployment_type", "organization_blockchain_deployments", ["deployment_type"])
        op.create_index("ix_organization_blockchain_deployments_contract_address", "organization_blockchain_deployments", ["contract_address"])

    if "users" in existing:
        cols = [c["name"] for c in inspector.get_columns("users")]
        if "organization_id" not in cols:
            op.add_column("users", sa.Column("organization_id", sa.Integer(), nullable=True))
            op.create_index("ix_users_organization_id", "users", ["organization_id"])
            op.create_foreign_key(
                "fk_users_organization_id",
                "users",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "cross_chain_transactions" in existing:
        cols = [c["name"] for c in inspector.get_columns("cross_chain_transactions")]
        if "organization_id" not in cols:
            op.add_column("cross_chain_transactions", sa.Column("organization_id", sa.Integer(), nullable=True))
            op.create_index("ix_cross_chain_transactions_organization_id", "cross_chain_transactions", ["organization_id"])
            op.create_foreign_key(
                "fk_cross_chain_transactions_organization_id",
                "cross_chain_transactions",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    if "cross_chain_transactions" in (sa.inspect(op.get_bind()).get_table_names() or []):
        try:
            op.drop_constraint("fk_cross_chain_transactions_organization_id", "cross_chain_transactions", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index("ix_cross_chain_transactions_organization_id", table_name="cross_chain_transactions")
        except Exception:
            pass
        try:
            op.drop_column("cross_chain_transactions", "organization_id")
        except Exception:
            pass
    if "users" in (sa.inspect(op.get_bind()).get_table_names() or []):
        try:
            op.drop_constraint("fk_users_organization_id", "users", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index("ix_users_organization_id", table_name="users")
        except Exception:
            pass
        try:
            op.drop_column("users", "organization_id")
        except Exception:
            pass
    op.drop_index("ix_organization_blockchain_deployments_contract_address", table_name="organization_blockchain_deployments")
    op.drop_index("ix_organization_blockchain_deployments_deployment_type", table_name="organization_blockchain_deployments")
    op.drop_index("ix_organization_blockchain_deployments_chain_id", table_name="organization_blockchain_deployments")
    op.drop_index("ix_organization_blockchain_deployments_organization_id", table_name="organization_blockchain_deployments")
    op.drop_table("organization_blockchain_deployments")
    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_table("organizations")
