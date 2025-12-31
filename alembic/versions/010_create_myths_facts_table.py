"""Create myths_facts table with indexes

Revision ID: 010_create_myths_facts_table
Revises: 009_make_category_slug_required
Create Date: 2025-08-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '010_create_myths_facts_table'
down_revision: Union[str, None] = '1a1c42044fff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create myths_facts table with proper indexes"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if table exists
    if 'myths_facts' not in inspector.get_table_names():
        # Create myths_facts table
        op.create_table('myths_facts',
            sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('title', sa.String(length=500), nullable=False),
            sa.Column('myth_content', sa.Text(), nullable=False),
            sa.Column('fact_content', sa.Text(), nullable=False),
            sa.Column('image_url', sa.String(length=500), nullable=True),
            sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.PrimaryKeyConstraint('id'),
            sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL')
        )
    
    # Get existing indexes
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('myths_facts')]
    
    # Create performance indexes for myths_facts table (only if they don't exist)
    if 'idx_myths_facts_created_at' not in existing_indexes:
        op.create_index('idx_myths_facts_created_at', 'myths_facts', ['created_at'], postgresql_using='btree')
    
    if 'idx_myths_facts_featured' not in existing_indexes:
        op.create_index('idx_myths_facts_featured', 'myths_facts', ['is_featured'], postgresql_where=sa.text('is_featured = true'))
    
    if 'idx_myths_facts_category' not in existing_indexes:
        op.create_index('idx_myths_facts_category', 'myths_facts', ['category_id'])
    
    if 'idx_myths_facts_title' not in existing_indexes:
        op.create_index('idx_myths_facts_title', 'myths_facts', ['title'])
    
    # Composite indexes for common query patterns
    if 'idx_myths_facts_featured_created' not in existing_indexes:
        op.create_index('idx_myths_facts_featured_created', 'myths_facts', ['is_featured', 'created_at'])
    
    if 'idx_myths_facts_category_created' not in existing_indexes:
        op.create_index('idx_myths_facts_category_created', 'myths_facts', ['category_id', 'created_at'])


def downgrade() -> None:
    """Drop myths_facts table and indexes"""
    
    # Drop indexes first
    op.drop_index('idx_myths_facts_category_created')
    op.drop_index('idx_myths_facts_featured_created')
    op.drop_index('idx_myths_facts_title')
    op.drop_index('idx_myths_facts_category')
    op.drop_index('idx_myths_facts_featured')
    op.drop_index('idx_myths_facts_created_at')
    
    # Drop table
    op.drop_table('myths_facts')