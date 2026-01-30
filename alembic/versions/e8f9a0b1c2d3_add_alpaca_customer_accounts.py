"""add alpaca customer accounts and order alpaca_account_id

Revision ID: e8f9a0b1c2d3
Revises: c4d5e6f7a8b9
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "alpaca_customer_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("alpaca_account_id", sa.String(length=64), nullable=False),
        sa.Column("account_number", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="SUBMITTED"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("action_required_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alpaca_customer_accounts_user_id"), "alpaca_customer_accounts", ["user_id"], unique=True)
    op.create_index(op.f("ix_alpaca_customer_accounts_alpaca_account_id"), "alpaca_customer_accounts", ["alpaca_account_id"], unique=True)
    op.create_index(op.f("ix_alpaca_customer_accounts_account_number"), "alpaca_customer_accounts", ["account_number"], unique=False)
    op.create_index(op.f("ix_alpaca_customer_accounts_status"), "alpaca_customer_accounts", ["status"], unique=False)

    op.add_column("orders", sa.Column("alpaca_account_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_orders_alpaca_account_id"), "orders", ["alpaca_account_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_orders_alpaca_account_id"), table_name="orders")
    op.drop_column("orders", "alpaca_account_id")

    op.drop_index(op.f("ix_alpaca_customer_accounts_status"), table_name="alpaca_customer_accounts")
    op.drop_index(op.f("ix_alpaca_customer_accounts_account_number"), table_name="alpaca_customer_accounts")
    op.drop_index(op.f("ix_alpaca_customer_accounts_alpaca_account_id"), table_name="alpaca_customer_accounts")
    op.drop_index(op.f("ix_alpaca_customer_accounts_user_id"), table_name="alpaca_customer_accounts")
    op.drop_table("alpaca_customer_accounts")
