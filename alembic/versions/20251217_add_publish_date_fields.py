"""add publish_date fields to videos

Revision ID: 20251217_add_publish_date_fields
Revises: 
Create Date: 2025-12-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '20251217_add_publish_date_fields'
# Chain to existing head so this becomes part of the main linear history
down_revision = '6f241fca9bda'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Get connection and inspector to check table existence
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Add publish_date to series_videos (only if table exists)
    if 'series_videos' in tables:
        columns = [col['name'] for col in inspector.get_columns('series_videos')]
        if 'publish_date' not in columns:
            op.add_column('series_videos', sa.Column('publish_date', sa.DateTime(timezone=True), nullable=True))
            op.create_index('ix_series_videos_publish_date', 'series_videos', ['publish_date'])
    else:
        print("⚠️  Skipping: series_videos table does not exist yet")

    # Add publish_date to general_knowledge_videos (only if table exists)
    if 'general_knowledge_videos' in tables:
        columns = [col['name'] for col in inspector.get_columns('general_knowledge_videos')]
        if 'publish_date' not in columns:
            op.add_column('general_knowledge_videos', sa.Column('publish_date', sa.DateTime(timezone=True), nullable=True))
            op.create_index('ix_gk_videos_publish_date', 'general_knowledge_videos', ['publish_date'])
    else:
        print("⚠️  Skipping: general_knowledge_videos table does not exist yet")


def downgrade() -> None:
    # Get connection and inspector to check table existence
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    # Drop indexes and columns added in upgrade (only if tables exist)
    if 'general_knowledge_videos' in tables:
        op.drop_index('ix_gk_videos_publish_date', table_name='general_knowledge_videos')
        op.drop_column('general_knowledge_videos', 'publish_date')

    if 'series_videos' in tables:
        op.drop_index('ix_series_videos_publish_date', table_name='series_videos')
        op.drop_column('series_videos', 'publish_date')