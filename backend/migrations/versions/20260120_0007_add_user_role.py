"""add user role column

Revision ID: 20260120_0007
Revises: 20260120_0006
Create Date: 2026-01-20 14:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260120_0007"
down_revision = "20260120_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add role column to users table with default 'user'
    op.add_column("users", sa.Column("role", sa.String(length=50), nullable=False, server_default="user"))
    
    # Update existing users: if email is in admin_emails config, set role to 'admin'
    # Note: This will be handled by the application logic or a data migration script
    # For now, all existing users will default to 'user' role


def downgrade() -> None:
    op.drop_column("users", "role")
