"""
Public API endpoints for videos (series and channels)
For frontend consumption
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from typing import List, Optional
from app.db.database import get_db
from app.models.video_series import VideoSeries, SeriesVideo
from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
from app.models.video_progress import VideoWatchProgress
from app.models.video_engagement import VideoLike, VideoComment, VideoCommentLike
from pydantic import BaseModel
import json

router = APIRouter()


class WatchProgressUpdate(BaseModel):
    current_time: float
    duration: float
    video_type: str


@router.get("")
async def get_all_videos(
    search: Optional[str] = Query(None, description="Search in title, subtitle, description"),
    category: Optional[str] = Query(None, description="Filter by tag category"),
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all videos (series videos + channel videos) for frontend display
    Returns combined list with type indicator and relevant metadata
    Includes watch progress if user is authenticated
    """
    
    if not user_id:
        user_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        videos_list = []
        
        # Fetch all watch progress for this user
        progress_query = select(VideoWatchProgress).where(
            VideoWatchProgress.user_id == user_id
        )
        progress_result = await db.execute(progress_query)
        progress_records = progress_result.scalars().all()
        
        # Create a dictionary for quick lookup
        progress_map = {p.video_slug: p for p in progress_records}
        
        # Fetch series videos with series information
        series_query = select(
            SeriesVideo,
            VideoSeries
        ).join(
            VideoSeries,
            SeriesVideo.series_id == VideoSeries.id
        ).where(
            VideoSeries.is_published == 1,
            # Only include episodes that either have no publish_date or whose publish_date is in the past
            or_(SeriesVideo.publish_date == None, SeriesVideo.publish_date <= func.now())
        ).order_by(VideoSeries.created_at.desc(), SeriesVideo.position)
        
        series_result = await db.execute(series_query)
        series_rows = series_result.all()
        
        for video, series in series_rows:
            # Parse tags from JSON
            try:
                tags = json.loads(video.tags) if video.tags else []
            except:
                tags = []
            
            video_data = {
                "id": str(video.id),
                "title": video.title,
                "subtitle": video.subtitle,
                "description": video.description,
                "thumbnail_url": f"/uploads/{video.thumbnail_url}" if video.thumbnail_url else None,
                "video_url": f"/uploads/{video.video_url}" if video.video_url else None,
                "duration": video.duration,
                "views": video.views or 0,
                "tags": tags,
                "hashtags": video.hashtags or "",
                "type": "series",
                "series_name": series.title,
                "episode_number": video.position,
                "total_episodes": series.total_videos,
                "is_published": True,
                "slug": video.slug,
                "publish_date": video.publish_date.isoformat() if video.publish_date else None,
                "progress_percentage": progress_map[video.slug].progress_percentage if video.slug in progress_map else 0,
                "completed": progress_map[video.slug].completed if video.slug in progress_map else 0
            }
            
            videos_list.append(video_data)
        
        # Fetch channel videos with channel information
        channel_query = select(
            GeneralKnowledgeVideo,
            VideoChannel
        ).join(
            VideoChannel,
            GeneralKnowledgeVideo.channel_id == VideoChannel.id
        ).where(
            GeneralKnowledgeVideo.is_published == True,
            VideoChannel.is_active == True,
            or_(GeneralKnowledgeVideo.publish_date == None, GeneralKnowledgeVideo.publish_date <= func.now())
        ).order_by(GeneralKnowledgeVideo.created_at.desc())
        
        channel_result = await db.execute(channel_query)
        channel_rows = channel_result.all()
        
        for video, channel in channel_rows:
            # Parse tags from JSON
            try:
                tags = json.loads(video.tags) if video.tags else []
            except:
                tags = []
            
            video_data = {
                "id": str(video.id),
                "title": video.title,
                "subtitle": video.subtitle,
                "description": video.description,
                "thumbnail_url": f"/uploads/{video.thumbnail_url}" if video.thumbnail_url else None,
                "video_url": f"/uploads/{video.video_url}" if video.video_url else None,
                "duration": video.duration,
                "views": video.views or 0,
                "tags": tags,
                "hashtags": video.hashtags or "",
                "type": "channel",
                "channel_name": channel.name,
                "is_published": True,
                "slug": video.slug,
                "publish_date": video.publish_date.isoformat() if video.publish_date else None,
                "progress_percentage": progress_map[video.slug].progress_percentage if video.slug in progress_map else 0,
                "completed": progress_map[video.slug].completed if video.slug in progress_map else 0
            }
            
            videos_list.append(video_data)
        
        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            videos_list = [
                v for v in videos_list
                if search_lower in v["title"].lower() 
                or search_lower in (v.get("subtitle") or "").lower()
                or search_lower in (v.get("description") or "").lower()
            ]
        
        # Apply category filter if provided
        if category and category != "all":
            if category == "series":
                videos_list = [v for v in videos_list if v["type"] == "series"]
            else:
                # Filter by tag
                videos_list = [
                    v for v in videos_list
                    if category in [tag.lower() for tag in v["tags"]]
                ]
        
        return {
            "videos": videos_list,
            "total": len(videos_list)
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching videos: {str(e)}")


@router.get("/categories")
async def get_video_categories(
    db: AsyncSession = Depends(get_db)
):
    """
    Get all unique tags from videos for dynamic category generation
    Returns tags with counts
    """
    
    all_tags = {}
    
    # Get tags from series videos (published series only)
    series_query = select(SeriesVideo).join(
        VideoSeries,
        SeriesVideo.series_id == VideoSeries.id
    ).where(VideoSeries.is_published == 1)
    
    series_result = await db.execute(series_query)
    series_videos = series_result.scalars().all()
    
    for video in series_videos:
        try:
            tags = json.loads(video.tags) if video.tags else []
            for tag in tags:
                tag_lower = tag.lower()
                all_tags[tag_lower] = all_tags.get(tag_lower, 0) + 1
        except:
            pass
    
    # Get tags from channel videos (published videos in active channels)
    channel_query = select(GeneralKnowledgeVideo).join(
        VideoChannel,
        GeneralKnowledgeVideo.channel_id == VideoChannel.id
    ).where(
        GeneralKnowledgeVideo.is_published == True,
        VideoChannel.is_active == True
    )
    
    channel_result = await db.execute(channel_query)
    channel_videos = channel_result.scalars().all()
    
    for video in channel_videos:
        try:
            tags = json.loads(video.tags) if video.tags else []
            for tag in tags:
                tag_lower = tag.lower()
                all_tags[tag_lower] = all_tags.get(tag_lower, 0) + 1
        except:
            pass
    
    # Convert to list format
    categories = [
        {
            "name": tag,
            "count": count,
            "label": tag.capitalize()
        }
        for tag, count in all_tags.items()
    ]
    
    # Sort by count descending
    categories.sort(key=lambda x: x["count"], reverse=True)
    
    return {
        "categories": categories
    }


@router.get("/featured-series")
async def get_featured_series(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the featured series with all its videos and user progress
    If no featured series, returns the most recent published series
    """
    
    if not user_id:
        user_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        # Try to get featured series first
        featured_query = select(VideoSeries).where(
            VideoSeries.is_featured == 1,
            VideoSeries.is_published == 1
        ).order_by(VideoSeries.featured_at.desc())
        
        featured_result = await db.execute(featured_query)
        series = featured_result.scalar_one_or_none()
        
        # If no featured series, get most recent published series
        if not series:
            recent_query = select(VideoSeries).where(
                VideoSeries.is_published == 1
            ).order_by(VideoSeries.created_at.desc()).limit(1)
            
            recent_result = await db.execute(recent_query)
            series = recent_result.scalar_one_or_none()
        
        if not series:
            return {
                "featured_series": None,
                "message": "No series available"
            }
        
        # Get all videos in this series
        videos_query = select(SeriesVideo).where(
            SeriesVideo.series_id == series.id
        ).order_by(SeriesVideo.position)
        
        videos_result = await db.execute(videos_query)
        videos = videos_result.scalars().all()
        
        # Get user's progress for all videos in this series
        video_slugs = [v.slug for v in videos]
        progress_query = select(VideoWatchProgress).where(
            VideoWatchProgress.user_id == user_id,
            VideoWatchProgress.video_slug.in_(video_slugs)
        )
        progress_result = await db.execute(progress_query)
        progress_records = progress_result.scalars().all()
        progress_map = {p.video_slug: p for p in progress_records}
        
        # Build videos list with progress
        videos_data = []
        for video in videos:
            progress = progress_map.get(video.slug)
            
            videos_data.append({
                "id": str(video.id),
                "title": video.title,
                "subtitle": video.subtitle,
                "description": video.description,
                "thumbnail_url": f"/uploads/{video.thumbnail_url}" if video.thumbnail_url else None,
                "video_url": f"/uploads/{video.video_url}" if video.video_url else None,
                "duration": video.duration,
                "views": video.views or 0,
                "slug": video.slug,
                "position": video.position,
                "progress_percentage": progress.progress_percentage if progress else 0,
                "completed": progress.completed if progress else False,
                "last_watched": progress.updated_at.isoformat() if progress else None
            })
        
        return {
            "featured_series": {
                "id": str(series.id),
                "title": series.title,
                "subtitle": series.subtitle,
                "description": series.description,
                "thumbnail_url": f"/uploads/{series.thumbnail_url}" if series.thumbnail_url else None,
                "slug": series.slug,
                "total_videos": series.total_videos,
                "total_views": series.total_views,
                "is_featured": series.is_featured == 1,
                "videos": videos_data
            }
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching featured series: {str(e)}")


@router.get("/tv_playlist")
async def get_tv_playlist(
    db: AsyncSession = Depends(get_db)
):
    """Return the ordered TV playlist (admin-selected) for the frontend carousel"""
    try:
        from app.models.tv_playlist import TVPlaylist
        playlist = []
        res = await db.execute(select(TVPlaylist).order_by(TVPlaylist.position))
        items = res.scalars().all()

        # Collect slugs to batch-resolve metadata
        slugs = [i.video_slug for i in items]

        # Resolve series videos
        series_map = {}
        if slugs:
            sres = await db.execute(select(SeriesVideo, VideoSeries).join(VideoSeries, SeriesVideo.series_id == VideoSeries.id).where(SeriesVideo.slug.in_(slugs)))
            for sv, series in sres.all():
                series_map[sv.slug] = {
                    "title": sv.title,
                    "thumbnail_url": sv.thumbnail_url,
                    "type": "series",
                    "parent": series.title
                }

            cres = await db.execute(select(GeneralKnowledgeVideo, VideoChannel).join(VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id).where(GeneralKnowledgeVideo.slug.in_(slugs)))
            channel_map = {}
            for gv, channel in cres.all():
                channel_map[gv.slug] = {
                    "title": gv.title,
                    "thumbnail_url": gv.thumbnail_url,
                    "type": "channel",
                    "parent": channel.name
                }

        for it in items:
            meta = series_map.get(it.video_slug) or channel_map.get(it.video_slug) or {}
            playlist.append({
                "position": it.position,
                "slug": it.video_slug,
                "title": meta.get("title") or it.title,
                "thumbnail_url": meta.get("thumbnail_url") or it.thumbnail_url,
                "type": meta.get("type") or None,
                "parent": meta.get("parent") or None
            })

        return {"playlist": playlist}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching TV playlist: {str(e)}")


@router.get("/recent-watched")
async def get_recent_watched_videos(
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    limit: int = Query(3, description="Number of recent videos to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's most recently watched videos (for General Knowledge section)
    If user hasn't watched any or is guest, returns most recent published videos
    """
    
    if not user_id:
        user_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        videos_data = []
        
        # Try to get user's recent watch history
        progress_query = select(VideoWatchProgress).where(
            VideoWatchProgress.user_id == user_id
        ).order_by(VideoWatchProgress.updated_at.desc()).limit(limit)
        
        progress_result = await db.execute(progress_query)
        progress_records = progress_result.scalars().all()
        
        if progress_records:
            # Get video details for watched videos
            watched_slugs = [p.video_slug for p in progress_records]
            
            # Try series videos first
            series_videos_query = select(SeriesVideo, VideoSeries).join(
                VideoSeries, SeriesVideo.series_id == VideoSeries.id
            ).where(
                SeriesVideo.slug.in_(watched_slugs)
            )
            series_result = await db.execute(series_videos_query)
            series_videos = {v.slug: (v, s) for v, s in series_result.all()}
            
            # Try channel videos
            channel_videos_query = select(GeneralKnowledgeVideo, VideoChannel).join(
                VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id
            ).where(
                GeneralKnowledgeVideo.slug.in_(watched_slugs)
            )
            channel_result = await db.execute(channel_videos_query)
            channel_videos = {v.slug: (v, c) for v, c in channel_result.all()}
            
            # Build videos list maintaining watch order
            for progress in progress_records:
                video_info = None
                video_type = None
                parent_name = None
                
                if progress.video_slug in series_videos:
                    video, series = series_videos[progress.video_slug]
                    video_info = video
                    video_type = "series"
                    parent_name = series.title
                elif progress.video_slug in channel_videos:
                    video, channel = channel_videos[progress.video_slug]
                    video_info = video
                    video_type = "channel"
                    parent_name = channel.name
                
                if video_info:
                    try:
                        tags = json.loads(video_info.tags) if video_info.tags else []
                    except:
                        tags = []
                    
                    videos_data.append({
                        "id": str(video_info.id),
                        "title": video_info.title,
                        "subtitle": video_info.subtitle,
                        "description": video_info.description,
                        "thumbnail_url": f"/uploads/{video_info.thumbnail_url}" if video_info.thumbnail_url else None,
                        "video_url": f"/uploads/{video_info.video_url}" if video_info.video_url else None,
                        "duration": video_info.duration,
                        "views": video_info.views or 0,
                        "slug": video_info.slug,
                        "tags": tags,
                        "type": video_type,
                        "parent_name": parent_name,
                        "progress_percentage": progress.progress_percentage,
                        "completed": progress.completed,
                        "last_watched": progress.updated_at.isoformat()
                    })
        
        # If no watch history or not enough videos, fill with recent published videos
        if len(videos_data) < limit:
            remaining = limit - len(videos_data)
            exclude_slugs = [v["slug"] for v in videos_data]
            
            # Get recent channel videos (General Knowledge videos)
            recent_query = select(GeneralKnowledgeVideo, VideoChannel).join(
                VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id
            ).where(
                GeneralKnowledgeVideo.is_published == True,
                VideoChannel.is_active == True
            )
            
            if exclude_slugs:
                recent_query = recent_query.where(~GeneralKnowledgeVideo.slug.in_(exclude_slugs))
            
            recent_query = recent_query.order_by(GeneralKnowledgeVideo.created_at.desc()).limit(remaining)
            
            recent_result = await db.execute(recent_query)
            recent_videos = recent_result.all()
            
            for video, channel in recent_videos:
                try:
                    tags = json.loads(video.tags) if video.tags else []
                except:
                    tags = []
                
                videos_data.append({
                    "id": str(video.id),
                    "title": video.title,
                    "subtitle": video.subtitle,
                    "description": video.description,
                    "thumbnail_url": f"/uploads/{video.thumbnail_url}" if video.thumbnail_url else None,
                    "video_url": f"/uploads/{video.video_url}" if video.video_url else None,
                    "duration": video.duration,
                    "views": video.views or 0,
                    "slug": video.slug,
                    "tags": tags,
                    "type": "channel",
                    "parent_name": channel.name,
                    "progress_percentage": 0,
                    "completed": False,
                    "last_watched": None
                })
        
        return {
            "recent_videos": videos_data[:limit]
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching recent videos: {str(e)}")


@router.get("/{slug}")
async def get_video_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get single video by slug with series navigation and related videos
    Returns video details, series videos (if part of series), and related videos
    """
    
    try:
        video_data = None
        series_videos = []
        related_videos = []
        
        # Try to find in series videos first
        series_query = select(
            SeriesVideo,
            VideoSeries
        ).join(
            VideoSeries,
            SeriesVideo.series_id == VideoSeries.id
        ).where(
            SeriesVideo.slug == slug,
            VideoSeries.is_published == 1
        )
        
        series_result = await db.execute(series_query)
        series_row = series_result.first()
        
        if series_row:
            video, series = series_row
            
            # Parse tags
            try:
                tags = json.loads(video.tags) if video.tags else []
            except:
                tags = []
            
            video_data = {
                "id": str(video.id),
                "title": video.title,
                "subtitle": video.subtitle,
                "description": video.description,
                "thumbnail_url": f"/uploads/{video.thumbnail_url}" if video.thumbnail_url else None,
                "video_url": f"/uploads/{video.video_url}" if video.video_url else None,
                "duration": video.duration,
                "views": video.views or 0,
                "tags": tags,
                "hashtags": video.hashtags or "",
                "type": "series",
                "series_id": str(series.id),
                "series_name": series.title,
                "episode_number": video.position,
                "total_episodes": series.total_videos,
                "is_published": True,
                "slug": video.slug,
                "created_at": video.created_at.isoformat() if video.created_at else None
            }
            
            # Get all videos in this series for series navigation
            all_series_videos_query = select(SeriesVideo).where(
                SeriesVideo.series_id == series.id
            ).order_by(SeriesVideo.position)
            
            all_series_result = await db.execute(all_series_videos_query)
            all_series_videos = all_series_result.scalars().all()
            
            for sv in all_series_videos:
                try:
                    sv_tags = json.loads(sv.tags) if sv.tags else []
                except:
                    sv_tags = []
                    
                series_videos.append({
                    "id": str(sv.id),
                    "title": sv.title,
                    "subtitle": sv.subtitle,
                    "thumbnail_url": f"/uploads/{sv.thumbnail_url}" if sv.thumbnail_url else None,
                    "video_url": f"/uploads/{sv.video_url}" if sv.video_url else None,
                    "duration": sv.duration,
                    "views": sv.views or 0,
                    "position": sv.position,
                    "slug": sv.slug,
                    "is_current": sv.id == video.id
                })
            
            # Get related videos from same channel or matching tags
            # First, get other videos with matching tags
            if tags:
                # Get series videos with matching tags (excluding current series)
                related_series_query = select(
                    SeriesVideo,
                    VideoSeries
                ).join(
                    VideoSeries,
                    SeriesVideo.series_id == VideoSeries.id
                ).where(
                    VideoSeries.is_published == 1,
                    SeriesVideo.series_id != series.id
                ).limit(10)
                
                related_series_result = await db.execute(related_series_query)
                related_series_rows = related_series_result.all()
                
                for rv, rs in related_series_rows:
                    try:
                        rv_tags = json.loads(rv.tags) if rv.tags else []
                        # Check if any tag matches
                        if any(tag in rv_tags for tag in tags):
                            related_videos.append({
                                "id": str(rv.id),
                                "title": rv.title,
                                "subtitle": rv.subtitle,
                                "thumbnail_url": f"/uploads/{rv.thumbnail_url}" if rv.thumbnail_url else None,
                                "duration": rv.duration,
                                "views": rv.views or 0,
                                "tags": rv_tags,
                                "type": "series",
                                "series_name": rs.title,
                                "slug": rv.slug
                            })
                    except:
                        pass
                
                # Get channel videos with matching tags
                related_channel_query = select(
                    GeneralKnowledgeVideo,
                    VideoChannel
                ).join(
                    VideoChannel,
                    GeneralKnowledgeVideo.channel_id == VideoChannel.id
                ).where(
                    GeneralKnowledgeVideo.is_published == True,
                    VideoChannel.is_active == True
                ).limit(10)
                
                related_channel_result = await db.execute(related_channel_query)
                related_channel_rows = related_channel_result.all()
                
                for rv, rc in related_channel_rows:
                    try:
                        rv_tags = json.loads(rv.tags) if rv.tags else []
                        # Check if any tag matches
                        if any(tag in rv_tags for tag in tags):
                            related_videos.append({
                                "id": str(rv.id),
                                "title": rv.title,
                                "subtitle": rv.subtitle,
                                "thumbnail_url": f"/uploads/{rv.thumbnail_url}" if rv.thumbnail_url else None,
                                "duration": rv.duration,
                                "views": rv.views or 0,
                                "tags": rv_tags,
                                "type": "channel",
                                "channel_name": rc.name,
                                "slug": rv.slug
                            })
                    except:
                        pass
        
        else:
            # Try to find in channel videos
            channel_query = select(
                GeneralKnowledgeVideo,
                VideoChannel
            ).join(
                VideoChannel,
                GeneralKnowledgeVideo.channel_id == VideoChannel.id
            ).where(
                GeneralKnowledgeVideo.slug == slug,
                GeneralKnowledgeVideo.is_published == True,
                VideoChannel.is_active == True
            )
            
            channel_result = await db.execute(channel_query)
            channel_row = channel_result.first()
            
            if channel_row:
                video, channel = channel_row
                
                # Parse tags
                try:
                    tags = json.loads(video.tags) if video.tags else []
                except:
                    tags = []
                
                video_data = {
                    "id": str(video.id),
                    "title": video.title,
                    "subtitle": video.subtitle,
                    "description": video.description,
                    "thumbnail_url": f"/uploads/{video.thumbnail_url}" if video.thumbnail_url else None,
                    "video_url": f"/uploads/{video.video_url}" if video.video_url else None,
                    "duration": video.duration,
                    "views": video.views or 0,
                    "tags": tags,
                    "hashtags": video.hashtags or "",
                    "type": "channel",
                    "channel_id": str(channel.id),
                    "channel_name": channel.name,
                    "is_published": True,
                    "slug": video.slug,
                    "created_at": video.created_at.isoformat() if video.created_at else None
                }
                
                # Get related videos from same channel
                same_channel_query = select(GeneralKnowledgeVideo).where(
                    GeneralKnowledgeVideo.channel_id == channel.id,
                    GeneralKnowledgeVideo.id != video.id,
                    GeneralKnowledgeVideo.is_published == True
                ).limit(6)
                
                same_channel_result = await db.execute(same_channel_query)
                same_channel_videos = same_channel_result.scalars().all()
                
                for rv in same_channel_videos:
                    try:
                        rv_tags = json.loads(rv.tags) if rv.tags else []
                    except:
                        rv_tags = []
                        
                    related_videos.append({
                        "id": str(rv.id),
                        "title": rv.title,
                        "subtitle": rv.subtitle,
                        "thumbnail_url": f"/uploads/{rv.thumbnail_url}" if rv.thumbnail_url else None,
                        "duration": rv.duration,
                        "views": rv.views or 0,
                        "tags": rv_tags,
                        "type": "channel",
                        "channel_name": channel.name,
                        "slug": rv.slug
                    })
                
                # Get videos with matching tags from other channels
                if tags:
                    related_by_tag_query = select(
                        GeneralKnowledgeVideo,
                        VideoChannel
                    ).join(
                        VideoChannel,
                        GeneralKnowledgeVideo.channel_id == VideoChannel.id
                    ).where(
                        GeneralKnowledgeVideo.channel_id != channel.id,
                        GeneralKnowledgeVideo.is_published == True,
                        VideoChannel.is_active == True
                    ).limit(10)
                    
                    related_by_tag_result = await db.execute(related_by_tag_query)
                    related_by_tag_rows = related_by_tag_result.all()
                    
                    for rv, rc in related_by_tag_rows:
                        try:
                            rv_tags = json.loads(rv.tags) if rv.tags else []
                            # Check if any tag matches
                            if any(tag in rv_tags for tag in tags):
                                related_videos.append({
                                    "id": str(rv.id),
                                    "title": rv.title,
                                    "subtitle": rv.subtitle,
                                    "thumbnail_url": f"/uploads/{rv.thumbnail_url}" if rv.thumbnail_url else None,
                                    "duration": rv.duration,
                                    "views": rv.views or 0,
                                    "tags": rv_tags,
                                    "type": "channel",
                                    "channel_name": rc.name,
                                    "slug": rv.slug
                                })
                        except:
                            pass
                    
                    # Also get series videos with matching tags
                    related_series_query = select(
                        SeriesVideo,
                        VideoSeries
                    ).join(
                        VideoSeries,
                        SeriesVideo.series_id == VideoSeries.id
                    ).where(
                        VideoSeries.is_published == 1
                    ).limit(10)
                    
                    related_series_result = await db.execute(related_series_query)
                    related_series_rows = related_series_result.all()
                    
                    for rv, rs in related_series_rows:
                        try:
                            rv_tags = json.loads(rv.tags) if rv.tags else []
                            # Check if any tag matches
                            if any(tag in rv_tags for tag in tags):
                                related_videos.append({
                                    "id": str(rv.id),
                                    "title": rv.title,
                                    "subtitle": rv.subtitle,
                                    "thumbnail_url": f"/uploads/{rv.thumbnail_url}" if rv.thumbnail_url else None,
                                    "duration": rv.duration,
                                    "views": rv.views or 0,
                                    "tags": rv_tags,
                                    "type": "series",
                                    "series_name": rs.title,
                                    "slug": rv.slug
                                })
                        except:
                            pass
        
        if not video_data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Limit related videos to 6
        related_videos = related_videos[:6]
        
        # Get likes/dislikes counts
        likes_query = select(func.count()).select_from(VideoLike).where(
            VideoLike.video_slug == slug,
            VideoLike.vote == 1
        )
        likes_result = await db.execute(likes_query)
        likes_count = likes_result.scalar() or 0
        
        dislikes_query = select(func.count()).select_from(VideoLike).where(
            VideoLike.video_slug == slug,
            VideoLike.vote == -1
        )
        dislikes_result = await db.execute(dislikes_query)
        dislikes_count = dislikes_result.scalar() or 0
        
        # Add likes/dislikes to video data
        video_data["likes"] = likes_count
        video_data["dislikes"] = dislikes_count
        
        return {
            "video": video_data,
            "series_videos": series_videos,
            "related_videos": related_videos
        }
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching video: {str(e)}")


@router.post("/{slug}/view")
async def increment_video_view(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Increment view count for a video
    Called when a user starts watching a video
    """
    
    try:
        # Try to find in series videos first
        series_query = select(SeriesVideo).where(SeriesVideo.slug == slug)
        series_result = await db.execute(series_query)
        series_video = series_result.scalar_one_or_none()
        
        if series_video:
            # Increment series video view count
            series_video.views = (series_video.views or 0) + 1
            
            # Also increment total views for the series
            series_query = select(VideoSeries).where(VideoSeries.id == series_video.series_id)
            series_result = await db.execute(series_query)
            series = series_result.scalar_one_or_none()
            if series:
                series.total_views = (series.total_views or 0) + 1
            
            await db.commit()
            
            return {
                "success": True,
                "views": series_video.views,
                "type": "series"
            }
        
        # Try to find in channel videos
        channel_query = select(GeneralKnowledgeVideo).where(GeneralKnowledgeVideo.slug == slug)
        channel_result = await db.execute(channel_query)
        channel_video = channel_result.scalar_one_or_none()
        
        if channel_video:
            # Increment channel video view count
            channel_video.views = (channel_video.views or 0) + 1
            await db.commit()
            
            return {
                "success": True,
                "views": channel_video.views,
                "type": "channel"
            }
        
        raise HTTPException(status_code=404, detail="Video not found")
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error incrementing view count: {str(e)}")


@router.post("/{slug}/progress")
async def save_watch_progress(
    slug: str,
    progress: WatchProgressUpdate,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Save or update watch progress for a video
    Requires authentication - only logged-in users can save progress
    """
    
    # Require authentication
    if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=401, detail="Must be logged in to save progress")
    
    try:
        # Calculate progress percentage
        progress_percentage = (progress.current_time / progress.duration * 100) if progress.duration > 0 else 0
        completed = 1 if progress_percentage >= 90 else 0  # Mark as completed if >90% watched
        
        # Check if progress record exists
        query = select(VideoWatchProgress).where(
            VideoWatchProgress.user_id == user_id,
            VideoWatchProgress.video_slug == slug
        )
        result = await db.execute(query)
        watch_progress = result.scalar_one_or_none()
        
        if watch_progress:
            # Update existing progress
            watch_progress.current_time = progress.current_time
            watch_progress.duration = progress.duration
            watch_progress.progress_percentage = progress_percentage
            watch_progress.completed = completed
            watch_progress.last_watched_at = func.now()
        else:
            # Create new progress record
            watch_progress = VideoWatchProgress(
                user_id=user_id,
                video_slug=slug,
                video_type=progress.video_type,
                current_time=progress.current_time,
                duration=progress.duration,
                progress_percentage=progress_percentage,
                completed=completed
            )
            db.add(watch_progress)
        
        await db.commit()
        
        return {
            "success": True,
            "progress_percentage": progress_percentage,
            "completed": completed
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving progress: {str(e)}")


@router.get("/{slug}/progress")
async def get_watch_progress(
    slug: str,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get watch progress for a specific video
    """
    
    if not user_id:
        user_id = "00000000-0000-0000-0000-000000000000"
    
    try:
        query = select(VideoWatchProgress).where(
            VideoWatchProgress.user_id == user_id,
            VideoWatchProgress.video_slug == slug
        )
        result = await db.execute(query)
        progress = result.scalar_one_or_none()
        
        if progress:
            return {
                "current_time": progress.current_time,
                "duration": progress.duration,
                "progress_percentage": progress.progress_percentage,
                "completed": progress.completed
            }
        
        return {
            "current_time": 0,
            "duration": 0,
            "progress_percentage": 0,
            "completed": 0
        }
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error fetching progress: {str(e)}")


# ==================== LIKES/DISLIKES ====================

class VoteRequest(BaseModel):
    vote: int  # 1 for like, -1 for dislike


@router.post("/{slug}/like")
async def toggle_video_like(
    slug: str,
    vote_data: VoteRequest,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Like or dislike a video
    vote: 1 = like, -1 = dislike
    If user already voted the same, remove the vote
    If user voted opposite, change the vote
    """
    
    if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=401, detail="Must be logged in to vote")
    
    if vote_data.vote not in [1, -1]:
        raise HTTPException(status_code=400, detail="Vote must be 1 (like) or -1 (dislike)")
    
    try:
        # Check if video exists and get type
        series_query = select(SeriesVideo).where(SeriesVideo.slug == slug)
        series_result = await db.execute(series_query)
        series_video = series_result.scalar_one_or_none()
        
        video_type = None
        if series_video:
            video_type = "series"
        else:
            channel_query = select(GeneralKnowledgeVideo).where(GeneralKnowledgeVideo.slug == slug)
            channel_result = await db.execute(channel_query)
            channel_video = channel_result.scalar_one_or_none()
            if channel_video:
                video_type = "channel"
        
        if not video_type:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Check if user already voted
        existing_query = select(VideoLike).where(
            VideoLike.user_id == user_id,
            VideoLike.video_slug == slug
        )
        existing_result = await db.execute(existing_query)
        existing_vote = existing_result.scalar_one_or_none()
        
        if existing_vote:
            if existing_vote.vote == vote_data.vote:
                # Remove vote if clicking same button
                await db.delete(existing_vote)
                await db.commit()
                return {"message": "Vote removed", "action": "removed"}
            else:
                # Change vote
                existing_vote.vote = vote_data.vote
                await db.commit()
                return {"message": "Vote updated", "action": "updated"}
        else:
            # New vote
            new_vote = VideoLike(
                user_id=user_id,
                video_slug=slug,
                video_type=video_type,
                vote=vote_data.vote
            )
            db.add(new_vote)
            await db.commit()
            return {"message": "Vote added", "action": "added"}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error voting: {str(e)}")


@router.get("/{slug}/likes")
async def get_video_likes(
    slug: str,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get like/dislike counts for a video and user's current vote
    """
    
    try:
        # Count likes
        likes_query = select(func.count()).select_from(VideoLike).where(
            VideoLike.video_slug == slug,
            VideoLike.vote == 1
        )
        likes_result = await db.execute(likes_query)
        likes_count = likes_result.scalar() or 0
        
        # Count dislikes
        dislikes_query = select(func.count()).select_from(VideoLike).where(
            VideoLike.video_slug == slug,
            VideoLike.vote == -1
        )
        dislikes_result = await db.execute(dislikes_query)
        dislikes_count = dislikes_result.scalar() or 0
        
        # Get user's vote if authenticated
        user_vote = None
        if user_id and user_id != "00000000-0000-0000-0000-000000000000":
            user_vote_query = select(VideoLike.vote).where(
                VideoLike.user_id == user_id,
                VideoLike.video_slug == slug
            )
            user_vote_result = await db.execute(user_vote_query)
            user_vote = user_vote_result.scalar_one_or_none()
        
        return {
            "likes": likes_count,
            "dislikes": dislikes_count,
            "user_vote": user_vote  # null, 1, or -1
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching likes: {str(e)}")


# ==================== COMMENTS ====================

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[str] = None


@router.post("/{slug}/comments")
async def add_video_comment(
    slug: str,
    comment_data: CommentCreate,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a comment to a video
    Supports replies via parent_id
    """
    
    if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=401, detail="Must be logged in to comment")
    
    if not comment_data.content or len(comment_data.content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    
    try:
        # Check if video exists and get type
        series_query = select(SeriesVideo).where(SeriesVideo.slug == slug)
        series_result = await db.execute(series_query)
        series_video = series_result.scalar_one_or_none()
        
        video_type = None
        if series_video:
            video_type = "series"
        else:
            channel_query = select(GeneralKnowledgeVideo).where(GeneralKnowledgeVideo.slug == slug)
            channel_result = await db.execute(channel_query)
            channel_video = channel_result.scalar_one_or_none()
            if channel_video:
                video_type = "channel"
        
        if not video_type:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Create comment
        new_comment = VideoComment(
            user_id=user_id,
            video_slug=slug,
            video_type=video_type,
            content=comment_data.content.strip(),
            parent_id=comment_data.parent_id
        )
        db.add(new_comment)
        
        # Update parent comment replies_count if it's a reply
        if comment_data.parent_id:
            parent_query = select(VideoComment).where(VideoComment.id == comment_data.parent_id)
            parent_result = await db.execute(parent_query)
            parent_comment = parent_result.scalar_one_or_none()
            if parent_comment:
                parent_comment.replies_count += 1
        
        await db.commit()
        await db.refresh(new_comment)
        
        # Get user info for response
        from app.models.user import User
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        return {
            "id": str(new_comment.id),
            "content": new_comment.content,
            "created_at": new_comment.created_at.isoformat(),
            "user": {
                "id": str(user.id) if user else None,
                "username": user.username if user else "Unknown",
                "avatar_url": user.avatar_url if user else None
            },
            "likes_count": 0,
            "replies_count": 0
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error adding comment: {str(e)}")


@router.get("/{slug}/comments")
async def get_video_comments(
    slug: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comments for a video
    Returns top-level comments (parent_id is null) with user info
    """
    
    try:
        from app.models.user import User
        
        # Get total count
        count_query = select(func.count()).select_from(VideoComment).where(
            VideoComment.video_slug == slug,
            VideoComment.parent_id == None,
            VideoComment.is_deleted == 0
        )
        count_result = await db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Get comments with user info
        query = (
            select(VideoComment, User)
            .join(User, VideoComment.user_id == User.id)
            .where(
                VideoComment.video_slug == slug,
                VideoComment.parent_id == None,
                VideoComment.is_deleted == 0
            )
            .order_by(VideoComment.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        comments_with_users = result.all()
        
        comments_list = []
        for comment, user in comments_with_users:
            comments_list.append({
                "id": str(comment.id),
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url
                },
                "likes_count": comment.likes_count,
                "replies_count": comment.replies_count,
                "is_edited": comment.is_edited
            })
        
        return {
            "comments": comments_list,
            "total": total_count,
            "skip": skip,
            "limit": limit
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching comments: {str(e)}")


@router.post("/comments/{comment_id}/like")
async def toggle_comment_like(
    comment_id: str,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle like on a comment
    """
    
    if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=401, detail="Must be logged in to like comments")
    
    try:
        # Check if comment exists
        comment_query = select(VideoComment).where(VideoComment.id == comment_id)
        comment_result = await db.execute(comment_query)
        comment = comment_result.scalar_one_or_none()
        
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user already liked
        existing_query = select(VideoCommentLike).where(
            VideoCommentLike.user_id == user_id,
            VideoCommentLike.comment_id == comment_id
        )
        existing_result = await db.execute(existing_query)
        existing_like = existing_result.scalar_one_or_none()
        
        if existing_like:
            # Remove like
            await db.delete(existing_like)
            comment.likes_count = max(0, comment.likes_count - 1)
            await db.commit()
            return {"message": "Like removed", "likes_count": comment.likes_count}
        else:
            # Add like
            new_like = VideoCommentLike(
                user_id=user_id,
                comment_id=comment_id
            )
            db.add(new_like)
            comment.likes_count += 1
            await db.commit()
            return {"message": "Like added", "likes_count": comment.likes_count}
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error liking comment: {str(e)}")


@router.get("/comments/{comment_id}/replies")
async def get_comment_replies(
    comment_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get replies for a specific comment"""
    try:
        from app.models.user import User
        
        # Fetch replies (comments with this parent_id)
        query = (
            select(VideoComment, User)
            .join(User, VideoComment.user_id == User.id)
            .where(VideoComment.parent_id == comment_id)
            .order_by(VideoComment.created_at.asc())
        )
        result = await db.execute(query)
        replies_data = result.all()
        
        replies = []
        for comment, user in replies_data:
            replies.append({
                "id": str(comment.id),
                "content": comment.content,
                "created_at": comment.created_at.isoformat(),
                "likes_count": comment.likes_count,
                "user_id": str(comment.user_id),
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "avatar_url": user.avatar_url
                }
            })
        
        return {"replies": replies}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching replies: {str(e)}")


@router.patch("/comments/{comment_id}")
async def edit_comment(
    comment_id: str,
    content: dict,
    user_id: Optional[str] = Header(None, alias="X-User-ID"),
    db: AsyncSession = Depends(get_db)
):
    """Edit a comment (only by the comment owner)"""
    if not user_id or user_id == "00000000-0000-0000-0000-000000000000":
        raise HTTPException(status_code=401, detail="Must be logged in to edit comments")
    
    new_content = content.get("content", "").strip()
    if not new_content:
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    
    try:
        # Find the comment
        query = select(VideoComment).where(VideoComment.id == comment_id)
        result = await db.execute(query)
        comment = result.scalar_one_or_none()
        
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        # Check if user owns the comment
        if str(comment.user_id) != user_id:
            raise HTTPException(status_code=403, detail="You can only edit your own comments")
        
        # Update the comment
        comment.content = new_content
        comment.updated_at = func.now()
        
        await db.commit()
        
        return {"message": "Comment updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error editing comment: {str(e)}")