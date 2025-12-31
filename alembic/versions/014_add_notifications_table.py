"""014_add_notifications_table

Revision ID: 014_add_notifications
Revises: 013_add_discussion_forum_v2
Create Date: 2025-12-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = '014_add_notifications'
down_revision = 'b2286b0056a3'  # Changed from 013_add_discussion_forum_v2 to b2286b0056a3
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if table already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create notifications table only if it doesn't exist
    if 'notifications' not in existing_tables:
        op.create_table(
            'notifications',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
            sa.Column('type', sa.String(50), nullable=False, index=True),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('message', sa.Text, nullable=False),
            sa.Column('resource_type', sa.String(50), nullable=True, index=True),
            sa.Column('resource_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
            sa.Column('resource_url', sa.String(1000), nullable=True),
            sa.Column('is_read', sa.Boolean, default=False, nullable=False, index=True),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('extra_data', postgresql.JSONB, default=dict, nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, index=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        )
        
        # Create composite indexes for efficient queries
        op.create_index('idx_user_unread', 'notifications', ['user_id', 'is_read'])
        op.create_index('idx_user_created', 'notifications', ['user_id', 'created_at'])


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_user_created', table_name='notifications')
    op.drop_index('idx_user_unread', table_name='notifications')
    
    # Drop table
    op.drop_table('notifications')
