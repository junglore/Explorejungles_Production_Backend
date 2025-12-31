-- ============================================================================
-- Manual Database Migration Script for Railway
-- Run this if automated migrations fail
-- ============================================================================

-- This script adds all the missing tables and columns to sync production DB
-- with your latest code changes

BEGIN;

-- ============================================================================
-- 1. ADD OAUTH COLUMNS TO USERS TABLE
-- ============================================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_id VARCHAR(255);

-- Add unique constraints for OAuth IDs
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_google_id') THEN
        ALTER TABLE users ADD CONSTRAINT uq_users_google_id UNIQUE (google_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_facebook_id') THEN
        ALTER TABLE users ADD CONSTRAINT uq_users_facebook_id UNIQUE (facebook_id);
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_linkedin_id') THEN
        ALTER TABLE users ADD CONSTRAINT uq_users_linkedin_id UNIQUE (linkedin_id);
    END IF;
END $$;

-- Create indexes for OAuth lookups
CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);
CREATE INDEX IF NOT EXISTS ix_users_facebook_id ON users(facebook_id);
CREATE INDEX IF NOT EXISTS ix_users_linkedin_id ON users(linkedin_id);

-- ============================================================================
-- 2. ADD COMMUNITY/DISCUSSION COLUMNS TO USERS TABLE
-- ============================================================================
ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS professional_title VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS discussion_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS comment_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS reputation_score INTEGER DEFAULT 0;

-- Update existing users to have default values
UPDATE users 
SET discussion_count = 0, 
    comment_count = 0, 
    reputation_score = 0 
WHERE discussion_count IS NULL 
   OR comment_count IS NULL 
   OR reputation_score IS NULL;

-- Make columns NOT NULL after setting defaults
ALTER TABLE users ALTER COLUMN discussion_count SET NOT NULL;
ALTER TABLE users ALTER COLUMN comment_count SET NOT NULL;
ALTER TABLE users ALTER COLUMN reputation_score SET NOT NULL;

-- ============================================================================
-- 3. CREATE MYTH FACT COLLECTIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS myth_fact_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    cards_count INTEGER DEFAULT 0 NOT NULL,
    
    -- Repeatability settings
    repeatability VARCHAR(20) DEFAULT 'daily' NOT NULL,
    
    -- Custom point rewards
    custom_points_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    custom_points_bronze INTEGER,
    custom_points_silver INTEGER,
    custom_points_gold INTEGER,
    custom_points_platinum INTEGER,
    
    -- Custom credit rewards
    custom_credits_enabled BOOLEAN DEFAULT FALSE NOT NULL,
    custom_credits_bronze INTEGER,
    custom_credits_silver INTEGER,
    custom_credits_gold INTEGER,
    custom_credits_platinum INTEGER,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_collections_category ON myth_fact_collections(category_id);
CREATE INDEX IF NOT EXISTS idx_collections_active ON myth_fact_collections(is_active);
CREATE INDEX IF NOT EXISTS idx_collections_created_at ON myth_fact_collections(created_at);

-- ============================================================================
-- 4. CREATE COLLECTION_MYTH_FACTS JUNCTION TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS collection_myth_facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL REFERENCES myth_fact_collections(id) ON DELETE CASCADE,
    myth_fact_id UUID NOT NULL REFERENCES myths_facts(id) ON DELETE CASCADE,
    order_index INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    CONSTRAINT uq_collection_myth_fact UNIQUE(collection_id, myth_fact_id),
    CONSTRAINT uq_collection_order UNIQUE(collection_id, order_index)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_collection_myth_facts_collection ON collection_myth_facts(collection_id);
CREATE INDEX IF NOT EXISTS idx_collection_myth_facts_myth_fact ON collection_myth_facts(myth_fact_id);
CREATE INDEX IF NOT EXISTS idx_collection_myth_facts_order ON collection_myth_facts(collection_id, order_index);

-- ============================================================================
-- 5. CREATE USER_COLLECTION_PROGRESS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_collection_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_id UUID NOT NULL REFERENCES myth_fact_collections(id) ON DELETE CASCADE,
    play_date DATE NOT NULL DEFAULT CURRENT_DATE,
    
    -- Progress tracking
    completed BOOLEAN DEFAULT FALSE NOT NULL,
    score_percentage INTEGER DEFAULT 0 NOT NULL,
    time_taken INTEGER,
    answers_correct INTEGER DEFAULT 0 NOT NULL,
    total_questions INTEGER DEFAULT 0 NOT NULL,
    
    -- Rewards
    points_earned INTEGER DEFAULT 0 NOT NULL,
    credits_earned INTEGER DEFAULT 0 NOT NULL,
    tier VARCHAR(20),
    bonus_applied BOOLEAN DEFAULT FALSE NOT NULL,
    
    -- Session tracking
    game_session_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT uq_user_collection_date UNIQUE(user_id, collection_id, play_date),
    CONSTRAINT valid_score_percentage CHECK (score_percentage >= 0 AND score_percentage <= 100),
    CONSTRAINT valid_answers CHECK (answers_correct >= 0 AND answers_correct <= total_questions)
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_user_progress_user ON user_collection_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_collection ON user_collection_progress(collection_id);
CREATE INDEX IF NOT EXISTS idx_user_progress_date ON user_collection_progress(play_date);
CREATE INDEX IF NOT EXISTS idx_user_progress_user_date ON user_collection_progress(user_id, play_date);
CREATE INDEX IF NOT EXISTS idx_user_progress_completed ON user_collection_progress(completed);

-- ============================================================================
-- 6. CREATE SITE_SETTINGS TABLE (if not exists)
-- ============================================================================
CREATE TABLE IF NOT EXISTS site_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    category VARCHAR(50) DEFAULT 'general' NOT NULL,
    label VARCHAR(200) NOT NULL,
    description TEXT,
    is_public BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create index
CREATE INDEX IF NOT EXISTS idx_site_settings_key ON site_settings(key);
CREATE INDEX IF NOT EXISTS idx_site_settings_category ON site_settings(category);

-- ============================================================================
-- 7. VERIFY ALL CHANGES
-- ============================================================================

-- Check if all new columns exist in users table
DO $$ 
DECLARE
    missing_columns TEXT[];
BEGIN
    SELECT ARRAY_AGG(column_name) INTO missing_columns
    FROM (
        SELECT unnest(ARRAY['google_id', 'facebook_id', 'linkedin_id', 
                            'organization', 'professional_title', 
                            'discussion_count', 'comment_count', 'reputation_score']) AS column_name
    ) expected
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'users' 
        AND column_name = expected.column_name
    );
    
    IF array_length(missing_columns, 1) > 0 THEN
        RAISE EXCEPTION 'Missing columns in users table: %', array_to_string(missing_columns, ', ');
    END IF;
    
    RAISE NOTICE '✅ All user table columns exist';
END $$;

-- Check if all new tables exist
DO $$
DECLARE
    missing_tables TEXT[];
BEGIN
    SELECT ARRAY_AGG(table_name) INTO missing_tables
    FROM (
        SELECT unnest(ARRAY['myth_fact_collections', 'collection_myth_facts', 
                            'user_collection_progress', 'site_settings']) AS table_name
    ) expected
    WHERE NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = expected.table_name
    );
    
    IF array_length(missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'Missing tables: %', array_to_string(missing_tables, ', ');
    END IF;
    
    RAISE NOTICE '✅ All new tables exist';
END $$;

COMMIT;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

SELECT '✅ Database migration completed successfully!' AS status;
SELECT 'Run this query to verify:' AS next_step;
SELECT 'SELECT column_name FROM information_schema.columns WHERE table_name = ''users'' ORDER BY ordinal_position;' AS verify_query;
