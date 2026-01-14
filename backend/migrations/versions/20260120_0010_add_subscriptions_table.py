"""add subscriptions table

Revision ID: 20260120_0010
Revises: 20260120_0009
Create Date: 2026-01-20 18:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import app.db.base

# revision identifiers, used by Alembic.
revision = "20260120_0010"
down_revision = "20260120_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create subscriptions table
    op.create_table(
        "subscriptions",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("plan", sa.String(length=50), nullable=False, server_default="free"),
        sa.Column("billing_cycle", sa.String(length=50), nullable=False, server_default="monthly"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_subscriptions_workspace", "subscriptions", ["workspace_id"], unique=False)
    op.create_index("ix_subscriptions_stripe_customer", "subscriptions", ["stripe_customer_id"], unique=False)
    op.create_index("ix_subscriptions_stripe_subscription", "subscriptions", ["stripe_subscription_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subscriptions_stripe_subscription", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_customer", table_name="subscriptions")
    op.drop_index("ix_subscriptions_workspace", table_name="subscriptions")
    op.drop_table("subscriptions")
