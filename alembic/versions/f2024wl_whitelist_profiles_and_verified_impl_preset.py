"""whitelist_profiles, VerifiedImplementation.whitelist_preset (wl_1)

Revision ID: f2024wl_wl1
Revises: e2024org_org
Create Date: 2026-01-21 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f2024wl_wl1"
down_revision: Union[str, Sequence[str], None] = "e2024org_org"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "whitelist_profiles" not in existing:
        op.create_table(
            "whitelist_profiles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("scope", sa.String(length=50), nullable=False),
            sa.Column("enabled_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("file_types", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("subdirectories", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("allowed_ips", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("allowed_cidrs", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("implementation_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("allowed_nodes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("preset_implementation_id", sa.Integer(), nullable=True),
            sa.Column("organization_id", sa.Integer(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_whitelist_profiles_name", "whitelist_profiles", ["name"])
        op.create_index("ix_whitelist_profiles_scope", "whitelist_profiles", ["scope"])
        op.create_index("ix_whitelist_profiles_is_active", "whitelist_profiles", ["is_active"])
        op.create_index("ix_whitelist_profiles_preset_implementation_id", "whitelist_profiles", ["preset_implementation_id"])
        op.create_index("ix_whitelist_profiles_organization_id", "whitelist_profiles", ["organization_id"])
        op.create_foreign_key(
            "fk_whitelist_profiles_preset_impl",
            "whitelist_profiles",
            "verified_implementations",
            ["preset_implementation_id"],
            ["id"],
            ondelete="SET NULL",
        )
        if "organizations" in existing:
            op.create_foreign_key(
                "fk_whitelist_profiles_organization_id",
                "whitelist_profiles",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="SET NULL",
            )

    if "verified_implementations" in existing:
        cols = [c["name"] for c in inspector.get_columns("verified_implementations")]
        if "whitelist_preset" not in cols:
            op.add_column(
                "verified_implementations",
                sa.Column("whitelist_preset", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            )


def downgrade() -> None:
    if "verified_implementations" in (sa.inspect(op.get_bind()).get_table_names() or []):
        try:
            op.drop_column("verified_implementations", "whitelist_preset")
        except Exception:
            pass
    if "whitelist_profiles" in (sa.inspect(op.get_bind()).get_table_names() or []):
        try:
            op.drop_constraint("fk_whitelist_profiles_organization_id", "whitelist_profiles", type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_constraint("fk_whitelist_profiles_preset_impl", "whitelist_profiles", type_="foreignkey")
        except Exception:
            pass
        op.drop_index("ix_whitelist_profiles_organization_id", table_name="whitelist_profiles")
        op.drop_index("ix_whitelist_profiles_preset_implementation_id", table_name="whitelist_profiles")
        op.drop_index("ix_whitelist_profiles_is_active", table_name="whitelist_profiles")
        op.drop_index("ix_whitelist_profiles_scope", table_name="whitelist_profiles")
        op.drop_index("ix_whitelist_profiles_name", table_name="whitelist_profiles")
        op.drop_table("whitelist_profiles")
