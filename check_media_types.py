import asyncio
from app.db.database import get_db_session
from sqlalchemy import select, distinct
from app.models.media import Media

async def check():
    async with get_db_session() as db:
        result = await db.execute(select(distinct(Media.media_type)))
        types = [r for r in result.scalars().all()]
        print('Media types in database:', types)
        
        # Count by type
        for media_type in types:
            count_result = await db.execute(
                select(Media).where(Media.media_type == media_type)
            )
            count = len(count_result.scalars().all())
            print(f"  {media_type}: {count} items")

asyncio.run(check())
