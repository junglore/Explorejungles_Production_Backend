"""add_video_watch_progress_table

Revision ID: db4a03506615
Revises: 6f241fca9bda
Create Date: 2025-12-17 19:37:27.586341

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'db4a03506615'
down_revision = '6f241fca9bda'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'video_watch_progress' not in existing_tables:
        # Create video_watch_progress table
        op.create_table(
            'video_watch_progress',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('video_slug', sa.String(255), nullable=False, index=True),
            sa.Column('video_type', sa.String(50), nullable=False),
            sa.Column('current_time', sa.Float, default=0, nullable=False),
            sa.Column('duration', sa.Float, nullable=True),
            sa.Column('progress_percentage', sa.Float, default=0, nullable=False),
            sa.Column('completed', sa.Integer, default=0, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.Column('last_watched_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
        )
        
        # Create indexes
        op.create_index('ix_video_progress_user_video', 'video_watch_progress', ['user_id', 'video_slug'])
        op.create_index('ix_video_progress_user_type', 'video_watch_progress', ['user_id', 'video_type'])


def downgrade() -> None:
    # Check if table exists before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'video_watch_progress' in existing_tables:
        # Drop indexes first
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('video_watch_progress')]
        if 'ix_video_progress_user_type' in existing_indexes:
            op.drop_index('ix_video_progress_user_type', table_name='video_watch_progress')
        if 'ix_video_progress_user_video' in existing_indexes:
            op.drop_index('ix_video_progress_user_video', table_name='video_watch_progress')
        
        # Drop table
        op.drop_table('video_watch_progress')
