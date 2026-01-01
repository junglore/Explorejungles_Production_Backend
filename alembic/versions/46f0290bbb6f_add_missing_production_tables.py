"""add_missing_production_tables

Revision ID: 46f0290bbb6f
Revises: 09cb61ce9c6c
Create Date: 2026-01-01 12:02:22.378814

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '46f0290bbb6f'
down_revision = '09cb61ce9c6c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add 16 missing production tables that exist in local but not in Railway"""
    
    # Get connection and inspector
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # 1. Conservation Efforts Table
    if 'conservation_efforts' not in existing_tables:
        print("Creating conservation_efforts table...")
        op.create_table(
            'conservation_efforts',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('description', sa.Text(), nullable=False),
            sa.Column('location', sa.String(255), nullable=True),
            sa.Column('organization', sa.String(255), nullable=True),
            sa.Column('image_url', sa.String(500), nullable=True),
            sa.Column('impact_metrics', sa.JSON(), server_default='{}'),
            sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
        )
    
    # 2. Site Settings Table
    if 'site_settings' not in existing_tables:
        print("Creating site_settings table...")
        op.create_table(
            'site_settings',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('key', sa.String(100), nullable=False, unique=True, index=True),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('data_type', sa.String(20), nullable=False),
            sa.Column('category', sa.String(50), nullable=False, server_default='general'),
            sa.Column('label', sa.String(200), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_public', sa.Boolean(), server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now())
        )
    
    # 3. Chatbot Conversations Table
    if 'chatbot_conversations' not in existing_tables:
        print("Creating chatbot_conversations table...")
        op.create_table(
            'chatbot_conversations',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('messages', sa.JSON(), server_default='[]'),
            sa.Column('conversation_metadata', sa.JSON(), server_default='{}'),
            sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.func.now())
        )
    
    # 4. Create ENUMs for livestreams
    stream_status_enum = ENUM('scheduled', 'live', 'ended', 'cancelled', name='streamstatusenum', create_type=False)
    if 'streamstatusenum' not in [t['name'] for t in inspector.get_enums()]:
        stream_status_enum.create(conn, checkfirst=True)
    
    # 5. LiveStreams Table
    if 'livestreams' not in existing_tables:
        print("Creating livestreams table...")
        op.create_table(
            'livestreams',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('host_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('stream_url', sa.String(500), nullable=True),
            sa.Column('thumbnail_url', sa.String(500), nullable=True),
            sa.Column('status', stream_status_enum, server_default='scheduled'),
            sa.Column('is_live', sa.Boolean(), server_default='false'),
            sa.Column('viewer_count', sa.Integer(), server_default='0'),
            sa.Column('tags', sa.JSON(), server_default='[]'),
            sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now())
        )
    
    # 6. Create ENUMs for animal profiles
    conservation_status_enum = ENUM(
        'least_concern', 'near_threatened', 'vulnerable', 'endangered', 
        'critically_endangered', 'extinct_in_wild', 'extinct', 'data_deficient',
        name='conservationstatusenum', create_type=False
    )
    habitat_type_enum = ENUM(
        'forest', 'grassland', 'desert', 'wetland', 'marine', 
        'freshwater', 'mountain', 'arctic', 'urban',
        name='habitattypeenum', create_type=False
    )
    
    existing_enums = [t['name'] for t in inspector.get_enums()]
    if 'conservationstatusenum' not in existing_enums:
        conservation_status_enum.create(conn, checkfirst=True)
    if 'habitattypeenum' not in existing_enums:
        habitat_type_enum.create(conn, checkfirst=True)
    
    # 7. Animal Profiles Table
    if 'animal_profiles' not in existing_tables:
        print("Creating animal_profiles table...")
        op.create_table(
            'animal_profiles',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
            sa.Column('common_name', sa.String(255), nullable=False, index=True),
            sa.Column('scientific_name', sa.String(255), nullable=False, index=True),
            sa.Column('other_names', sa.JSON(), server_default='[]'),
            sa.Column('kingdom', sa.String(100), server_default='Animalia'),
            sa.Column('phylum', sa.String(100), nullable=True),
            sa.Column('class_name', sa.String(100), nullable=True),
            sa.Column('order', sa.String(100), nullable=True),
            sa.Column('family', sa.String(100), nullable=True),
            sa.Column('genus', sa.String(100), nullable=True),
            sa.Column('species', sa.String(100), nullable=True),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('physical_description', sa.Text(), nullable=True),
            sa.Column('average_lifespan', sa.String(100), nullable=True),
            sa.Column('average_size', sa.String(200), nullable=True),
            sa.Column('average_weight', sa.String(200), nullable=True),
            sa.Column('diet_type', sa.String(100), nullable=True),
            sa.Column('diet_description', sa.Text(), nullable=True),
            sa.Column('habitat_types', sa.JSON(), server_default='[]'),
            sa.Column('geographic_range', sa.Text(), nullable=True),
            sa.Column('conservation_status', conservation_status_enum, nullable=True),
            sa.Column('population_trend', sa.String(50), nullable=True),
            sa.Column('threats', sa.JSON(), server_default='[]'),
            sa.Column('conservation_efforts', sa.Text(), nullable=True),
            sa.Column('behavior_description', sa.Text(), nullable=True),
            sa.Column('social_structure', sa.String(100), nullable=True),
            sa.Column('reproduction_info', sa.Text(), nullable=True),
            sa.Column('fun_facts', sa.JSON(), server_default='[]'),
            sa.Column('image_urls', sa.JSON(), server_default='[]'),
            sa.Column('video_urls', sa.JSON(), server_default='[]'),
            sa.Column('audio_urls', sa.JSON(), server_default='[]'),
            sa.Column('is_featured', sa.Boolean(), server_default='false'),
            sa.Column('view_count', sa.Integer(), server_default='0'),
            sa.Column('popularity_score', sa.Float(), server_default='0.0'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now())
        )
    
    # 8. User Animal Interactions Table
    if 'user_animal_interactions' not in existing_tables:
        print("Creating user_animal_interactions table...")
        op.create_table(
            'user_animal_interactions',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('animal_profile_id', UUID(as_uuid=True), sa.ForeignKey('animal_profiles.id', ondelete='CASCADE'), nullable=False),
            sa.Column('is_favorite', sa.Boolean(), server_default='false'),
            sa.Column('has_viewed', sa.Boolean(), server_default='true'),
            sa.Column('view_count', sa.Integer(), server_default='1'),
            sa.Column('first_viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('last_viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('favorited_at', sa.DateTime(timezone=True), nullable=True)
        )
    
    # 9. Animal Sightings Table
    if 'animal_sightings' not in existing_tables:
        print("Creating animal_sightings table...")
        op.create_table(
            'animal_sightings',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('animal_profile_id', UUID(as_uuid=True), sa.ForeignKey('animal_profiles.id', ondelete='SET NULL'), nullable=True),
            sa.Column('title', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('location_name', sa.String(255), nullable=True),
            sa.Column('latitude', sa.Float(), nullable=True),
            sa.Column('longitude', sa.Float(), nullable=True),
            sa.Column('country', sa.String(100), nullable=True),
            sa.Column('sighting_date', sa.DateTime(timezone=True), nullable=False),
            sa.Column('photo_urls', sa.JSON(), server_default='[]'),
            sa.Column('is_verified', sa.Boolean(), server_default='false'),
            sa.Column('verification_notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now())
        )
    
    # 10. Myth Fact Collections Table
    if 'myth_fact_collections' not in existing_tables:
        print("Creating myth_fact_collections table...")
        op.create_table(
            'myth_fact_collections',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='SET NULL'), nullable=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true'),
            sa.Column('cards_count', sa.Integer(), server_default='0'),
            sa.Column('repeatability', sa.String(20), server_default='unlimited'),
            sa.Column('custom_points_enabled', sa.Boolean(), server_default='false'),
            sa.Column('custom_points_bronze', sa.Integer(), nullable=True),
            sa.Column('custom_points_silver', sa.Integer(), nullable=True),
            sa.Column('custom_points_gold', sa.Integer(), nullable=True),
            sa.Column('custom_points_platinum', sa.Integer(), nullable=True),
            sa.Column('custom_credits_enabled', sa.Boolean(), server_default='false'),
            sa.Column('custom_credits_bronze', sa.Integer(), nullable=True),
            sa.Column('custom_credits_silver', sa.Integer(), nullable=True),
            sa.Column('custom_credits_gold', sa.Integer(), nullable=True),
            sa.Column('custom_credits_platinum', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
        )
    
    # 11. Collection Myth Facts Junction Table
    if 'collection_myth_facts' not in existing_tables:
        print("Creating collection_myth_facts table...")
        op.create_table(
            'collection_myth_facts',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('myth_fact_collections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('myth_fact_id', UUID(as_uuid=True), sa.ForeignKey('myths_facts.id', ondelete='CASCADE'), nullable=False),
            sa.Column('order_index', sa.Integer(), server_default='0', nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint('collection_id', 'myth_fact_id', name='uq_collection_myth_fact'),
            sa.UniqueConstraint('collection_id', 'order_index', name='uq_collection_order')
        )
    
    # 12. User Collection Progress Table
    if 'user_collection_progress' not in existing_tables:
        print("Creating user_collection_progress table...")
        op.create_table(
            'user_collection_progress',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('collection_id', UUID(as_uuid=True), sa.ForeignKey('myth_fact_collections.id', ondelete='CASCADE'), nullable=False),
            sa.Column('play_date', sa.Date(), nullable=False, server_default=sa.func.current_date()),
            sa.Column('completed', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('score_percentage', sa.Integer(), server_default='0', nullable=False),
            sa.Column('time_taken', sa.Integer(), nullable=True),
            sa.Column('answers_correct', sa.Integer(), server_default='0', nullable=False),
            sa.Column('total_questions', sa.Integer(), server_default='0', nullable=False),
            sa.Column('points_earned', sa.Integer(), server_default='0', nullable=False),
            sa.Column('credits_earned', sa.Integer(), server_default='0', nullable=False),
            sa.Column('tier', sa.String(20), nullable=True),
            sa.Column('bonus_applied', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('game_session_id', UUID(as_uuid=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint('user_id', 'collection_id', 'play_date', name='uq_user_collection_daily'),
            sa.CheckConstraint('score_percentage >= 0 AND score_percentage <= 100', name='valid_score_percentage'),
            sa.CheckConstraint('answers_correct >= 0 AND answers_correct <= total_questions', name='valid_answers')
        )
    
    # 13. User Quiz Best Scores Table
    if 'user_quiz_best_scores' not in existing_tables:
        print("Creating user_quiz_best_scores table...")
        op.create_table(
            'user_quiz_best_scores',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('quiz_id', UUID(as_uuid=True), sa.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('best_score', sa.Integer(), nullable=False),
            sa.Column('best_percentage', sa.Integer(), nullable=False),
            sa.Column('best_time', sa.Integer(), nullable=True),
            sa.Column('credits_earned', sa.Integer(), server_default='0'),
            sa.Column('points_earned', sa.Integer(), server_default='0'),
            sa.Column('reward_tier', sa.String(50), nullable=True),
            sa.Column('achieved_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz_best')
        )
        op.create_index('idx_user_quiz_best_user_id', 'user_quiz_best_scores', ['user_id'])
        op.create_index('idx_user_quiz_best_quiz_id', 'user_quiz_best_scores', ['quiz_id'])
        op.create_index('idx_user_quiz_best_percentage', 'user_quiz_best_scores', ['best_percentage'])
        op.create_index('idx_user_quiz_best_achieved_at', 'user_quiz_best_scores', ['achieved_at'])
    
    # 14. Create ENUMs for recommendations
    recommendation_type_enum = ENUM(
        'content', 'animal_profile', 'category', 'livestream', 'quiz', 'media',
        name='recommendationtypeenum', create_type=False
    )
    recommendation_source_enum = ENUM(
        'collaborative_filtering', 'content_based', 'popular', 'trending', 
        'recent', 'category_based', 'admin_featured',
        name='recommendationsourceenum', create_type=False
    )
    
    existing_enums = [t['name'] for t in inspector.get_enums()]
    if 'recommendationtypeenum' not in existing_enums:
        recommendation_type_enum.create(conn, checkfirst=True)
    if 'recommendationsourceenum' not in existing_enums:
        recommendation_source_enum.create(conn, checkfirst=True)
    
    # 15. User Recommendations Table
    if 'user_recommendations' not in existing_tables:
        print("Creating user_recommendations table...")
        op.create_table(
            'user_recommendations',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('recommendation_type', recommendation_type_enum, nullable=False),
            sa.Column('item_id', UUID(as_uuid=True), nullable=False),
            sa.Column('source', recommendation_source_enum, nullable=False),
            sa.Column('relevance_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.0'),
            sa.Column('is_clicked', sa.Boolean(), server_default='false'),
            sa.Column('is_dismissed', sa.Boolean(), server_default='false'),
            sa.Column('clicked_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True)
        )
    
    # 16. User Preferences Table
    if 'user_preferences' not in existing_tables:
        print("Creating user_preferences table...")
        op.create_table(
            'user_preferences',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
            sa.Column('favorite_categories', sa.JSON(), server_default='[]'),
            sa.Column('favorite_animals', sa.JSON(), server_default='[]'),
            sa.Column('preferred_content_types', sa.JSON(), server_default='[]'),
            sa.Column('avg_session_duration', sa.Integer(), nullable=True),
            sa.Column('preferred_time_of_day', sa.Integer(), nullable=True),
            sa.Column('most_active_day', sa.Integer(), nullable=True),
            sa.Column('total_content_views', sa.Integer(), server_default='0'),
            sa.Column('total_quiz_attempts', sa.Integer(), server_default='0'),
            sa.Column('total_livestream_views', sa.Integer(), server_default='0'),
            sa.Column('wildlife_interest_score', sa.Float(), server_default='0.5'),
            sa.Column('conservation_interest_score', sa.Float(), server_default='0.5'),
            sa.Column('education_interest_score', sa.Float(), server_default='0.5'),
            sa.Column('entertainment_interest_score', sa.Float(), server_default='0.5'),
            sa.Column('preference_metadata', sa.JSON(), server_default='{}'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now())
        )
    
    # 17. Viewing History Table
    if 'viewing_history' not in existing_tables:
        print("Creating viewing_history table...")
        op.create_table(
            'viewing_history',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('item_type', sa.String(50), nullable=False),
            sa.Column('item_id', UUID(as_uuid=True), nullable=False),
            sa.Column('view_duration', sa.Integer(), nullable=True),
            sa.Column('completion_percentage', sa.Float(), nullable=True),
            sa.Column('interaction_score', sa.Float(), server_default='0.0'),
            sa.Column('referrer_type', sa.String(50), nullable=True),
            sa.Column('referrer_id', UUID(as_uuid=True), nullable=True),
            sa.Column('device_type', sa.String(50), nullable=True),
            sa.Column('viewed_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('session_start', sa.DateTime(timezone=True), nullable=True),
            sa.Column('session_end', sa.DateTime(timezone=True), nullable=True)
        )
    
    # 18. Trending Items Table
    if 'trending_items' not in existing_tables:
        print("Creating trending_items table...")
        op.create_table(
            'trending_items',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('item_type', sa.String(50), nullable=False),
            sa.Column('item_id', UUID(as_uuid=True), nullable=False),
            sa.Column('view_count_24h', sa.Integer(), server_default='0'),
            sa.Column('view_count_7d', sa.Integer(), server_default='0'),
            sa.Column('view_count_30d', sa.Integer(), server_default='0'),
            sa.Column('unique_viewers_24h', sa.Integer(), server_default='0'),
            sa.Column('unique_viewers_7d', sa.Integer(), server_default='0'),
            sa.Column('unique_viewers_30d', sa.Integer(), server_default='0'),
            sa.Column('engagement_score_24h', sa.Float(), server_default='0.0'),
            sa.Column('engagement_score_7d', sa.Float(), server_default='0.0'),
            sa.Column('engagement_score_30d', sa.Float(), server_default='0.0'),
            sa.Column('trending_score', sa.Float(), server_default='0.0'),
            sa.Column('velocity_score', sa.Float(), server_default='0.0'),
            sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column('trending_since', sa.DateTime(timezone=True), nullable=True)
        )
    
    # 19. Weekly Leaderboard Cache Table
    if 'weekly_leaderboard_cache' not in existing_tables:
        print("Creating weekly_leaderboard_cache table...")
        op.create_table(
            'weekly_leaderboard_cache',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('week_start_date', sa.Date(), nullable=False),
            sa.Column('week_end_date', sa.Date(), nullable=False),
            sa.Column('week_number', sa.Integer(), nullable=False),
            sa.Column('year', sa.Integer(), nullable=False),
            sa.Column('total_credits_earned', sa.Integer(), server_default='0'),
            sa.Column('total_points_earned', sa.Integer(), server_default='0'),
            sa.Column('quizzes_completed', sa.Integer(), server_default='0'),
            sa.Column('perfect_scores', sa.Integer(), server_default='0'),
            sa.Column('average_percentage', sa.Integer(), server_default='0'),
            sa.Column('credits_rank', sa.Integer(), nullable=True),
            sa.Column('points_rank', sa.Integer(), nullable=True),
            sa.Column('completion_rank', sa.Integer(), nullable=True),
            sa.Column('improvement_from_last_week', sa.Integer(), server_default='0'),
            sa.Column('is_personal_best_week', sa.Boolean(), server_default='false'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('last_calculated_at', sa.DateTime(), nullable=True)
        )
    
    print("✅ Successfully created all 16 missing production tables!")


def downgrade() -> None:
    """Drop all 16 tables in reverse order"""
    op.drop_table('weekly_leaderboard_cache')
    op.drop_table('trending_items')
    op.drop_table('viewing_history')
    op.drop_table('user_preferences')
    op.drop_table('user_recommendations')
    op.drop_table('user_quiz_best_scores')
    op.drop_table('user_collection_progress')
    op.drop_table('collection_myth_facts')
    op.drop_table('myth_fact_collections')
    op.drop_table('animal_sightings')
    op.drop_table('user_animal_interactions')
    op.drop_table('animal_profiles')
    op.drop_table('livestreams')
    op.drop_table('chatbot_conversations')
    op.drop_table('site_settings')
    op.drop_table('conservation_efforts')
    
    # Drop ENUMs
    conn = op.get_bind()
    ENUM(name='recommendationsourceenum').drop(conn, checkfirst=True)
    ENUM(name='recommendationtypeenum').drop(conn, checkfirst=True)
    ENUM(name='habitattypeenum').drop(conn, checkfirst=True)
    ENUM(name='conservationstatusenum').drop(conn, checkfirst=True)
    ENUM(name='streamstatusenum').drop(conn, checkfirst=True)
