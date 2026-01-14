"""add state column to clients

Revision ID: 20260120_0009
Revises: 20260120_0008
Create Date: 2026-01-20 17:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "20260120_0009"
down_revision = "20260120_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add state column
    op.add_column("clients", sa.Column("state", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("clients", "state")
