"""Create enum types for content table

Revision ID: 005_create_enum_types
Revises: 004_make_category_slug_required
Create Date: 2025-01-28 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '005_create_enum_types'
down_revision = '009_make_category_slug_required'
branch_labels = None
depends_on = None


def upgrade():
    """Create enum types and update content table columns"""
    
    # Create enum types
    content_type_enum = postgresql.ENUM(
        'BLOG', 'CASE_STUDY', 'DAILY_UPDATE', 'CONSERVATION_EFFORT', 'NEWS', 'ARTICLE',
        name='contenttypeenum'
    )
    content_type_enum.create(op.get_bind())
    
    content_status_enum = postgresql.ENUM(
        'DRAFT', 'PUBLISHED', 'ARCHIVED',
        name='contentstatusenum'
    )
    content_status_enum.create(op.get_bind())
    
    # Remove default constraints first
    op.alter_column('content', 'status', server_default=None)
    
    # Update content table columns to use enum types
    op.alter_column('content', 'type',
                    type_=content_type_enum,
                    postgresql_using='type::contenttypeenum')
    
    op.alter_column('content', 'status',
                    type_=content_status_enum,
                    postgresql_using='status::contentstatusenum')
    
    # Add back the default constraint with proper enum value
    op.alter_column('content', 'status', server_default='DRAFT')


def downgrade():
    """Revert enum types back to varchar"""
    
    # Revert columns back to varchar
    op.alter_column('content', 'type',
                    type_=sa.String(length=50),
                    postgresql_using='type::varchar')
    
    op.alter_column('content', 'status',
                    type_=sa.String(length=20),
                    postgresql_using='status::varchar')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS contenttypeenum')
    op.execute('DROP TYPE IF EXISTS contentstatusenum')