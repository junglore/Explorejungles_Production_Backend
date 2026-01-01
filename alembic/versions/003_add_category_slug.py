"""Add slug column to categories table

Revision ID: 003_add_category_slug
Revises: 002_fix_content_table_schema
Create Date: 2025-01-28 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003_add_category_slug'
down_revision = '002_fix_content_table_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Add slug column to categories table"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'categories' not in tables:
        print("⚠️  Skipping: categories table does not exist yet")
        return
    
    columns = [col['name'] for col in inspector.get_columns('categories')]
    
    # Add slug column if it doesn't exist
    if 'slug' not in columns:
        op.add_column('categories', sa.Column('slug', sa.String(length=255), nullable=True))
    
    # Create unique constraint on slug
    op.create_unique_constraint('uq_categories_slug', 'categories', ['slug'])
    
    # Create index on slug
    indexes = [idx['name'] for idx in inspector.get_indexes('categories')]
    if 'ix_categories_slug' not in indexes:
        op.create_index('ix_categories_slug', 'categories', ['slug'])
    
    # Add other missing columns from the model
    if 'image_url' not in columns:
        op.add_column('categories', sa.Column('image_url', sa.String(length=500), nullable=True))
    if 'viewer_count' not in columns:
        op.add_column('categories', sa.Column('viewer_count', sa.Integer(), nullable=False, server_default='0'))
    if 'is_active' not in columns:
        op.add_column('categories', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
    if 'updated_at' not in columns:
        op.add_column('categories', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    
    # Create indexes
    op.create_index('ix_categories_is_active', 'categories', ['is_active'])
    op.create_index('ix_categories_active_name', 'categories', ['is_active', 'name'])


def downgrade():
    """Remove slug column and other additions from categories table"""
    
    # Drop indexes
    op.drop_index('ix_categories_active_name', 'categories')
    op.drop_index('ix_categories_is_active', 'categories')
    op.drop_index('ix_categories_slug', 'categories')
    
    # Drop constraint
    op.drop_constraint('uq_categories_slug', 'categories', type_='unique')
    
    # Drop columns
    op.drop_column('categories', 'updated_at')
    op.drop_column('categories', 'is_active')
    op.drop_column('categories', 'viewer_count')
    op.drop_column('categories', 'image_url')
    op.drop_column('categories', 'slug')