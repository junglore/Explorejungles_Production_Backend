"""add_myths_facts_indexes_and_constraints

Revision ID: 4943ae846168
Revises: d869f2f395fa
Create Date: 2025-08-29 18:43:20.972623

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '4943ae846168'
down_revision = '004_add_featured_media_support'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add indexes and constraints to existing myths_facts table"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if myths_facts table exists
    if 'myths_facts' not in inspector.get_table_names():
        return  # Table doesn't exist yet, skip this migration
    
    # Get existing indexes and constraints
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('myths_facts')]
    existing_constraints = [constraint['name'] for constraint in inspector.get_check_constraints('myths_facts')]
    existing_unique_constraints = [constraint['name'] for constraint in inspector.get_unique_constraints('myths_facts')]
    
    # Task 5.1: Create performance indexes for myths_facts table (if they don't exist)
    # Index on created_at for chronological queries
    if 'idx_myths_facts_created_at' not in existing_indexes:
        op.create_index('idx_myths_facts_created_at', 'myths_facts', ['created_at'], postgresql_using='btree')
    
    # Partial index on is_featured for featured content queries
    if 'idx_myths_facts_featured' not in existing_indexes:
        op.create_index('idx_myths_facts_featured', 'myths_facts', ['is_featured'], 
                       postgresql_where=sa.text('is_featured = true'))
    
    # Index on category_id for category-based queries
    if 'idx_myths_facts_category' not in existing_indexes:
        op.create_index('idx_myths_facts_category', 'myths_facts', ['category_id'])
    
    # Index on title for search functionality
    if 'idx_myths_facts_title' not in existing_indexes:
        op.create_index('idx_myths_facts_title', 'myths_facts', ['title'])
    
    # Composite indexes for common query patterns
    if 'idx_myths_facts_featured_created' not in existing_indexes:
        op.create_index('idx_myths_facts_featured_created', 'myths_facts', ['is_featured', 'created_at'])
        
    if 'idx_myths_facts_category_created' not in existing_indexes:
        op.create_index('idx_myths_facts_category_created', 'myths_facts', ['category_id', 'created_at'])
    
    # Task 5.2: Add additional database constraints (if they don't exist)
    # Add check constraints for data validation
    if 'ck_myths_facts_title_not_empty' not in existing_constraints:
        op.create_check_constraint('ck_myths_facts_title_not_empty', 'myths_facts', "title != ''")
        
    if 'ck_myths_facts_myth_content_not_empty' not in existing_constraints:
        op.create_check_constraint('ck_myths_facts_myth_content_not_empty', 'myths_facts', "myth_content != ''")
        
    if 'ck_myths_facts_fact_content_not_empty' not in existing_constraints:
        op.create_check_constraint('ck_myths_facts_fact_content_not_empty', 'myths_facts', "fact_content != ''")
        
    if 'ck_myths_facts_title_length' not in existing_constraints:
        op.create_check_constraint('ck_myths_facts_title_length', 'myths_facts', "length(title) <= 500")
        
    if 'ck_myths_facts_image_url_length' not in existing_constraints:
        op.create_check_constraint('ck_myths_facts_image_url_length', 'myths_facts', "length(image_url) <= 500")
    
    # Add unique constraint on title to prevent duplicates
    if 'uq_myths_facts_title' not in existing_unique_constraints:
        op.create_unique_constraint('uq_myths_facts_title', 'myths_facts', ['title'])


def downgrade() -> None:
    """Drop indexes and constraints (but keep table)"""
    
    # Drop unique constraint
    try:
        op.drop_constraint('uq_myths_facts_title', 'myths_facts', type_='unique')
    except Exception:
        pass
    
    # Drop check constraints
    try:
        op.drop_constraint('ck_myths_facts_title_not_empty', 'myths_facts', type_='check')
    except Exception:
        pass
        
    try:
        op.drop_constraint('ck_myths_facts_myth_content_not_empty', 'myths_facts', type_='check')
    except Exception:
        pass
        
    try:
        op.drop_constraint('ck_myths_facts_fact_content_not_empty', 'myths_facts', type_='check')
    except Exception:
        pass
        
    try:
        op.drop_constraint('ck_myths_facts_title_length', 'myths_facts', type_='check')
    except Exception:
        pass
        
    try:
        op.drop_constraint('ck_myths_facts_image_url_length', 'myths_facts', type_='check')
    except Exception:
        pass
    
    # Drop indexes
    try:
        op.drop_index('idx_myths_facts_category_created')
    except Exception:
        pass
        
    try:
        op.drop_index('idx_myths_facts_featured_created')
    except Exception:
        pass
        
    try:
        op.drop_index('idx_myths_facts_title')
    except Exception:
        pass
        
    try:
        op.drop_index('idx_myths_facts_category')
    except Exception:
        pass
        
    try:
        op.drop_index('idx_myths_facts_featured')
    except Exception:
        pass
        
    try:
        op.drop_index('idx_myths_facts_created_at')
    except Exception:
        pass
