"""merge_heads

Revision ID: 1a1c42044fff
Revises: 003_add_performance_indexes, 007_media_varchar
Create Date: 2025-08-28 20:31:15.818080

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a1c42044fff'
down_revision = ('008_add_performance_indexes', '007_media_varchar')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
