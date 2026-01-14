"""add clients table

Revision ID: 20260120_0005
Revises: da2fd07bfb00
Create Date: 2026-01-20 12:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import app.db.base

# revision identifiers, used by Alembic.
revision = "20260120_0005"
down_revision = "20260107_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create clients table
    op.create_table(
        "clients",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="prospect"),
        sa.Column("industry", sa.String(length=100), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("contact_email", sa.String(length=255), nullable=False),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("health_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_activity", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clients_workspace", "clients", ["workspace_id"], unique=False)
    op.create_index("ix_clients_status", "clients", ["status"], unique=False)
    op.create_index("ix_clients_industry", "clients", ["industry"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_clients_industry", table_name="clients")
    op.drop_index("ix_clients_status", table_name="clients")
    op.drop_index("ix_clients_workspace", table_name="clients")
    op.drop_table("clients")
