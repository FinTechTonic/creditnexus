"""add consent tables

Revision ID: c1a2b3d4e5f6
Revises: 3a7f8b9c1d2e, 9f0a1b2c3d4e
Create Date: 2026-01-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = ("3a7f8b9c1d2e", "9f0a1b2c3d4e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "consents" not in existing:
        op.create_table(
            "consents",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("consent_type", sa.String(length=50), nullable=False),
            sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "consent_type", name="uq_consents_user_type"),
        )
        op.create_index("ix_consents_user_id", "consents", ["user_id"])
        op.create_index("ix_consents_consent_type", "consents", ["consent_type"])

    if "consent_history" not in existing:
        op.create_table(
            "consent_history",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("consent_type", sa.String(length=50), nullable=False),
            sa.Column("granted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("change_reason", sa.Text(), nullable=True),
            sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_consent_history_user_id", "consent_history", ["user_id"])
        op.create_index("ix_consent_history_consent_type", "consent_history", ["consent_type"])
        op.create_index("ix_consent_history_recorded_at", "consent_history", ["recorded_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "consent_history" in existing:
        op.drop_index("ix_consent_history_recorded_at", table_name="consent_history")
        op.drop_index("ix_consent_history_consent_type", table_name="consent_history")
        op.drop_index("ix_consent_history_user_id", table_name="consent_history")
        op.drop_table("consent_history")

    if "consents" in existing:
        op.drop_index("ix_consents_consent_type", table_name="consents")
        op.drop_index("ix_consents_user_id", table_name="consents")
        op.drop_table("consents")
