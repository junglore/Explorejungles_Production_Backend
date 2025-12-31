"""Add cover_image column to quizzes table

Revision ID: 012_add_quiz_cover_image
Revises: d869f2f395fa
Create Date: 2025-01-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_add_quiz_cover_image'
down_revision: Union[str, None] = 'd869f2f395fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cover_image column to quizzes table"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('quizzes')]
    
    if 'cover_image' not in columns:
        # Add cover_image column to quizzes table
        op.add_column('quizzes', sa.Column('cover_image', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove cover_image column from quizzes table"""
    
    # Remove cover_image column from quizzes table
    op.drop_column('quizzes', 'cover_image')