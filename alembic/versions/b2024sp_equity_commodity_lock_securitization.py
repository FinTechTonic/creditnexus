"""add_equity_commodity_lock_securitization

Revision ID: b2024sp_ec
Revises: a2b3c4d5e6f7
Create Date: 2025-01-15

Adds equity/commodity asset types and deterministic lock for equity bundles:
- securitization_pool_assets: equity_symbol, commodity_code
- securitization_pools: lock_period_days, lock_until
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2024sp_ec"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table: str, col: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns WHERE table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": col},
    )
    return r.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # securitization_pool_assets: equity_symbol, commodity_code
    if not _column_exists(conn, "securitization_pool_assets", "equity_symbol"):
        op.add_column(
            "securitization_pool_assets",
            sa.Column("equity_symbol", sa.String(length=50), nullable=True),
        )
    if not _column_exists(conn, "securitization_pool_assets", "commodity_code"):
        op.add_column(
            "securitization_pool_assets",
            sa.Column("commodity_code", sa.String(length=50), nullable=True),
        )

    # securitization_pools: lock_period_days, lock_until (deterministic lock for equity bundles)
    if not _column_exists(conn, "securitization_pools", "lock_period_days"):
        op.add_column(
            "securitization_pools",
            sa.Column("lock_period_days", sa.Integer(), nullable=True),
        )
    if not _column_exists(conn, "securitization_pools", "lock_until"):
        op.add_column(
            "securitization_pools",
            sa.Column("lock_until", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "securitization_pools", "lock_until"):
        op.drop_column("securitization_pools", "lock_until")
    if _column_exists(conn, "securitization_pools", "lock_period_days"):
        op.drop_column("securitization_pools", "lock_period_days")

    if _column_exists(conn, "securitization_pool_assets", "commodity_code"):
        op.drop_column("securitization_pool_assets", "commodity_code")
    if _column_exists(conn, "securitization_pool_assets", "equity_symbol"):
        op.drop_column("securitization_pool_assets", "equity_symbol")
