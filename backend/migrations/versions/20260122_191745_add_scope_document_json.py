"""Add scope_document_json to scopes table

Revision ID: 20260122_191745
Revises: 20260120_0016
Create Date: 2026-01-22 19:17:45

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260122_191745'
down_revision = '20c1ec8d8a44'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add scope_document_json column to scopes table
    op.add_column('scopes', sa.Column('scope_document_json', sa.Text(), nullable=True))


def downgrade() -> None:
    # Remove scope_document_json column
    op.drop_column('scopes', 'scope_document_json')
