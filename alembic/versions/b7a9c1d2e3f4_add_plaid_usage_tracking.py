"""add plaid usage tracking

Revision ID: b7a9c1d2e3f4
Revises: 909aa752bb02
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7a9c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "909aa752bb02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "plaid_usage_tracking",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("api_endpoint", sa.String(length=100), nullable=False),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=4), server_default="0", nullable=False),
        sa.Column("item_id", sa.String(length=255), nullable=True),
        sa.Column("account_id", sa.String(length=255), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("usage_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plaid_usage_tracking_user_id"), "plaid_usage_tracking", ["user_id"], unique=False)
    op.create_index(op.f("ix_plaid_usage_tracking_organization_id"), "plaid_usage_tracking", ["organization_id"], unique=False)
    op.create_index(op.f("ix_plaid_usage_tracking_api_endpoint"), "plaid_usage_tracking", ["api_endpoint"], unique=False)
    op.create_index(op.f("ix_plaid_usage_tracking_request_id"), "plaid_usage_tracking", ["request_id"], unique=False)
    op.create_index(op.f("ix_plaid_usage_tracking_timestamp"), "plaid_usage_tracking", ["timestamp"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_plaid_usage_tracking_timestamp"), table_name="plaid_usage_tracking")
    op.drop_index(op.f("ix_plaid_usage_tracking_request_id"), table_name="plaid_usage_tracking")
    op.drop_index(op.f("ix_plaid_usage_tracking_api_endpoint"), table_name="plaid_usage_tracking")
    op.drop_index(op.f("ix_plaid_usage_tracking_organization_id"), table_name="plaid_usage_tracking")
    op.drop_index(op.f("ix_plaid_usage_tracking_user_id"), table_name="plaid_usage_tracking")
    op.drop_table("plaid_usage_tracking")

