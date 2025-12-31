"""add_video_series_tables

Revision ID: 4c1ea39912b5
Revises: c7a9ed89461c
Create Date: 2025-12-11 13:34:14.498511

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4c1ea39912b5'
down_revision = 'c7a9ed89461c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create video_series table if it doesn't exist
    if 'video_series' not in existing_tables:
        op.create_table(
            'video_series',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('subtitle', sa.String(500), nullable=True),
            sa.Column('slug', sa.String(255), nullable=False, unique=True),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('thumbnail_url', sa.String(500), nullable=True),
            sa.Column('total_videos', sa.Integer, server_default='0', nullable=False),
            sa.Column('total_views', sa.Integer, server_default='0', nullable=False),
            sa.Column('is_published', sa.Integer, server_default='1', nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        )
        # Create indexes for video_series
        op.create_index('ix_video_series_slug', 'video_series', ['slug'])
        op.create_index('ix_video_series_published', 'video_series', ['is_published', 'created_at'])
    
    # Create series_videos table if it doesn't exist
    if 'series_videos' not in existing_tables:
        op.create_table(
            'series_videos',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('series_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('subtitle', sa.String(500), nullable=True),
            sa.Column('slug', sa.String(255), nullable=False),
            sa.Column('description', sa.Text, nullable=True),
            sa.Column('video_url', sa.String(500), nullable=False),
            sa.Column('thumbnail_url', sa.String(500), nullable=True),
            sa.Column('duration', sa.Integer, nullable=True),
            sa.Column('position', sa.Integer, nullable=False),
            sa.Column('tags', postgresql.JSON, server_default='[]', nullable=False),
            sa.Column('hashtags', sa.String(500), nullable=True),
            sa.Column('views', sa.Integer, server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['series_id'], ['video_series.id'], ondelete='CASCADE'),
        )
        # Create indexes for series_videos
        op.create_index('ix_series_videos_series_position', 'series_videos', ['series_id', 'position'])
        op.create_index('ix_series_videos_slug', 'series_videos', ['slug'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Drop series_videos if it exists
    if 'series_videos' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('series_videos')]
        if 'ix_series_videos_slug' in existing_indexes:
            op.drop_index('ix_series_videos_slug', table_name='series_videos')
        if 'ix_series_videos_series_position' in existing_indexes:
            op.drop_index('ix_series_videos_series_position', table_name='series_videos')
        op.drop_table('series_videos')
    
    # Drop video_series if it exists
    if 'video_series' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('video_series')]
        if 'ix_video_series_published' in existing_indexes:
            op.drop_index('ix_video_series_published', table_name='video_series')
        if 'ix_video_series_slug' in existing_indexes:
            op.drop_index('ix_video_series_slug', table_name='video_series')
        op.drop_table('video_series')