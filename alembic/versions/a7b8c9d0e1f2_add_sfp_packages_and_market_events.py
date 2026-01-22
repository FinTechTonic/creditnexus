"""add_sfp_packages_and_market_events

Revision ID: a7b8c9d0e1f2
Revises: 2e636e0e3f8b, 8c92e21f2aa9
Create Date: 2026-01-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = ("2e636e0e3f8b", "8c92e21f2aa9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sfp_packages and market_events tables."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "sfp_packages" not in existing:
        op.create_table(
            "sfp_packages",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("sfp_id", sa.String(length=255), nullable=False),
            sa.Column("deal_id", sa.Integer(), nullable=False),
            sa.Column("merkle_root", sa.String(length=66), nullable=False),
            sa.Column("cdm_hash", sa.String(length=66), nullable=False),
            sa.Column("signature_hashes", JSONB(), nullable=False),
            sa.Column("filing_hashes", JSONB(), nullable=False),
            sa.Column("transaction_hash", sa.String(length=66), nullable=True),
            sa.Column("block_number", sa.Integer(), nullable=True),
            sa.Column("bundle_timestamp", sa.DateTime(), nullable=False),
            sa.Column("market_event_type", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], name="fk_sfp_packages_deal_id"),
        )
        op.create_index("ix_sfp_packages_sfp_id", "sfp_packages", ["sfp_id"], unique=True)
        op.create_index("ix_sfp_packages_deal_id", "sfp_packages", ["deal_id"])

    if "market_events" not in existing:
        op.create_table(
            "market_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("market_id", sa.String(length=255), nullable=False),
            sa.Column("sfp_package_id", sa.Integer(), nullable=False),
            sa.Column("deal_id", sa.Integer(), nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("outcome_type", sa.String(length=50), nullable=False),
            sa.Column("resolution_condition", JSONB(), nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("resolved_at", sa.DateTime(), nullable=True),
            sa.Column("resolution_outcome", sa.String(length=20), nullable=True),
            sa.Column("oracle_triggered", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("liquidity_pool_address", sa.String(length=66), nullable=True),
            sa.Column("visibility", sa.String(length=20), nullable=False, server_default=sa.text("'public'")),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["sfp_package_id"], ["sfp_packages.id"], name="fk_market_events_sfp_package_id"),
            sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], name="fk_market_events_deal_id"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_market_events_created_by"),
        )
        op.create_index("ix_market_events_market_id", "market_events", ["market_id"], unique=True)
        op.create_index("ix_market_events_sfp_package_id", "market_events", ["sfp_package_id"])
        op.create_index("ix_market_events_deal_id", "market_events", ["deal_id"])


def downgrade() -> None:
    """Drop market_events and sfp_packages."""
    op.drop_index("ix_market_events_deal_id", table_name="market_events")
    op.drop_index("ix_market_events_sfp_package_id", table_name="market_events")
    op.drop_index("ix_market_events_market_id", table_name="market_events")
    op.drop_table("market_events")
    op.drop_index("ix_sfp_packages_deal_id", table_name="sfp_packages")
    op.drop_index("ix_sfp_packages_sfp_id", table_name="sfp_packages")
    op.drop_table("sfp_packages")
