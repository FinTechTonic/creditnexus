"""add_organization_social_feed_whitelist (UX whitelist for social feeds)

Revision ID: uxwhitelist001
Revises: p10billing001
Create Date: 2026-01-30

Adds organization_social_feed_whitelist table so org owners can whitelist
other organisations for social feeds; NewsfeedService.get_newsfeed includes
posts from whitelisted orgs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "uxwhitelist001"
down_revision: Union[str, None] = "p10billing001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organization_social_feed_whitelist",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("whitelisted_organization_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["whitelisted_organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "whitelisted_organization_id",
            name="uq_org_social_feed_whitelist",
        ),
    )
    op.create_index(
        "ix_organization_social_feed_whitelist_organization_id",
        "organization_social_feed_whitelist",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        "ix_organization_social_feed_whitelist_whitelisted_organization_id",
        "organization_social_feed_whitelist",
        ["whitelisted_organization_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_organization_social_feed_whitelist_whitelisted_organization_id",
        table_name="organization_social_feed_whitelist",
    )
    op.drop_index(
        "ix_organization_social_feed_whitelist_organization_id",
        table_name="organization_social_feed_whitelist",
    )
    op.drop_table("organization_social_feed_whitelist")
