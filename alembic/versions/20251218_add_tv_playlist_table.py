"""add tv_playlist table

Revision ID: 20251218_add_tv_playlist_table
Revises: merge_20251217_complete
Create Date: 2025-12-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20251218_add_tv_playlist_table'
down_revision = 'merge_20251217_complete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tv_playlist',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('video_slug', sa.String(length=200), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    )
    op.create_index('ix_tv_playlist_position', 'tv_playlist', ['position'], unique=True)
    op.create_index('ix_tv_playlist_video_slug', 'tv_playlist', ['video_slug'])


def downgrade() -> None:
    op.drop_index('ix_tv_playlist_video_slug', table_name='tv_playlist')
    op.drop_index('ix_tv_playlist_position', table_name='tv_playlist')
    op.drop_table('tv_playlist')