"""add publish_date fields to videos

Revision ID: 20251217_add_publish_date_fields
Revises: 
Create Date: 2025-12-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251217_add_publish_date_fields'
# Chain to existing head so this becomes part of the main linear history
down_revision = '6f241fca9bda'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add publish_date to series_videos
    op.add_column('series_videos', sa.Column('publish_date', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_series_videos_publish_date', 'series_videos', ['publish_date'])

    # Add publish_date to general_knowledge_videos
    op.add_column('general_knowledge_videos', sa.Column('publish_date', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_gk_videos_publish_date', 'general_knowledge_videos', ['publish_date'])


def downgrade() -> None:
    # Drop indexes and columns added in upgrade
    op.drop_index('ix_gk_videos_publish_date', table_name='general_knowledge_videos')
    op.drop_column('general_knowledge_videos', 'publish_date')

    op.drop_index('ix_series_videos_publish_date', table_name='series_videos')
    op.drop_column('series_videos', 'publish_date')