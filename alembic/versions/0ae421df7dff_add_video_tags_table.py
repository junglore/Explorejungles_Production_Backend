"""add_video_tags_table

Revision ID: 0ae421df7dff
Revises: 4c1ea39912b5
Create Date: 2025-12-11 14:11:09.880305

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID
import uuid


# revision identifiers, used by Alembic.
revision = '0ae421df7dff'
down_revision = '4c1ea39912b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Create video_tags table if it doesn't exist
    if 'video_tags' not in existing_tables:
        op.create_table(
            'video_tags',
            sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
            sa.Column('name', sa.String(100), nullable=False, unique=True),
            sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now())
        )
        
        # Create index on name for faster lookups
        op.create_index('ix_video_tags_name', 'video_tags', ['name'])
        
        # Seed with initial predefined tags
        op.execute("""
            INSERT INTO video_tags (id, name, usage_count, created_at) VALUES
            (gen_random_uuid(), 'Wildlife', 0, NOW()),
            (gen_random_uuid(), 'Conservation', 0, NOW()),
            (gen_random_uuid(), 'Endangered Species', 0, NOW()),
            (gen_random_uuid(), 'Habitat', 0, NOW()),
            (gen_random_uuid(), 'Behavior', 0, NOW()),
            (gen_random_uuid(), 'Documentary', 0, NOW()),
            (gen_random_uuid(), 'Education', 0, NOW()),
            (gen_random_uuid(), 'Nature', 0, NOW()),
            (gen_random_uuid(), 'Animals', 0, NOW()),
            (gen_random_uuid(), 'Ecology', 0, NOW()),
            (gen_random_uuid(), 'Birds', 0, NOW()),
            (gen_random_uuid(), 'Mammals', 0, NOW()),
            (gen_random_uuid(), 'Reptiles', 0, NOW()),
            (gen_random_uuid(), 'Marine Life', 0, NOW()),
            (gen_random_uuid(), 'Insects', 0, NOW())
        """)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'video_tags' in existing_tables:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('video_tags')]
        if 'ix_video_tags_name' in existing_indexes:
            op.drop_index('ix_video_tags_name', 'video_tags')
        op.drop_table('video_tags')
