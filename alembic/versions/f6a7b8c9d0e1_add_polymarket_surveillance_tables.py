"""Add Polymarket surveillance tables (baselines, alerts).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: add polymarket_surveillance_baselines and polymarket_surveillance_alerts

"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def upgrade() -> None:
    op.create_table(
        "polymarket_surveillance_baselines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("window", sa.String(50), nullable=False),
        sa.Column("metric", sa.String(100), nullable=False),
        sa.Column("value", _json_type(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("entity_type", "entity_id", "window", "metric", name="uq_polymarket_surveillance_baseline"),
    )
    op.create_index("ix_polymarket_surveillance_baselines_entity_type", "polymarket_surveillance_baselines", ["entity_type"])
    op.create_index("ix_polymarket_surveillance_baselines_entity_id", "polymarket_surveillance_baselines", ["entity_id"])
    op.create_index("ix_polymarket_surveillance_baselines_metric", "polymarket_surveillance_baselines", ["metric"])

    op.create_table(
        "polymarket_surveillance_alerts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_type", sa.String(100), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("condition_id", sa.String(255), nullable=True),
        sa.Column("proxy_wallet", sa.String(66), nullable=True),
        sa.Column("event_id", sa.String(255), nullable=True),
        sa.Column("signal_values", _json_type(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), nullable=True),
        sa.Column("resolution", sa.String(50), nullable=True),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_polymarket_surveillance_alerts_alert_type", "polymarket_surveillance_alerts", ["alert_type"])
    op.create_index("ix_polymarket_surveillance_alerts_condition_id", "polymarket_surveillance_alerts", ["condition_id"])
    op.create_index("ix_polymarket_surveillance_alerts_proxy_wallet", "polymarket_surveillance_alerts", ["proxy_wallet"])
    op.create_index("ix_polymarket_surveillance_alerts_created_at", "polymarket_surveillance_alerts", ["created_at"])


def downgrade() -> None:
    op.drop_table("polymarket_surveillance_alerts")
    op.drop_table("polymarket_surveillance_baselines")
