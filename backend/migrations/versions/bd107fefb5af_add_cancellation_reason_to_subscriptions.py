"""add cancellation_reason to subscriptions

Revision ID: bd107fefb5af
Revises: 20260120_0010
Create Date: 2026-01-14 13:42:24.734766
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bd107fefb5af"
down_revision = "20260120_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cancellation_reason column to subscriptions table
    op.add_column(
        "subscriptions",
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "cancellation_reason")
