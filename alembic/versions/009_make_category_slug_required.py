"""Make category slug column required

Revision ID: 009_make_category_slug_required
Revises: 003_add_category_slug
Create Date: 2025-01-28 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_make_category_slug_required'
down_revision = '003_add_category_slug'
branch_labels = None
depends_on = None


def upgrade():
    """Make category slug column required"""
    
    # Make slug column NOT NULL
    op.alter_column('categories', 'slug', nullable=False)


def downgrade():
    """Make category slug column optional"""
    
    # Make slug column nullable
    op.alter_column('categories', 'slug', nullable=True)