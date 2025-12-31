#!/usr/bin/env python3
"""
Check users table columns to fix the admin queries test.
"""

import asyncio
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import get_db_session
from sqlalchemy import text


async def check_users_table():
    """Check what columns exist in the users table."""
    try:
        async with get_db_session() as db:
            result = await db.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'users' AND table_schema = 'public'
                ORDER BY column_name
            """))
            columns = [row[0] for row in result.fetchall()]
            print("Users table columns:")
            for col in columns:
                print(f"  - {col}")
            return columns
    except Exception as e:
        print(f"Error checking users table: {e}")
        return []


if __name__ == "__main__":
    columns = asyncio.run(check_users_table())
    print(f"\nTotal columns: {len(columns)}")