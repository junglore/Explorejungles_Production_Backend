"""add_missing_columns_to_production

Revision ID: 25e79e82002d
Revises: 46f0290bbb6f
Create Date: 2026-01-01 12:49:35.828860

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '25e79e82002d'
down_revision = '46f0290bbb6f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns to production tables"""
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = inspector.get_table_names()
    
    print("=" * 80)
    print("Adding missing columns to production tables...")
    print("=" * 80)
    
    # 1. Add missing columns to animal_profiles table
    if 'animal_profiles' in tables:
        existing_columns = [col['name'] for col in inspector.get_columns('animal_profiles')]
        
        if 'average_height_cm' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('average_height_cm', sa.Float(), nullable=True))
            print("✅ Added column: animal_profiles.average_height_cm")
        
        if 'average_length_cm' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('average_length_cm', sa.Float(), nullable=True))
            print("✅ Added column: animal_profiles.average_length_cm")
        
        if 'average_weight_kg' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('average_weight_kg', sa.Float(), nullable=True))
            print("✅ Added column: animal_profiles.average_weight_kg")
        
        if 'lifespan_years' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('lifespan_years', sa.Integer(), nullable=True))
            print("✅ Added column: animal_profiles.lifespan_years")
        
        if 'geographic_distribution' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('geographic_distribution', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'))
            print("✅ Added column: animal_profiles.geographic_distribution")
        
        if 'habitat_description' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('habitat_description', sa.Text(), nullable=True))
            print("✅ Added column: animal_profiles.habitat_description")
        
        if 'population_estimate' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('population_estimate', sa.String(255), nullable=True))
            print("✅ Added column: animal_profiles.population_estimate")
        
        if 'conservation_threats' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('conservation_threats', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'))
            print("✅ Added column: animal_profiles.conservation_threats")
        
        if 'profile_image_url' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('profile_image_url', sa.String(500), nullable=True))
            print("✅ Added column: animal_profiles.profile_image_url")
        
        if 'gallery_images' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('gallery_images', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'))
            print("✅ Added column: animal_profiles.gallery_images")
        
        if 'featured_video_url' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('featured_video_url', sa.String(500), nullable=True))
            print("✅ Added column: animal_profiles.featured_video_url")
        
        if 'cultural_significance' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('cultural_significance', sa.Text(), nullable=True))
            print("✅ Added column: animal_profiles.cultural_significance")
        
        if 'profile_metadata' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('profile_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'))
            print("✅ Added column: animal_profiles.profile_metadata")
        
        if 'is_active' not in existing_columns:
            op.add_column('animal_profiles', sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'))
            print("✅ Added column: animal_profiles.is_active")
    
    # 2. Add missing columns to categories table
    if 'categories' in tables:
        existing_columns = [col['name'] for col in inspector.get_columns('categories')]
        
        if 'custom_credits' not in existing_columns:
            op.add_column('categories', sa.Column('custom_credits', sa.Integer(), nullable=True))
            print("✅ Added column: categories.custom_credits")
        
        if 'is_featured' not in existing_columns:
            op.add_column('categories', sa.Column('is_featured', sa.Boolean(), nullable=False, server_default='false'))
            print("✅ Added column: categories.is_featured")
        
        if 'mvf_enabled' not in existing_columns:
            op.add_column('categories', sa.Column('mvf_enabled', sa.Boolean(), nullable=False, server_default='true'))
            print("✅ Added column: categories.mvf_enabled")
    
    # 3. Add missing column to general_knowledge_videos table
    if 'general_knowledge_videos' in tables:
        existing_columns = [col['name'] for col in inspector.get_columns('general_knowledge_videos')]
        
        if 'publish_date' not in existing_columns:
            op.add_column('general_knowledge_videos', sa.Column('publish_date', sa.DateTime(timezone=True), nullable=True))
            print("✅ Added column: general_knowledge_videos.publish_date")
    
    # 4. Add missing column to myths_facts table
    if 'myths_facts' in tables:
        existing_columns = [col['name'] for col in inspector.get_columns('myths_facts')]
        
        if 'custom_points' not in existing_columns:
            op.add_column('myths_facts', sa.Column('custom_points', sa.Integer(), nullable=True))
            print("✅ Added column: myths_facts.custom_points")
    
    # 5. Add missing columns to user_recommendations table
    if 'user_recommendations' in tables:
        existing_columns = [col['name'] for col in inspector.get_columns('user_recommendations')]
        
        if 'recommendation_reason' not in existing_columns:
            op.add_column('user_recommendations', sa.Column('recommendation_reason', sa.Text(), nullable=True))
            print("✅ Added column: user_recommendations.recommendation_reason")
        
        if 'recommendation_metadata' not in existing_columns:
            op.add_column('user_recommendations', sa.Column('recommendation_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'))
            print("✅ Added column: user_recommendations.recommendation_metadata")
        
        if 'is_viewed' not in existing_columns:
            op.add_column('user_recommendations', sa.Column('is_viewed', sa.Boolean(), nullable=False, server_default='false'))
            print("✅ Added column: user_recommendations.is_viewed")
        
        if 'viewed_at' not in existing_columns:
            op.add_column('user_recommendations', sa.Column('viewed_at', sa.DateTime(timezone=True), nullable=True))
            print("✅ Added column: user_recommendations.viewed_at")
    
    print("=" * 80)
    print("✅ Successfully added all missing columns to production tables!")
    print("=" * 80)


def downgrade() -> None:
    """Remove added columns (rollback)"""
    # Animal profiles columns
    op.drop_column('animal_profiles', 'is_active')
    op.drop_column('animal_profiles', 'profile_metadata')
    op.drop_column('animal_profiles', 'cultural_significance')
    op.drop_column('animal_profiles', 'featured_video_url')
    op.drop_column('animal_profiles', 'gallery_images')
    op.drop_column('animal_profiles', 'profile_image_url')
    op.drop_column('animal_profiles', 'conservation_threats')
    op.drop_column('animal_profiles', 'population_estimate')
    op.drop_column('animal_profiles', 'habitat_description')
    op.drop_column('animal_profiles', 'geographic_distribution')
    op.drop_column('animal_profiles', 'lifespan_years')
    op.drop_column('animal_profiles', 'average_weight_kg')
    op.drop_column('animal_profiles', 'average_length_cm')
    op.drop_column('animal_profiles', 'average_height_cm')
    
    # Categories columns
    op.drop_column('categories', 'mvf_enabled')
    op.drop_column('categories', 'is_featured')
    op.drop_column('categories', 'custom_credits')
    
    # General knowledge videos column
    op.drop_column('general_knowledge_videos', 'publish_date')
    
    # Myths facts column
    op.drop_column('myths_facts', 'custom_points')
    
    # User recommendations columns
    op.drop_column('user_recommendations', 'viewed_at')
    op.drop_column('user_recommendations', 'is_viewed')
    op.drop_column('user_recommendations', 'recommendation_metadata')
    op.drop_column('user_recommendations', 'recommendation_reason')
