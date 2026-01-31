"""add bank_product_listings table (Week 14)

Revision ID: g3a4b5c6d7e9
Revises: f3a4b5c6d7e8
Create Date: 2026-01-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "g3a4b5c6d7e9"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bank_product_listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plaid_account_id", sa.String(length=64), nullable=True),
        sa.Column("plaid_security_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("product_type", sa.String(length=50), nullable=True),
        sa.Column("asking_price", sa.Numeric(20, 2), nullable=False),
        sa.Column("flat_fee", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bank_product_listings_user_id", "bank_product_listings", ["user_id"], unique=False)
    op.create_index("ix_bank_product_listings_status", "bank_product_listings", ["status"], unique=False)
    op.create_index("ix_bank_product_listings_created_at", "bank_product_listings", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bank_product_listings_created_at", table_name="bank_product_listings")
    op.drop_index("ix_bank_product_listings_status", table_name="bank_product_listings")
    op.drop_index("ix_bank_product_listings_user_id", table_name="bank_product_listings")
    op.drop_table("bank_product_listings")
