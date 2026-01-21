"""Add cross_chain_transactions table for Polymarket cross-chain bridge.

Revision ID: a1c2d3e4f5b6
Revises: c9d0e1f2a3b4
Create Date: cross_chain_transactions

"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1c2d3e4f5b6"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.create_table(
        "cross_chain_transactions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_chain_id", sa.Integer(), nullable=False),
        sa.Column("dest_chain_id", sa.Integer(), nullable=False),
        sa.Column("bridge_external_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("amount", sa.Numeric(36, 18), nullable=True),
        sa.Column("token_address", sa.String(66), nullable=True),
        sa.Column("market_event_id", sa.Integer(), nullable=True),
        sa.Column("outcome_token_id", sa.String(255), nullable=True),
        sa.Column("dest_tx_hash", sa.String(66), nullable=True),
        sa.Column("extra_data", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["market_event_id"], ["market_events.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cross_chain_transactions_user_id", "cross_chain_transactions", ["user_id"])
    op.create_index("ix_cross_chain_transactions_source_chain_id", "cross_chain_transactions", ["source_chain_id"])
    op.create_index("ix_cross_chain_transactions_dest_chain_id", "cross_chain_transactions", ["dest_chain_id"])
    op.create_index("ix_cross_chain_transactions_bridge_external_id", "cross_chain_transactions", ["bridge_external_id"])
    op.create_index("ix_cross_chain_transactions_status", "cross_chain_transactions", ["status"])
    op.create_index("ix_cross_chain_transactions_market_event_id", "cross_chain_transactions", ["market_event_id"])
    op.create_index("ix_cross_chain_transactions_outcome_token_id", "cross_chain_transactions", ["outcome_token_id"])
    op.create_index("ix_cross_chain_transactions_dest_tx_hash", "cross_chain_transactions", ["dest_tx_hash"])


def downgrade() -> None:
    op.drop_table("cross_chain_transactions")
