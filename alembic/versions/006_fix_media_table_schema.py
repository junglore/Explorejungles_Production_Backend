"""Fix media table schema

Revision ID: 006_fix_media_table_schema
Revises: 005_create_enum_types
Create Date: 2025-08-28 19:59:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_fix_media_table_schema'
down_revision = '005_create_enum_types'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'media' not in tables:
        print("⚠️  Skipping: media table does not exist yet")
        return
    
    # Create media_type enum if it doesn't exist
    media_type_enum = postgresql.ENUM('IMAGE', 'VIDEO', 'AUDIO', 'PODCAST', 'DOCUMENT', name='mediatypeenum')
    media_type_enum.create(conn, checkfirst=True)
    
    # Update existing NULL media_type values to 'IMAGE' as default
    op.execute("UPDATE media SET media_type = 'IMAGE' WHERE media_type IS NULL")
    
    # Make media_type column non-nullable and add enum constraint
    op.alter_column('media', 'media_type',
                    existing_type=sa.VARCHAR(length=50),
                    type_=media_type_enum,
                    nullable=False,
                    existing_nullable=True,
                    existing_server_default=None,
                    postgresql_using='media_type::mediatypeenum')
    
    # Add index for media_type if it doesn't exist
    try:
        op.create_index('ix_media_type', 'media', ['media_type'])
    except Exception:
        # Index might already exist
        pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    if 'media' not in tables:
        return
    
    # Remove the index
    try:
        op.drop_index('ix_media_type', table_name='media')
    except Exception:
        pass
    
    # Revert media_type column back to varchar and nullable
    op.alter_column('media', 'media_type',
                    existing_type=postgresql.ENUM('IMAGE', 'VIDEO', 'AUDIO', 'PODCAST', 'DOCUMENT', name='mediatypeenum'),
                    type_=sa.VARCHAR(length=50),
                    nullable=True,
                    existing_nullable=False,
                    postgresql_using='media_type::varchar')
    
    # Drop the enum type
    media_type_enum = postgresql.ENUM('IMAGE', 'VIDEO', 'AUDIO', 'PODCAST', 'DOCUMENT', name='mediatypeenum')
    media_type_enum.drop(op.get_bind(), checkfirst=True)