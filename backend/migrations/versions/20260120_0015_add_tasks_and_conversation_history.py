"""add tasks and conversation_history tables

Revision ID: 20260120_0015
Revises: 20260120_0014
Create Date: 2026-01-20 23:30:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

import app.db.base

# revision identifiers, used by Alembic.
revision = "20260120_0015"
down_revision = "20260120_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="none"),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="general"),
        sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reminder_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reminder_notified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("project_id", app.db.base.GUID(), nullable=True),
        sa.Column("scope_id", app.db.base.GUID(), nullable=True),
        sa.Column("created_by", app.db.base.GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["scope_id"], ["scopes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for tasks
    op.create_index("ix_tasks_workspace", "tasks", ["workspace_id"], unique=False)
    op.create_index("ix_tasks_due_date", "tasks", ["due_date"], unique=False)
    op.create_index("ix_tasks_completed", "tasks", ["completed"], unique=False)
    op.create_index("ix_tasks_priority", "tasks", ["priority"], unique=False)
    op.create_index("ix_tasks_created_by", "tasks", ["created_by"], unique=False)
    
    # Create partial index for reminder_time where reminder_enabled is true
    op.execute("""
        CREATE INDEX ix_tasks_reminder_time ON tasks(reminder_time) 
        WHERE reminder_enabled = TRUE;
    """)
    
    # Create conversation_history table
    op.create_table(
        "conversation_history",
        sa.Column("id", app.db.base.GUID(), nullable=False),
        sa.Column("workspace_id", app.db.base.GUID(), nullable=False),
        sa.Column("user_id", app.db.base.GUID(), nullable=False),
        sa.Column("conversation_id", app.db.base.GUID(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("intent_type", sa.String(length=50), nullable=True),
        sa.Column("intent_confidence", sa.Float(), nullable=True),
        sa.Column("actions", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    
    # Create indexes for conversation_history
    op.create_index("ix_conversation_history_workspace", "conversation_history", ["workspace_id"], unique=False)
    op.create_index("ix_conversation_history_conversation_id", "conversation_history", ["conversation_id"], unique=False)
    op.create_index("ix_conversation_history_created_at", "conversation_history", ["created_at"], unique=False)
    op.create_index("ix_conversation_history_user", "conversation_history", ["user_id"], unique=False)


def downgrade() -> None:
    # Drop conversation_history indexes and table
    op.drop_index("ix_conversation_history_user", table_name="conversation_history")
    op.drop_index("ix_conversation_history_created_at", table_name="conversation_history")
    op.drop_index("ix_conversation_history_conversation_id", table_name="conversation_history")
    op.drop_index("ix_conversation_history_workspace", table_name="conversation_history")
    op.drop_table("conversation_history")
    
    # Drop tasks indexes and table
    op.drop_index("ix_tasks_reminder_time", table_name="tasks")
    op.drop_index("ix_tasks_created_by", table_name="tasks")
    op.drop_index("ix_tasks_priority", table_name="tasks")
    op.drop_index("ix_tasks_completed", table_name="tasks")
    op.drop_index("ix_tasks_due_date", table_name="tasks")
    op.drop_index("ix_tasks_workspace", table_name="tasks")
    op.drop_table("tasks")
