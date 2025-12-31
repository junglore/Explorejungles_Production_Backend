("""Placeholder revision to satisfy Alembic parser

This file previously contained no revision metadata which caused
`alembic upgrade head` to fail. Adding a minimal revision header
and empty upgrade/downgrade functions so Alembic can continue.
""")

from alembic import op

# revision identifiers, used by Alembic.
revision = 'complete_all_changes'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	# no-op placeholder
	pass


def downgrade() -> None:
	# no-op placeholder
	pass