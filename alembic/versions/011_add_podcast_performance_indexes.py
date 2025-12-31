"""Add performance indexes for podcast queries

Revision ID: 011_add_podcast_perf
Revises: d869f2f395fa
Create Date: 2025-01-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '011_add_podcast_perf'
down_revision = 'd869f2f395fa'
branch_labels = None
depends_on = None


def upgrade():
    """Add performance indexes for podcast queries"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get existing indexes on media table
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('media')]
    
    # Index for podcast media type filtering (most common query)
    if 'idx_media_type_podcast' not in existing_indexes:
        op.create_index(
            'idx_media_type_podcast',
            'media',
            ['media_type'],
            postgresql_where=sa.text("media_type = 'PODCAST'")
        )
    
    # Composite index for podcast listing with created_at ordering
    if 'idx_media_podcast_created_at' not in existing_indexes:
        op.create_index(
            'idx_media_podcast_created_at',
            'media',
            ['media_type', 'created_at'],
            postgresql_where=sa.text("media_type = 'PODCAST'")
        )
    
    # Index for podcast search by title and description
    if 'idx_media_podcast_title_search' not in existing_indexes:
        op.create_index(
            'idx_media_podcast_title_search',
            'media',
            ['media_type', 'title'],
            postgresql_where=sa.text("media_type = 'PODCAST'")
        )
    
    # Index for podcast search by photographer (host)
    if 'idx_media_podcast_photographer' not in existing_indexes:
        op.create_index(
            'idx_media_podcast_photographer',
            'media',
            ['media_type', 'photographer'],
            postgresql_where=sa.text("media_type = 'PODCAST'")
        )
    
    # Index for podcast search by national_park (show name)
    if 'idx_media_podcast_show' not in existing_indexes:
        op.create_index(
            'idx_media_podcast_show',
            'media',
            ['media_type', 'national_park'],
            postgresql_where=sa.text("media_type = 'PODCAST'")
        )
    
    # Index for featured podcasts
    if 'idx_media_podcast_featured' not in existing_indexes:
        op.create_index(
            'idx_media_podcast_featured',
            'media',
            ['media_type', 'is_featured'],
            postgresql_where=sa.text("media_type = 'PODCAST' AND is_featured > 0")
        )
    
    # Index for podcast duration filtering
    if 'idx_media_podcast_duration' not in existing_indexes:
        op.create_index(
            'idx_media_podcast_duration',
            'media',
            ['media_type', 'duration'],
            postgresql_where=sa.text("media_type = 'PODCAST' AND duration IS NOT NULL")
        )
    
    # Composite index for podcast category filtering
    if 'idx_media_podcast_content_id' not in existing_indexes:
        op.create_index(
            'idx_media_podcast_content_id',
            'media',
            ['media_type', 'content_id'],
            postgresql_where=sa.text("media_type = 'PODCAST' AND content_id IS NOT NULL")
        )
    
    # GIN index for full-text search on podcast content
    if 'idx_media_podcast_fulltext_search' not in existing_indexes:
        op.execute("""
            CREATE INDEX idx_media_podcast_fulltext_search 
            ON media USING gin(
                to_tsvector('english', 
                    COALESCE(title, '') || ' ' || 
                    COALESCE(description, '') || ' ' || 
                    COALESCE(photographer, '') || ' ' || 
                    COALESCE(national_park, '')
                )
            ) 
            WHERE media_type = 'PODCAST'
        """)
    
    # GIN index for podcast file metadata JSON queries (on file_metadata column)
    # Note: file_metadata is json type, not jsonb, so we use standard GIN index
    if 'idx_media_podcast_metadata' not in existing_indexes:
        # Check column type first
        columns = inspector.get_columns('media')
        file_metadata_col = next((col for col in columns if col['name'] == 'file_metadata'), None)
        
        if file_metadata_col and file_metadata_col['type'].__class__.__name__.lower() in ('json', 'jsonb'):
            # For JSON type, we can't use jsonb_path_ops, just use regular GIN
            op.execute("""
                CREATE INDEX idx_media_podcast_metadata 
                ON media USING gin((file_metadata::jsonb))
                WHERE media_type = 'PODCAST' AND file_metadata IS NOT NULL
            """)


def downgrade():
    """Remove performance indexes for podcast queries"""
    
    # Drop all the indexes we created
    op.drop_index('idx_media_podcast_metadata', table_name='media')
    op.execute("DROP INDEX IF EXISTS idx_media_podcast_fulltext_search")
    op.drop_index('idx_media_podcast_content_id', table_name='media')
    op.drop_index('idx_media_podcast_duration', table_name='media')
    op.drop_index('idx_media_podcast_featured', table_name='media')
    op.drop_index('idx_media_podcast_show', table_name='media')
    op.drop_index('idx_media_podcast_photographer', table_name='media')
    op.drop_index('idx_media_podcast_title_search', table_name='media')
    op.drop_index('idx_media_podcast_created_at', table_name='media')
    op.drop_index('idx_media_type_podcast', table_name='media')
    