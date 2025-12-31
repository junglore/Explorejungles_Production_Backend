"""add_featured_series_fields

Revision ID: 6f241fca9bda
Revises: add_video_engagement
Create Date: 2025-12-16 22:40:56.631767

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '6f241fca9bda'
down_revision = 'add_video_engagement'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'video_series' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('video_series')]
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('video_series')]
        
        # Add is_featured column if it doesn't exist
        if 'is_featured' not in existing_columns:
            op.add_column('video_series', sa.Column('is_featured', sa.Integer(), nullable=False, server_default='0'))
        
        # Add featured_at column if it doesn't exist
        if 'featured_at' not in existing_columns:
            op.add_column('video_series', sa.Column('featured_at', sa.DateTime(timezone=True), nullable=True))
        
        # Create index if it doesn't exist
        if 'ix_video_series_featured' not in existing_indexes:
            op.create_index('ix_video_series_featured', 'video_series', ['is_featured', 'featured_at'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'video_series' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('video_series')]
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('video_series')]
        
        # Drop index if it exists
        if 'ix_video_series_featured' in existing_indexes:
            op.drop_index('ix_video_series_featured', table_name='video_series')
        
        # Drop columns if they exist
        if 'featured_at' in existing_columns:
            op.drop_column('video_series', 'featured_at')
        if 'is_featured' in existing_columns:
            op.drop_column('video_series', 'is_featured')
