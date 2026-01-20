"""add settings page tables

Revision ID: 20260120_0016
Revises: 20260120_0015
Create Date: 2025-01-20 12:00:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

import app.db.base

# revision identifiers, used by Alembic.
revision = '20260120_0016'
down_revision = '20260120_0015'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new fields to users table
    op.add_column('users', sa.Column('phone', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('company', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('job_role', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('last_password_change', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('two_factor_secret', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('two_factor_method', sa.String(10), nullable=True))
    op.add_column('users', sa.Column('two_factor_backup_codes', postgresql.ARRAY(sa.String()), nullable=True))
    
    # Create workspace_settings table
    op.create_table(
        'workspace_settings',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('workspace_id', app.db.base.GUID(), nullable=False),
        sa.Column('workspace_mode', sa.String(10), nullable=False, server_default='team'),
        sa.Column('require_scope_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('require_prd_approval', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('auto_create_project', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('default_engagement_type', sa.String(20), nullable=False, server_default='fixed'),
        sa.Column('ai_assist_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('ai_model_preference', sa.String(20), nullable=False, server_default='orbit-pro'),
        sa.Column('show_client_health', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
        sa.Column('date_format', sa.String(20), nullable=False, server_default='MM/DD/YYYY'),
        sa.Column('time_format', sa.String(5), nullable=False, server_default='12h'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('workspace_id', name='uq_workspace_settings_workspace'),
    )
    op.create_index('ix_workspace_settings_workspace', 'workspace_settings', ['workspace_id'])
    
    # Create teams table
    op.create_table(
        'teams',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('workspace_id', app.db.base.GUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', app.db.base.GUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_teams_workspace', 'teams', ['workspace_id'])
    
    # Create team_members table
    op.create_table(
        'team_members',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('team_id', app.db.base.GUID(), nullable=False),
        sa.Column('user_id', app.db.base.GUID(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='member'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_members_team_user'),
    )
    op.create_index('ix_team_members_team', 'team_members', ['team_id'])
    op.create_index('ix_team_members_user', 'team_members', ['user_id'])
    
    # Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('user_id', app.db.base.GUID(), nullable=False),
        sa.Column('workspace_id', app.db.base.GUID(), nullable=True),
        sa.Column('preference_type', sa.String(50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('channels', postgresql.ARRAY(sa.String()), nullable=False, server_default=sa.text("ARRAY['email', 'in-app']")),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'workspace_id', 'preference_type', name='uq_notification_preferences_user_workspace_type'),
    )
    op.create_index('ix_notification_preferences_user', 'notification_preferences', ['user_id'])
    op.create_index('ix_notification_preferences_workspace', 'notification_preferences', ['workspace_id'])
    
    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('user_id', app.db.base.GUID(), nullable=False),
        sa.Column('device', sa.String(255), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('last_active', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_user_sessions_user', 'user_sessions', ['user_id'])
    op.create_index('ix_user_sessions_active', 'user_sessions', ['user_id', 'is_active'])
    
    # Create login_activity table
    op.create_table(
        'login_activity',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('user_id', app.db.base.GUID(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('failure_reason', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_login_activity_user', 'login_activity', ['user_id'])
    op.create_index('ix_login_activity_timestamp', 'login_activity', ['timestamp'])
    
    # Create billing_history table
    op.create_table(
        'billing_history',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('workspace_id', app.db.base.GUID(), nullable=False),
        sa.Column('subscription_id', app.db.base.GUID(), nullable=True),
        sa.Column('description', sa.String(255), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('invoice_url', sa.Text(), nullable=True),
        sa.Column('billing_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payment_method_id', app.db.base.GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_billing_history_workspace', 'billing_history', ['workspace_id'])
    op.create_index('ix_billing_history_status', 'billing_history', ['status'])
    
    # Create data_exports table
    op.create_table(
        'data_exports',
        sa.Column('id', app.db.base.GUID(), primary_key=True),
        sa.Column('user_id', app.db.base.GUID(), nullable=False),
        sa.Column('workspace_id', app.db.base.GUID(), nullable=True),
        sa.Column('format', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='processing'),
        sa.Column('include_data', postgresql.JSONB(), nullable=False),
        sa.Column('file_url', sa.Text(), nullable=True),
        sa.Column('file_size', sa.BigInteger(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_data_exports_user', 'data_exports', ['user_id'])
    op.create_index('ix_data_exports_status', 'data_exports', ['status'])


def downgrade() -> None:
    op.drop_table('data_exports')
    op.drop_table('billing_history')
    op.drop_table('login_activity')
    op.drop_table('user_sessions')
    op.drop_table('notification_preferences')
    op.drop_table('team_members')
    op.drop_table('teams')
    op.drop_table('workspace_settings')
    
    op.drop_column('users', 'two_factor_backup_codes')
    op.drop_column('users', 'two_factor_method')
    op.drop_column('users', 'two_factor_secret')
    op.drop_column('users', 'last_password_change')
    op.drop_column('users', 'two_factor_enabled')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'job_role')
    op.drop_column('users', 'company')
    op.drop_column('users', 'phone')
