import asyncio
from app.db.database import get_db_session
from app.models.video_series import SeriesVideo
from app.models.video_channel import GeneralKnowledgeVideo
from sqlalchemy import select

async def check_slugs():
    async with get_db_session() as db:
        # Check series videos
        result = await db.execute(select(SeriesVideo).limit(5))
        series_videos = result.scalars().all()
        
        print("Series Videos:")
        print("-" * 80)
        for v in series_videos:
            print(f"ID: {v.id}")
            print(f"Title: {v.title}")
            print(f"Slug: {v.slug}")
            print("-" * 80)
        
        # Check channel videos
        result2 = await db.execute(select(GeneralKnowledgeVideo).limit(5))
        channel_videos = result2.scalars().all()
        
        print("\nChannel Videos:")
        print("-" * 80)
        for v in channel_videos:
            print(f"ID: {v.id}")
            print(f"Title: {v.title}")
            print(f"Slug: {v.slug}")
            print("-" * 80)

if __name__ == "__main__":
    asyncio.run(check_slugs())