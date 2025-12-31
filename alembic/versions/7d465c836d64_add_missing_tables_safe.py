"""add_missing_tables_safe

Revision ID: 7d465c836d64
Revises: add_expedition_slugs
Create Date: 2025-12-19 15:34:04.336852

SAFE MIGRATION: Only creates missing tables using IF NOT EXISTS.
Will not modify or drop any existing tables.

Creates:
- video_channels
- general_knowledge_videos  
- national_parks
- temp_user_registrations
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '7d465c836d64'
down_revision = 'add_expedition_slugs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create missing tables using raw SQL with IF NOT EXISTS"""
    conn = op.get_bind()
    
    # 1. CREATE VIDEO_CHANNELS TABLE
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS video_channels (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL UNIQUE,
            slug VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            thumbnail_url VARCHAR(500),
            banner_url VARCHAR(500),
            total_videos INTEGER DEFAULT 0 NOT NULL,
            total_views INTEGER DEFAULT 0 NOT NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            created_by UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
    """))
    
    # Create indexes for video_channels
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_video_channels_slug 
        ON video_channels(slug);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_video_channels_active 
        ON video_channels(is_active, created_at);
    """))
    
    # 2. CREATE GENERAL_KNOWLEDGE_VIDEOS TABLE
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS general_knowledge_videos (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            channel_id UUID NOT NULL REFERENCES video_channels(id) ON DELETE CASCADE,
            title VARCHAR(500) NOT NULL,
            subtitle VARCHAR(500),
            slug VARCHAR(255) NOT NULL,
            description TEXT,
            video_url VARCHAR(500) NOT NULL,
            thumbnail_url VARCHAR(500),
            duration INTEGER,
            tags TEXT,
            hashtags VARCHAR(500),
            views INTEGER DEFAULT 0 NOT NULL,
            likes INTEGER DEFAULT 0 NOT NULL,
            is_published BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
    """))
    
    # Create indexes for general_knowledge_videos
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_gk_videos_channel 
        ON general_knowledge_videos(channel_id, created_at);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_gk_videos_slug 
        ON general_knowledge_videos(slug);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_gk_videos_published 
        ON general_knowledge_videos(is_published, created_at);
    """))
    
    # 3. CREATE NATIONAL_PARKS TABLE
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS national_parks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL UNIQUE,
            slug VARCHAR(255) NOT NULL UNIQUE,
            state VARCHAR(100),
            description TEXT,
            biodiversity TEXT,
            conservation TEXT,
            media_urls JSONB DEFAULT '[]'::jsonb NOT NULL,
            video_urls JSONB DEFAULT '[]'::jsonb NOT NULL,
            banner_media_url VARCHAR(500),
            banner_media_type VARCHAR(20),
            expedition_slugs JSONB DEFAULT '[]'::jsonb NOT NULL,
            is_active BOOLEAN DEFAULT TRUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
        );
    """))
    
    # Create indexes for national_parks
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_national_parks_name 
        ON national_parks(name);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_national_parks_slug 
        ON national_parks(slug);
    """))
    
    # 4. CREATE TEMP_USER_REGISTRATIONS TABLE
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS temp_user_registrations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL UNIQUE,
            username VARCHAR(50) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            full_name VARCHAR(100),
            gender VARCHAR(20),
            country VARCHAR(100),
            email_verification_token VARCHAR(10) NOT NULL,
            email_verification_expires TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            verified_at TIMESTAMP,
            is_expired BOOLEAN DEFAULT FALSE
        );
    """))
    
    # Create indexes for temp_user_registrations
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_temp_user_registrations_email 
        ON temp_user_registrations(email);
    """))
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_temp_user_registrations_username 
        ON temp_user_registrations(username);
    """))
    
    print("✅ Successfully created 4 missing tables (using IF NOT EXISTS - safe)")


def downgrade() -> None:
    """Drop the tables if they exist (careful - only run if you want to remove them)"""
    conn = op.get_bind()
    
    # Drop in reverse order due to foreign keys
    conn.execute(text("DROP TABLE IF EXISTS general_knowledge_videos CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS video_channels CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS national_parks CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS temp_user_registrations CASCADE;"))
    
    print("⚠️  Dropped 4 tables")
