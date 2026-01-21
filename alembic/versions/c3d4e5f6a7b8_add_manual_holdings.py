"""add_manual_holdings

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-01-21 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "manual_holdings" not in existing:
        op.create_table(
            "manual_holdings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("symbol", sa.String(length=50), nullable=False),
            sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False),
            sa.Column("average_cost", sa.Numeric(precision=20, scale=8), nullable=True),
            sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'USD'")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_manual_holdings_user_id"),
        )
        op.create_index("ix_manual_holdings_user_id", "manual_holdings", ["user_id"])
        op.create_index("ix_manual_holdings_symbol", "manual_holdings", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_manual_holdings_symbol", table_name="manual_holdings")
    op.drop_index("ix_manual_holdings_user_id", table_name="manual_holdings")
    op.drop_table("manual_holdings")
