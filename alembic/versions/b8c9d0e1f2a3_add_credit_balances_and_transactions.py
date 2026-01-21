"""Add credit_balances and credit_transactions (rolling credits).

Revision ID: b8c9d0e1f2a3
Revises: f6a7b8c9d0e1
Create Date: credit_balances, credit_transactions for rolling credits

"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def _json_default():
    return sa.text("'{}'::jsonb") if op.get_bind().dialect.name == "postgresql" else sa.text("'{}'")


def upgrade() -> None:
    op.create_table(
        "credit_balances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("balances", _json_type(), nullable=False, server_default=_json_default()),
        sa.Column("total_balance", sa.Numeric(19, 4), nullable=False, server_default=sa.text("0")),
        sa.Column("lifetime_earned", _json_type(), nullable=False, server_default=_json_default()),
        sa.Column("lifetime_spent", _json_type(), nullable=False, server_default=_json_default()),
        sa.Column("blockchain_registered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blockchain_token_id", sa.String(255), nullable=True),
        sa.Column("blockchain_tx_hash", sa.String(255), nullable=True),
        sa.Column("blockchain_chain_id", sa.Integer(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_balances_user_id", "credit_balances", ["user_id"])
    op.create_index("ix_credit_balances_organization_id", "credit_balances", ["organization_id"])
    op.create_index("ix_credit_balances_blockchain_token_id", "credit_balances", ["blockchain_token_id"], unique=True)
    op.create_index("ix_credit_balances_blockchain_tx_hash", "credit_balances", ["blockchain_tx_hash"])

    op.create_table(
        "credit_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("balance_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("transaction_type", sa.String(50), nullable=False),
        sa.Column("credit_type", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("balance_before", _json_type(), nullable=True),
        sa.Column("balance_after", _json_type(), nullable=True),
        sa.Column("feature", sa.String(100), nullable=True),
        sa.Column("related_transaction_id", sa.String(255), nullable=True),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("blockchain_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blockchain_tx_hash", sa.String(255), nullable=True),
        sa.Column("bridge_tx_hash", sa.String(255), nullable=True),
        sa.Column("base_cost", sa.Numeric(19, 4), nullable=True),
        sa.Column("adaptive_cost", sa.Numeric(19, 4), nullable=True),
        sa.Column("pricing_factors", _json_type(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("payment_event_id", sa.Integer(), nullable=True),
        sa.Column("metadata", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["balance_id"], ["credit_balances.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["subscription_id"], ["user_subscriptions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["payment_event_id"], ["payment_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_transactions_balance_id", "credit_transactions", ["balance_id"])
    op.create_index("ix_credit_transactions_user_id", "credit_transactions", ["user_id"])
    op.create_index("ix_credit_transactions_organization_id", "credit_transactions", ["organization_id"])
    op.create_index("ix_credit_transactions_transaction_type", "credit_transactions", ["transaction_type"])
    op.create_index("ix_credit_transactions_credit_type", "credit_transactions", ["credit_type"])
    op.create_index("ix_credit_transactions_feature", "credit_transactions", ["feature"])
    op.create_index("ix_credit_transactions_related_transaction_id", "credit_transactions", ["related_transaction_id"])
    op.create_index("ix_credit_transactions_subscription_id", "credit_transactions", ["subscription_id"])
    op.create_index("ix_credit_transactions_blockchain_tx_hash", "credit_transactions", ["blockchain_tx_hash"])
    op.create_index("ix_credit_transactions_bridge_tx_hash", "credit_transactions", ["bridge_tx_hash"])
    op.create_index("ix_credit_transactions_payment_event_id", "credit_transactions", ["payment_event_id"])
    op.create_index("ix_credit_transactions_created_at", "credit_transactions", ["created_at"])


def downgrade() -> None:
    op.drop_table("credit_transactions")
    op.drop_table("credit_balances")
