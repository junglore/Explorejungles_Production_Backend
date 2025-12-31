"""Add featured media support

Revision ID: 004_add_featured_media_support
Revises: 003_add_category_slug
Create Date: 2025-01-28 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '004_add_featured_media_support'
down_revision = '003_add_category_slug'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add featured media support"""
    
    # Check if is_featured column already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('media')]
    
    if 'is_featured' not in columns:
        # Add is_featured column to media table
        op.add_column('media', sa.Column('is_featured', sa.Integer(), nullable=False, server_default='0'))
        
        # Add index for featured media queries
        op.create_index('ix_media_featured', 'media', ['is_featured'])
    
    # Ensure uploaded_by column exists for proper user tracking
    if 'uploaded_by' not in columns:
        op.add_column('media', sa.Column('uploaded_by', sa.UUID(), nullable=True))
        op.create_foreign_key('fk_media_uploaded_by', 'media', 'users', ['uploaded_by'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    """Remove featured media support"""
    
    # Drop the featured index
    try:
        op.drop_index('ix_media_featured', table_name='media')
    except:
        pass
    
    # Drop the is_featured column
    try:
        op.drop_column('media', 'is_featured')
    except:
        pass
    
    # Drop uploaded_by foreign key and column if they were added
    try:
        op.drop_constraint('fk_media_uploaded_by', 'media', type_='foreignkey')
        op.drop_column('media', 'uploaded_by')
    except:
        pass