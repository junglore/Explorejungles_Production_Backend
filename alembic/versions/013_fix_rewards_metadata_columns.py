"""fix rewards metadata column names

Revision ID: 013_fix_rewards_meta
Revises: d869f2f395fa
Create Date: 2025-09-22 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '013_fix_rewards_meta'
down_revision = 'd869f2f395fa'  # Latest migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Fix SQLAlchemy reserved attribute name conflicts"""
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Check and rename metadata column to transaction_metadata in user_currency_transactions
    if 'user_currency_transactions' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('user_currency_transactions')]
        if 'metadata' in columns and 'transaction_metadata' not in columns:
            op.alter_column(
                'user_currency_transactions', 
                'metadata',
                new_column_name='transaction_metadata',
                existing_type=sa.JSON(),
                existing_nullable=True
            )
    
    # Check and rename metadata column to achievement_metadata in user_achievements
    if 'user_achievements' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('user_achievements')]
        if 'metadata' in columns and 'achievement_metadata' not in columns:
            op.alter_column(
                'user_achievements',
                'metadata', 
                new_column_name='achievement_metadata',
                existing_type=sa.JSON(),
                existing_nullable=True
            )


def downgrade() -> None:
    """Revert column name changes"""
    
    # Rename back to metadata in user_achievements
    op.alter_column(
        'user_achievements',
        'achievement_metadata',
        new_column_name='metadata', 
        existing_type=sa.JSON(),
        existing_nullable=True
    )
    
    # Rename back to metadata in user_currency_transactions
    op.alter_column(
        'user_currency_transactions',
        'transaction_metadata',
        new_column_name='metadata',
        existing_type=sa.JSON(),
        existing_nullable=True
    )