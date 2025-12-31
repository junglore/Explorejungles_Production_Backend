"""
Automated setup script for new video features
Run this to set up your database to match your friend's
"""

import asyncio
import sys
from sqlalchemy import text, inspect
from app.db.database import get_db_session, engine


async def check_and_report():
    """Check what tables exist and what's missing"""
    
    print("=" * 70)
    print("🔍 CHECKING YOUR DATABASE STATUS")
    print("=" * 70)
    
    async with engine.begin() as conn:
        def check_tables(connection):
            inspector = inspect(connection)
            existing_tables = inspector.get_table_names()
            
            required_tables = {
                'video_series': 'Video series/playlists',
                'series_videos': 'Videos within series',
                'video_tags': 'Tag definitions',
                'video_likes': 'User likes on videos',
                'video_comments': 'Video comments',
                'video_comment_likes': 'Likes on comments',
                'video_watch_progress': 'Watch progress tracking'
            }
            
            print("\n📊 Table Status:")
            print("-" * 70)
            
            missing_tables = []
            for table, description in required_tables.items():
                if table in existing_tables:
                    print(f"✅ {table:25} - {description}")
                else:
                    print(f"❌ {table:25} - {description} (MISSING)")
                    missing_tables.append(table)
            
            # Check for featured series columns
            if 'video_series' in existing_tables:
                columns = [col['name'] for col in inspector.get_columns('video_series')]
                print(f"\n📋 video_series columns:")
                if 'is_featured' in columns:
                    print(f"✅ is_featured column exists")
                else:
                    print(f"❌ is_featured column missing")
                    
                if 'featured_at' in columns:
                    print(f"✅ featured_at column exists")
                else:
                    print(f"❌ featured_at column missing")
            
            return missing_tables
        
        missing = await conn.run_sync(check_tables)
        
    print("\n" + "=" * 70)
    
    if not missing:
        print("✅ ALL TABLES EXIST! Your database is ready!")
        print("\nYou can now:")
        print("  1. Start your backend: python start_with_large_limits.py")
        print("  2. Access admin panel: http://localhost:8000/admin")
        print("  3. Create your first video series!")
    else:
        print(f"⚠️  {len(missing)} tables are missing")
        print("\n🔧 SOLUTION:")
        print("Run this command to create missing tables:")
        print("\n  alembic upgrade head")
        print("\nIf that fails, run these scripts manually:")
        print("  python create_video_series_tables.py")
        print("  python create_video_engagement_tables.py")
        print("  python add_featured_series_columns")
    
    print("=" * 70)


async def main():
    try:
        await check_and_report()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. PostgreSQL is running")
        print("  2. Database credentials in .env are correct")
        print("  3. Database 'Junglore_KE' exists")
        sys.exit(1)


if __name__ == "__main__":
    print("\n🚀 Starting database check...\n")
    asyncio.run(main())
    print("\nDone! Check the report above. ⬆️\n")
