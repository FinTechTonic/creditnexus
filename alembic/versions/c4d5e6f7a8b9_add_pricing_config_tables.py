"""add pricing config tables

Revision ID: c4d5e6f7a8b9
Revises: b7a9c1d2e3f4
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "b7a9c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plaid_pricing_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("api_endpoint", sa.String(length=100), nullable=False),
        sa.Column("cost_per_call_usd", sa.Numeric(precision=10, scale=4), server_default="0", nullable=False),
        sa.Column("cost_per_call_credits", sa.Numeric(precision=10, scale=4), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plaid_pricing_configs_instance_id"), "plaid_pricing_configs", ["instance_id"], unique=False)
    op.create_index(op.f("ix_plaid_pricing_configs_organization_id"), "plaid_pricing_configs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_plaid_pricing_configs_api_endpoint"), "plaid_pricing_configs", ["api_endpoint"], unique=False)

    op.create_table(
        "service_pricing_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("service_name", sa.String(length=120), nullable=False),
        sa.Column("cost_per_call_usd", sa.Numeric(precision=10, scale=4), server_default="0", nullable=False),
        sa.Column("cost_per_call_credits", sa.Numeric(precision=10, scale=4), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_pricing_configs_instance_id"), "service_pricing_configs", ["instance_id"], unique=False)
    op.create_index(op.f("ix_service_pricing_configs_organization_id"), "service_pricing_configs", ["organization_id"], unique=False)
    op.create_index(op.f("ix_service_pricing_configs_service_name"), "service_pricing_configs", ["service_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_service_pricing_configs_service_name"), table_name="service_pricing_configs")
    op.drop_index(op.f("ix_service_pricing_configs_organization_id"), table_name="service_pricing_configs")
    op.drop_index(op.f("ix_service_pricing_configs_instance_id"), table_name="service_pricing_configs")
    op.drop_table("service_pricing_configs")

    op.drop_index(op.f("ix_plaid_pricing_configs_api_endpoint"), table_name="plaid_pricing_configs")
    op.drop_index(op.f("ix_plaid_pricing_configs_organization_id"), table_name="plaid_pricing_configs")
    op.drop_index(op.f("ix_plaid_pricing_configs_instance_id"), table_name="plaid_pricing_configs")
    op.drop_table("plaid_pricing_configs")

