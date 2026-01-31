"""add_billing_tables (Phase 10)

Revision ID: p10billing001
Revises: p8org001
Create Date: 2026-01-30

Adds invoices, billing_periods, cost_allocations for Phase 10 Billing Dashboard.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "p10billing001"
down_revision: Union[str, None] = "p8org001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("invoice_date", sa.DateTime(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("subtotal", sa.Numeric(19, 4), nullable=False),
        sa.Column("tax", sa.Numeric(19, 4), nullable=False),
        sa.Column("total", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("payment_event_id", sa.Integer(), nullable=True),
        sa.Column("line_items", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["payment_event_id"], ["payment_events.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invoices_invoice_number"), "invoices", ["invoice_number"], unique=True)
    op.create_index(op.f("ix_invoices_invoice_date"), "invoices", ["invoice_date"], unique=False)
    op.create_index(op.f("ix_invoices_due_date"), "invoices", ["due_date"], unique=False)
    op.create_index(op.f("ix_invoices_organization_id"), "invoices", ["organization_id"], unique=False)
    op.create_index(op.f("ix_invoices_user_id"), "invoices", ["user_id"], unique=False)
    op.create_index(op.f("ix_invoices_status"), "invoices", ["status"], unique=False)

    op.create_table(
        "billing_periods",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("period_start", sa.DateTime(), nullable=False),
        sa.Column("period_end", sa.DateTime(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("total_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("subscription_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("usage_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("commission_revenue", sa.Numeric(19, 4), nullable=False),
        sa.Column("credit_purchases", sa.Numeric(19, 4), nullable=False),
        sa.Column("credit_usage", sa.Numeric(19, 4), nullable=False),
        sa.Column("payment_cost", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_billing_periods_period_start"), "billing_periods", ["period_start"], unique=False)
    op.create_index(op.f("ix_billing_periods_period_end"), "billing_periods", ["period_end"], unique=False)
    op.create_index(op.f("ix_billing_periods_organization_id"), "billing_periods", ["organization_id"], unique=False)
    op.create_index(op.f("ix_billing_periods_user_id"), "billing_periods", ["user_id"], unique=False)
    op.create_index(op.f("ix_billing_periods_status"), "billing_periods", ["status"], unique=False)
    op.create_index(op.f("ix_billing_periods_invoice_id"), "billing_periods", ["invoice_id"], unique=False)

    op.create_table(
        "cost_allocations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("billing_period_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_role", sa.String(50), nullable=True),
        sa.Column("cost_type", sa.String(50), nullable=False),
        sa.Column("feature", sa.String(100), nullable=True),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("allocation_method", sa.String(50), nullable=False),
        sa.Column("allocation_percentage", sa.Numeric(5, 2), nullable=True),
        sa.Column("source_transaction_id", sa.String(255), nullable=True),
        sa.Column("source_transaction_type", sa.String(50), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["billing_period_id"], ["billing_periods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_allocations_billing_period_id"), "cost_allocations", ["billing_period_id"], unique=False)
    op.create_index(op.f("ix_cost_allocations_organization_id"), "cost_allocations", ["organization_id"], unique=False)
    op.create_index(op.f("ix_cost_allocations_user_id"), "cost_allocations", ["user_id"], unique=False)
    op.create_index(op.f("ix_cost_allocations_user_role"), "cost_allocations", ["user_role"], unique=False)
    op.create_index(op.f("ix_cost_allocations_cost_type"), "cost_allocations", ["cost_type"], unique=False)
    op.create_index(op.f("ix_cost_allocations_feature"), "cost_allocations", ["feature"], unique=False)
    op.create_index(op.f("ix_cost_allocations_source_transaction_id"), "cost_allocations", ["source_transaction_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cost_allocations_source_transaction_id"), table_name="cost_allocations")
    op.drop_index(op.f("ix_cost_allocations_feature"), table_name="cost_allocations")
    op.drop_index(op.f("ix_cost_allocations_cost_type"), table_name="cost_allocations")
    op.drop_index(op.f("ix_cost_allocations_user_role"), table_name="cost_allocations")
    op.drop_index(op.f("ix_cost_allocations_user_id"), table_name="cost_allocations")
    op.drop_index(op.f("ix_cost_allocations_organization_id"), table_name="cost_allocations")
    op.drop_index(op.f("ix_cost_allocations_billing_period_id"), table_name="cost_allocations")
    op.drop_table("cost_allocations")
    op.drop_index(op.f("ix_billing_periods_invoice_id"), table_name="billing_periods")
    op.drop_index(op.f("ix_billing_periods_status"), table_name="billing_periods")
    op.drop_index(op.f("ix_billing_periods_user_id"), table_name="billing_periods")
    op.drop_index(op.f("ix_billing_periods_organization_id"), table_name="billing_periods")
    op.drop_index(op.f("ix_billing_periods_period_end"), table_name="billing_periods")
    op.drop_index(op.f("ix_billing_periods_period_start"), table_name="billing_periods")
    op.drop_table("billing_periods")
    op.drop_index(op.f("ix_invoices_status"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_user_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_organization_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_due_date"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_invoice_date"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_invoice_number"), table_name="invoices")
    op.drop_table("invoices")
