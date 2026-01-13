"""Add remote verification and notarization tables and deal columns

Revision ID: add_remote_verification
Revises:
Create Date: 2024-01-11

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

# revision identifiers, used by Alembic.
revision: str = "add_remote_verification"
down_revision = "cb70003e8b8c"
branch_labels = None
depends_on = None


def upgrade():
    # Create remote_app_profiles table
    op.create_table(
        "remote_app_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("profile_name", sa.String(length=100), nullable=False),
        sa.Column("api_key_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "allowed_ips",
            postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "permissions",
            postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_name"),
    )
    op.create_index("ix_remote_app_profiles_profile_name", "remote_app_profiles", ["profile_name"])
    op.create_index("ix_remote_app_profiles_is_active", "remote_app_profiles", ["is_active"])

    # Create verification_requests table
    op.create_table(
        "verification_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("verification_id", sa.String(length=255), nullable=False),
        sa.Column("deal_id", sa.Integer(), nullable=True),
        sa.Column("verifier_user_id", sa.Integer(), nullable=True),
        sa.Column("verification_link_token", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("declined_at", sa.DateTime(), nullable=True),
        sa.Column("declined_reason", sa.Text(), nullable=True),
        sa.Column(
            "verification_metadata",
            postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verification_id"),
        sa.UniqueConstraint("verification_link_token"),
        sa.ForeignKeyConstraint(
            ["deal_id"], ["deals.id"], name="fk_verification_requests_deal_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["verifier_user_id"],
            ["users.id"],
            name="fk_verification_requests_verifier_user_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"], name="fk_verification_requests_created_by"
        ),
    )
    op.create_index(
        "ix_verification_requests_verification_id", "verification_requests", ["verification_id"]
    )
    op.create_index("ix_verification_requests_deal_id", "verification_requests", ["deal_id"])
    op.create_index(
        "ix_verification_requests_verifier_user_id", "verification_requests", ["verifier_user_id"]
    )
    op.create_index("ix_verification_requests_status", "verification_requests", ["status"])
    op.create_index(
        "ix_verification_requests_verification_link_token",
        "verification_requests",
        ["verification_link_token"],
    )
    op.create_index("ix_verification_requests_expires_at", "verification_requests", ["expires_at"])

    # Create notarization_records table
    op.create_table(
        "notarization_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("deal_id", sa.Integer(), nullable=False),
        sa.Column("notarization_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "required_signers",
            postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "signatures",
            postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("cdm_event_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["deal_id"], ["deals.id"], name="fk_notarization_records_deal_id", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_notarization_records_deal_id", "notarization_records", ["deal_id"])
    op.create_index("ix_notarization_records_status", "notarization_records", ["status"])

    # Create verification_audit_log table
    op.create_table(
        "verification_audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("verification_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("actor_ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB() if op.get_bind().dialect.name == "postgresql" else sa.JSON(),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["verification_id"],
            ["verification_requests.id"],
            name="fk_verification_audit_log_verification_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["users.id"], name="fk_verification_audit_log_actor_user_id"
        ),
    )
    op.create_index(
        "ix_verification_audit_log_verification_id", "verification_audit_log", ["verification_id"]
    )
    op.create_index(
        "ix_verification_audit_log_created_at", "verification_audit_log", ["created_at"]
    )

    # Add new columns to deals table
    with op.batch_alter_table("deals") as batch_op:
        batch_op.add_column(
            sa.Column(
                "verification_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.add_column(sa.Column("verification_completed_at", sa.DateTime(), nullable=True))
        batch_op.add_column(
            sa.Column(
                "notarization_required",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )
        batch_op.add_column(sa.Column("notarization_completed_at", sa.DateTime(), nullable=True))


def downgrade():
    # Remove new columns from deals table
    with op.batch_alter_table("deals") as batch_op:
        batch_op.drop_column("notarization_completed_at")
        batch_op.drop_column("notarization_required")
        batch_op.drop_column("verification_completed_at")
        batch_op.drop_column("verification_required")

    # Drop tables
    op.drop_index("ix_verification_audit_log_created_at", "verification_audit_log")
    op.drop_index("ix_verification_audit_log_verification_id", "verification_audit_log")
    op.drop_table("verification_audit_log")

    op.drop_index("ix_notarization_records_status", "notarization_records")
    op.drop_index("ix_notarization_records_deal_id", "notarization_records")
    op.drop_table("notarization_records")

    op.drop_index("ix_verification_requests_expires_at", "verification_requests")
    op.drop_index("ix_verification_requests_verification_link_token", "verification_requests")
    op.drop_index("ix_verification_requests_status", "verification_requests")
    op.drop_index("ix_verification_requests_verifier_user_id", "verification_requests")
    op.drop_index("ix_verification_requests_deal_id", "verification_requests")
    op.drop_index("ix_verification_requests_verification_id", "verification_requests")
    op.drop_table("verification_requests")

    op.drop_index("ix_remote_app_profiles_is_active", "remote_app_profiles")
    op.drop_index("ix_remote_app_profiles_profile_name", "remote_app_profiles")
    op.drop_table("remote_app_profiles")
