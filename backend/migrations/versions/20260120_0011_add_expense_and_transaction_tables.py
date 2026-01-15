"""add expense and transaction tables

Revision ID: 20260120_0011
Revises: bd107fefb5af
Create Date: 2026-01-20 19:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import app.db.base

# revision identifiers, used by Alembic.
revision = "20260120_0011"
down_revision = "bd107fefb5af"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create expense_categories table
    op.create_table(
        "expense_categories",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_expense_categories_name", "expense_categories", ["name"], unique=False)
    
    # Create expenses table
    op.create_table(
        "expenses",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=True),
        sa.Column("category_id", app.db.base.GUID(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("expense_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vendor", sa.String(length=255), nullable=True),
        sa.Column("receipt_url", sa.String(length=500), nullable=True),
        sa.Column("created_by", app.db.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["expense_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_expenses_category", "expenses", ["category_id"], unique=False)
    op.create_index("ix_expenses_date", "expenses", ["expense_date"], unique=False)
    op.create_index("ix_expenses_workspace", "expenses", ["workspace_id"], unique=False)
    
    # Create transactions table
    op.create_table(
        "transactions",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=True),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payment_method", sa.String(length=100), nullable=True),
        sa.Column("reference_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_by", app.db.base.GUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transactions_workspace", "transactions", ["workspace_id"], unique=False)
    op.create_index("ix_transactions_date", "transactions", ["transaction_date"], unique=False)
    op.create_index("ix_transactions_type", "transactions", ["type"], unique=False)
    op.create_index("ix_transactions_status", "transactions", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transactions_status", table_name="transactions")
    op.drop_index("ix_transactions_type", table_name="transactions")
    op.drop_index("ix_transactions_date", table_name="transactions")
    op.drop_index("ix_transactions_workspace", table_name="transactions")
    op.drop_table("transactions")
    
    op.drop_index("ix_expenses_workspace", table_name="expenses")
    op.drop_index("ix_expenses_date", table_name="expenses")
    op.drop_index("ix_expenses_category", table_name="expenses")
    op.drop_table("expenses")
    
    op.drop_index("ix_expense_categories_name", table_name="expense_categories")
    op.drop_table("expense_categories")
