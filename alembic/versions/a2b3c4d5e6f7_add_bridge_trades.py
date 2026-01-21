"""Add bridge_trades table for ChallengeCoin NFT bridge builder.

Revision ID: a2b3c4d5e6f7
Revises: a1c2d3e4f5b6
Create Date: 2025-01-15

"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "a1c2d3e4f5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bridge_trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_id", sa.Integer(), nullable=False),
        sa.Column("source_chain_id", sa.Integer(), nullable=False),
        sa.Column("target_chain_id", sa.Integer(), nullable=False),
        sa.Column("target_address", sa.String(66), nullable=False),
        sa.Column("trade_type", sa.String(50), nullable=False, server_default="transfer"),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("lock_tx_hash", sa.String(66), nullable=True),
        sa.Column("bridge_external_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bridge_trades_user_id", "bridge_trades", ["user_id"])
    op.create_index("ix_bridge_trades_token_id", "bridge_trades", ["token_id"])
    op.create_index("ix_bridge_trades_source_chain_id", "bridge_trades", ["source_chain_id"])
    op.create_index("ix_bridge_trades_target_chain_id", "bridge_trades", ["target_chain_id"])
    op.create_index("ix_bridge_trades_target_address", "bridge_trades", ["target_address"])
    op.create_index("ix_bridge_trades_trade_type", "bridge_trades", ["trade_type"])
    op.create_index("ix_bridge_trades_status", "bridge_trades", ["status"])
    op.create_index("ix_bridge_trades_lock_tx_hash", "bridge_trades", ["lock_tx_hash"])
    op.create_index("ix_bridge_trades_bridge_external_id", "bridge_trades", ["bridge_external_id"])


def downgrade() -> None:
    op.drop_table("bridge_trades")
