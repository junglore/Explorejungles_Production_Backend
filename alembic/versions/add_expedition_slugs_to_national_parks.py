"""add expedition_slugs to national_parks

Revision ID: add_expedition_slugs
Revises: db4a03506615
Create Date: 2025-12-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_expedition_slugs'
down_revision = 'db4a03506615'  # Updated to current head
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if column already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'national_parks' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('national_parks')]
        
        # Only add column if it doesn't exist
        if 'expedition_slugs' not in existing_columns:
            op.add_column('national_parks', 
                sa.Column('expedition_slugs', postgresql.JSONB, nullable=False, server_default='[]'))


def downgrade() -> None:
    # Check if column exists before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'national_parks' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('national_parks')]
        
        if 'expedition_slugs' in existing_columns:
            op.drop_column('national_parks', 'expedition_slugs')