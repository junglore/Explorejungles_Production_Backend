"""Add OAuth fields to users table

Revision ID: 010_add_oauth_fields
Revises: 009_make_category_slug_required
Create Date: 2025-10-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '010_add_oauth_fields'
down_revision = '009_make_category_slug_required'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add OAuth provider ID fields to users table"""
    
    # Check existing columns and constraints
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'users' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
        existing_constraints = [c['name'] for c in inspector.get_unique_constraints('users')]
        
        # Add OAuth columns only if they don't exist
        if 'google_id' not in existing_columns:
            op.add_column('users', sa.Column('google_id', sa.String(255), nullable=True))
        if 'facebook_id' not in existing_columns:
            op.add_column('users', sa.Column('facebook_id', sa.String(255), nullable=True))
        if 'linkedin_id' not in existing_columns:
            op.add_column('users', sa.Column('linkedin_id', sa.String(255), nullable=True))
        
        # Create unique constraints only if they don't exist
        if 'uq_users_google_id' not in existing_constraints:
            op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
        if 'uq_users_facebook_id' not in existing_constraints:
            op.create_unique_constraint('uq_users_facebook_id', 'users', ['facebook_id'])
        if 'uq_users_linkedin_id' not in existing_constraints:
            op.create_unique_constraint('uq_users_linkedin_id', 'users', ['linkedin_id'])
        
        # Create indexes only if they don't exist
        if 'ix_users_google_id' not in existing_indexes:
            op.create_index('ix_users_google_id', 'users', ['google_id'])
        if 'ix_users_facebook_id' not in existing_indexes:
            op.create_index('ix_users_facebook_id', 'users', ['facebook_id'])
        if 'ix_users_linkedin_id' not in existing_indexes:
            op.create_index('ix_users_linkedin_id', 'users', ['linkedin_id'])


def downgrade() -> None:
    """Remove OAuth fields from users table"""
    
    # Check what exists before dropping
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'users' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('users')]
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
        existing_constraints = [c['name'] for c in inspector.get_unique_constraints('users')]
        
        # Drop indexes if they exist
        if 'ix_users_linkedin_id' in existing_indexes:
            op.drop_index('ix_users_linkedin_id', table_name='users')
        if 'ix_users_facebook_id' in existing_indexes:
            op.drop_index('ix_users_facebook_id', table_name='users')
        if 'ix_users_google_id' in existing_indexes:
            op.drop_index('ix_users_google_id', table_name='users')
        
        # Drop unique constraints if they exist
        if 'uq_users_linkedin_id' in existing_constraints:
            op.drop_constraint('uq_users_linkedin_id', 'users', type_='unique')
        if 'uq_users_facebook_id' in existing_constraints:
            op.drop_constraint('uq_users_facebook_id', 'users', type_='unique')
        if 'uq_users_google_id' in existing_constraints:
            op.drop_constraint('uq_users_google_id', 'users', type_='unique')
        
        # Drop columns if they exist
        if 'linkedin_id' in existing_columns:
            op.drop_column('users', 'linkedin_id')
        if 'facebook_id' in existing_columns:
            op.drop_column('users', 'facebook_id')
        if 'google_id' in existing_columns:
            op.drop_column('users', 'google_id')