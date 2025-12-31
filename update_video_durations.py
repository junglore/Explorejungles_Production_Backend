"""
Script to update video durations for all existing videos
Run this once to extract and save durations for videos that don't have them
"""
import asyncio
from pathlib import Path
from sqlalchemy import select
from app.db.database import get_db_session
from app.models.video_series import SeriesVideo
from app.models.video_channel import GeneralKnowledgeVideo
from app.utils.video_utils import get_video_duration


async def update_all_video_durations():
    """Update durations for all videos in the database"""
    
    updated_count = 0
    error_count = 0
    
    async with get_db_session() as session:
        print("Fetching all series videos...")
        
        # Get all series videos
        series_result = await session.execute(select(SeriesVideo))
        series_videos = series_result.scalars().all()
        
        print(f"Found {len(series_videos)} series videos")
        
        for video in series_videos:
            try:
                # Skip if already has duration
                if video.duration and video.duration > 0:
                    print(f"  ✓ {video.title} - already has duration ({video.duration}s)")
                    continue
                
                # Get video file path
                if not video.video_url:
                    print(f"  ✗ {video.title} - no video URL")
                    error_count += 1
                    continue
                
                # Remove leading slash and construct full path
                video_path = Path(video.video_url.lstrip('/'))
                
                if not video_path.exists():
                    print(f"  ✗ {video.title} - file not found: {video_path}")
                    error_count += 1
                    continue
                
                # Extract duration
                duration = get_video_duration(str(video_path))
                
                if duration > 0:
                    video.duration = duration
                    print(f"  ✓ {video.title} - updated duration: {duration}s ({duration//60}m {duration%60}s)")
                    updated_count += 1
                else:
                    print(f"  ✗ {video.title} - could not extract duration")
                    error_count += 1
                    
            except Exception as e:
                print(f"  ✗ {video.title} - error: {e}")
                error_count += 1
        
        print("\nFetching all general knowledge videos...")
        
        # Get all general knowledge videos
        gk_result = await session.execute(select(GeneralKnowledgeVideo))
        gk_videos = gk_result.scalars().all()
        
        print(f"Found {len(gk_videos)} general knowledge videos")
        
        for video in gk_videos:
            try:
                # Skip if already has duration
                if video.duration and video.duration > 0:
                    print(f"  ✓ {video.title} - already has duration ({video.duration}s)")
                    continue
                
                # Get video file path
                if not video.video_url:
                    print(f"  ✗ {video.title} - no video URL")
                    error_count += 1
                    continue
                
                # Remove leading slash and construct full path
                video_path = Path(video.video_url.lstrip('/'))
                
                if not video_path.exists():
                    print(f"  ✗ {video.title} - file not found: {video_path}")
                    error_count += 1
                    continue
                
                # Extract duration
                duration = get_video_duration(str(video_path))
                
                if duration > 0:
                    video.duration = duration
                    print(f"  ✓ {video.title} - updated duration: {duration}s ({duration//60}m {duration%60}s)")
                    updated_count += 1
                else:
                    print(f"  ✗ {video.title} - could not extract duration")
                    error_count += 1
                    
            except Exception as e:
                print(f"  ✗ {video.title} - error: {e}")
                error_count += 1
        
        # Commit all changes
        await session.commit()
        
    print("\n" + "="*60)
    print(f"✅ Successfully updated {updated_count} videos")
    print(f"❌ Failed to update {error_count} videos")
    print("="*60)


if __name__ == "__main__":
    print("Starting video duration update...")
    print("="*60)
    asyncio.run(update_all_video_durations())
    print("\nDone! You can now refresh your frontend to see the durations.")