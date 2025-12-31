"""merge migration heads

Revision ID: 036276795a10
Revises: 014_add_notifications, bridge_4f268_036276  
Create Date: 2025-12-04 14:38:33.690210

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '036276795a10'
down_revision = ('014_add_notifications', 'bridge_4f268_036276')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
