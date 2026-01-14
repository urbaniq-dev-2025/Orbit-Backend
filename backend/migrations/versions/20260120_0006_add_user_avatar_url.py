"""add user avatar_url column

Revision ID: 20260120_0006
Revises: 20260120_0005
Create Date: 2026-01-20 13:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260120_0006"
down_revision = "20260120_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add avatar_url column to users table
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
