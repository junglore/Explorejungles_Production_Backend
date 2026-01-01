"""Fix content table schema to match model

Revision ID: 002_fix_content_table_schema
Revises: 001_initial_postgresql_schema
Create Date: 2025-01-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '002_fix_content_table_schema'
down_revision = '001_initial_postgresql_schema'
branch_labels = None
depends_on = None


def upgrade():
    """Fix content table schema to match the Content model"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'content' not in tables:
        print("⚠️  Skipping: content table does not exist yet")
        return
    
    columns = [col['name'] for col in inspector.get_columns('content')]
    
    # Add missing author_id column if it doesn't exist
    if 'author_id' not in columns:
        op.add_column('content', sa.Column('author_id', postgresql.UUID(as_uuid=True), nullable=True))
    
    # Rename content_type to type if content_type exists and type doesn't
    if 'content_type' in columns and 'type' not in columns:
        op.alter_column('content', 'content_type', new_column_name='type')
    
    # Rename body to content if body exists and content doesn't
    if 'body' in columns and 'content' not in columns:
        op.alter_column('content', 'body', new_column_name='content')
    
    # Add missing columns
    op.add_column('content', sa.Column('featured_image', sa.String(length=500), nullable=True))
    op.add_column('content', sa.Column('slug', sa.String(length=500), nullable=True))
    op.add_column('content', sa.Column('excerpt', sa.Text(), nullable=True))
    op.add_column('content', sa.Column('meta_description', sa.String(length=255), nullable=True))
    op.add_column('content', sa.Column('content_metadata', postgresql.JSON(), nullable=False, server_default='{}'))
    op.add_column('content', sa.Column('view_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('content', sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'))
    op.add_column('content', sa.Column('published_at', sa.DateTime(timezone=True), nullable=True))
    
    # Modify existing columns to match model constraints
    op.alter_column('content', 'title', type_=sa.String(length=500), nullable=False)
    op.alter_column('content', 'content', nullable=False)
    op.alter_column('content', 'featured', nullable=False, server_default='false')
    op.alter_column('content', 'feature_place', nullable=False, server_default='0')
    
    # Add foreign key constraint for author_id
    op.create_foreign_key('fk_content_author_id_users', 'content', 'users', ['author_id'], ['id'], ondelete='CASCADE')
    
    # Create unique constraint on slug
    op.create_unique_constraint('uq_content_slug', 'content', ['slug'])
    
    # Create indexes for performance
    op.create_index('ix_content_type', 'content', ['type'])
    op.create_index('ix_content_title', 'content', ['title'])
    op.create_index('ix_content_featured', 'content', ['featured'])
    op.create_index('ix_content_slug', 'content', ['slug'])
    op.create_index('ix_content_status', 'content', ['status'])
    op.create_index('ix_content_published_at', 'content', ['published_at'])
    
    # Composite indexes
    op.create_index('ix_content_published_type_date', 'content', ['status', 'type', 'published_at'])
    op.create_index('ix_content_featured_place', 'content', ['featured', 'feature_place'])
    op.create_index('ix_content_author_status', 'content', ['author_id', 'status'])
    op.create_index('ix_content_category_status', 'content', ['category_id', 'status'])
    op.create_index('ix_content_type_created', 'content', ['type', 'created_at'])


def downgrade():
    """Revert content table schema changes"""
    
    # Drop indexes
    op.drop_index('ix_content_type_created', 'content')
    op.drop_index('ix_content_category_status', 'content')
    op.drop_index('ix_content_author_status', 'content')
    op.drop_index('ix_content_featured_place', 'content')
    op.drop_index('ix_content_published_type_date', 'content')
    op.drop_index('ix_content_published_at', 'content')
    op.drop_index('ix_content_status', 'content')
    op.drop_index('ix_content_slug', 'content')
    op.drop_index('ix_content_featured', 'content')
    op.drop_index('ix_content_title', 'content')
    op.drop_index('ix_content_type', 'content')
    
    # Drop constraints
    op.drop_constraint('uq_content_slug', 'content', type_='unique')
    op.drop_constraint('fk_content_author_id_users', 'content', type_='foreignkey')
    
    # Revert column changes
    op.alter_column('content', 'type', new_column_name='content_type')
    op.alter_column('content', 'content', new_column_name='body')
    
    # Drop added columns
    op.drop_column('content', 'published_at')
    op.drop_column('content', 'status')
    op.drop_column('content', 'view_count')
    op.drop_column('content', 'content_metadata')
    op.drop_column('content', 'meta_description')
    op.drop_column('content', 'excerpt')
    op.drop_column('content', 'slug')
    op.drop_column('content', 'featured_image')
    op.drop_column('content', 'author_id')