"""merge_tv_playlist_and_missing_tables

Revision ID: 09cb61ce9c6c
Revises: 7d465c836d64, 20251218_add_tv_playlist_table
Create Date: 2025-12-22 12:13:01.104030

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '09cb61ce9c6c'
down_revision = ('7d465c836d64', '20251218_add_tv_playlist_table')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
