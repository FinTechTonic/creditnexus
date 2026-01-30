"""add brokerage_ach_relationships table

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-01-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brokerage_ach_relationships",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("alpaca_account_id", sa.String(length=64), nullable=False),
        sa.Column("alpaca_relationship_id", sa.String(length=64), nullable=False),
        sa.Column("plaid_account_id", sa.String(length=64), nullable=True),
        sa.Column("nickname", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "alpaca_account_id",
            "alpaca_relationship_id",
            name="uq_brokerage_ach_user_account_relationship",
        ),
    )
    op.create_index(
        op.f("ix_brokerage_ach_relationships_user_id"),
        "brokerage_ach_relationships",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_brokerage_ach_relationships_alpaca_account_id"),
        "brokerage_ach_relationships",
        ["alpaca_account_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_brokerage_ach_relationships_user_id_alpaca_account_id"),
        "brokerage_ach_relationships",
        ["user_id", "alpaca_account_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_brokerage_ach_relationships_user_id_alpaca_account_id"),
        table_name="brokerage_ach_relationships",
    )
    op.drop_index(
        op.f("ix_brokerage_ach_relationships_alpaca_account_id"),
        table_name="brokerage_ach_relationships",
    )
    op.drop_index(
        op.f("ix_brokerage_ach_relationships_user_id"),
        table_name="brokerage_ach_relationships",
    )
    op.drop_table("brokerage_ach_relationships")
