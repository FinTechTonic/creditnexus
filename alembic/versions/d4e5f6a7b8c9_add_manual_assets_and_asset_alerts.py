"""add_manual_assets_and_asset_alerts (Phase 3: Amortization & Alerts)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-01-21 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "manual_assets" not in existing:
        op.create_table(
            "manual_assets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("asset_type", sa.String(length=50), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("purchase_price", sa.Numeric(precision=19, scale=4), nullable=False),
            sa.Column("current_value", sa.Numeric(precision=19, scale=4), nullable=True),
            sa.Column("quantity", sa.Numeric(precision=19, scale=4), nullable=True),
            sa.Column("unit", sa.String(length=20), nullable=True),
            sa.Column("maturity_date", sa.Date(), nullable=True),
            sa.Column("interest_rate", sa.Numeric(precision=10, scale=4), nullable=True),
            sa.Column("payment_frequency", sa.String(length=20), nullable=True),
            sa.Column("amortization_schedule", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("purchase_date", sa.Date(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_manual_assets_user_id"),
        )
        op.create_index("ix_manual_assets_user_id", "manual_assets", ["user_id"])
        op.create_index("ix_manual_assets_asset_type", "manual_assets", ["asset_type"])
        op.create_index("ix_manual_assets_maturity_date", "manual_assets", ["maturity_date"])

    if "asset_alerts" not in existing:
        op.create_table(
            "asset_alerts",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("asset_id", sa.Integer(), nullable=False),
            sa.Column("alert_type", sa.String(length=50), nullable=False),
            sa.Column("trigger_date", sa.Date(), nullable=True),
            sa.Column("trigger_price", sa.Numeric(precision=19, scale=4), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("notified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("notified_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["asset_id"], ["manual_assets.id"], ondelete="CASCADE", name="fk_asset_alerts_asset_id"),
        )
        op.create_index("ix_asset_alerts_asset_id", "asset_alerts", ["asset_id"])
        op.create_index("ix_asset_alerts_alert_type", "asset_alerts", ["alert_type"])
        op.create_index("ix_asset_alerts_trigger_date", "asset_alerts", ["trigger_date"])


def downgrade() -> None:
    op.drop_index("ix_asset_alerts_trigger_date", table_name="asset_alerts")
    op.drop_index("ix_asset_alerts_alert_type", table_name="asset_alerts")
    op.drop_index("ix_asset_alerts_asset_id", table_name="asset_alerts")
    op.drop_table("asset_alerts")
    op.drop_index("ix_manual_assets_maturity_date", table_name="manual_assets")
    op.drop_index("ix_manual_assets_asset_type", table_name="manual_assets")
    op.drop_index("ix_manual_assets_user_id", table_name="manual_assets")
    op.drop_table("manual_assets")
