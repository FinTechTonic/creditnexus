"""add_market_events_pool_tranche_loan

Revision ID: c2024sp_mpl
Revises: b2024sp_ec
Create Date: 2025-01-15

Adds pool/tranche/loan listing and loan binary markets:
- market_events: pool_id, tranche_id, loan_asset_id (nullable); deal_id, sfp_package_id nullable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2024sp_mpl"
down_revision: Union[str, Sequence[str], None] = "b2024sp_ec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col(conn, table: str, c: str) -> bool:
    r = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns WHERE table_name=:t AND column_name=:c"
    ), {"t": table, "c": c})
    return r.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()
    t = "market_events"

    if not _col(conn, t, "pool_id"):
        op.add_column(t, sa.Column("pool_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_market_events_pool", t, "securitization_pools", ["pool_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_market_events_pool_id", t, ["pool_id"])
    if not _col(conn, t, "tranche_id"):
        op.add_column(t, sa.Column("tranche_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_market_events_tranche", t, "securitization_tranches", ["tranche_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_market_events_tranche_id", t, ["tranche_id"])
    if not _col(conn, t, "loan_asset_id"):
        op.add_column(t, sa.Column("loan_asset_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_market_events_loan_asset", t, "loan_assets", ["loan_asset_id"], ["id"], ondelete="SET NULL")
        op.create_index("ix_market_events_loan_asset_id", t, ["loan_asset_id"])

    op.alter_column(t, "sfp_package_id", existing_type=sa.INTEGER(), nullable=True)
    op.alter_column(t, "deal_id", existing_type=sa.INTEGER(), nullable=True)


def downgrade() -> None:
    op.alter_column("market_events", "deal_id", existing_type=sa.INTEGER(), nullable=False)
    op.alter_column("market_events", "sfp_package_id", existing_type=sa.INTEGER(), nullable=False)
    op.drop_index("ix_market_events_loan_asset_id", table_name="market_events")
    op.drop_constraint("fk_market_events_loan_asset", "market_events", type_="foreignkey")
    op.drop_column("market_events", "loan_asset_id")
    op.drop_index("ix_market_events_tranche_id", table_name="market_events")
    op.drop_constraint("fk_market_events_tranche", "market_events", type_="foreignkey")
    op.drop_column("market_events", "tranche_id")
    op.drop_index("ix_market_events_pool_id", table_name="market_events")
    op.drop_constraint("fk_market_events_pool", "market_events", type_="foreignkey")
    op.drop_column("market_events", "pool_id")
