"""merge_publish_date_and_complete_placeholder

Revision ID: merge_20251217_complete
Revises: 20251217_add_publish_date_fields, complete_all_changes
Create Date: 2025-12-17 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_20251217_complete'
down_revision = ('20251217_add_publish_date_fields', 'complete_all_changes')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass