"""add client_id to projects

Revision ID: 20260120_0014
Revises: 20260120_0013
Create Date: 2026-01-20 23:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import app.db.base

# revision identifiers, used by Alembic.
revision = "20260120_0014"
down_revision = "20260120_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add client_id column to projects table
    op.add_column(
        "projects",
        sa.Column("client_id", app.db.base.GUID(), nullable=True),
    )
    
    # Create foreign key constraint
    op.create_foreign_key(
        "fk_projects_client_id",
        "projects",
        "clients",
        ["client_id"],
        ["id"],
        ondelete="SET NULL",
    )
    
    # Create index for better query performance
    op.create_index("ix_projects_client", "projects", ["client_id"], unique=False)
    
    # Optional: Populate client_id from existing client_name matches
    # This helps with backward compatibility
    # Note: This is a best-effort migration - projects with matching client names will get client_id set
    op.execute("""
        UPDATE projects p
        SET client_id = c.id
        FROM clients c
        WHERE p.client_name = c.name
          AND p.workspace_id = c.workspace_id
          AND p.client_id IS NULL;
    """)


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_projects_client", table_name="projects")
    
    # Drop foreign key constraint
    op.drop_constraint("fk_projects_client_id", "projects", type_="foreignkey")
    
    # Drop column
    op.drop_column("projects", "client_id")
