"""add_market_orders

Revision ID: b2c3d4e5f6a7
Revises: a7b8c9d0e1f2
Create Date: 2026-01-21 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create market_orders table for internal SFP marketplace order book."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "market_orders" not in existing:
        op.create_table(
            "market_orders",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("market_event_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("side", sa.String(length=10), nullable=False),
            sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("size", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'open'")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("filled_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["market_event_id"], ["market_events.id"], name="fk_market_orders_market_event_id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_market_orders_user_id"),
        )
        op.create_index("ix_market_orders_market_event_id", "market_orders", ["market_event_id"])
        op.create_index("ix_market_orders_user_id", "market_orders", ["user_id"])
        op.create_index("ix_market_orders_status", "market_orders", ["status"])


def downgrade() -> None:
    """Drop market_orders table."""
    op.drop_index("ix_market_orders_status", table_name="market_orders")
    op.drop_index("ix_market_orders_user_id", table_name="market_orders")
    op.drop_index("ix_market_orders_market_event_id", table_name="market_orders")
    op.drop_table("market_orders")
