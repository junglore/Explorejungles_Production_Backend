"""Bridge migration from 4f268e2a07b5 to next step

Revision ID: bridge_4f268_036276
Revises: 4f268e2a07b5
Create Date: 2025-12-19 15:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'bridge_4f268_036276'
down_revision = '4f268e2a07b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No-op bridge to continue migration chain"""
    pass


def downgrade() -> None:
    """No-op bridge"""
    pass
