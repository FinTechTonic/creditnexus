"""add_internal_signature_fields

Revision ID: cafedeadbeef
Revises: ff16ad99f573
Create Date: 2026-01-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "cafedeadbeef"
down_revision: Union[str, Sequence[str], None] = "ff16ad99f573"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add internal/native signature fields to document_signatures."""
    op.add_column(
        "document_signatures",
        sa.Column("access_token", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "document_signatures",
        sa.Column("coordinates", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "document_signatures",
        sa.Column("audit_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "document_signatures",
        sa.Column("metamask_signature", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "document_signatures",
        sa.Column("metamask_signed_at", sa.DateTime(), nullable=True),
    )

    op.create_index(
        "ix_document_signatures_access_token",
        "document_signatures",
        ["access_token"],
        unique=False,
    )


def downgrade() -> None:
    """Remove internal/native signature fields from document_signatures."""
    op.drop_index(
        "ix_document_signatures_access_token",
        table_name="document_signatures",
    )
    op.drop_column("document_signatures", "metamask_signed_at")
    op.drop_column("document_signatures", "metamask_signature")
    op.drop_column("document_signatures", "audit_data")
    op.drop_column("document_signatures", "coordinates")
    op.drop_column("document_signatures", "access_token")

