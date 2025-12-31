#!/usr/bin/env python3
"""
Create Myth Fact Collections Database Tables

This script creates the necessary database tables for implementing category-based
deck system for Myths vs Facts game with repeatability control.

New Tables:
1. myth_fact_collections - Define themed collections/decks
2. collection_myth_facts - Junction table for cards in collections  
3. user_collection_progress - Track daily completion per user per collection

Run this script to set up the database schema for Phase 2.
"""

import asyncio
import sys
import os

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.core.config import settings
from app.db.database import engine


async def create_collections_tables():
    """Create all necessary tables for myth fact collections system"""
    
    # SQL for creating myth_fact_collections table
    create_collections_table = """
    CREATE TABLE IF NOT EXISTS myth_fact_collections (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        is_active BOOLEAN DEFAULT TRUE,
        cards_count INTEGER DEFAULT 0,
        repeatability VARCHAR(20) DEFAULT 'daily', -- 'daily', 'weekly', 'unlimited'
        custom_points_enabled BOOLEAN DEFAULT FALSE,
        custom_points_bronze INTEGER DEFAULT NULL,
        custom_points_silver INTEGER DEFAULT NULL,
        custom_points_gold INTEGER DEFAULT NULL,
        custom_points_platinum INTEGER DEFAULT NULL,
        custom_credits_enabled BOOLEAN DEFAULT FALSE,
        custom_credits_bronze INTEGER DEFAULT NULL,
        custom_credits_silver INTEGER DEFAULT NULL,
        custom_credits_gold INTEGER DEFAULT NULL,
        custom_credits_platinum INTEGER DEFAULT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        created_by UUID REFERENCES users(id) ON DELETE SET NULL
    );
    """

    # SQL for creating collection_myth_facts junction table
    create_junction_table = """
    CREATE TABLE IF NOT EXISTS collection_myth_facts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        collection_id UUID NOT NULL REFERENCES myth_fact_collections(id) ON DELETE CASCADE,
        myth_fact_id UUID NOT NULL REFERENCES myths_facts(id) ON DELETE CASCADE,
        order_index INTEGER DEFAULT 0,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(collection_id, myth_fact_id),
        UNIQUE(collection_id, order_index)
    );
    """

    # SQL for creating user_collection_progress table
    create_progress_table = """
    CREATE TABLE IF NOT EXISTS user_collection_progress (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        collection_id UUID NOT NULL REFERENCES myth_fact_collections(id) ON DELETE CASCADE,
        play_date DATE NOT NULL DEFAULT CURRENT_DATE,
        completed BOOLEAN DEFAULT FALSE,
        score_percentage INTEGER DEFAULT 0,
        time_taken INTEGER DEFAULT NULL,
        answers_correct INTEGER DEFAULT 0,
        total_questions INTEGER DEFAULT 0,
        points_earned INTEGER DEFAULT 0,
        credits_earned INTEGER DEFAULT 0,
        tier VARCHAR(20) DEFAULT NULL,
        bonus_applied BOOLEAN DEFAULT FALSE,
        game_session_id UUID DEFAULT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        completed_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
        UNIQUE(user_id, collection_id, play_date),
        CONSTRAINT valid_score_percentage CHECK (score_percentage >= 0 AND score_percentage <= 100),
        CONSTRAINT valid_answers CHECK (answers_correct >= 0 AND answers_correct <= total_questions)
    );
    """

    # SQL for creating indexes for performance
    create_indexes = """
    -- Indexes for myth_fact_collections
    CREATE INDEX IF NOT EXISTS idx_collections_category ON myth_fact_collections(category_id);
    CREATE INDEX IF NOT EXISTS idx_collections_active ON myth_fact_collections(is_active);
    CREATE INDEX IF NOT EXISTS idx_collections_created_at ON myth_fact_collections(created_at);

    -- Indexes for collection_myth_facts
    CREATE INDEX IF NOT EXISTS idx_collection_myths_collection ON collection_myth_facts(collection_id);
    CREATE INDEX IF NOT EXISTS idx_collection_myths_myth_fact ON collection_myth_facts(myth_fact_id);
    CREATE INDEX IF NOT EXISTS idx_collection_myths_order ON collection_myth_facts(collection_id, order_index);

    -- Indexes for user_collection_progress
    CREATE INDEX IF NOT EXISTS idx_progress_user ON user_collection_progress(user_id);
    CREATE INDEX IF NOT EXISTS idx_progress_collection ON user_collection_progress(collection_id);
    CREATE INDEX IF NOT EXISTS idx_progress_date ON user_collection_progress(play_date);
    CREATE INDEX IF NOT EXISTS idx_progress_completed ON user_collection_progress(completed);
    CREATE INDEX IF NOT EXISTS idx_progress_user_date ON user_collection_progress(user_id, play_date);
    """

    # SQL for creating useful views
    create_views = """
    -- View for collection statistics
    CREATE OR REPLACE VIEW collection_stats AS
    SELECT 
        c.id,
        c.name,
        c.description,
        c.is_active,
        c.repeatability,
        cat.name as category_name,
        COUNT(cmf.myth_fact_id) as total_cards,
        COUNT(DISTINCT ucp.user_id) as unique_players,
        COUNT(ucp.id) as total_plays,
        COUNT(CASE WHEN ucp.completed = true THEN 1 END) as completions,
        ROUND(AVG(ucp.score_percentage), 2) as avg_score,
        ROUND(AVG(ucp.time_taken), 2) as avg_time
    FROM myth_fact_collections c
    LEFT JOIN categories cat ON c.category_id = cat.id
    LEFT JOIN collection_myth_facts cmf ON c.id = cmf.collection_id
    LEFT JOIN user_collection_progress ucp ON c.id = ucp.collection_id
    GROUP BY c.id, c.name, c.description, c.is_active, c.repeatability, cat.name;

    -- View for user daily progress summary
    CREATE OR REPLACE VIEW user_daily_collection_summary AS
    SELECT 
        user_id,
        play_date,
        COUNT(*) as collections_attempted,
        COUNT(CASE WHEN completed = true THEN 1 END) as collections_completed,
        SUM(points_earned) as total_points_earned,
        SUM(credits_earned) as total_credits_earned,
        ROUND(AVG(score_percentage), 2) as avg_score_percentage
    FROM user_collection_progress
    GROUP BY user_id, play_date;
    """

    async with engine.begin() as conn:
        try:
            print("🗄️  Creating myth_fact_collections table...")
            await conn.execute(text(create_collections_table))
            
            print("🔗 Creating collection_myth_facts junction table...")
            await conn.execute(text(create_junction_table))
            
            print("📊 Creating user_collection_progress table...")
            await conn.execute(text(create_progress_table))
            
            print("⚡ Creating performance indexes...")
            
            # Create indexes individually to avoid PostgreSQL prepared statement limitations
            indexes = [
                # Indexes for myth_fact_collections
                "CREATE INDEX IF NOT EXISTS idx_collections_category ON myth_fact_collections(category_id);",
                "CREATE INDEX IF NOT EXISTS idx_collections_active ON myth_fact_collections(is_active);",
                "CREATE INDEX IF NOT EXISTS idx_collections_created_at ON myth_fact_collections(created_at);",
                
                # Indexes for collection_myth_facts
                "CREATE INDEX IF NOT EXISTS idx_collection_myths_collection ON collection_myth_facts(collection_id);",
                "CREATE INDEX IF NOT EXISTS idx_collection_myths_myth_fact ON collection_myth_facts(myth_fact_id);",
                "CREATE INDEX IF NOT EXISTS idx_collection_myths_order ON collection_myth_facts(collection_id, order_index);",
                
                # Indexes for user_collection_progress
                "CREATE INDEX IF NOT EXISTS idx_progress_user ON user_collection_progress(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_progress_collection ON user_collection_progress(collection_id);",
                "CREATE INDEX IF NOT EXISTS idx_progress_date ON user_collection_progress(play_date);",
                "CREATE INDEX IF NOT EXISTS idx_progress_completed ON user_collection_progress(completed);",
                "CREATE INDEX IF NOT EXISTS idx_progress_user_date ON user_collection_progress(user_id, play_date);"
            ]
            
            for index_sql in indexes:
                await conn.execute(text(index_sql))
                print(f"   ✅ Created index: {index_sql.split()[4]}")  # Extract index name
            
            print("👁️  Creating useful views...")
            
            # Create views individually to avoid PostgreSQL prepared statement limitations
            views = [
                """CREATE OR REPLACE VIEW collection_stats AS
    SELECT 
        c.id,
        c.name,
        c.description,
        c.is_active,
        c.repeatability,
        cat.name as category_name,
        COUNT(cmf.myth_fact_id) as total_cards,
        COUNT(DISTINCT ucp.user_id) as unique_players,
        COUNT(ucp.id) as total_plays,
        COUNT(CASE WHEN ucp.completed = true THEN 1 END) as completions,
        ROUND(AVG(ucp.score_percentage), 2) as avg_score,
        ROUND(AVG(ucp.time_taken), 2) as avg_time
    FROM myth_fact_collections c
    LEFT JOIN categories cat ON c.category_id = cat.id
    LEFT JOIN collection_myth_facts cmf ON c.id = cmf.collection_id
    LEFT JOIN user_collection_progress ucp ON c.id = ucp.collection_id
    GROUP BY c.id, c.name, c.description, c.is_active, c.repeatability, cat.name;""",
                
                """CREATE OR REPLACE VIEW user_daily_collection_summary AS
    SELECT 
        user_id,
        play_date,
        COUNT(*) as collections_attempted,
        COUNT(CASE WHEN completed = true THEN 1 END) as collections_completed,
        SUM(points_earned) as total_points_earned,
        SUM(credits_earned) as total_credits_earned,
        ROUND(AVG(score_percentage), 2) as avg_score_percentage
    FROM user_collection_progress
    GROUP BY user_id, play_date;"""
            ]
            
            for view_sql in views:
                await conn.execute(text(view_sql))
                # Extract view name for logging
                view_name = view_sql.split("VIEW ")[1].split(" AS")[0].strip()
                print(f"   ✅ Created view: {view_name}")
            
            print("✅ All collections tables created successfully!")
            print("\n📋 Tables created:")
            print("   - myth_fact_collections (themed collections/decks)")
            print("   - collection_myth_facts (cards assignment)")
            print("   - user_collection_progress (daily tracking)")
            print("\n🔍 Views created:")
            print("   - collection_stats (analytics)")
            print("   - user_daily_collection_summary (user progress)")
            
        except Exception as e:
            print(f"❌ Error creating tables: {str(e)}")
            raise


async def create_default_collections():
    """Create some default collections for testing"""
    
    default_collections_sql = """
    -- Create default Wildlife collection
    WITH wildlife_category AS (
        SELECT id FROM categories WHERE LOWER(name) = 'wildlife' LIMIT 1
    ),
    wildlife_collection AS (
        INSERT INTO myth_fact_collections (
            category_id, name, description, is_active, repeatability
        ) 
        SELECT 
            wc.id,
            'Wildlife Myths & Facts',
            'Common myths and facts about wildlife behavior and conservation',
            true,
            'daily'
        FROM wildlife_category wc
        WHERE NOT EXISTS (
            SELECT 1 FROM myth_fact_collections 
            WHERE name = 'Wildlife Myths & Facts'
        )
        RETURNING id
    )
    SELECT id FROM wildlife_collection;

    -- Create default Marine Life collection if marine category exists
    INSERT INTO myth_fact_collections (
        category_id, name, description, is_active, repeatability
    ) 
    SELECT 
        c.id,
        'Marine Life Mysteries',
        'Myths and facts about ocean life and marine conservation',
        true,
        'daily'
    FROM categories c 
    WHERE LOWER(c.name) LIKE '%marine%' OR LOWER(c.name) LIKE '%ocean%'
    AND NOT EXISTS (
        SELECT 1 FROM myth_fact_collections 
        WHERE name = 'Marine Life Mysteries'
    )
    LIMIT 1;
    """

    async with engine.begin() as conn:
        try:
            print("🎯 Creating default collections...")
            await conn.execute(text(default_collections_sql))
            print("✅ Default collections created!")
            
        except Exception as e:
            print(f"⚠️  Note: Default collections creation had issues: {str(e)}")
            print("   This is normal if categories don't exist yet.")


async def main():
    """Main function to run the table creation"""
    print("🚀 Starting Myth Fact Collections Database Setup...")
    print(f"📍 Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Local'}")
    
    try:
        await create_collections_tables()
        await create_default_collections()
        
        print("\n🎉 Phase 2 Database Setup Complete!")
        print("\n📝 Next steps:")
        print("   1. Create collection management API endpoints")
        print("   2. Update MythFact models with collection relationships")
        print("   3. Build admin interface for collection management")
        print("   4. Update frontend to support collection selection")
        
    except Exception as e:
        print(f"\n💥 Setup failed: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)