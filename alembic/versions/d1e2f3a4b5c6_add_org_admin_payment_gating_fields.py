"""add org admin payment gating fields

Revision ID: d1e2f3a4b5c6
Revises: c4d5e6f7a8b9
Create Date: 2026-01-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("org_admin_payment_status", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("org_admin_payment_id", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("org_admin_paid_at", sa.DateTime(), nullable=True))

    op.create_index(op.f("ix_users_org_admin_payment_status"), "users", ["org_admin_payment_status"], unique=False)

    op.create_foreign_key(
        "fk_users_org_admin_payment_id_payment_events",
        "users",
        "payment_events",
        ["org_admin_payment_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_users_org_admin_payment_id_payment_events", "users", type_="foreignkey")
    op.drop_index(op.f("ix_users_org_admin_payment_status"), table_name="users")
    op.drop_column("users", "org_admin_paid_at")
    op.drop_column("users", "org_admin_payment_id")
    op.drop_column("users", "org_admin_payment_status")

