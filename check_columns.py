#!/usr/bin/env python3
"""Quick check if migrations were applied to Railway database"""
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check_columns():
    """Check if the new columns exist"""
    database_url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ No DATABASE_PUBLIC_URL or DATABASE_URL found")
        sys.exit(1)
    
    # Fix URL to use asyncpg
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    print(f"🔗 Connecting to database...")
    print(f"   URL: {database_url[:50]}...")
    
    engine = create_async_engine(database_url, echo=False)
    
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='users' 
                AND column_name IN ('organization', 'professional_title', 'google_id', 
                                   'facebook_id', 'linkedin_id', 'discussion_count', 
                                   'comment_count', 'reputation_score')
                ORDER BY column_name
            """))
            
            columns = [row[0] for row in result]
            
            print(f"\n📊 Found {len(columns)} new columns:")
            for col in columns:
                print(f"   ✅ {col}")
            
            if len(columns) == 8:
                print("\n🎉 All 8 columns exist! Migration was successful!")
                print("   BUT the backend service needs to RESTART to pick up the changes!")
            else:
                missing = set(['organization', 'professional_title', 'google_id', 
                             'facebook_id', 'linkedin_id', 'discussion_count', 
                             'comment_count', 'reputation_score']) - set(columns)
                print(f"\n❌ Missing {len(missing)} columns:")
                for col in missing:
                    print(f"   ⚠️  {col}")
                    
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_columns())
