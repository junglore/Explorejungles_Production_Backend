"""Add performance indexes

Revision ID: 008_add_performance_indexes
Revises: 002_fix_content_table_schema
Create Date: 2025-08-28 20:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '008_add_performance_indexes'
down_revision: Union[str, None] = '002_fix_content_table_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes"""
    
    # Content table indexes for better query performance
    op.create_index('idx_content_status_published', 'content', ['status', 'published_at'])
    op.create_index('idx_content_category_status', 'content', ['category_id', 'status'])
    op.create_index('idx_content_author_created', 'content', ['author_id', 'created_at'])
    op.create_index('idx_content_featured_status', 'content', ['featured', 'status'])
    op.create_index('idx_content_type_status', 'content', ['type', 'status'])
    op.create_index('idx_content_slug_unique', 'content', ['slug'], unique=True)
    op.create_index('idx_content_view_count', 'content', ['view_count'])
    
    # Media table indexes for better performance
    op.create_index('idx_media_type_created', 'media', ['media_type', 'created_at'])
    op.create_index('idx_media_content_type', 'media', ['content_id', 'media_type'])
    op.create_index('idx_media_uploader_created', 'media', ['uploaded_by', 'created_at'])
    op.create_index('idx_media_photographer_park', 'media', ['photographer', 'national_park'])
    op.create_index('idx_media_featured', 'media', ['is_featured'])
    op.create_index('idx_media_file_size', 'media', ['file_size'])
    
    # Categories table indexes
    op.create_index('idx_categories_slug_unique', 'categories', ['slug'], unique=True)
    
    # Users table indexes
    op.create_index('idx_users_email_unique', 'users', ['email'], unique=True)
    op.create_index('idx_users_username_unique', 'users', ['username'], unique=True)
    op.create_index('idx_users_active_super', 'users', ['is_active', 'is_superuser'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    
    # Composite indexes for common queries
    op.create_index('idx_content_published_featured', 'content', ['status', 'featured', 'published_at'])
    op.create_index('idx_media_type_featured_created', 'media', ['media_type', 'is_featured', 'created_at'])


def downgrade() -> None:
    """Remove performance indexes"""
    
    # Content indexes
    op.drop_index('idx_content_status_published')
    op.drop_index('idx_content_category_status')
    op.drop_index('idx_content_author_created')
    op.drop_index('idx_content_featured_status')
    op.drop_index('idx_content_type_status')
    op.drop_index('idx_content_slug_unique')
    op.drop_index('idx_content_view_count')
    
    # Media indexes
    op.drop_index('idx_media_type_created')
    op.drop_index('idx_media_content_type')
    op.drop_index('idx_media_uploader_created')
    op.drop_index('idx_media_photographer_park')
    op.drop_index('idx_media_featured')
    op.drop_index('idx_media_file_size')
    
    # Categories indexes
    op.drop_index('idx_categories_slug_unique')
    
    # Users indexes
    op.drop_index('idx_users_email_unique')
    op.drop_index('idx_users_username_unique')
    op.drop_index('idx_users_active_super')
    op.drop_index('idx_users_created_at')
    
    # Composite indexes
    op.drop_index('idx_content_published_featured')
    op.drop_index('idx_media_type_featured_created')