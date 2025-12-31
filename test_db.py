#!/usr/bin/env python3
import os
import asyncio
from app.db.database import get_db_session
from sqlalchemy import text

async def test():
    try:
        async with get_db_session() as db:
            result = await db.execute(text('SELECT COUNT(*) FROM users'))
            count = result.scalar()
            print(f'✅ Connected! Users count: {count}')
    except Exception as e:
        print(f'❌ Connection failed: {e}')

if __name__ == "__main__":
    # Override with production URL
    if "DATABASE_PUBLIC_URL" in os.environ:
        os.environ["DATABASE_URL"] = os.environ["DATABASE_PUBLIC_URL"]
        print("Using production database")

    asyncio.run(test())