"""add company_size to clients

Revision ID: 20260120_0012
Revises: 20260120_0011
Create Date: 2026-01-20 20:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260120_0012"
down_revision = "20260120_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add company_size column to clients table
    op.add_column("clients", sa.Column("company_size", sa.String(length=50), nullable=True))
    
    # Create index for better query performance
    op.create_index("ix_clients_company_size", "clients", ["company_size"], unique=False)


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_clients_company_size", table_name="clients")
    
    # Drop column
    op.drop_column("clients", "company_size")
