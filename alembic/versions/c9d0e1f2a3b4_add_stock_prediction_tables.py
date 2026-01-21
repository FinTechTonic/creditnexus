"""Add stock prediction tables: stock_predictions, stock_prediction_cache, prediction_order_recommendations, training_jobs.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: stock prediction and training models

"""
from typing import Union, Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return postgresql.JSONB(astext_type=sa.Text()) if op.get_bind().dialect.name == "postgresql" else sa.JSON()


def _json_default():
    return sa.text("'{}'::jsonb") if op.get_bind().dialect.name == "postgresql" else sa.text("'{}'")


def upgrade() -> None:
    op.create_table(
        "stock_predictions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("timeframe", sa.String(20), nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("strategy", sa.String(50), nullable=False),
        sa.Column("forecast", _json_type(), nullable=True),
        sa.Column("lookback_days", sa.Integer(), nullable=False),
        sa.Column("horizon", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", _json_type(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_predictions_user_id", "stock_predictions", ["user_id"])
    op.create_index("ix_stock_predictions_symbol", "stock_predictions", ["symbol"])
    op.create_index("ix_stock_predictions_timeframe", "stock_predictions", ["timeframe"])
    op.create_index("ix_stock_predictions_strategy", "stock_predictions", ["strategy"])
    op.create_index("ix_stock_predictions_created_at", "stock_predictions", ["created_at"])

    op.create_table(
        "stock_prediction_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cache_key", sa.String(512), nullable=False),
        sa.Column("result", _json_type(), nullable=False, server_default=_json_default()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stock_prediction_cache_cache_key", "stock_prediction_cache", ["cache_key"], unique=True)
    op.create_index("ix_stock_prediction_cache_expires_at", "stock_prediction_cache", ["expires_at"])

    op.create_table(
        "prediction_order_recommendations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("prediction_id", sa.Integer(), nullable=True),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("size", sa.Numeric(19, 4), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("strategy", sa.String(50), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("extra", _json_type(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["prediction_id"], ["stock_predictions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prediction_order_recommendations_user_id", "prediction_order_recommendations", ["user_id"])
    op.create_index("ix_prediction_order_recommendations_prediction_id", "prediction_order_recommendations", ["prediction_id"])
    op.create_index("ix_prediction_order_recommendations_symbol", "prediction_order_recommendations", ["symbol"])
    op.create_index("ix_prediction_order_recommendations_action", "prediction_order_recommendations", ["action"])
    op.create_index("ix_prediction_order_recommendations_strategy", "prediction_order_recommendations", ["strategy"])
    op.create_index("ix_prediction_order_recommendations_created_at", "prediction_order_recommendations", ["created_at"])

    op.create_table(
        "training_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("config", _json_type(), nullable=False, server_default=_json_default()),
        sa.Column("metrics", _json_type(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_training_jobs_model_id", "training_jobs", ["model_id"])
    op.create_index("ix_training_jobs_status", "training_jobs", ["status"])
    op.create_index("ix_training_jobs_created_at", "training_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_table("training_jobs")
    op.drop_table("prediction_order_recommendations")
    op.drop_table("stock_prediction_cache")
    op.drop_table("stock_predictions")
