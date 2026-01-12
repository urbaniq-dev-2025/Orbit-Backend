"""Update password reset code storage to use hashed values.

Revision ID: 20260107_0003
Revises: da2fd07bfb00
Create Date: 2026-01-07 16:44:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260107_0003"
down_revision = "da2fd07bfb00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_password_reset_user_code", "password_resets", type_="unique")
    op.drop_index("ix_password_resets_code", table_name="password_resets")
    op.alter_column("password_resets", "code", new_column_name="code_hash")
    op.alter_column(
        "password_resets",
        "code_hash",
        existing_type=sa.String(length=6),
        type_=sa.String(length=128),
        existing_nullable=False,
    )
    op.create_index(
        "ix_password_resets_code_hash", "password_resets", ["code_hash"], unique=False
    )
    op.create_unique_constraint(
        "uq_password_reset_user_code", "password_resets", ["user_id", "code_hash"]
    )
    op.add_column(
        "password_resets",
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("password_resets", "used_at")
    op.drop_constraint("uq_password_reset_user_code", "password_resets", type_="unique")
    op.drop_index("ix_password_resets_code_hash", table_name="password_resets")
    op.alter_column("password_resets", "code_hash", new_column_name="code")
    op.alter_column(
        "password_resets",
        "code",
        existing_type=sa.String(length=128),
        type_=sa.String(length=6),
        existing_nullable=False,
    )
    op.create_index(
        "ix_password_resets_code", "password_resets", ["code"], unique=False
    )
    op.create_unique_constraint(
        "uq_password_reset_user_code", "password_resets", ["user_id", "code"]
    )




