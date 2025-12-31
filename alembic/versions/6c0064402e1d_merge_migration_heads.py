"""merge_migration_heads

Revision ID: 6c0064402e1d
Revises: 4943ae846168, d869f2f395fa
Create Date: 2025-09-04 17:12:45.892131

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6c0064402e1d'
down_revision = ('4943ae846168', 'd869f2f395fa')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
