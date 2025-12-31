import asyncio
from app.db.database import get_db_session
from app.models.media import Media
from sqlalchemy import select

async def check():
    async with get_db_session() as db:
        result = await db.execute(
            select(Media.id, Media.media_type, Media.title, Media.file_url).limit(10)
        )
        rows = result.all()
        print(f'Total media records: {len(rows)}')
        for r in rows:
            print(f'{r.media_type}: {r.title} - {r.file_url}')

asyncio.run(check())
