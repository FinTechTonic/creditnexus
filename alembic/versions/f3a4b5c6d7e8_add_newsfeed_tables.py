"""add newsfeed_posts, newsfeed_likes, newsfeed_comments, newsfeed_shares tables

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-01-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "newsfeed_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("deal_id", sa.Integer(), nullable=True),
        sa.Column("market_id", sa.Integer(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column("polymarket_market_id", sa.String(length=255), nullable=True),
        sa.Column("polymarket_market_url", sa.String(length=500), nullable=True),
        sa.Column("likes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comments_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("shares_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("views_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="public"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["deal_id"], ["deals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["market_id"], ["market_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_newsfeed_posts_post_type", "newsfeed_posts", ["post_type"], unique=False)
    op.create_index("ix_newsfeed_posts_deal_id", "newsfeed_posts", ["deal_id"], unique=False)
    op.create_index("ix_newsfeed_posts_market_id", "newsfeed_posts", ["market_id"], unique=False)
    op.create_index("ix_newsfeed_posts_organization_id", "newsfeed_posts", ["organization_id"], unique=False)
    op.create_index("ix_newsfeed_posts_author_id", "newsfeed_posts", ["author_id"], unique=False)
    op.create_index("ix_newsfeed_posts_polymarket_market_id", "newsfeed_posts", ["polymarket_market_id"], unique=False)
    op.create_index("ix_newsfeed_posts_created_at", "newsfeed_posts", ["created_at"], unique=False)

    op.create_table(
        "newsfeed_likes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["newsfeed_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("post_id", "user_id", name="uq_newsfeed_like_post_user"),
    )
    op.create_index("ix_newsfeed_likes_post_id", "newsfeed_likes", ["post_id"], unique=False)
    op.create_index("ix_newsfeed_likes_user_id", "newsfeed_likes", ["user_id"], unique=False)

    op.create_table(
        "newsfeed_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("parent_comment_id", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["newsfeed_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_comment_id"], ["newsfeed_comments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_newsfeed_comments_post_id", "newsfeed_comments", ["post_id"], unique=False)
    op.create_index("ix_newsfeed_comments_user_id", "newsfeed_comments", ["user_id"], unique=False)
    op.create_index("ix_newsfeed_comments_parent_comment_id", "newsfeed_comments", ["parent_comment_id"], unique=False)

    op.create_table(
        "newsfeed_shares",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("share_type", sa.String(length=20), nullable=False, server_default="internal"),
        sa.Column("shared_to", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["newsfeed_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_newsfeed_shares_post_id", "newsfeed_shares", ["post_id"], unique=False)
    op.create_index("ix_newsfeed_shares_user_id", "newsfeed_shares", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_newsfeed_shares_user_id", table_name="newsfeed_shares")
    op.drop_index("ix_newsfeed_shares_post_id", table_name="newsfeed_shares")
    op.drop_table("newsfeed_shares")

    op.drop_index("ix_newsfeed_comments_parent_comment_id", table_name="newsfeed_comments")
    op.drop_index("ix_newsfeed_comments_user_id", table_name="newsfeed_comments")
    op.drop_index("ix_newsfeed_comments_post_id", table_name="newsfeed_comments")
    op.drop_table("newsfeed_comments")

    op.drop_index("ix_newsfeed_likes_user_id", table_name="newsfeed_likes")
    op.drop_index("ix_newsfeed_likes_post_id", table_name="newsfeed_likes")
    op.drop_table("newsfeed_likes")

    op.drop_index("ix_newsfeed_posts_created_at", table_name="newsfeed_posts")
    op.drop_index("ix_newsfeed_posts_polymarket_market_id", table_name="newsfeed_posts")
    op.drop_index("ix_newsfeed_posts_author_id", table_name="newsfeed_posts")
    op.drop_index("ix_newsfeed_posts_organization_id", table_name="newsfeed_posts")
    op.drop_index("ix_newsfeed_posts_market_id", table_name="newsfeed_posts")
    op.drop_index("ix_newsfeed_posts_deal_id", table_name="newsfeed_posts")
    op.drop_index("ix_newsfeed_posts_post_type", table_name="newsfeed_posts")
    op.drop_table("newsfeed_posts")
