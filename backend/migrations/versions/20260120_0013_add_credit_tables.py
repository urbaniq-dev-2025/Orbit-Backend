"""add credit tables

Revision ID: 20260120_0013
Revises: 20260120_0012
Create Date: 2026-01-20 22:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import app.db.base

# revision identifiers, used by Alembic.
revision = "20260120_0013"
down_revision = "20260120_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create credit_packages table
    op.create_table(
        "credit_packages",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_packages_name", "credit_packages", ["name"], unique=True)
    
    # Create credit_purchases table
    op.create_table(
        "credit_purchases",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=False),
        sa.Column("package_id", app.db.base.GUID(), nullable=False),
        sa.Column("credits", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("transaction_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="completed"),
        sa.Column("purchase_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["package_id"], ["credit_packages.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_credit_purchases_workspace", "credit_purchases", ["workspace_id"], unique=False)
    op.create_index("ix_credit_purchases_package", "credit_purchases", ["package_id"], unique=False)
    op.create_index("ix_credit_purchases_status", "credit_purchases", ["status"], unique=False)
    op.create_index("ix_credit_purchases_date", "credit_purchases", ["purchase_date"], unique=False)
    
    # Create workspace_credit_balances table
    op.create_table(
        "workspace_credit_balances",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=False),
        sa.Column("balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_purchased", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_consumed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id"),
    )
    op.create_index("ix_workspace_credit_balances_workspace", "workspace_credit_balances", ["workspace_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_workspace_credit_balances_workspace", table_name="workspace_credit_balances")
    op.drop_table("workspace_credit_balances")
    op.drop_index("ix_credit_purchases_date", table_name="credit_purchases")
    op.drop_index("ix_credit_purchases_status", table_name="credit_purchases")
    op.drop_index("ix_credit_purchases_package", table_name="credit_purchases")
    op.drop_index("ix_credit_purchases_workspace", table_name="credit_purchases")
    op.drop_table("credit_purchases")
    op.drop_index("ix_credit_packages_name", table_name="credit_packages")
    op.drop_table("credit_packages")
