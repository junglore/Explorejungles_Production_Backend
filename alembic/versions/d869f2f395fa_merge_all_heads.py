"""merge_all_heads

Revision ID: d869f2f395fa
Revises: 004_add_featured_media_support, 010_create_myths_facts_table
Create Date: 2025-08-29 18:42:57.462924

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd869f2f395fa'
down_revision = ('004_add_featured_media_support', '010_create_myths_facts_table')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
