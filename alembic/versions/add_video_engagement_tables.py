"""add video engagement tables

Revision ID: add_video_engagement
Revises: 
Create Date: 2025-12-15 23:30:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID
import uuid

# revision identifiers, used by Alembic.
revision = 'add_video_engagement'
down_revision = '0ae421df7dff'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create video_likes table if it doesn't exist
    if 'video_likes' not in existing_tables:
        op.create_table(
            'video_likes',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('user_id', UUID(as_uuid=True), nullable=False),
            sa.Column('video_slug', sa.String(255), nullable=False),
            sa.Column('video_type', sa.String(50), nullable=False),
            sa.Column('vote', sa.Integer, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.UniqueConstraint('user_id', 'video_slug', name='uq_user_video_like')
        )
        op.create_index('ix_video_likes_user_video', 'video_likes', ['user_id', 'video_slug'])
    
    # Create video_comments table if it doesn't exist
    if 'video_comments' not in existing_tables:
        op.create_table(
            'video_comments',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('video_slug', sa.String(255), nullable=False),
            sa.Column('video_type', sa.String(50), nullable=False),
            sa.Column('content', sa.Text, nullable=False),
            sa.Column('parent_id', UUID(as_uuid=True), sa.ForeignKey('video_comments.id', ondelete='CASCADE'), nullable=True),
            sa.Column('likes_count', sa.Integer, default=0, nullable=False),
            sa.Column('replies_count', sa.Integer, default=0, nullable=False),
            sa.Column('is_edited', sa.Integer, default=0, nullable=False),
            sa.Column('is_deleted', sa.Integer, default=0, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
        )
        op.create_index('ix_video_comments_video', 'video_comments', ['video_slug', 'created_at'])
        op.create_index('ix_video_comments_user', 'video_comments', ['user_id', 'created_at'])
        op.create_index('ix_video_comments_parent', 'video_comments', ['parent_id'])
    
    # Create video_comment_likes table if it doesn't exist
    if 'video_comment_likes' not in existing_tables:
        op.create_table(
            'video_comment_likes',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('user_id', UUID(as_uuid=True), nullable=False),
            sa.Column('comment_id', UUID(as_uuid=True), sa.ForeignKey('video_comments.id', ondelete='CASCADE'), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint('user_id', 'comment_id', name='uq_user_comment_like')
        )
        op.create_index('ix_video_comment_likes_user_comment', 'video_comment_likes', ['user_id', 'comment_id'])


def downgrade():
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'video_comment_likes' in existing_tables:
        op.drop_table('video_comment_likes')
    if 'video_comments' in existing_tables:
        op.drop_table('video_comments')
    if 'video_likes' in existing_tables:
        op.drop_table('video_likes')
