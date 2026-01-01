"""remove_extra_columns_from_animal_profiles

Revision ID: 89d10e22c218
Revises: 25e79e82002d
Create Date: 2026-01-01 13:08:00.786165

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '89d10e22c218'
down_revision = '25e79e82002d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Remove extra columns from animal_profiles that don't exist in local model"""
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    print("=" * 80)
    print("Removing extra columns from animal_profiles table...")
    print("=" * 80)
    
    if 'animal_profiles' in tables:
        existing_columns = [col['name'] for col in inspector.get_columns('animal_profiles')]
        
        # List of extra columns that should be removed
        extra_columns = [
            'audio_urls',
            'average_lifespan',
            'average_size',
            'average_weight',
            'geographic_range',
            'image_urls',
            'popularity_score',
            'population_trend',
            'reproduction_info',
            'threats',
            'video_urls'
        ]
        
        for column in extra_columns:
            if column in existing_columns:
                op.drop_column('animal_profiles', column)
                print(f"✅ Removed extra column: animal_profiles.{column}")
            else:
                print(f"⏭️  Column already removed: animal_profiles.{column}")
    
    print("=" * 80)
    print("✅ Successfully removed all extra columns from animal_profiles!")
    print("=" * 80)


def downgrade() -> None:
    """Restore the removed columns (if needed for rollback)"""
    op.add_column('animal_profiles', sa.Column('video_urls', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('animal_profiles', sa.Column('threats', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('animal_profiles', sa.Column('reproduction_info', sa.Text(), nullable=True))
    op.add_column('animal_profiles', sa.Column('population_trend', sa.String(100), nullable=True))
    op.add_column('animal_profiles', sa.Column('popularity_score', sa.Float(), nullable=True))
    op.add_column('animal_profiles', sa.Column('image_urls', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('animal_profiles', sa.Column('geographic_range', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('animal_profiles', sa.Column('average_weight', sa.String(100), nullable=True))
    op.add_column('animal_profiles', sa.Column('average_size', sa.String(100), nullable=True))
    op.add_column('animal_profiles', sa.Column('average_lifespan', sa.String(100), nullable=True))
    op.add_column('animal_profiles', sa.Column('audio_urls', postgresql.JSON(astext_type=sa.Text()), nullable=True))
