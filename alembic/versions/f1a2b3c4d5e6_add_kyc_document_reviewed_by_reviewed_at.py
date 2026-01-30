"""add kyc_document reviewed_by and reviewed_at

Revision ID: f1a2b3c4d5e6
Revises: e8f9a0b1c2d3
Create Date: 2026-01-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("kyc_documents", sa.Column("reviewed_by", sa.Integer(), nullable=True))
    op.add_column("kyc_documents", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_kyc_documents_reviewed_by"), "kyc_documents", ["reviewed_by"], unique=False)
    op.create_foreign_key(
        "fk_kyc_documents_reviewed_by_users",
        "kyc_documents",
        "users",
        ["reviewed_by"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_kyc_documents_reviewed_by_users", "kyc_documents", type_="foreignkey")
    op.drop_index(op.f("ix_kyc_documents_reviewed_by"), table_name="kyc_documents")
    op.drop_column("kyc_documents", "reviewed_at")
    op.drop_column("kyc_documents", "reviewed_by")
