#!/usr/bin/env python3
"""
Database migration script to create leaderboard tables:
- user_quiz_best_scores: Track personal best scores for each user per quiz
- weekly_leaderboard_cache: Optimized weekly rankings with auto-reset functionality
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.db.database import get_db_session
from sqlalchemy import text


async def create_leaderboard_tables():
    """Create leaderboard tables if they don't exist"""
    try:
        async with get_db_session() as db:
            print("Creating leaderboard database tables...")
            
            # Check if tables exist first
            check_best_scores_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'user_quiz_best_scores'
            """)
            
            check_leaderboard_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'weekly_leaderboard_cache'
            """)
            
            best_scores_exists = await db.execute(check_best_scores_query)
            leaderboard_exists = await db.execute(check_leaderboard_query)
            
            tables_created = 0
            
            # Create user_quiz_best_scores table
            if not best_scores_exists.fetchone():
                # Create table
                create_best_scores_table = text("""
                    CREATE TABLE user_quiz_best_scores (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        quiz_id UUID NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
                        best_score INTEGER NOT NULL,
                        best_percentage INTEGER NOT NULL,
                        best_time INTEGER,
                        credits_earned INTEGER DEFAULT 0,
                        points_earned INTEGER DEFAULT 0,
                        reward_tier VARCHAR(50),
                        achieved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        CONSTRAINT unique_user_quiz_best UNIQUE (user_id, quiz_id)
                    );
                """)
                await db.execute(create_best_scores_table)
                
                # Create indexes separately
                index_queries = [
                    "CREATE INDEX idx_user_quiz_best_user_id ON user_quiz_best_scores(user_id);",
                    "CREATE INDEX idx_user_quiz_best_quiz_id ON user_quiz_best_scores(quiz_id);",
                    "CREATE INDEX idx_user_quiz_best_percentage ON user_quiz_best_scores(best_percentage);",
                    "CREATE INDEX idx_user_quiz_best_achieved_at ON user_quiz_best_scores(achieved_at);"
                ]
                
                for index_query in index_queries:
                    await db.execute(text(index_query))
                
                tables_created += 1
                print("   ✅ user_quiz_best_scores table created")
            else:
                print("   ℹ️  user_quiz_best_scores table already exists")
            
            # Create weekly_leaderboard_cache table
            if not leaderboard_exists.fetchone():
                # Create table
                create_leaderboard_table = text("""
                    CREATE TABLE weekly_leaderboard_cache (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        week_start_date DATE NOT NULL,
                        week_end_date DATE NOT NULL,
                        week_number INTEGER NOT NULL,
                        year INTEGER NOT NULL,
                        total_credits_earned INTEGER DEFAULT 0,
                        total_points_earned INTEGER DEFAULT 0,
                        quizzes_completed INTEGER DEFAULT 0,
                        perfect_scores INTEGER DEFAULT 0,
                        average_percentage INTEGER DEFAULT 0,
                        credits_rank INTEGER,
                        points_rank INTEGER,
                        completion_rank INTEGER,
                        improvement_from_last_week INTEGER DEFAULT 0,
                        is_personal_best_week BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        last_calculated_at TIMESTAMP WITH TIME ZONE
                    );
                """)
                await db.execute(create_leaderboard_table)
                
                # Create indexes separately
                leaderboard_index_queries = [
                    "CREATE INDEX idx_weekly_leaderboard_user_week ON weekly_leaderboard_cache(user_id, week_start_date);",
                    "CREATE INDEX idx_weekly_leaderboard_week_credits ON weekly_leaderboard_cache(week_start_date, total_credits_earned);",
                    "CREATE INDEX idx_weekly_leaderboard_credits_rank ON weekly_leaderboard_cache(credits_rank);",
                    "CREATE INDEX idx_weekly_leaderboard_current_week ON weekly_leaderboard_cache(week_start_date, year);",
                    "CREATE INDEX idx_weekly_leaderboard_user_id ON weekly_leaderboard_cache(user_id);"
                ]
                
                for index_query in leaderboard_index_queries:
                    await db.execute(text(index_query))
                
                tables_created += 1
                print("   ✅ weekly_leaderboard_cache table created")
            else:
                print("   ℹ️  weekly_leaderboard_cache table already exists")
            
            if tables_created > 0:
                await db.commit()
                print(f"\n✅ Successfully created {tables_created} leaderboard table(s)!")
            else:
                print("\n✅ All leaderboard tables already exist!")
                
        return True
        
    except Exception as e:
        print(f"❌ Error creating leaderboard tables: {e}")
        return False


async def main():
    """Main function to run the migration"""
    print("=" * 60)
    print("🏆 LEADERBOARD TABLES MIGRATION")
    print("=" * 60)
    
    success = await create_leaderboard_tables()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("   Leaderboard system database foundation is ready.")
        print("   You can now track user achievements and weekly rankings.")
        print("\n📊 UserQuizBestScore features:")
        print("   • Personal best tracking per user per quiz")
        print("   • Score, percentage, and time tracking")
        print("   • Credits and points earned recording")
        print("   • Achievement timestamps")
        print("   • Optimized indexes for quick lookups")
        print("\n🏆 WeeklyLeaderboardCache features:")
        print("   • Automated week tracking (Monday-Sunday)")
        print("   • Multiple ranking categories (credits, points, completion)")
        print("   • Performance metrics and improvement tracking")
        print("   • Personal best week flagging")
        print("   • Optimized for leaderboard queries")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED!")
        print("   Please check the error messages above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())