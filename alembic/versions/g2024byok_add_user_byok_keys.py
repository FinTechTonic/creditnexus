"""add user_byok_keys table (BYOK – Bring Your Own Keys, crypto/trading only)

Revision ID: g2024byok
Revises: f1a2b3c4d5e6
Create Date: 2026-01-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "g2024byok"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_byok_keys",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_type", sa.String(length=64), nullable=True),
        sa.Column("credentials_encrypted", JSONB(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unlocks_trading", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_user_byok_provider"),
    )
    op.create_index(op.f("ix_user_byok_keys_user_id"), "user_byok_keys", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_byok_keys_provider"), "user_byok_keys", ["provider"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_byok_keys_provider"), table_name="user_byok_keys")
    op.drop_index(op.f("ix_user_byok_keys_user_id"), table_name="user_byok_keys")
    op.drop_table("user_byok_keys")
