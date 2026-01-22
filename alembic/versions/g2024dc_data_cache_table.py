"""data_cache table for market data, tool results, and external API caching (timeseries + punctual).

Revision ID: g2024dc_dc1
Revises: f2024wl_wl1
Create Date: 2026-01-21 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "g2024dc_dc1"
down_revision: Union[str, Sequence[str], None] = "f2024wl_wl1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.create_table(
        "data_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_key", sa.String(512), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("result", _json_type(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_data_cache_cache_key", "data_cache", ["cache_key"], unique=True)
    op.create_index("ix_data_cache_source", "data_cache", ["source"])
    op.create_index("ix_data_cache_kind", "data_cache", ["kind"])
    op.create_index("ix_data_cache_expires_at", "data_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_table("data_cache")
