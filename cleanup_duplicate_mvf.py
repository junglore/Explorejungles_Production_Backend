#!/usr/bin/env python3
"""
Clean up duplicate MVF settings in production database
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Override DATABASE_URL for railway run
if 'DATABASE_PUBLIC_URL' in os.environ:
    os.environ['DATABASE_URL'] = os.environ['DATABASE_PUBLIC_URL']
    # Ensure asyncpg driver
    if os.environ['DATABASE_URL'].startswith('postgresql://'):
        os.environ['DATABASE_URL'] = os.environ['DATABASE_URL'].replace('postgresql://', 'postgresql+asyncpg://', 1)

from app.db.database import get_db_session
from app.models.site_setting import SiteSetting
from sqlalchemy import delete


async def cleanup_duplicate_settings():
    """Remove duplicate MVF settings"""

    try:
        async with get_db_session() as db:
            print("🧹 Cleaning up duplicate MVF settings...")

            # Remove the duplicate max_myths_facts_games_per_day from SECURITY category
            # Keep mvf_max_games_per_day from MYTHS_VS_FACTS category
            result = await db.execute(
                delete(SiteSetting).where(SiteSetting.key == 'max_myths_facts_games_per_day')
            )
            deleted_count = result.rowcount

            await db.commit()

            print(f"✅ Cleanup complete!")
            print(f"   🗑️  Removed {deleted_count} duplicate setting(s)")

    except Exception as e:
        print(f"❌ Error cleaning up duplicates: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(cleanup_duplicate_settings())