"""Convert media_type to varchar

Revision ID: 007_media_varchar
Revises: 006_fix_media_table_schema
Create Date: 2025-08-28 20:11:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_media_varchar'
down_revision = '006_fix_media_table_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Convert media_type column from enum to varchar
    op.alter_column('media', 'media_type',
                    existing_type=postgresql.ENUM('IMAGE', 'VIDEO', 'AUDIO', 'PODCAST', 'DOCUMENT', name='mediatypeenum'),
                    type_=sa.VARCHAR(length=50),
                    nullable=False,
                    existing_nullable=False,
                    postgresql_using='media_type::varchar')


def downgrade() -> None:
    # Create enum type if it doesn't exist
    media_type_enum = postgresql.ENUM('IMAGE', 'VIDEO', 'AUDIO', 'PODCAST', 'DOCUMENT', name='mediatypeenum')
    media_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Convert back to enum
    op.alter_column('media', 'media_type',
                    existing_type=sa.VARCHAR(length=50),
                    type_=media_type_enum,
                    nullable=False,
                    existing_nullable=False,
                    postgresql_using='media_type::mediatypeenum')