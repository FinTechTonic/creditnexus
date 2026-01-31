"""add lender_scores table (Week 16)

Revision ID: h4a5b6c7d8e0
Revises: g3a4b5c6d7e9
Create Date: 2026-01-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "h4a5b6c7d8e0"
down_revision: Union[str, Sequence[str], None] = "g3a4b5c6d7e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lender_scores",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("score_value", sa.Numeric(10, 4), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_lender_scores_user_id"),
    )
    op.create_index("ix_lender_scores_user_id", "lender_scores", ["user_id"], unique=True)
    op.create_index("ix_lender_scores_source", "lender_scores", ["source"], unique=False)
    op.create_index("ix_lender_scores_updated_at", "lender_scores", ["updated_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_lender_scores_updated_at", table_name="lender_scores")
    op.drop_index("ix_lender_scores_source", table_name="lender_scores")
    op.drop_index("ix_lender_scores_user_id", table_name="lender_scores")
    op.drop_table("lender_scores")
