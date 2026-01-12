"""Add onboarding progress columns to users.

Revision ID: 20260107_0004
Revises: 20260107_0003
Create Date: 2026-01-07 17:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260107_0004"
down_revision = "20260107_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "onboarding_step",
            sa.String(length=50),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column("users", sa.Column("onboarding_state", sa.JSON(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "onboarding_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Drop server defaults for new inserts once existing rows are migrated
    op.alter_column("users", "onboarding_step", server_default=None)
    op.alter_column("users", "onboarding_completed", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "onboarding_completed")
    op.drop_column("users", "onboarding_state")
    op.drop_column("users", "onboarding_step")




