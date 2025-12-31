"""Initial PostgreSQL schema for Junglore Backend

Revision ID: 001_initial_postgresql_schema
Revises: 
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '001_initial_postgresql_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial PostgreSQL schema"""
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    
    # Create categories table
    op.create_table('categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create content table
    op.create_table('content',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('author_name', sa.String(length=200), nullable=True),
        sa.Column('banner', sa.String(length=500), nullable=True),
        sa.Column('video', sa.String(length=500), nullable=True),
        sa.Column('featured', sa.Boolean(), nullable=True, default=False),
        sa.Column('feature_place', sa.Integer(), nullable=True, default=0),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL')
    )
    
    # Create media table
    op.create_table('media',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('media_type', sa.String(length=50), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=False),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('photographer', sa.String(length=255), nullable=True),
        sa.Column('national_park', sa.String(length=255), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('file_metadata', postgresql.JSON(), nullable=False, default=dict),
        sa.Column('is_featured', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['content_id'], ['content.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('file_url')
    )
    
    # Create indexes
    op.create_index('ix_media_content_type', 'media', ['content_id', 'media_type'])
    op.create_index('ix_media_uploader_created', 'media', ['uploaded_by', 'created_at'])
    op.create_index('ix_media_type_created', 'media', ['media_type', 'created_at'])
    op.create_index('ix_media_photographer_park', 'media', ['photographer', 'national_park'])
    op.create_index('ix_media_featured', 'media', ['is_featured'])
    op.create_index('ix_media_media_type', 'media', ['media_type'])
    op.create_index('ix_media_national_park', 'media', ['national_park'])
    op.create_index('ix_media_photographer', 'media', ['photographer'])


def downgrade():
    """Drop initial PostgreSQL schema"""
    
    # Drop tables in reverse order
    op.drop_table('media')
    op.drop_table('content')
    op.drop_table('categories')
    op.drop_table('users')
