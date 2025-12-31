import asyncio
from app.db.database import get_db_session
from app.models.video_progress import VideoWatchProgress
from sqlalchemy import select

async def check_progress_data():
    async with get_db_session() as db:
        # Get all progress records
        result = await db.execute(select(VideoWatchProgress))
        progress_records = result.scalars().all()
        
        print(f"\nTotal progress records: {len(progress_records)}")
        
        if progress_records:
            print("\nProgress records:")
            for p in progress_records:
                print(f"\nUser: {p.user_id}")
                print(f"Video: {p.video_slug}")
                print(f"Type: {p.video_type}")
                print(f"Current Time: {p.current_time}s")
                print(f"Duration: {p.duration}s")
                print(f"Progress: {p.progress_percentage}%")
                print(f"Completed: {p.completed}")
                print(f"Last Watched: {p.last_watched_at}")
        else:
            print("\n⚠️ No progress records found!")
            print("\nThis means the progress is not being saved.")
            print("Check browser console for errors when watching a video.")

if __name__ == "__main__":
    asyncio.run(check_progress_data())