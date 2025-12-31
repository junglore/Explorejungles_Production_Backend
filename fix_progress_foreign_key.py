"""
Remove foreign key constraint from video_watch_progress table
to allow tracking progress for guest users
"""

import asyncio
import asyncpg
from app.core.config import settings


async def fix_foreign_key():
    """Drop the foreign key constraint from video_watch_progress"""
    
    conn = await asyncpg.connect(settings.DATABASE_URL)
    
    try:
        # Drop the foreign key constraint
        print("Dropping foreign key constraint...")
        await conn.execute("""
            ALTER TABLE video_watch_progress 
            DROP CONSTRAINT IF EXISTS fk_video_watch_progress_user_id_users;
        """)
        
        print("✓ Foreign key constraint removed successfully!")
        print("\nNow guest users can track their watch progress.")
        
    except Exception as e:
        print(f"✗ Error: {e}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(fix_foreign_key())