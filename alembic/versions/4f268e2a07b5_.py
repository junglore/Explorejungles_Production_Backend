"""empty message

Revision ID: 4f268e2a07b5
Revises: 001_add_rewards_system, 011_add_podcast_perf, 012_add_quiz_cover_image, 013_fix_rewards_meta, bc95c2de78e7
Create Date: 2025-10-13 22:33:59.519298

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f268e2a07b5'
down_revision = ('001_add_rewards_system', '011_add_podcast_perf', '012_add_quiz_cover_image', '013_fix_rewards_meta', 'bc95c2de78e7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
