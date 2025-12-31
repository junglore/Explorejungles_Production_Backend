"""
Video management admin routes
Handles video upload, editing, and management for community videos section
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_, or_, text, text
from typing import Optional, List
from uuid import UUID, uuid4
import os
from pathlib import Path
import shutil
from datetime import datetime

from app.db.database import get_db, get_db_session
from app.models.media import Media, MediaTypeEnum
from app.models.user import User
from app.models.video_series import VideoSeries, SeriesVideo
from app.models.video_channel import GeneralKnowledgeVideo
from app.models.video_tag import VideoTag
from app.admin.templates.base import create_html_page
from app.services.file_upload import file_upload_service
import json

router = APIRouter()


@router.get("/videos", response_class=HTMLResponse)
async def videos_management(request: Request):
    """Video library management page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    content = """
    <div class="page-header">
        <div>
            <h1 class="page-title">Video Library</h1>
            <p class="page-subtitle">Manage community videos and educational content</p>
        </div>
        <div style="display: flex; gap: 1rem;">
            <a href="/admin/videos/analytics?period=week" class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-chart-line"></i> Analytics
            </a>
            <button class="btn btn-primary" onclick="openVideoTypeModal()">
                <i class="fas fa-plus"></i> Add Video
            </button>
            <button class="btn btn-primary" onclick="openTVModal()" style="background: #2d3748; border-color: #2d3748;">
                <i class="fas fa-tv"></i> TV
            </button>
        </div>
    </div>
    
    <!-- Video Management Section -->
    <div style="margin-bottom: 2rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <h2 style="font-size: 1.5rem; font-weight: 700; color: #2d3748; margin: 0;">
                <i class="fas fa-video"></i> Video Management
            </h2>
            <a href="/admin/videos/tags" class="btn btn-secondary" style="text-decoration: none;">
                <i class="fas fa-tags"></i> Manage Tags
            </a>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem;">
            <a href="/admin/videos/all" style="text-decoration: none;">
                <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); border-radius: 12px; padding: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: pointer;" onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 12px rgba(0, 0, 0, 0.15)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0, 0, 0, 0.1)';">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div style="width: 60px; height: 60px; background: rgba(255, 255, 255, 0.2); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                            <i class="fas fa-th-large" style="font-size: 1.75rem; color: white;"></i>
                        </div>
                        <i class="fas fa-arrow-right" style="color: white; font-size: 1.25rem;"></i>
                    </div>
                    <h3 style="color: white; font-size: 1.25rem; font-weight: 700; margin: 0 0 0.5rem 0;">All Videos</h3>
                    <p style="color: rgba(255, 255, 255, 0.9); margin: 0; font-size: 0.95rem;">View and manage all videos in one place</p>
                </div>
            </a>
            
            <a href="/admin/videos/series" style="text-decoration: none;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: pointer;" onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 12px rgba(0, 0, 0, 0.15)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0, 0, 0, 0.1)';">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div style="width: 60px; height: 60px; background: rgba(255, 255, 255, 0.2); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                            <i class="fas fa-film" style="font-size: 1.75rem; color: white;"></i>
                        </div>
                        <i class="fas fa-arrow-right" style="color: white; font-size: 1.25rem;"></i>
                    </div>
                    <h3 style="color: white; font-size: 1.25rem; font-weight: 700; margin: 0 0 0.5rem 0;">Video Series</h3>
                    <p style="color: rgba(255, 255, 255, 0.9); margin: 0; font-size: 0.95rem;">Browse and manage episodic video series</p>
                </div>
            </a>
            
            <a href="/admin/videos/channels" style="text-decoration: none;">
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 12px; padding: 2rem; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); transition: transform 0.3s ease, box-shadow 0.3s ease; cursor: pointer;" onmouseover="this.style.transform='translateY(-4px)'; this.style.boxShadow='0 8px 12px rgba(0, 0, 0, 0.15)';" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 6px rgba(0, 0, 0, 0.1)';">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                        <div style="width: 60px; height: 60px; background: rgba(255, 255, 255, 0.2); border-radius: 12px; display: flex; align-items: center; justify-content: center;">
                            <i class="fas fa-tv" style="font-size: 1.75rem; color: white;"></i>
                        </div>
                        <i class="fas fa-arrow-right" style="color: white; font-size: 1.25rem;"></i>
                    </div>
                    <h3 style="color: white; font-size: 1.25rem; font-weight: 700; margin: 0 0 0.5rem 0;">Channels</h3>
                    <p style="color: rgba(255, 255, 255, 0.9); margin: 0; font-size: 0.95rem;">Manage video channels and playlists</p>
                </div>
            </a>
        </div>
    </div>
    
    <!-- Video Type Selection Modal -->
    <div id="video-type-modal" class="modal">
        <div class="modal-content" style="max-width: 700px;">
            <div class="modal-header">
                <h2><i class="fas fa-video"></i> Select Video Type</h2>
                <button class="modal-close" onclick="closeVideoTypeModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <p style="margin-bottom: 2rem; color: #718096; text-align: center;">Choose the type of video you want to add</p>
                
                <div class="video-type-grid">
                    <div class="video-type-card" onclick="selectVideoType('series')">
                        <div class="video-type-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                            <i class="fas fa-film"></i>
                        </div>
                        <h3>Video Series</h3>
                        <p>Create a series of related videos organized in episodes</p>
                        <div class="video-type-arrow">
                            <i class="fas fa-arrow-right"></i>
                        </div>
                    </div>
                    
                    <div class="video-type-card" onclick="selectVideoType('knowledge')">
                        <div class="video-type-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                            <i class="fas fa-graduation-cap"></i>
                        </div>
                        <h3>General Knowledge</h3>
                        <p>Educational content and informative videos</p>
                        <div class="video-type-arrow">
                            <i class="fas fa-arrow-right"></i>
                        </div>
                    </div>
                    
                    <div class="video-type-card" onclick="selectVideoType('normal')">
                        <div class="video-type-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                            <i class="fas fa-video"></i>
                        </div>
                        <h3>Normal Video</h3>
                        <p>Single standalone video content</p>
                        <div class="video-type-arrow">
                            <i class="fas fa-arrow-right"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <style>
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            align-items: center;
            justify-content: center;
        }
        
        .modal.active {
            display: flex;
        }
        
        .modal-content {
            background: white;
            border-radius: 12px;
            max-width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: modalSlideIn 0.3s ease-out;
        }
        
        @keyframes modalSlideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .modal-header {
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-header h2 {
            margin: 0;
            color: #2d3748;
            font-size: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 1.5rem;
            color: #a0aec0;
            cursor: pointer;
            padding: 0.25rem;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            transition: all 0.2s ease;
        }
        
        .modal-close:hover {
            background: #f7fafc;
            color: #2d3748;
        }
        
        .modal-body {
            padding: 2rem;
        }
        
        .video-type-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
        }
        
        .video-type-card {
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 2rem 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .video-type-card:hover {
            border-color: #667eea;
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
        }
        
        .video-type-icon {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 1.5rem;
            transition: transform 0.3s ease;
        }
        
        .video-type-card:hover .video-type-icon {
            transform: scale(1.1);
        }
        
        .video-type-icon i {
            font-size: 2rem;
            color: white;
        }
        
        .video-type-card h3 {
            font-size: 1.25rem;
            font-weight: 700;
            color: #2d3748;
            margin: 0 0 0.75rem 0;
        }
        
        .video-type-card p {
            font-size: 0.95rem;
            color: #718096;
            margin: 0;
            line-height: 1.5;
        }
        
        .video-type-arrow {
            position: absolute;
            bottom: 1rem;
            right: 1rem;
            width: 32px;
            height: 32px;
            background: #f7fafc;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: all 0.3s ease;
        }
        
        .video-type-card:hover .video-type-arrow {
            opacity: 1;
            background: #667eea;
        }
        
        .video-type-arrow i {
            color: #667eea;
            font-size: 0.9rem;
        }
        
        .video-type-card:hover .video-type-arrow i {
            color: white;
        }
        
        @media (max-width: 768px) {
            .video-type-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    
    <script>
        function openVideoTypeModal() {
            document.getElementById('video-type-modal').classList.add('active');
        }
        
        function closeVideoTypeModal() {
            document.getElementById('video-type-modal').classList.remove('active');
        }
        
        function selectVideoType(type) {
            if (type === 'series') {
                window.location.href = '/admin/videos/create-series';
            } else if (type === 'knowledge') {
                window.location.href = '/admin/videos/general-knowledge/create';
            } else if (type === 'normal') {
                // Handle normal video
                alert('Normal video - Coming soon');
            }
            closeVideoTypeModal();
        }
        
        // Close modal on outside click
        window.onclick = function(event) {
            const modal = document.getElementById('video-type-modal');
            if (event.target === modal) {
                closeVideoTypeModal();
            }
        }
    </script>
    """

    # Append TV selector modal (populated via admin endpoint)
    content = content + """
    <!-- TV Selector Modal -->
    <div id="tv-modal" class="modal">
        <div class="modal-content" style="max-width: 900px;">
            <div class="modal-header">
                <h2><i class="fas fa-tv"></i> Select TV Videos (max 3)</h2>
                <button class="modal-close" onclick="closeTVModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <form id="tv-form">
                    <div id="tv-options" style="max-height: 400px; overflow-y: auto;">
                        <!-- options loaded dynamically -->
                    </div>
                    <div style="display:flex; gap:1rem; justify-content:flex-end; margin-top:1rem;">
                        <button type="button" class="btn btn-secondary" onclick="closeTVModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">Save TV Selection</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
        function openTVModal(){
            document.getElementById('tv-modal').classList.add('active');
            loadTVOptions();
        }
        function closeTVModal(){ document.getElementById('tv-modal').classList.remove('active'); }

        async function loadTVOptions(){
            try{
                const res = await fetch('/admin/videos/tv/options');
                const data = await res.json();
                const container = document.getElementById('tv-options');
                container.innerHTML = '';
                const selectedRes = await fetch('/admin/videos/tv');
                const selData = await selectedRes.json();
                const selected = selData.selected || [];
                data.forEach(item=>{
                    const checked = selected.includes(item.slug) ? 'checked' : '';
                    const row = document.createElement('div');
                    row.className = 'tv-option';
                    row.innerHTML = `<label><input type="checkbox" name="tv_video" value="${item.slug}" ${checked}> ${item.title} (${item.parent})</label>`;
                    container.appendChild(row);
                });
            }catch(e){ console.error('Failed to load TV options', e); }
        }

        // Enforce max 3 selection
        document.addEventListener('change', function(e){
            if(e.target && e.target.name === 'tv_video'){
                const checked = document.querySelectorAll('#tv-options input[name="tv_video"]:checked');
                if(checked.length > 3){ e.target.checked = false; alert('You can select up to 3 videos for TV.'); }
            }
        });

        document.getElementById('tv-form').addEventListener('submit', async function(e){
            e.preventDefault();
            const selected = Array.from(document.querySelectorAll('#tv-options input[name="tv_video"]:checked')).map(cb=>cb.value);
            try{
                const res = await fetch('/admin/videos/tv', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({selected}) });
                const data = await res.json();
                if(data.success){ alert('TV selection saved'); closeTVModal(); } else alert('Failed to save');
            }catch(err){ console.error(err); alert('Save failed'); }
        });
    </script>
    """

    return HTMLResponse(content=create_html_page("Video Library", content, "videos"))


@router.get("/videos/tv/options")
async def admin_tv_options(request: Request):
    """Return list of all videos (slug, title, parent name) for TV selector"""
    if not request.session.get("authenticated"):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
        options = []
        async with get_db_session() as session:
            series_videos_result = await session.execute(
                select(SeriesVideo, VideoSeries).join(VideoSeries, SeriesVideo.series_id == VideoSeries.id).order_by(desc(SeriesVideo.created_at))
            )
            for video, series in series_videos_result.all():
                options.append({"slug": video.slug, "title": video.title, "parent": series.title, "type": "series"})

            channel_videos_result = await session.execute(
                select(GeneralKnowledgeVideo, VideoChannel).join(VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id).order_by(desc(GeneralKnowledgeVideo.created_at))
            )
            for video, channel in channel_videos_result.all():
                options.append({"slug": video.slug, "title": video.title, "parent": channel.name, "type": "channel"})

        return JSONResponse(content=options)
    except Exception as e:
        print('Error fetching TV options:', e)
        return JSONResponse(status_code=500, content={"error": "Failed to load options"})


@router.get("/videos/tv")
async def admin_get_tv(request: Request):
    """Return current TV selection"""
    if not request.session.get("authenticated"):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})
    try:
        from app.models.tv_playlist import TVPlaylist
        selected = []
        async with get_db_session() as session:
            res = await session.execute(select(TVPlaylist).order_by(TVPlaylist.position))
            rows = res.scalars().all()
            selected = [r.video_slug for r in rows]

        return JSONResponse(content={"selected": selected})
    except Exception as e:
        print('Error reading TV selection:', e)
        return JSONResponse(status_code=500, content={"error": "Failed to load selection"})


@router.post("/videos/tv")
async def admin_save_tv(request: Request):
    """Save TV selection (expects JSON {selected: [slugs]})"""
    if not request.session.get("authenticated"):
        return JSONResponse(status_code=401, content={"error": "Unauthorized"})

    try:
        body = await request.json()
        selected = body.get('selected', []) if isinstance(body, dict) else []
        if not isinstance(selected, list) or len(selected) > 3:
            return JSONResponse(status_code=400, content={"success": False, "message": "Select up to 3 videos"})
        # Persist selection into TVPlaylist table
        from app.models.tv_playlist import TVPlaylist
        async with get_db_session() as session:
            # Remove existing entries
            await session.execute(text("DELETE FROM tv_playlist"))
            # Insert new entries with positions
            for idx, slug in enumerate(selected, start=1):
                # Try to fetch basic metadata (title, thumbnail) from videos
                title = None
                thumbnail = None
                try:
                    from app.models.video_series import SeriesVideo, VideoSeries
                    res = await session.execute(select(SeriesVideo).where(SeriesVideo.slug == slug).limit(1))
                    sv = res.scalar_one_or_none()
                    if sv:
                        title = sv.title
                        thumbnail = sv.thumbnail_url
                    else:
                        from app.models.video_channel import GeneralKnowledgeVideo
                        res2 = await session.execute(select(GeneralKnowledgeVideo).where(GeneralKnowledgeVideo.slug == slug).limit(1))
                        gv = res2.scalar_one_or_none()
                        if gv:
                            title = gv.title
                            thumbnail = gv.thumbnail_url
                except Exception:
                    pass

                new = TVPlaylist(position=idx, video_slug=slug, title=title, thumbnail_url=thumbnail)
                session.add(new)
            await session.commit()

        return JSONResponse(content={"success": True})
    except Exception as e:
        print('Error saving TV selection:', e)
        return JSONResponse(status_code=500, content={"success": False, "message": "Failed to save"})


@router.get("/videos/all", response_class=HTMLResponse)
async def all_videos(request: Request):
    """View all videos from series and channels in one place"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
        from app.models.video_engagement import VideoComment, VideoLike
        
        all_videos = []
        all_tags = set()
        
        async with get_db_session() as session:
            # Get all series videos
            series_videos_result = await session.execute(
                select(SeriesVideo, VideoSeries)
                .join(VideoSeries, SeriesVideo.series_id == VideoSeries.id)
                .order_by(desc(SeriesVideo.created_at))
            )
            series_videos = series_videos_result.all()
            
            for video, series in series_videos:
                # Parse tags
                try:
                    tags = json.loads(video.tags) if video.tags else []
                    all_tags.update(tags)
                except:
                    tags = []
                
                # Get comment count for this video
                comment_count_result = await session.execute(
                    select(func.count(VideoComment.id))
                    .where(VideoComment.video_slug == video.slug, VideoComment.is_deleted == 0, VideoComment.parent_id == None)
                )
                comment_count = comment_count_result.scalar() or 0
                
                # Get like count for this video
                like_count_result = await session.execute(
                    select(func.count(VideoLike.id))
                    .where(VideoLike.video_slug == video.slug, VideoLike.vote == 1)
                )
                like_count = like_count_result.scalar() or 0
                
                all_videos.append({
                    'id': str(video.id),
                    'title': video.title,
                    'subtitle': video.subtitle or '',
                    'thumbnail_url': video.thumbnail_url,
                    'video_url': video.video_url,
                    'slug': video.slug,
                    'views': video.views or 0,
                    'likes': like_count,
                    'comments': comment_count,
                    'tags': tags,
                    'is_published': series.is_published == 1,  # Series-level publishing
                    'created_at': video.created_at.isoformat() if video.created_at else None,
                    'type': 'series',
                    'series_name': series.title,
                    'series_id': str(series.id),
                    'episode_number': video.position,
                    'total_episodes': series.total_videos
                })
            
            # Get all channel videos
            channel_videos_result = await session.execute(
                select(GeneralKnowledgeVideo, VideoChannel)
                .join(VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id)
                .order_by(desc(GeneralKnowledgeVideo.created_at))
            )
            channel_videos = channel_videos_result.all()
            
            for video, channel in channel_videos:
                # Parse tags
                try:
                    tags = json.loads(video.tags) if video.tags else []
                    all_tags.update(tags)
                except:
                    tags = []
                
                # Get comment count for this video
                comment_count_result = await session.execute(
                    select(func.count(VideoComment.id))
                    .where(VideoComment.video_slug == video.slug, VideoComment.is_deleted == 0, VideoComment.parent_id == None)
                )
                comment_count = comment_count_result.scalar() or 0
                
                # Get like count for this video
                like_count_result = await session.execute(
                    select(func.count(VideoLike.id))
                    .where(VideoLike.video_slug == video.slug, VideoLike.vote == 1)
                )
                like_count = like_count_result.scalar() or 0
                
                all_videos.append({
                    'id': str(video.id),
                    'title': video.title,
                    'subtitle': video.subtitle or '',
                    'thumbnail_url': video.thumbnail_url,
                    'video_url': video.video_url,
                    'slug': video.slug,
                    'views': video.views or 0,
                    'likes': like_count,
                    'comments': comment_count,
                    'tags': tags,
                    'is_published': video.is_published,
                    'created_at': video.created_at.isoformat() if video.created_at else None,
                    'type': 'channel',
                    'channel_name': channel.name,
                    'channel_id': str(channel.id)
                })
        
        # Sort all videos by created_at initially
        all_videos.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Generate tag options HTML
        tags_options = ''.join([f'<option value="{tag}">{tag}</option>' for tag in sorted(all_tags)])
        
        content = f"""
        <div class="page-header">
            <div>
                <h1 class="page-title"><i class="fas fa-th-large"></i> All Videos</h1>
                <p class="page-subtitle">View and manage all videos from series and channels</p>
            </div>
            <div style="display: flex; gap: 1rem;">
                <a href="/admin/videos" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back
                </a>
                <button class="btn btn-primary" onclick="openFilterModal()">
                    <i class="fas fa-filter"></i> Filter
                </button>
            </div>
        </div>
        
        <!-- Stats Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-video" style="font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <p style="margin: 0; opacity: 0.9; font-size: 0.85rem;">Total Videos</p>
                        <h3 style="margin: 0.25rem 0 0 0; font-size: 1.75rem; font-weight: 700;">{len(all_videos)}</h3>
                    </div>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-tv" style="font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <p style="margin: 0; opacity: 0.9; font-size: 0.85rem;">Channel Videos</p>
                        <h3 style="margin: 0.25rem 0 0 0; font-size: 1.75rem; font-weight: 700;">{len([v for v in all_videos if v['type'] == 'channel'])}</h3>
                    </div>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-film" style="font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <p style="margin: 0; opacity: 0.9; font-size: 0.85rem;">Series Videos</p>
                        <h3 style="margin: 0.25rem 0 0 0; font-size: 1.75rem; font-weight: 700;">{len([v for v in all_videos if v['type'] == 'series'])}</h3>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Search and Filter -->
        <div style="background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);">
            <div style="display: grid; grid-template-columns: 2fr 1fr 1fr 1fr 1fr; gap: 1rem; align-items: center;">
                <div>
                    <input type="text" id="search-input" placeholder="🔍 Search videos by title..." style="width: 100%; padding: 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem;" onkeyup="filterVideos()">
                </div>
                <select id="type-filter" style="padding: 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; cursor: pointer; width: 100%;" onchange="filterVideos()">
                    <option value="all">All Types</option>
                    <option value="series">Series Videos</option>
                    <option value="channel">Channel Videos</option>
                </select>
                <select id="status-filter" style="padding: 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; cursor: pointer; width: 100%;" onchange="filterVideos()">
                    <option value="all">All Status</option>
                    <option value="published">Published</option>
                    <option value="draft">Draft</option>
                </select>
                <select id="tag-filter" style="padding: 0.75rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; cursor: pointer; width: 100%;" onchange="filterVideos()">
                    <option value="all">All Tags</option>
                    {tags_options}
                </select>
                <select id="sort-filter" style="padding: 0.75rem; border: 2px solid #667eea; border-radius: 8px; font-size: 0.95rem; cursor: pointer; width: 100%; background: white; color: #667eea; font-weight: 600;" onchange="filterVideos()">
                    <option value="recent" style="background: white; color: #2d3748;">📅 Most Recent</option>
                    <option value="views" style="background: white; color: #2d3748;">👁️ Most Views</option>
                    <option value="likes" style="background: white; color: #2d3748;">👍 Most Likes</option>
                    <option value="comments" style="background: white; color: #2d3748;">💬 Most Comments</option>
                    <option value="engagement" style="background: white; color: #2d3748;">🔥 Most Engaging</option>
                </select>
            </div>
        </div>
        
        <!-- Videos Grid -->
        <div id="videos-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem;">
            {generate_all_videos_cards(all_videos)}
        </div>
        
        <style>
            .video-card {{
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
            }}
            
            .video-card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
            }}
            
            .video-thumbnail {{
                width: 100%;
                height: 180px;
                object-fit: cover;
                background: #f7fafc;
            }}
            
            .video-badge {{
                position: absolute;
                top: 0.75rem;
                right: 0.75rem;
                padding: 0.375rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                color: white;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
            }}
            
            .badge-series {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            
            .badge-channel {{
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            }}
            
            .video-meta {{
                position: absolute;
                top: 0.75rem;
                left: 0.75rem;
                padding: 0.375rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                background: rgba(0, 0, 0, 0.7);
                color: white;
            }}
            
            .video-content {{
                padding: 1.5rem;
            }}
            
            .video-title {{
                font-size: 1.1rem;
                font-weight: 600;
                color: #2d3748;
                margin: 0 0 0.5rem 0;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }}
            
            .video-subtitle {{
                font-size: 0.9rem;
                color: #718096;
                margin: 0 0 1rem 0;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }}
            
            .video-stats {{
                display: flex;
                align-items: center;
                gap: 1rem;
                font-size: 0.85rem;
                color: #a0aec0;
                padding-top: 1rem;
                border-top: 1px solid #e2e8f0;
            }}
            
            .video-stat {{
                display: flex;
                align-items: center;
                gap: 0.25rem;
            }}
            
            .video-source {{
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                padding: 0.5rem 1rem;
                background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
                border-radius: 8px;
                font-size: 0.85rem;
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.75rem;
            }}
            
            .empty-state {{
                text-align: center;
                padding: 4rem 2rem;
                background: white;
                border-radius: 12px;
            }}
            
            .empty-state i {{
                font-size: 3rem;
                color: #cbd5e0;
                margin-bottom: 1rem;
            }}
        </style>
        
        <script>
            const allVideosData = {json.dumps(all_videos)};
            
            function filterVideos() {{
                const searchTerm = document.getElementById('search-input').value.toLowerCase();
                const typeFilter = document.getElementById('type-filter').value;
                const statusFilter = document.getElementById('status-filter').value;
                const tagFilter = document.getElementById('tag-filter').value;
                const sortFilter = document.getElementById('sort-filter').value;
                
                let filtered = allVideosData.filter(video => {{
                    const matchesSearch = video.title.toLowerCase().includes(searchTerm) || 
                                        (video.subtitle && video.subtitle.toLowerCase().includes(searchTerm));
                    const matchesType = typeFilter === 'all' || video.type === typeFilter;
                    const matchesStatus = statusFilter === 'all' || 
                                        (statusFilter === 'published' && video.is_published) ||
                                        (statusFilter === 'draft' && !video.is_published);
                    const matchesTag = tagFilter === 'all' || (video.tags && video.tags.includes(tagFilter));
                    
                    return matchesSearch && matchesType && matchesStatus && matchesTag;
                }});
                
                // Apply sorting
                switch(sortFilter) {{
                    case 'views':
                        filtered.sort((a, b) => (b.views || 0) - (a.views || 0));
                        break;
                    case 'likes':
                        filtered.sort((a, b) => (b.likes || 0) - (a.likes || 0));
                        break;
                    case 'comments':
                        filtered.sort((a, b) => (b.comments || 0) - (a.comments || 0));
                        break;
                    case 'engagement':
                        filtered.sort((a, b) => {{
                            const engagementA = (a.likes || 0) + (a.comments || 0);
                            const engagementB = (b.likes || 0) + (b.comments || 0);
                            return engagementB - engagementA;
                        }});
                        break;
                    case 'recent':
                    default:
                        filtered.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
                        break;
                }}
                
                displayVideos(filtered);
            }}
            
            function displayVideos(videos) {{
                const grid = document.getElementById('videos-grid');
                
                if (videos.length === 0) {{
                    grid.innerHTML = `
                        <div class="empty-state" style="grid-column: 1 / -1;">
                            <i class="fas fa-video-slash"></i>
                            <h3 style="color: #2d3748; margin: 0 0 0.5rem 0;">No Videos Found</h3>
                            <p style="color: #718096; margin: 0;">Try adjusting your filters or search term</p>
                        </div>
                    `;
                    return;
                }}
                
                grid.innerHTML = videos.map(video => {{
                    const thumbnail = video.thumbnail_url ? `/uploads/${{video.thumbnail_url}}` : '/static/images/video-placeholder.jpg';
                    const statusBadge = video.is_published 
                        ? '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; background: #48bb78; color: white;">Published</span>'
                        : '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; background: #ed8936; color: white;">Draft</span>';
                    
                    let sourceBadge = '';
                    let sourceInfo = '';
                    let clickAction = '';
                    
                    if (video.type === 'series') {{
                        sourceBadge = `<div class="video-badge badge-series"><i class="fas fa-film"></i> Episode ${{video.episode_number}}/${{video.total_episodes}}</div>`;
                        sourceInfo = `<div class="video-source"><i class="fas fa-film" style="color: #667eea;"></i> ${{video.series_name}}</div>`;
                        clickAction = `onclick="window.location.href='/admin/videos/series/${{video.series_id}}'"`;
                    }} else {{
                        sourceBadge = `<div class="video-badge badge-channel"><i class="fas fa-tv"></i> Channel</div>`;
                        sourceInfo = `<div class="video-source"><i class="fas fa-tv" style="color: #f093fb;"></i> ${{video.channel_name}}</div>`;
                        clickAction = `onclick="window.location.href='/admin/videos/channels/${{video.channel_id}}'"`;
                    }}
                    
                    return `
                        <div class="video-card" ${{clickAction}}>
                            <img src="${{thumbnail}}" alt="${{video.title}}" class="video-thumbnail">
                            ${{sourceBadge}}
                            <div class="video-content">
                                ${{sourceInfo}}
                                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                                    <h3 class="video-title">${{video.title}}</h3>
                                    ${{statusBadge}}
                                </div>
                                <p class="video-subtitle">${{video.subtitle || 'No subtitle'}}</p>
                                <div class="video-stats">
                                    <div class="video-stat">
                                        <i class="fas fa-eye"></i>
                                        <span>${{(video.views || 0).toLocaleString()}} views</span>
                                    </div>
                                    <div class="video-stat">
                                        <i class="fas fa-thumbs-up"></i>
                                        <span>${{(video.likes || 0).toLocaleString()}}</span>
                                    </div>
                                    <div class="video-stat">
                                        <i class="fas fa-comments"></i>
                                        <span>${{(video.comments || 0).toLocaleString()}}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    `;
                }}).join('');
            }}
            
            // Initialize display
            displayVideos(allVideosData);
        </script>
        """
        
        return HTMLResponse(content=create_html_page("All Videos", content, "videos"))
        
    except Exception as e:
        print(f"Error loading all videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_all_videos_cards(videos):
    """Generate HTML cards for all videos"""
    if not videos:
        return """
        <div class="empty-state" style="grid-column: 1 / -1;">
            <i class="fas fa-video-slash"></i>
            <h3 style="color: #2d3748; margin: 0 0 0.5rem 0;">No Videos Yet</h3>
            <p style="color: #718096; margin: 0;">Start by creating a video series or uploading to a channel</p>
        </div>
        """
    
    return ""  # JavaScript will handle rendering


@router.get("/videos/series", response_class=HTMLResponse)
async def video_series_list(request: Request, search: Optional[str] = None, status: Optional[str] = None):
    """List all video series with search and filter"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Fetch series from database with filters
    async with get_db_session() as session:
        query = select(VideoSeries)
        
        # Apply search filter
        if search:
            query = query.where(
                or_(
                    VideoSeries.title.ilike(f"%{search}%"),
                    VideoSeries.subtitle.ilike(f"%{search}%"),
                    VideoSeries.slug.ilike(f"%{search}%")
                )
            )
        
        # Apply status filter
        if status and status in ['published', 'draft']:
            status_value = 1 if status == 'published' else 0
            query = query.where(VideoSeries.is_published == status_value)
        
        query = query.order_by(desc(VideoSeries.created_at))
        result = await session.execute(query)
        all_series = result.scalars().all()
        
        series_data = [
            {
                'id': str(series.id),
                'title': series.title,
                'subtitle': series.subtitle or '',
                'slug': series.slug,
                'video_count': series.total_videos,
                'views': series.total_views,
                'is_published': series.is_published,
                'is_featured': series.is_featured,
                'featured_at': series.featured_at.isoformat() if series.featured_at else None
            }
            for series in all_series
        ]
    
    content = f"""
    <div class="page-header">
        <div>
            <h1 class="page-title">Video Series</h1>
            <p class="page-subtitle">Manage all video series</p>
        </div>
        <div style="display: flex; gap: 1rem;">
            <a href="/admin/videos" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to Library
            </a>
            <a href="/admin/videos/create-series" class="btn btn-primary">
                <i class="fas fa-plus"></i> Add Series
            </a>
        </div>
    </div>
    
    <!-- Search and Filter Section -->
    <div style="background: white; border-radius: 12px; padding: 1.5rem; margin: 1.5rem 0; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
        <form method="get" action="/admin/videos/series" style="display: flex; gap: 1rem; flex-wrap: wrap; align-items: flex-end;">
            <div style="flex: 1; min-width: 250px;">
                <label style="display: block; font-size: 0.9rem; font-weight: 600; color: #2d3748; margin-bottom: 0.5rem;">
                    <i class="fas fa-search"></i> Search Series
                </label>
                <input type="text" name="search" value="{search or ''}" placeholder="Search by title, subtitle, or slug..." 
                       style="width: 100%; padding: 0.75rem 1rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; transition: border-color 0.2s;" 
                       onfocus="this.style.borderColor='#667eea'" onblur="this.style.borderColor='#e2e8f0'">
            </div>
            <div style="min-width: 180px;">
                <label style="display: block; font-size: 0.9rem; font-weight: 600; color: #2d3748; margin-bottom: 0.5rem;">
                    <i class="fas fa-filter"></i> Status
                </label>
                <select name="status" style="width: 100%; padding: 0.75rem 1rem; border: 2px solid #e2e8f0; border-radius: 8px; font-size: 0.95rem; background: white;">
                    <option value="">All Status</option>
                    <option value="published" {'selected' if status == 'published' else ''}>Published</option>
                    <option value="draft" {'selected' if status == 'draft' else ''}>Draft</option>
                </select>
            </div>
            <button type="submit" class="btn btn-primary" style="height: fit-content;">
                <i class="fas fa-search"></i> Filter
            </button>
            <a href="/admin/videos/series" class="btn btn-secondary" style="height: fit-content; text-decoration: none;">
                <i class="fas fa-redo"></i> Reset
            </a>
        </form>
    </div>
    
    <div id="series-container">
        {generate_series_cards(series_data)}
    </div>
    
    <style>
        .series-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }}
        
        .series-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}
        
        .series-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
        }}
        
        .series-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            color: white;
        }}
        
        .series-title {{
            font-size: 1.25rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
        }}
        
        .series-subtitle {{
            font-size: 0.95rem;
            opacity: 0.9;
            margin: 0;
        }}
        
        .series-body {{
            padding: 1.5rem;
        }}
        
        .series-info {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .series-info-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #718096;
            font-size: 0.9rem;
        }}
        
        .series-actions {{
            display: flex;
            gap: 0.5rem;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 4rem 2rem;
            background: white;
            border-radius: 12px;
            margin-top: 2rem;
        }}
        
        .empty-state i {{
            font-size: 4rem;
            color: #cbd5e0;
            margin-bottom: 1rem;
        }}
        
        .empty-state h3 {{
            font-size: 1.5rem;
            color: #2d3748;
            margin: 0 0 0.5rem 0;
        }}
        
        .empty-state p {{
            color: #718096;
            margin: 0 0 1.5rem 0;
        }}
    </style>
    """
    
    return HTMLResponse(content=create_html_page("Video Series", content, "videos"))


def generate_series_cards(series_data):
    """Generate HTML for series cards"""
    if not series_data:
        return """
        <div class="empty-state">
            <i class="fas fa-film"></i>
            <h3>No Series Found</h3>
            <p>Try adjusting your search or filters, or create a new video series</p>
            <a href="/admin/videos/create-series" class="btn btn-primary">
                <i class="fas fa-plus"></i> Create Series
            </a>
        </div>
        """
    
    cards_html = '<div class="series-grid">'
    for series in series_data:
        status_badge = '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; background: #48bb78; color: white;">Published</span>' if series.get('is_published', 1) == 1 else '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; background: #ed8936; color: white;">Draft</span>'
        
        # Featured badge
        featured_badge = ''
        featured_action = ''
        if series.get('is_featured'):
            featured_badge = '<div style="position: absolute; top: 0.75rem; right: 0.75rem; padding: 0.5rem 1rem; background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); border-radius: 20px; font-size: 0.75rem; font-weight: 700; color: #fff; box-shadow: 0 4px 8px rgba(255, 215, 0, 0.3);"><i class="fas fa-star"></i> FEATURED</div>'
            featured_action = f'<button class="btn btn-sm" style="background: #e0e0e0; color: #666;" onclick="event.stopPropagation(); unfeaturedSeries(\'{series["id"]}\', \'{series["title"]}\')"><i class="fas fa-star-half-alt"></i> Unfeatured</button>'
        else:
            featured_action = f'<button class="btn btn-sm" style="background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%); color: white;" onclick="event.stopPropagation(); setFeaturedSeries(\'{series["id"]}\', \'{series["title"]}\')"><i class="fas fa-star"></i> Set Featured</button>'
        
        cards_html += f"""
        <div class="series-card" onclick="window.location.href='/admin/videos/series/{series['id']}'" style="position: relative;">
            {featured_badge}
            <div class="series-header">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <h3 class="series-title" style="margin: 0; flex: 1;">{series['title']}</h3>
                    {status_badge}
                </div>
                <p class="series-subtitle">{series.get('subtitle', '')}</p>
            </div>
            <div class="series-body">
                <div class="series-info">
                    <div class="series-info-item">
                        <i class="fas fa-video"></i>
                        <span>{series.get('video_count', 0)} Videos</span>
                    </div>
                    <div class="series-info-item">
                        <i class="fas fa-eye"></i>
                        <span>{series.get('views', 0)} Views</span>
                    </div>
                </div>
                <div class="series-actions" style="display: flex; gap: 0.5rem;">
                    {featured_action}
                    <a href="/admin/videos/series/{series['id']}" class="btn btn-primary" style="flex: 1;" onclick="event.stopPropagation()">
                        <i class="fas fa-eye"></i> View
                    </a>
                    <a href="/admin/videos/series/{series['id']}/edit" class="btn btn-secondary" onclick="event.stopPropagation()">
                        <i class="fas fa-edit"></i> Edit
                    </a>
                </div>
            </div>
        </div>
        """
    cards_html += '</div>'
    
    # Add JavaScript for featured series management
    cards_html += """
    <script>
        async function setFeaturedSeries(seriesId, seriesTitle) {
            if (!confirm(`Set "${seriesTitle}" as the featured series? This will unfeatured any currently featured series.`)) {
                return;
            }
            
            try {
                const response = await fetch(`/admin/videos/series/${seriesId}/set-featured`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.status) {
                    showNotification(result.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification('Error: ' + result.message, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('Error setting featured series', 'error');
            }
        }
        
        async function unfeaturedSeries(seriesId, seriesTitle) {
            if (!confirm(`Remove "${seriesTitle}" from featured series?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/admin/videos/series/${seriesId}/unfeature`, {
                    method: 'POST'
                });
                
                const result = await response.json();
                
                if (result.status) {
                    showNotification(result.message, 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification('Error: ' + result.message, 'error');
                }
            } catch (error) {
                console.error('Error:', error);
                showNotification('Error unfeaturing series', 'error');
            }
        }
        
        function showNotification(message, type) {
            const notification = document.createElement('div');
            notification.style.cssText = `
                position: fixed;
                top: 2rem;
                right: 2rem;
                padding: 1rem 1.5rem;
                background: ${type === 'success' ? '#48bb78' : '#f56565'};
                color: white;
                border-radius: 12px;
                box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
                z-index: 9999;
                font-weight: 600;
                animation: slideIn 0.3s ease;
            `;
            notification.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> ${message}`;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.animation = 'slideOut 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
        
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(400px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(400px); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    </script>
    """
    
    return cards_html


@router.get("/videos/series/{series_id}", response_class=HTMLResponse)
async def view_series(request: Request, series_id: str):
    """View a specific video series and its videos"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Fetch series and videos from database
    async with get_db_session() as session:
        # Get series
        series_result = await session.execute(
            select(VideoSeries).where(VideoSeries.id == UUID(series_id))
        )
        series_obj = series_result.scalar_one_or_none()
        
        if not series_obj:
            raise HTTPException(status_code=404, detail="Series not found")
        
        series = {
            'id': str(series_obj.id),
            'title': series_obj.title,
            'subtitle': series_obj.subtitle or '',
            'slug': series_obj.slug,
            'video_count': series_obj.total_videos
        }
        
        # Get videos in series
        videos_result = await session.execute(
            select(SeriesVideo)
            .where(SeriesVideo.series_id == series_obj.id)
            .order_by(SeriesVideo.position)
        )
        videos_objs = videos_result.scalars().all()
        
        videos = [
            {
                'id': str(video.id),
                'title': video.title,
                'subtitle': video.subtitle or '',
                'position': video.position,
                'slug': video.slug,
                'video_url': video.video_url
            }
            for video in videos_objs
        ]
    
    content = f"""
    <div class="page-header">
        <div>
            <h1 class="page-title">{series['title']}</h1>
            <p class="page-subtitle">{series.get('subtitle', '')}</p>
        </div>
        <div style="display: flex; gap: 1rem;">
            <button id="bulk-delete-btn" class="btn btn-danger" onclick="bulkDeleteVideos()" style="display: none;">
                <i class="fas fa-trash-alt"></i> Delete Selected (<span id="selected-count">0</span>)
            </button>
            <a href="/admin/videos/series" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to Series
            </a>
            <a href="/admin/videos/series/{series_id}/edit" class="btn btn-secondary">
                <i class="fas fa-edit"></i> Edit Series
            </a>
            <button class="btn btn-danger" onclick="deleteSeries('{series_id}')">
                <i class="fas fa-trash"></i> Delete Series
            </button>
        </div>
    </div>
    
    <div style="background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
        <h3 style="font-size: 1.1rem; font-weight: 700; color: #2d3748; margin: 0 0 1rem 0;">
            <i class="fas fa-info-circle"></i> Series Details
        </h3>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
            <div>
                <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Slug</label>
                <span style="font-weight: 600; color: #2d3748;">{series['slug']}</span>
            </div>
            <div>
                <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Total Videos</label>
                <span style="font-weight: 600; color: #2d3748;">{series['video_count']}</span>
            </div>
        </div>
    </div>
    
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #2d3748; margin: 0;">
            <i class="fas fa-video"></i> Videos in Series
        </h2>
        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-weight: 600; color: #667eea;">
            <input type="checkbox" id="select-all" onchange="toggleSelectAll()" style="width: 18px; height: 18px; cursor: pointer;">
            Select All
        </label>
    </div>
    
    <div id="videos-list">
        {generate_video_list(videos, series_id)}
    </div>
    
    <style>
        .video-item {{
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            gap: 1.5rem;
            transition: transform 0.2s ease;
        }}
        
        .video-item:hover {{
            transform: translateX(4px);
        }}
        
        .video-number {{
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            font-size: 1.25rem;
            flex-shrink: 0;
        }}
        
        .video-details {{
            flex: 1;
        }}
        
        .video-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: #2d3748;
            margin: 0 0 0.25rem 0;
        }}
        
        .video-subtitle {{
            font-size: 0.9rem;
            color: #718096;
            margin: 0;
        }}
        
        .video-actions {{
            display: flex;
            gap: 0.5rem;
        }}
        
        .empty-videos {{
            text-align: center;
            padding: 3rem 2rem;
            background: white;
            border-radius: 12px;
        }}
        
        .empty-videos i {{
            font-size: 3rem;
            color: #cbd5e0;
            margin-bottom: 1rem;
        }}
    </style>
    
    <script>
        function viewVideoStats(slug, event) {{
            // Don't navigate if clicking on checkbox or buttons
            if (event && (event.target.type === 'checkbox' || event.target.closest('.btn'))) {{
                return;
            }}
            window.location.href = `/admin/video/${{slug}}/stats`;
        }}
        
        async function deleteSeries(seriesId) {{
            if (!confirm('Are you sure you want to delete this series? This will delete all videos in the series.')) {{
                return;
            }}
            
            try {{
                const response = await fetch(`/admin/videos/series/${{seriesId}}`, {{
                    method: 'DELETE'
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    alert(result.message);
                    window.location.href = '/admin/videos/series';
                }} else {{
                    alert('Error: ' + result.message);
                }}
            }} catch (error) {{
                console.error('Error:', error);
                alert('Error deleting series');
            }}
        }}
        
        let selectedVideos = new Set();
        
        function toggleVideoSelection(videoId, checkbox) {{
            if (checkbox.checked) {{
                selectedVideos.add(videoId);
            }} else {{
                selectedVideos.delete(videoId);
            }}
            updateBulkDeleteButton();
        }}
        
        function toggleSelectAll() {{
            const selectAll = document.getElementById('select-all');
            const checkboxes = document.querySelectorAll('.video-checkbox');
            selectedVideos.clear();
            
            checkboxes.forEach(cb => {{
                cb.checked = selectAll.checked;
                if (selectAll.checked) {{
                    selectedVideos.add(cb.value);
                }}
            }});
            
            updateBulkDeleteButton();
        }}
        
        function updateBulkDeleteButton() {{
            const bulkBtn = document.getElementById('bulk-delete-btn');
            const countSpan = document.getElementById('selected-count');
            
            if (selectedVideos.size > 0) {{
                bulkBtn.style.display = 'block';
                countSpan.textContent = selectedVideos.size;
            }} else {{
                bulkBtn.style.display = 'none';
            }}
        }}
        
        async function bulkDeleteVideos() {{
            if (!confirm(`Are you sure you want to delete ${{selectedVideos.size}} selected video(s)?`)) {{
                return;
            }}
            
            try {{
                const videoIds = Array.from(selectedVideos);
                const response = await fetch('/admin/videos/series/bulk-delete', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ video_ids: videoIds }})
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    alert(result.message);
                    location.reload();
                }} else {{
                    alert('Error: ' + result.message);
                }}
            }} catch (error) {{
                console.error('Error:', error);
                alert('Error deleting videos');
            }}
        }}
    </script>
    """
    
    return HTMLResponse(content=create_html_page(f"Series: {series['title']}", content, "videos"))


def generate_video_list(videos, series_id=None):
    """Generate HTML for video list"""
    if not videos:
        return """
        <div class="empty-videos">
            <i class="fas fa-video-slash"></i>
            <h3 style="color: #2d3748; margin: 0 0 0.5rem 0;">No Videos Yet</h3>
            <p style="color: #718096; margin: 0;">Add videos to this series to get started</p>
        </div>
        """
    
    videos_html = ''
    for idx, video in enumerate(videos, 1):
        videos_html += f"""
        <div class="video-item" id="video-{video['id']}" style="cursor: pointer;" onclick="viewVideoStats('{video['slug']}', event)">
            <input type="checkbox" class="video-checkbox" value="{video['id']}" 
                   onchange="toggleVideoSelection('{video['id']}', this)" 
                   onclick="event.stopPropagation()"
                   style="width: 20px; height: 20px; cursor: pointer; flex-shrink: 0;">
            <div class="video-number">{idx}</div>
            <div class="video-details">
                <h4 class="video-title">{video['title']}</h4>
                <p class="video-subtitle">{video.get('subtitle', '')}</p>
            </div>
            <div class="video-actions">
                <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); window.location.href='/admin/video/{video['slug']}/stats'">
                    <i class="fas fa-chart-line"></i> Stats
                </button>
            </div>
        </div>
        """
    return videos_html


@router.get("/videos/series/{series_id}/edit", response_class=HTMLResponse)
async def edit_series(request: Request, series_id: str):
    """Edit a video series"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Fetch series and videos from database
    async with get_db_session() as session:
        # Get series
        series_result = await session.execute(
            select(VideoSeries).where(VideoSeries.id == UUID(series_id))
        )
        series_obj = series_result.scalar_one_or_none()
        
        if not series_obj:
            raise HTTPException(status_code=404, detail="Series not found")
        
        # Get videos in series
        videos_result = await session.execute(
            select(SeriesVideo)
            .where(SeriesVideo.series_id == series_obj.id)
            .order_by(SeriesVideo.position)
        )
        videos_objs = videos_result.scalars().all()
        
        # Fetch tags from database
        tags_result = await session.execute(
            select(VideoTag).order_by(VideoTag.usage_count.desc(), VideoTag.name)
        )
        tags_objs = tags_result.scalars().all()
        predefined_tags = [tag.name for tag in tags_objs]
    
    content = f"""
    <div class="page-header">
        <div>
            <h1 class="page-title">Edit Series</h1>
            <p class="page-subtitle">Update series information and videos</p>
        </div>
        <a href="/admin/videos/series/{series_id}" class="btn btn-secondary">
            <i class="fas fa-arrow-left"></i> Back to Series
        </a>
    </div>
    
    <div id="message-container"></div>
    
    <form id="edit-series-form" class="form-container">
        <input type="hidden" name="series_id" value="{series_id}">
        
        <div class="form-section">
            <h3 class="section-title">
                <i class="fas fa-film"></i> Series Information
            </h3>
            
            <div class="form-row">
                <div class="form-group" style="flex: 2;">
                    <label for="series-title">Series Title *</label>
                    <input type="text" id="series-title" name="title" class="form-control" 
                           value="{series_obj.title}" required onkeyup="formatSeriesSlug()">
                </div>
                <div class="form-group">
                    <label for="series-subtitle">Subtitle</label>
                    <input type="text" id="series-subtitle" name="subtitle" class="form-control" 
                           value="{series_obj.subtitle or ''}">
                </div>
            </div>
            
            <div class="form-group">
                <label for="series-slug">Series Slug *</label>
                <input type="text" id="series-slug" name="slug" class="form-control" 
                       value="{series_obj.slug}" required>
                <small class="field-help">URL-friendly identifier (lowercase, hyphens)</small>
            </div>
        </div>
        
        <!-- Videos Section -->
        <div class="form-section">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 class="section-title" style="margin-bottom: 0;">
                    <i class="fas fa-video"></i> <span id="videos-count">Videos ({len(videos_objs)} videos)</span>
                </h3>
                <button type="button" class="btn btn-success" onclick="addNewVideo()">
                    <i class="fas fa-plus"></i> Add Video
                </button>
            </div>
            <div style="background: #eef2ff; border: 2px solid #667eea; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;">
                <p style="margin: 0; color: #4c51bf; font-weight: 600;">
                    <i class="fas fa-info-circle"></i> Drag videos by the grip icon to change their order in the series. Click "Add Video" to add new episodes.
                </p>
            </div>
            <div id="videos-container">
                {generate_edit_video_forms(videos_objs, predefined_tags)}
            </div>
        </div>
        
        <div class="form-actions">
            <button type="button" class="btn btn-secondary" onclick="window.history.back()">
                <i class="fas fa-times"></i> Cancel
            </button>
            <button type="submit" class="btn btn-primary">
                <i class="fas fa-save"></i> Save All Changes
            </button>
        </div>
    </form>
    
    <script>
        let videoTags = {{}};
        const predefinedTags = {predefined_tags};
        let draggedElement = null;
        
        // Initialize video tags from existing data
        {generate_video_tags_init(videos_objs)}
        
        // Drag and drop handlers
        function handleDragStart(e) {{
            draggedElement = e.currentTarget;
            e.currentTarget.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        }}
        
        function handleDragEnd(e) {{
            e.currentTarget.classList.remove('dragging');
            document.querySelectorAll('.video-form-section').forEach(section => {{
                section.classList.remove('drag-over');
            }});
            updateVideoNumbers();
        }}
        
        function handleDragOver(e) {{
            if (e.preventDefault) e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            e.currentTarget.classList.add('drag-over');
            return false;
        }}
        
        function handleDrop(e) {{
            if (e.stopPropagation) e.stopPropagation();
            
            const dropTarget = e.currentTarget;
            
            if (draggedElement && draggedElement !== dropTarget) {{
                const bounding = dropTarget.getBoundingClientRect();
                const offset = e.clientY - bounding.top;
                const midpoint = bounding.height / 2;
                
                if (offset > midpoint) {{
                    dropTarget.parentNode.insertBefore(draggedElement, dropTarget.nextSibling);
                }} else {{
                    dropTarget.parentNode.insertBefore(draggedElement, dropTarget);
                }}
            }}
            
            return false;
        }}
        
        function handleDragLeave(e) {{
            e.currentTarget.classList.remove('drag-over');
        }}
        
        function updateVideoNumbers() {{
            const videoSections = document.querySelectorAll('.video-form-section');
            videoSections.forEach((section, index) => {{
                const newPosition = index + 1;
                
                // Update visual episode number
                const videoNumber = section.querySelector('.video-number');
                if (videoNumber) {{
                    // Find the NEW badge or Episode text
                    const newBadge = videoNumber.querySelector('span[style*="gradient"]');
                    const icon = videoNumber.querySelector('i.fa-video');
                    
                    videoNumber.innerHTML = '';
                    if (icon) videoNumber.appendChild(icon.cloneNode(true));
                    if (newBadge) videoNumber.appendChild(newBadge.cloneNode(true));
                    videoNumber.innerHTML += ` Episode ${{newPosition}}`;
                }}
                
                // Update position input
                const positionInput = section.querySelector('.video-position-input');
                if (positionInput) {{
                    positionInput.value = newPosition;
                }}
                
                // Update episode input
                const episodeInput = section.querySelector('input[name$="_episode"]');
                if (episodeInput) {{
                    episodeInput.value = newPosition;
                }}
            }});
        }}
        
        function formatSeriesSlug() {{
            const title = document.getElementById('series-title').value;
            const slug = document.getElementById('series-slug');
            slug.value = title.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/^-+|-+$/g, '');
        }}
        
        function formatSlug(input) {{
            input.value = input.value.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/^-+|-+$/g, '');
        }}
        
        let newVideoCounter = {len(videos_objs) + 1};  // Start from next number
        
        function addNewVideo() {{
            const container = document.getElementById('videos-container');
            const videoNum = newVideoCounter++;
            
            // Find max episode number to suggest next
            const existingEpisodes = Array.from(document.querySelectorAll('[name*="_episode"]'))
                .map(input => parseInt(input.value) || 0);
            const suggestedEpisode = existingEpisodes.length > 0 ? Math.max(...existingEpisodes) + 1 : videoNum;
            
            // Initialize tags for new video
            videoTags[videoNum] = [];
            
            const predefinedTagsHTML = predefinedTags.map(tag => 
                `<span class="tag-option" onclick="toggleTag(${{videoNum}}, this)" data-tag="${{tag}}">${{tag}}</span>`
            ).join(' ');
            
            console.log('Adding new video', videoNum, 'suggested episode:', suggestedEpisode);
            
            const newVideoHtml = `
                <div class="video-form-section" draggable="true" data-video-id="new-${{videoNum}}" data-position="${{videoNum}}" ondragstart="handleDragStart(event)" ondragend="handleDragEnd(event)" ondragover="handleDragOver(event)" ondrop="handleDrop(event)" ondragleave="handleDragLeave(event)" style="border: 2px solid #48bb78;">
                    <input type="hidden" name="video_${{videoNum}}_id" value="new">
                    <input type="hidden" name="video_${{videoNum}}_position" value="${{videoNum}}" class="video-position-input">
                    <input type="hidden" name="video_${{videoNum}}_episode" value="${{suggestedEpisode}}">
                    <div class="video-header">
                        <div class="drag-handle">
                            <i class="fas fa-grip-vertical"></i>
                        </div>
                        <h4 class="video-number">
                            <i class="fas fa-video"></i>
                            <span style="background: linear-gradient(135deg, #48bb78 0%, #38a169 100%); padding: 0.25rem 0.75rem; border-radius: 12px; color: white; font-size: 0.75rem; margin-right: 0.5rem;">NEW</span>
                            Episode ${{suggestedEpisode}}
                        </h4>
                        <div style="display: flex; gap: 0.5rem;">
                            <button type="button" class="btn-icon" onclick="moveVideoUp(this)" title="Move Up">
                                <i class="fas fa-arrow-up"></i>
                            </button>
                            <button type="button" class="btn-icon" onclick="moveVideoDown(this)" title="Move Down">
                                <i class="fas fa-arrow-down"></i>
                            </button>
                            <button type="button" class="btn-icon" onclick="removeNewVideo(this)" title="Remove Video" style="color: #e53e3e;">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group" style="flex: 2;">
                            <label for="video-${{videoNum}}-title">Video Title *</label>
                            <input type="text" id="video-${{videoNum}}-title" name="video_${{videoNum}}_title" 
                                   class="form-control" required placeholder="e.g., Episode ${{suggestedEpisode}}: Wildlife Adventure">
                        </div>
                        <div class="form-group">
                            <label for="video-${{videoNum}}-subtitle">Subtitle</label>
                            <input type="text" id="video-${{videoNum}}-subtitle" name="video_${{videoNum}}_subtitle" 
                                   class="form-control" placeholder="Episode subtitle">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="video-${{videoNum}}-slug">Slug *</label>
                            <input type="text" id="video-${{videoNum}}-slug" name="video_${{videoNum}}_slug" 
                                   class="form-control" required placeholder="e.g., wildlife-adventure"
                                   onkeyup="formatSlug(this)">
                            <small class="field-help">Auto-formats on typing</small>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{videoNum}}-description">Description</label>
                        <textarea id="video-${{videoNum}}-description" name="video_${{videoNum}}_description" 
                                  class="form-control" rows="3" 
                                  placeholder="Brief description of this video..."></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{videoNum}}-file">Video File *</label>
                        <div class="file-upload-box" onclick="document.getElementById('video-${{videoNum}}-file').click()">
                            <i class="fas fa-cloud-upload-alt"></i>
                            <p>Click to upload video file</p>
                            <small>Leave empty to keep current video</small>
                        </div>
                        <input type="file" id="video-${{videoNum}}-file" name="video_${{videoNum}}_file" 
                               accept="video/*" style="display: none;" onchange="handleVideoUpload(${{videoNum}}, this)" required>
                        <small id="file-name-${{videoNum}}" style="display: none; margin-top: 0.5rem; color: #4CAF50;"></small>
                        
                        <div id="video-preview-${{videoNum}}" style="display: none; margin-top: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                                <i class="fas fa-eye"></i> New Video Preview
                            </label>
                            <video id="video-player-${{videoNum}}" controls style="width: 100%; max-width: 500px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                                Your browser does not support the video tag.
                            </video>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{videoNum}}-thumbnail">Video Thumbnail</label>
                        <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                            <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="document.getElementById('video-${{videoNum}}-thumbnail').click()">
                                <i class="fas fa-upload"></i> Upload Thumbnail
                            </button>
                            <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="captureFrameFromVideo(${{videoNum}})">
                                <i class="fas fa-camera"></i> Capture from Video
                            </button>
                        </div>
                        <input type="file" id="video-${{videoNum}}-thumbnail" name="video_${{videoNum}}_thumbnail" 
                               accept="image/*" style="display: none;" onchange="handleThumbnailUpload(${{videoNum}}, this)">
                        <div id="thumbnail-preview-${{videoNum}}" style="display: none; margin-top: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                                <i class="fas fa-image"></i> New Thumbnail Preview
                            </label>
                            <img id="thumbnail-image-${{videoNum}}" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="Thumbnail preview">
                        </div>
                        <canvas id="thumbnail-canvas-${{videoNum}}" style="display: none;"></canvas>
                    </div>
                    
                    <div class="form-group">
                        <label>Publish Date (optional)</label>
                        <input type="datetime-local" id="video-${{num}}-publish" name="video_${{num}}_publish_date" class="form-control">
                        <small class="field-help">If set, the video will become visible on the frontend only on this date/time.</small>
                    </div>

                    <div class="form-group">
                        <label>Tags</label>
                        <div class="tags-container" id="tags-container-${{videoNum}}">
                            ${{predefinedTagsHTML}}
                        </div>
                        <div class="custom-tag-input" style="margin-top: 1rem;">
                            <input type="text" id="custom-tag-input-${{videoNum}}" class="form-control" 
                                   style="border: 2px solid #e2e8f0; border-radius: 8px; padding: 0.75rem; font-size: 0.875rem;" 
                                   placeholder="💡 Type custom tag and press Enter" 
                                   onkeypress="addCustomTag(${{videoNum}}, event)">
                        </div>
                        <div class="selected-tags" id="selected-tags-${{videoNum}}" style="margin-top: 1rem;">
                            <!-- Will be populated by JS -->
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{videoNum}}-hashtags">Hashtags</label>
                        <input type="text" id="video-${{videoNum}}-hashtags" name="video_${{videoNum}}_hashtags" 
                               class="form-control" placeholder="e.g., #wildlife #tigers #conservation">
                        <small class="field-help">Separate hashtags with spaces</small>
                    </div>
                </div>
            `;
            
            container.insertAdjacentHTML('beforeend', newVideoHtml);
            
            // Update count
            const count = document.querySelectorAll('.video-form-section').length;
            document.getElementById('videos-count').textContent = `Videos (${{count}} videos)`;
            
            // Scroll to new video
            const newVideo = container.lastElementChild;
            newVideo.scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
        }}
        
        function removeNewVideo(button) {{
            if (confirm('Remove this new video?')) {{
                const videoSection = button.closest('.video-form-section');
                videoSection.remove();
                
                // Update count
                const count = document.querySelectorAll('.video-form-section').length;
                document.getElementById('videos-count').textContent = `Videos (${{count}} videos)`;
            }}
        }}
        
        function moveVideoUp(button) {{
            const videoSection = button.closest('.video-form-section');
            const previousSection = videoSection.previousElementSibling;
            
            if (previousSection && previousSection.classList.contains('video-form-section')) {{
                videoSection.parentNode.insertBefore(videoSection, previousSection);
                updateVideoNumbers();
            }}
        }}
        
        function moveVideoDown(button) {{
            const videoSection = button.closest('.video-form-section');
            const nextSection = videoSection.nextElementSibling;
            
            if (nextSection && nextSection.classList.contains('video-form-section')) {{
                videoSection.parentNode.insertBefore(nextSection, videoSection);
                updateVideoNumbers();
            }}
        }}
        
        function handleVideoUpload(num, input) {{
            const fileNameEl = document.getElementById('file-name-' + num);
            const previewDiv = document.getElementById('video-preview-' + num);
            const videoPlayer = document.getElementById('video-player-' + num);
            
            if (input.files && input.files[0]) {{
                const file = input.files[0];
                
                // Show file name
                fileNameEl.textContent = '✓ ' + file.name;
                fileNameEl.style.display = 'block';
                
                // Show video preview
                const videoURL = URL.createObjectURL(file);
                videoPlayer.src = videoURL;
                previewDiv.style.display = 'block';
                
                // Clean up the object URL when video is loaded
                videoPlayer.onload = function() {{
                    URL.revokeObjectURL(videoURL);
                }};
            }}
        }}
        
        function handleThumbnailUpload(num, input) {{
            const previewDiv = document.getElementById('thumbnail-preview-' + num);
            const thumbnailImage = document.getElementById('thumbnail-image-' + num);
            
            if (input.files && input.files[0]) {{
                const file = input.files[0];
                const imageURL = URL.createObjectURL(file);
                thumbnailImage.src = imageURL;
                previewDiv.style.display = 'block';
            }}
        }}
        
        function captureFrameFromVideo(num) {{
            const videoPlayer = document.getElementById('video-player-' + num);
            const canvas = document.getElementById('thumbnail-canvas-' + num);
            const thumbnailImage = document.getElementById('thumbnail-image-' + num);
            const previewDiv = document.getElementById('thumbnail-preview-' + num);
            
            // Use the preview video if available, otherwise use the current video
            let videoElement = videoPlayer;
            if (!videoPlayer.src || videoPlayer.style.display === 'none') {{
                // Try to find the current video element for this position
                const videos = document.querySelectorAll('video[controls]');
                for (let v of videos) {{
                    if (v.closest('.video-form-section')) {{
                        videoElement = v;
                        break;
                    }}
                }}
            }}
            
            if (!videoElement || !videoElement.videoWidth) {{
                alert('Please upload or play a video first before capturing a frame.');
                return;
            }}
            
            // Set canvas dimensions to match video
            canvas.width = videoElement.videoWidth;
            canvas.height = videoElement.videoHeight;
            
            // Draw current frame to canvas
            const ctx = canvas.getContext('2d');
            ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
            
            // Convert canvas to blob and create file
            canvas.toBlob(function(blob) {{
                const file = new File([blob], `thumbnail-video-${{num}}.jpg`, {{ type: 'image/jpeg' }});
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                document.getElementById('video-' + num + '-thumbnail').files = dataTransfer.files;
                
                // Show preview
                thumbnailImage.src = URL.createObjectURL(blob);
                previewDiv.style.display = 'block';
            }}, 'image/jpeg', 0.9);
        }}
        
        function toggleTag(videoNum, element) {{
            const tag = element.getAttribute('data-tag');
            element.classList.toggle('selected');
            
            if (!videoTags[videoNum]) {{
                videoTags[videoNum] = [];
            }}
            
            if (element.classList.contains('selected')) {{
                if (!videoTags[videoNum].includes(tag)) {{
                    videoTags[videoNum].push(tag);
                }}
            }} else {{
                videoTags[videoNum] = videoTags[videoNum].filter(t => t !== tag);
            }}
            
            updateSelectedTagsDisplay(videoNum);
        }}
        
        function addCustomTag(videoNum, event) {{
            if (event.key === 'Enter') {{
                event.preventDefault();
                const input = document.getElementById('custom-tag-input-' + videoNum);
                const tag = input.value.trim();
                
                if (!videoTags[videoNum]) {{
                    videoTags[videoNum] = [];
                }}
                
                if (tag && !videoTags[videoNum].includes(tag)) {{
                    videoTags[videoNum].push(tag);
                    updateSelectedTagsDisplay(videoNum);
                    input.value = '';
                }}
            }}
        }}
        
        function removeTag(videoNum, tag) {{
            if (videoTags[videoNum]) {{
                videoTags[videoNum] = videoTags[videoNum].filter(t => t !== tag);
            }}
            
            // Unselect predefined tag if it exists
            const container = document.getElementById('tags-container-' + videoNum);
            if (container) {{
                const tagOptions = container.querySelectorAll('.tag-option');
                tagOptions.forEach(option => {{
                    if (option.getAttribute('data-tag') === tag) {{
                        option.classList.remove('selected');
                    }}
                }});
            }}
            
            updateSelectedTagsDisplay(videoNum);
        }}
        
        function updateSelectedTagsDisplay(videoNum) {{
            const container = document.getElementById('selected-tags-' + videoNum);
            if (!container) return;
            
            const tags = videoTags[videoNum] || [];
            
            if (tags.length === 0) {{
                container.innerHTML = '<p style="color: #a0aec0; font-style: italic;">No tags selected</p>';
            }} else {{
                container.innerHTML = tags.map(tag => 
                    `<span class="selected-tag">
                        ${{tag}}
                        <i class="fas fa-times" onclick="removeTag(${{videoNum}}, '${{tag}}')"></i>
                    </span>`
                ).join('');
            }}
        }}
        
        // Form submission
        document.getElementById('edit-series-form').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving Changes...';
            
            try {{
                const formData = new FormData(this);
                formData.append('video_tags', JSON.stringify(videoTags));
                
                // Update positions based on current order
                const videoSections = document.querySelectorAll('.video-form-section');
                videoSections.forEach((section, index) => {{
                    const positionInput = section.querySelector('.video-position-input');
                    if (positionInput) {{
                        positionInput.value = index + 1;
                    }}
                }});
                
                // Re-collect formData to include updated positions
                const updatedFormData = new FormData(this);
                updatedFormData.append('video_tags', JSON.stringify(videoTags));
                
                const response = await fetch('/admin/videos/series/{series_id}/edit', {{
                    method: 'POST',
                    body: updatedFormData
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    const messageDiv = document.getElementById('message-container');
                    messageDiv.innerHTML = `
                        <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                            <i class="fas fa-check-circle"></i> ${{result.message}}
                        </div>
                    `;
                    
                    setTimeout(() => {{
                        window.location.href = '/admin/videos/series/{series_id}';
                    }}, 1500);
                }} else {{
                    throw new Error(result.message || 'Failed to update series');
                }}
            }} catch (error) {{
                console.error('Error:', error);
                const messageDiv = document.getElementById('message-container');
                messageDiv.innerHTML = `
                    <div style="background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <i class="fas fa-exclamation-circle"></i> Error: ${{error.message}}
                    </div>
                `;
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }}
        }});
    </script>
    
    <style>
        .form-section {{
            background: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
            transition: box-shadow 0.3s ease;
        }}
        
        .form-section:hover {{
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #2d3748;
            margin: 0 0 1.5rem 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        .section-title i {{
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            font-size: 1rem;
        }}
        
        .video-form-section {{
            background: #f7fafc;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            border: 2px solid #e2e8f0;
            cursor: move;
            transition: all 0.2s ease;
        }}
        
        .video-form-section.dragging {{
            opacity: 0.5;
            transform: scale(0.98);
        }}
        
        .video-form-section.drag-over {{
            border-color: #667eea;
            background: #eef2ff;
        }}
        
        .video-header {{
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        
        .drag-handle {{
            cursor: grab;
            padding: 0.5rem;
            color: #718096;
            font-size: 1.25rem;
        }}
        
        .drag-handle:active {{
            cursor: grabbing;
        }}
        
        .video-number {{
            font-size: 1.1rem;
            font-weight: 700;
            color: #2d3748;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            flex: 1;
        }}
        
        .tags-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            padding: 1.25rem;
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-radius: 12px;
            border: 2px solid #e2e8f0;
            min-height: 80px;
            align-items: flex-start;
        }}
        
        .tag-option {{
            padding: 0.625rem 1.25rem;
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 24px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            color: #4a5568;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }}
        
        .tag-option:hover {{
            border-color: #667eea;
            background: #f7fafc;
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.2);
        }}
        
        .tag-option.selected {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        
        .tag-option.selected:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
        }}
        
        .selected-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            min-height: 40px;
        }}
        
        .selected-tag {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.625rem 1rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 24px;
            font-size: 0.875rem;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
            animation: slideIn 0.3s ease;
        }}
        
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .selected-tag i {{
            cursor: pointer;
            opacity: 0.8;
            transition: all 0.2s ease;
            width: 18px;
            height: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%%;
            background: rgba(255, 255, 255, 0.2);
        }}
        
        .selected-tag i:hover {{
            opacity: 1;
            background: rgba(255, 255, 255, 0.3);
            transform: rotate(90deg);
        }}
        
        .form-actions {{
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
            padding: 1.5rem 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
            border-top: 3px solid #667eea;
            position: sticky;
            bottom: 0;
            z-index: 10;
        }}
        
        .file-upload-box {{
            border: 2px dashed #cbd5e0;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: #f7fafc;
        }}
        
        .file-upload-box:hover {{
            border-color: #667eea;
            background: white;
        }}
        
        .file-upload-box i {{
            font-size: 2rem;
            color: #667eea;
            margin-bottom: 0.5rem;
        }}
        
        .btn-icon {{
            background: none;
            border: none;
            color: #667eea;
            cursor: pointer;
            padding: 0.5rem;
            border-radius: 6px;
            transition: all 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .btn-icon:hover {{
            background: #eef2ff;
            transform: scale(1.1);
        }}
        
        .btn-icon:active {{
            transform: scale(0.95);
        }}
    </style>
    """
    
    return HTMLResponse(content=create_html_page(f"Edit Series: {series_obj.title}", content, "videos"))


def generate_edit_video_forms(videos, predefined_tags):
    """Generate edit forms for existing videos"""
    if not videos:
        return '<p style="color: #718096;">No videos in this series yet.</p>'
    
    forms_html = ''
    for video in videos:
        video_tags = video.tags or []
        predefined_tags_html = ' '.join([
            f'<span class="tag-option {"selected" if tag in video_tags else ""}" onclick="toggleTag({video.position}, this)" data-tag="{tag}">{tag}</span>'
            for tag in predefined_tags
        ])
        
        forms_html += f"""
        <div class="video-form-section" draggable="true" data-video-id="{video.id}" data-position="{video.position}" ondragstart="handleDragStart(event)" ondragend="handleDragEnd(event)" ondragover="handleDragOver(event)" ondrop="handleDrop(event)" ondragleave="handleDragLeave(event)">
            <input type="hidden" name="video_{video.position}_id" value="{video.id}">
            <input type="hidden" name="video_{video.position}_position" value="{video.position}" class="video-position-input">
            <input type="hidden" name="video_{video.position}_episode" value="{video.position}">
            <div class="video-header">
                <div class="drag-handle">
                    <i class="fas fa-grip-vertical"></i>
                </div>
                <h4 class="video-number">
                    <i class="fas fa-video"></i>
                    Episode {video.position}
                </h4>
                <div style="display: flex; gap: 0.5rem;">
                    <button type="button" class="btn-icon" onclick="moveVideoUp(this)" title="Move Up">
                        <i class="fas fa-arrow-up"></i>
                    </button>
                    <button type="button" class="btn-icon" onclick="moveVideoDown(this)" title="Move Down">
                        <i class="fas fa-arrow-down"></i>
                    </button>
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group" style="flex: 2;">
                    <label for="video-{video.position}-title">Video Title *</label>
                    <input type="text" id="video-{video.position}-title" name="video_{video.position}_title" 
                           class="form-control" required value="{video.title}">
                </div>
                <div class="form-group">
                    <label for="video-{video.position}-subtitle">Subtitle</label>
                    <input type="text" id="video-{video.position}-subtitle" name="video_{video.position}_subtitle" 
                           class="form-control" value="{video.subtitle or ''}">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="video-{video.position}-slug">Slug *</label>
                    <input type="text" id="video-{video.position}-slug" name="video_{video.position}_slug" 
                           class="form-control" required value="{video.slug}" onkeyup="formatSlug(this)">
                    <small class="field-help">Auto-formats on typing</small>
                </div>
            </div>
            
            <div class="form-group">
                <label for="video-{video.position}-description">Description</label>
                <textarea id="video-{video.position}-description" name="video_{video.position}_description" 
                          class="form-control" rows="3">{video.description or ''}</textarea>
            </div>
            
            <div class="form-group">
                <label>Current Video</label>
                <video controls style="width: 100%; max-width: 500px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                    <source src="/uploads/{video.video_url}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
            </div>
            
            <div class="form-group">
                <label for="video-{video.position}-file">Replace Video File (optional)</label>
                <div class="file-upload-box" onclick="document.getElementById('video-{video.position}-file').click()">
                    <i class="fas fa-cloud-upload-alt"></i>
                    <p>Click to upload new video file</p>
                    <small>Leave empty to keep current video</small>
                </div>
                <input type="file" id="video-{video.position}-file" name="video_{video.position}_file" 
                       accept="video/*" style="display: none;" onchange="handleVideoUpload({video.position}, this)">
                <small id="file-name-{video.position}" style="display: none; margin-top: 0.5rem; color: #4CAF50;"></small>
                
                <div id="video-preview-{video.position}" style="display: none; margin-top: 1rem;">
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                        <i class="fas fa-eye"></i> New Video Preview
                    </label>
                    <video id="video-player-{video.position}" controls style="width: 100%; max-width: 500px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                        Your browser does not support the video tag.
                    </video>
                </div>
            </div>
            
            <div class="form-group">
                <label for="video-{video.position}-thumbnail">Video Thumbnail</label>
                <div style="margin-bottom: 1rem;">
                    {f'<img src="/uploads/{video.thumbnail_url}" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="Current thumbnail">' if video.thumbnail_url else '<p style="color: #a0aec0; font-style: italic;">No thumbnail set</p>'}
                </div>
                <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                    <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="document.getElementById('video-{video.position}-thumbnail').click()">
                        <i class="fas fa-upload"></i> Upload Thumbnail
                    </button>
                    <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="captureFrameFromVideo({video.position})">
                        <i class="fas fa-camera"></i> Capture from Video
                    </button>
                </div>
                <input type="file" id="video-{video.position}-thumbnail" name="video_{video.position}_thumbnail" 
                       accept="image/*" style="display: none;" onchange="handleThumbnailUpload({video.position}, this)">
                <div id="thumbnail-preview-{video.position}" style="display: none; margin-top: 1rem;">
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                        <i class="fas fa-image"></i> New Thumbnail Preview
                    </label>
                    <img id="thumbnail-image-{video.position}" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="Thumbnail preview">
                </div>
                <canvas id="thumbnail-canvas-{video.position}" style="display: none;"></canvas>
            </div>
            
            <div class="form-group">
                <label>Publish Date (optional)</label>
                <input type="datetime-local" id="video-{video.position}-publish" name="video_{video.position}_publish_date" class="form-control" value="{video.publish_date.strftime('%Y-%m-%dT%H:%M') if video.publish_date else ''}">
                <small class="field-help">If set, the episode will only be visible on the frontend from this date/time.</small>
            </div>

            <div class="form-group">
                <label>Tags</label>
                <div class="tags-container" id="tags-container-{video.position}">
                    {predefined_tags_html}
                </div>
                <div class="custom-tag-input" style="margin-top: 1rem;">
                    <input type="text" id="custom-tag-input-{video.position}" class="form-control" 
                           style="border: 2px solid #e2e8f0; border-radius: 8px; padding: 0.75rem; font-size: 0.875rem;" 
                           placeholder="💡 Type custom tag and press Enter" 
                           onkeypress="addCustomTag({video.position}, event)">
                </div>
                <div class="selected-tags" id="selected-tags-{video.position}" style="margin-top: 1rem;">
                    <!-- Will be populated by JS -->
                </div>
            </div>
            
            <div class="form-group">
                <label for="video-{video.position}-hashtags">Hashtags</label>
                <input type="text" id="video-{video.position}-hashtags" name="video_{video.position}_hashtags" 
                       class="form-control" value="{video.hashtags or ''}" 
                       placeholder="e.g., #wildlife #tigers #conservation">
                <small class="field-help">Separate hashtags with spaces</small>
            </div>
        </div>
        """
    
    return forms_html


def generate_video_tags_init(videos):
    """Generate JavaScript to initialize video tags"""
    if not videos:
        return ''
    
    init_code = ''
    for video in videos:
        # Parse tags - handle both JSON string and list
        try:
            if isinstance(video.tags, str):
                tags = json.loads(video.tags) if video.tags else []
            elif isinstance(video.tags, list):
                tags = video.tags
            else:
                tags = []
        except (json.JSONDecodeError, ValueError):
            tags = []
        
        tags_json = json.dumps(tags)
        init_code += f"videoTags[{video.position}] = {tags_json};\n        "
        init_code += f"updateSelectedTagsDisplay({video.position});\n        "
    
    return init_code


# Add bulk delete route for videos
@router.post("/videos/series/bulk-delete")
async def bulk_delete_videos(request: Request):
    """Bulk delete videos from series"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        body = await request.json()
        video_ids = body.get("video_ids", [])
        
        if not video_ids:
            return JSONResponse(content={"status": False, "message": "No videos selected"})
        
        async with get_db_session() as session:
            # Delete videos
            for video_id in video_ids:
                video_result = await session.execute(
                    select(SeriesVideo).where(SeriesVideo.id == UUID(video_id))
                )
                video = video_result.scalar_one_or_none()
                
                if video:
                    series_id = video.series_id
                    await session.delete(video)
            
            # Update series video count
            if video_ids:
                # Get series from first video
                first_video_result = await session.execute(
                    select(SeriesVideo).where(SeriesVideo.id == UUID(video_ids[0]))
                )
                first_video = first_video_result.scalar_one_or_none()
                
                if first_video:
                    # Update video count and reorder positions
                    # Update series total (keep original episode numbers, don't renumber)
                    remaining_videos_result = await session.execute(
                        select(func.count(SeriesVideo.id))
                        .where(SeriesVideo.series_id == first_video.series_id)
                    )
                    remaining_count = remaining_videos_result.scalar()
                    
                    # Update series total
                    series_result = await session.execute(
                        select(VideoSeries).where(VideoSeries.id == first_video.series_id)
                    )
                    series = series_result.scalar_one_or_none()
                    if series:
                        series.total_videos = remaining_count
            
            await session.commit()
        
        return JSONResponse(content={
            "status": True,
            "message": f"Successfully deleted {len(video_ids)} video(s)"
        })
    
    except Exception as e:
        print(f"Error bulk deleting videos: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


# Add DELETE route for series
@router.delete("/videos/series/{series_id}")
async def delete_series(request: Request, series_id: str):
    """Delete a video series and all its videos"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as session:
            # Get series
            series_result = await session.execute(
                select(VideoSeries).where(VideoSeries.id == UUID(series_id))
            )
            series_obj = series_result.scalar_one_or_none()
            
            if not series_obj:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Series not found"}
                )
            
            # Delete series (cascade will delete videos)
            await session.delete(series_obj)
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": f"Series '{series_obj.title}' deleted successfully"
            })
            
    except Exception as e:
        print(f"Error deleting series: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": f"Error deleting series: {str(e)}"}
        )


@router.post("/videos/series/{series_id}/set-featured")
async def set_featured_series(request: Request, series_id: str):
    """Set a series as featured (unfeatured all others automatically)"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        from datetime import datetime
        
        async with get_db_session() as session:
            # Get the series to be featured
            series_result = await session.execute(
                select(VideoSeries).where(VideoSeries.id == UUID(series_id))
            )
            series = series_result.scalar_one_or_none()
            
            if not series:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Series not found"}
                )
            
            # Unfeatured all other series first
            await session.execute(
                text("UPDATE video_series SET is_featured = 0, featured_at = NULL WHERE is_featured = 1")
            )
            
            # Feature this series
            series.is_featured = 1
            series.featured_at = datetime.now()
            
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": f"'{series.title}' is now the featured series!"
            })
            
    except Exception as e:
        print(f"Error setting featured series: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.post("/videos/series/{series_id}/unfeature")
async def unfeature_series(request: Request, series_id: str):
    """Remove featured status from a series"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as session:
            # Get the series
            series_result = await session.execute(
                select(VideoSeries).where(VideoSeries.id == UUID(series_id))
            )
            series = series_result.scalar_one_or_none()
            
            if not series:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Series not found"}
                )
            
            # Unfeature the series
            series.is_featured = 0
            series.featured_at = None
            
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": f"'{series.title}' is no longer featured"
            })
            
    except Exception as e:
        print(f"Error unfeaturing series: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


# Add POST route for series update
@router.post("/videos/series/{series_id}/edit")
async def update_series(
    request: Request,
    series_id: str,
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    slug: str = Form(...),
):
    """Handle series update"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        form_data = await request.form()
        video_tags_json = form_data.get("video_tags", "{}")
        video_tags_dict = json.loads(video_tags_json)
        
        async with get_db_session() as session:
            # Get series
            series_result = await session.execute(
                select(VideoSeries).where(VideoSeries.id == UUID(series_id))
            )
            series_obj = series_result.scalar_one_or_none()
            
            if not series_obj:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Series not found"}
                )
            
            # Update series info
            series_obj.title = title
            series_obj.subtitle = subtitle
            series_obj.slug = slug
            
            # Get all video positions from form data
            all_positions = set()
            for key in form_data.keys():
                if key.startswith("video_") and key.endswith("_id"):
                    pos_str = key.replace("video_", "").replace("_id", "")
                    try:
                        all_positions.add(int(pos_str))
                    except:
                        pass
            
            # Update existing videos
            videos_result = await session.execute(
                select(SeriesVideo)
                .where(SeriesVideo.series_id == series_obj.id)
                .order_by(SeriesVideo.position)
            )
            videos = videos_result.scalars().all()
            
            all_used_tags = set()  # Track all tags used for auto-save
            
            for video in videos:
                pos = video.position
                video_title = form_data.get(f"video_{pos}_title")
                if video_title:
                    video.title = video_title
                    video.subtitle = form_data.get(f"video_{pos}_subtitle", "")
                    video.slug = form_data.get(f"video_{pos}_slug", video.slug)
                    video.description = form_data.get(f"video_{pos}_description", "")
                    video.hashtags = form_data.get(f"video_{pos}_hashtags", "")
                    
                    # Update episode number
                    video_episode = form_data.get(f"video_{pos}_episode")
                    if video_episode:
                        video.position = int(video_episode)
                    
                    video_tags_list = video_tags_dict.get(str(pos), [])
                    video.tags = json.dumps(video_tags_list)
                    all_used_tags.update(video_tags_list)
                    # Update publish date if provided
                    publish_val = form_data.get(f"video_{pos}_publish_date")
                    if publish_val is not None:
                        video.publish_date = datetime.fromisoformat(publish_val) if publish_val else None
                    
                    # Check if new video file uploaded
                    video_file = form_data.get(f"video_{pos}_file")
                    if video_file and video_file.filename:
                        # Upload video to R2/local via file_upload_service
                        upload_result = await file_upload_service.upload_file(
                            file=video_file,
                            file_category="videos",
                            validate_content=False
                        )
                        
                        video.video_url = upload_result["file_url"]  # e.g., "videos/abc.mp4"
                        
                        # Extract video duration
                        video.duration = upload_result.get("duration")
                    
                    # Check if new thumbnail uploaded
                    video_thumbnail = form_data.get(f"video_{pos}_thumbnail")
                    if video_thumbnail and video_thumbnail.filename:
                        # Upload thumbnail to R2/local via file_upload_service
                        upload_result = await file_upload_service.upload_file(
                            file=video_thumbnail,
                            file_category="thumbnails",
                            validate_content=False
                        )
                        
                        video.thumbnail_url = upload_result["file_url"]  # e.g., "thumbnails/xyz.jpg"
            
            # Process NEW videos
            for pos in all_positions:
                video_id = form_data.get(f"video_{pos}_id")
                if video_id == "new":
                    # This is a new video
                    video_title = form_data.get(f"video_{pos}_title")
                    video_file = form_data.get(f"video_{pos}_file")
                    
                    if not video_title or not video_file or not video_file.filename:
                        continue
                    
                    # Get episode number
                    video_episode = int(form_data.get(f"video_{pos}_episode", pos))
                    
                    # Upload video to R2/local via file_upload_service
                    upload_result = await file_upload_service.upload_file(
                        file=video_file,
                        file_category="videos",
                        validate_content=False
                    )
                    
                    video_url = upload_result["file_url"]  # e.g., "videos/abc.mp4"
                    video_duration = upload_result.get("duration")
                    
                    # Save thumbnail if provided
                    thumbnail_url = None
                    video_thumbnail = form_data.get(f"video_{pos}_thumbnail")
                    if video_thumbnail and video_thumbnail.filename:
                        # Upload thumbnail to R2/local via file_upload_service
                        thumbnail_result = await file_upload_service.upload_file(
                            file=video_thumbnail,
                            file_category="thumbnails",
                            validate_content=False
                        )
                        thumbnail_url = thumbnail_result["file_url"]  # e.g., "thumbnails/xyz.jpg"
                    
                    # Get tags for this video
                    video_tags_list = video_tags_dict.get(str(pos), [])
                    all_used_tags.update(video_tags_list)
                    
                    # Create new video
                    new_video = SeriesVideo(
                        id=uuid4(),
                        series_id=series_obj.id,
                        title=video_title,
                        subtitle=form_data.get(f"video_{pos}_subtitle", "") or None,
                        slug=form_data.get(f"video_{pos}_slug"),
                        description=form_data.get(f"video_{pos}_description", "") or None,
                        video_url=video_url,  # Already formatted as "videos/abc.mp4"
                        thumbnail_url=thumbnail_url,
                        duration=video_duration,
                        position=video_episode,
                        tags=json.dumps(video_tags_list),
                        hashtags=form_data.get(f"video_{pos}_hashtags", "") or None,
                        publish_date=datetime.fromisoformat(form_data.get(f"video_{pos}_publish_date")) if form_data.get(f"video_{pos}_publish_date") else None,
                        views=0
                    )
                    session.add(new_video)
            
            # Update series total videos count
            total_videos_result = await session.execute(
                select(func.count(SeriesVideo.id))
                .where(SeriesVideo.series_id == series_obj.id)
            )
            series_obj.total_videos = total_videos_result.scalar()
            
            # Auto-save new custom tags to database
            if all_used_tags:
                # Get existing tags from database
                existing_tags_result = await session.execute(
                    select(VideoTag.name)
                )
                existing_tag_names = {tag for (tag,) in existing_tags_result.fetchall()}
                
                # Find new tags that don't exist in database
                new_tags = all_used_tags - existing_tag_names
                
                # Add new tags to database
                for tag_name in new_tags:
                    new_tag = VideoTag(
                        id=uuid4(),
                        name=tag_name,
                        usage_count=1
                    )
                    session.add(new_tag)
                
                # Increment usage count for existing tags
                for tag_name in all_used_tags & existing_tag_names:
                    await session.execute(
                        text("UPDATE video_tags SET usage_count = usage_count + 1 WHERE name = :tag_name"),
                        {"tag_name": tag_name}
                    )
            
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": f"Series '{title}' updated successfully!"
            })
            
    except Exception as e:
        print(f"Error updating series: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": f"Error updating series: {str(e)}"}
        )


@router.get("/videos/create-series", response_class=HTMLResponse)
async def create_video_series(request: Request):
    """Create video series page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Fetch tags from database
    async with get_db_session() as session:
        tags_result = await session.execute(
            select(VideoTag).order_by(VideoTag.usage_count.desc(), VideoTag.name)
        )
        tags_objs = tags_result.scalars().all()
        predefined_tags = [tag.name for tag in tags_objs]
    
    content = f"""
    <div class="page-header">
        <div>
            <h1 class="page-title">Create Video Series</h1>
            <p class="page-subtitle">Add a new video series with multiple episodes</p>
        </div>
        <a href="/admin/videos" class="btn btn-secondary">
            <i class="fas fa-arrow-left"></i> Back to Library
        </a>
    </div>
    
    <div id="message-container"></div>
    
    <form id="series-form" class="form-container">
        <!-- Series Details Section -->
        <div class="form-section">
            <h3 class="section-title">
                <i class="fas fa-film"></i> Series Information
            </h3>
            
            <div class="form-row">
                <div class="form-group" style="flex: 2;">
                    <label for="series-title">Series Title *</label>
                    <input type="text" id="series-title" name="title" class="form-control" required 
                           placeholder="e.g., Wildlife of India" onkeyup="formatSeriesSlug()">
                </div>
                <div class="form-group">
                    <label for="series-subtitle">Subtitle</label>
                    <input type="text" id="series-subtitle" name="subtitle" class="form-control" 
                           placeholder="e.g., A Journey Through Nature">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="series-slug">Series Slug *</label>
                    <input type="text" id="series-slug" name="slug" class="form-control" required 
                           placeholder="e.g., wildlife-of-india">
                    <small class="field-help">Auto-generated from title (lowercase, hyphens)</small>
                </div>
                <div class="form-group">
                    <label for="num-videos">Number of Videos *</label>
                    <select id="num-videos" name="num_videos" class="form-control" onchange="updateVideoForms()" required>
                        <option value="">Select number</option>
                        <option value="1">1 Video</option>
                        <option value="2">2 Videos</option>
                        <option value="3">3 Videos</option>
                        <option value="4">4 Videos</option>
                        <option value="5">5 Videos</option>
                        <option value="6">6 Videos</option>
                        <option value="7">7 Videos</option>
                        <option value="8">8 Videos</option>
                        <option value="9">9 Videos</option>
                        <option value="10">10 Videos</option>
                    </select>
                    <small class="field-help">Maximum 10 videos per series</small>
                </div>
            </div>
        </div>
        
        <!-- Individual Videos Section -->
        <div id="videos-container">
            <!-- Video forms will be dynamically added here -->
        </div>
        
        <!-- Submit Button -->
        <div class="form-actions">
            <button type="button" class="btn btn-secondary" onclick="window.history.back()">
                <i class="fas fa-times"></i> Cancel
            </button>
            <button type="submit" class="btn btn-primary">
                <i class="fas fa-save"></i> Create Series
            </button>
        </div>
    </form>
    
    <style>
        .form-section {{
            background: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
            transition: box-shadow 0.3s ease;
        }}
        
        .form-section:hover {{
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.06);
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #2d3748;
            margin: 0 0 1.5rem 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        .section-title i {{
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            font-size: 1rem;
        }}
        }}
        
        .video-form-section {{
            background: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            border: 2px solid #e2e8f0;
            transition: all 0.3s ease;
        }}
        
        .video-form-section:hover {{
            border-color: #667eea;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
        }}
        
        .video-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        .video-number {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .tags-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            padding: 1.25rem;
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-radius: 12px;
            border: 2px solid #e2e8f0;
            min-height: 80px;
            align-items: flex-start;
        }}
        
        .tag-option {{
            padding: 0.625rem 1.25rem;
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 24px;
            cursor: pointer;
            font-size: 0.875rem;
            font-weight: 500;
            color: #4a5568;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            user-select: none;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
        }}
        
        .tag-option:hover {{
            border-color: #667eea;
            background: #f7fafc;
            transform: translateY(-2px);
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.2);
        }}
        
        .tag-option.selected {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-color: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }}
        
        .tag-option.selected:hover {{
            transform: translateY(-3px);
            box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
        }}
        
        .selected-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            min-height: 40px;
        }}
        
        .selected-tag {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.625rem 1rem;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 24px;
            font-size: 0.875rem;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
            animation: slideIn 0.3s ease;
        }}
        
        @keyframes slideIn {{
            from {{
                opacity: 0;
                transform: translateY(-10px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .selected-tag i {{
            cursor: pointer;
            opacity: 0.8;
            transition: all 0.2s ease;
            width: 18px;
            height: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: rgba(255, 255, 255, 0.2);
        }}
        
        .selected-tag i:hover {{
            opacity: 1;
            background: rgba(255, 255, 255, 0.3);
            transform: rotate(90deg);
        }}
        
        .form-actions {{
            display: flex;
            gap: 1rem;
            justify-content: flex-end;
            padding: 1.5rem 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
            border-top: 3px solid #667eea;
            position: sticky;
            bottom: 0;
            z-index: 10;
        }}
        
        .file-upload-box {{
            border: 2px dashed #cbd5e0;
            border-radius: 8px;
            padding: 1.5rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: #f7fafc;
        }}
        
        .file-upload-box:hover {{
            border-color: #667eea;
            background: white;
        }}
        
        .file-upload-box i {{
            font-size: 2rem;
            color: #667eea;
            margin-bottom: 0.5rem;
        }}
    </style>
    
    <script>
        let videoTags = {{}};
        const predefinedTags = {predefined_tags};
        
        function updateVideoForms() {{
            const numVideos = parseInt(document.getElementById('num-videos').value);
            const container = document.getElementById('videos-container');
            container.innerHTML = '';
            
            // Initialize tags for each video
            for (let i = 1; i <= numVideos; i++) {{
                videoTags[i] = [];
            }}
            
            for (let i = 1; i <= numVideos; i++) {{
                container.innerHTML += createVideoForm(i);
            }}
        }}
        
        function createVideoForm(num) {{
            const predefinedTagsHTML = predefinedTags.map(tag => 
                `<span class="tag-option" onclick="toggleTag(${{num}}, this)" data-tag="${{tag}}">${{tag}}</span>`
            ).join(' ');
            
            return `
                <div class="video-form-section">
                    <div class="video-header">
                        <h4 class="video-number">
                            <i class="fas fa-video"></i>
                            Video ${{num}}
                        </h4>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group" style="flex: 2;">
                            <label for="video-${{num}}-title">Video Title *</label>
                            <input type="text" id="video-${{num}}-title" name="video_${{num}}_title" 
                                   class="form-control" required placeholder="e.g., Episode ${{num}}: Tigers in the Wild">
                        </div>
                        <div class="form-group">
                            <label for="video-${{num}}-subtitle">Subtitle</label>
                            <input type="text" id="video-${{num}}-subtitle" name="video_${{num}}_subtitle" 
                                   class="form-control" placeholder="Episode subtitle">
                        </div>
                        <div class="form-group" style="max-width: 150px;">
                            <label for="video-${{num}}-episode">Episode # *</label>
                            <input type="number" id="video-${{num}}-episode" name="video_${{num}}_episode" 
                                   class="form-control" required min="1" value="${{num}}" 
                                   placeholder="${{num}}">
                            <small class="field-help">Episode number</small>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{num}}-slug">Slug *</label>
                        <input type="text" id="video-${{num}}-slug" name="video_${{num}}_slug" 
                               class="form-control" required placeholder="e.g., tigers-in-the-wild"
                               onkeyup="formatSlug(this)">
                        <small class="field-help">URL-friendly version (lowercase, hyphens instead of spaces)</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{num}}-description">Description</label>
                        <textarea id="video-${{num}}-description" name="video_${{num}}_description" 
                                  class="form-control" rows="3" 
                                  placeholder="Brief description of this video..."></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{num}}-file">Video File *</label>
                        <div class="file-upload-box" onclick="document.getElementById('video-${{num}}-file').click()">
                            <i class="fas fa-cloud-upload-alt"></i>
                            <p>Click to upload video file</p>
                            <small>MP4, WebM, MOV (Max 50MB)</small>
                        </div>
                        <input type="file" id="video-${{num}}-file" name="video_${{num}}_file" 
                               accept="video/*" style="display: none;" onchange="handleVideoUpload(${{num}}, this)" required>
                        <small id="file-name-${{num}}" style="display: none; margin-top: 0.5rem; color: #4CAF50;"></small>
                        
                        <!-- Video Preview -->
                        <div id="video-preview-${{num}}" style="display: none; margin-top: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                                <i class="fas fa-eye"></i> Preview
                            </label>
                            <video id="video-player-${{num}}" controls style="width: 100%; max-width: 500px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                                Your browser does not support the video tag.
                            </video>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{num}}-thumbnail">Video Thumbnail</label>
                        <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                            <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="document.getElementById('video-${{num}}-thumbnail').click()">
                                <i class="fas fa-upload"></i> Upload Thumbnail
                            </button>
                            <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="captureFrameFromVideo(${{num}})">
                                <i class="fas fa-camera"></i> Capture from Video
                            </button>
                        </div>
                        <input type="file" id="video-${{num}}-thumbnail" name="video_${{num}}_thumbnail" 
                               accept="image/*" style="display: none;" onchange="handleThumbnailUpload(${{num}}, this)">
                        <div id="thumbnail-preview-${{num}}" style="display: none; margin-top: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                                <i class="fas fa-image"></i> Thumbnail Preview
                            </label>
                            <img id="thumbnail-image-${{num}}" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="Thumbnail preview">
                        </div>
                        <canvas id="thumbnail-canvas-${{num}}" style="display: none;"></canvas>
                    </div>
                    
                    <div class="form-group">
                        <label>Tags</label>
                        <div class="tags-container" id="tags-container-${{num}}">
                            ${{predefinedTagsHTML}}
                        </div>
                        <div class="custom-tag-input" style="margin-top: 1rem;">
                            <input type="text" id="custom-tag-input-${{num}}" class="form-control" 
                                   placeholder="Type custom tag and press Enter" 
                                   onkeypress="addCustomTag(${{num}}, event)">
                        </div>
                        <div class="selected-tags" id="selected-tags-${{num}}" style="margin-top: 1rem;">
                            <p style="color: #a0aec0; font-style: italic;">No tags selected</p>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="video-${{num}}-hashtags">Hashtags</label>
                        <input type="text" id="video-${{num}}-hashtags" name="video_${{num}}_hashtags" 
                               class="form-control" placeholder="e.g., #wildlife #tigers #conservation">
                        <small class="field-help">Separate hashtags with spaces (e.g., #wildlife #nature)</small>
                    </div>
                    <div class="form-group">
                        <label for="video-${{num}}-publish">Publish Date</label>
                        <input type="datetime-local" id="video-${{num}}-publish" name="video_${{num}}_publish_date" 
                               class="form-control">
                        <small class="field-help">Optional: schedule when this video becomes visible on the frontend</small>
                    </div>
                </div>
            `;
        }}
        
        function formatSlug(input) {{
            input.value = input.value.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/^-+|-+$/g, '');
        }}
        
        function formatSeriesSlug() {{
            const title = document.getElementById('series-title').value;
            const slug = document.getElementById('series-slug');
            slug.value = title.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/^-+|-+$/g, '');
        }}
        
        function handleVideoUpload(num, input) {{
            const fileNameEl = document.getElementById('file-name-' + num);
            const previewDiv = document.getElementById('video-preview-' + num);
            const videoPlayer = document.getElementById('video-player-' + num);
            
            if (input.files && input.files[0]) {{
                const file = input.files[0];
                
                // Show file name
                fileNameEl.textContent = '✓ ' + file.name;
                fileNameEl.style.display = 'block';
                
                // Show video preview
                const videoURL = URL.createObjectURL(file);
                videoPlayer.src = videoURL;
                previewDiv.style.display = 'block';
                
                // Clean up the object URL when video is loaded
                videoPlayer.onload = function() {{
                    URL.revokeObjectURL(videoURL);
                }};
            }}
        }}
        
        function handleThumbnailUpload(num, input) {{
            const previewDiv = document.getElementById('thumbnail-preview-' + num);
            const thumbnailImage = document.getElementById('thumbnail-image-' + num);
            
            if (input.files && input.files[0]) {{
                const file = input.files[0];
                const imageURL = URL.createObjectURL(file);
                thumbnailImage.src = imageURL;
                previewDiv.style.display = 'block';
            }}
        }}
        
        function captureFrameFromVideo(num) {{
            const videoPlayer = document.getElementById('video-player-' + num);
            const canvas = document.getElementById('thumbnail-canvas-' + num);
            const thumbnailImage = document.getElementById('thumbnail-image-' + num);
            const previewDiv = document.getElementById('thumbnail-preview-' + num);
            
            if (!videoPlayer.videoWidth) {{
                alert('Please upload and play the video first before capturing a frame.');
                return;
            }}
            
            // Set canvas dimensions to match video
            canvas.width = videoPlayer.videoWidth;
            canvas.height = videoPlayer.videoHeight;
            
            // Draw current frame to canvas
            const ctx = canvas.getContext('2d');
            ctx.drawImage(videoPlayer, 0, 0, canvas.width, canvas.height);
            
            // Convert canvas to blob and create file
            canvas.toBlob(function(blob) {{
                const file = new File([blob], `thumbnail-video-${{num}}.jpg`, {{ type: 'image/jpeg' }});
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                document.getElementById('video-' + num + '-thumbnail').files = dataTransfer.files;
                
                // Show preview
                thumbnailImage.src = URL.createObjectURL(blob);
                previewDiv.style.display = 'block';
            }}, 'image/jpeg', 0.9);
        }}
        
        function toggleTag(videoNum, element) {{
            const tag = element.getAttribute('data-tag');
            element.classList.toggle('selected');
            
            if (!videoTags[videoNum]) {{
                videoTags[videoNum] = [];
            }}
            
            if (element.classList.contains('selected')) {{
                if (!videoTags[videoNum].includes(tag)) {{
                    videoTags[videoNum].push(tag);
                }}
            }} else {{
                videoTags[videoNum] = videoTags[videoNum].filter(t => t !== tag);
            }}
            
            updateSelectedTagsDisplay(videoNum);
        }}
        
        function addCustomTag(videoNum, event) {{
            if (event.key === 'Enter') {{
                event.preventDefault();
                const input = document.getElementById('custom-tag-input-' + videoNum);
                const tag = input.value.trim();
                
                if (!videoTags[videoNum]) {{
                    videoTags[videoNum] = [];
                }}
                
                if (tag && !videoTags[videoNum].includes(tag)) {{
                    videoTags[videoNum].push(tag);
                    updateSelectedTagsDisplay(videoNum);
                    input.value = '';
                }}
            }}
        }}
        
        function removeTag(videoNum, tag) {{
            if (videoTags[videoNum]) {{
                videoTags[videoNum] = videoTags[videoNum].filter(t => t !== tag);
            }}
            
            // Unselect predefined tag if it exists
            const container = document.getElementById('tags-container-' + videoNum);
            if (container) {{
                const tagOptions = container.querySelectorAll('.tag-option');
                tagOptions.forEach(option => {{
                    if (option.getAttribute('data-tag') === tag) {{
                        option.classList.remove('selected');
                    }}
                }});
            }}
            
            updateSelectedTagsDisplay(videoNum);
        }}
        
        function updateSelectedTagsDisplay(videoNum) {{
            const container = document.getElementById('selected-tags-' + videoNum);
            if (!container) return;
            
            const tags = videoTags[videoNum] || [];
            
            if (tags.length === 0) {{
                container.innerHTML = '<p style="color: #a0aec0; font-style: italic;">No tags selected</p>';
            }} else {{
                container.innerHTML = tags.map(tag => 
                    `<span class="selected-tag">
                        ${{tag}}
                        <i class="fas fa-times" onclick="removeTag(${{videoNum}}, '${{tag}}')"></i>
                    </span>`
                ).join('');
            }}
        }}
        
        // Form submission
        document.getElementById('series-form').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Creating Series...';
            
            try {{
                // Collect all form data including tags per video
                const formData = new FormData(this);
                formData.append('video_tags', JSON.stringify(videoTags));
                
                const response = await fetch('/admin/videos/create-series', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    // Show success message
                    const messageDiv = document.getElementById('message-container');
                    messageDiv.innerHTML = `
                        <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                            <i class="fas fa-check-circle"></i> ${{result.message}}
                        </div>
                    `;
                    
                    // Redirect to series detail page after a short delay
                    setTimeout(() => {{
                        window.location.href = result.redirect;
                    }}, 1500);
                }} else {{
                    throw new Error(result.message || 'Failed to create series');
                }}
            }} catch (error) {{
                console.error('Error:', error);
                const messageDiv = document.getElementById('message-container');
                messageDiv.innerHTML = `
                    <div style="background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <i class="fas fa-exclamation-circle"></i> Error: ${{error.message}}
                    </div>
                `;
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }}
        }});
    </script>
    """
    
    return HTMLResponse(content=create_html_page("Create Video Series", content, "videos"))


@router.post("/videos/create-series")
async def submit_video_series(
    request: Request,
    title: str = Form(...),
    subtitle: Optional[str] = Form(None),
    slug: str = Form(...),
    num_videos: int = Form(...),
):
    """Handle video series creation"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        form_data = await request.form()
        
        # Parse video tags from JSON
        video_tags_json = form_data.get("video_tags", "{}")
        video_tags_dict = json.loads(video_tags_json)
        
        async with get_db_session() as session:
            # Check if slug already exists and make it unique
            original_slug = slug
            counter = 1
            while True:
                existing = await session.execute(
                    select(VideoSeries).where(VideoSeries.slug == slug)
                )
                if not existing.scalar_one_or_none():
                    break
                slug = f"{original_slug}-{counter}"
                counter += 1
            
            # Create video series
            series = VideoSeries(
                id=uuid4(),
                title=title,
                subtitle=subtitle,
                slug=slug,
                total_videos=num_videos,
                total_views=0,
                is_published=1
            )
            session.add(series)
            
            # Process each video
            videos_created = []
            all_used_tags = set()  # Track all tags used for auto-save
            
            for i in range(1, num_videos + 1):
                video_title = form_data.get(f"video_{i}_title")
                video_subtitle = form_data.get(f"video_{i}_subtitle", "")
                video_slug = form_data.get(f"video_{i}_slug")
                video_description = form_data.get(f"video_{i}_description", "")
                video_hashtags = form_data.get(f"video_{i}_hashtags", "")
                video_episode = int(form_data.get(f"video_{i}_episode", i))  # Custom episode number
                video_file = form_data.get(f"video_{i}_file")
                video_thumbnail = form_data.get(f"video_{i}_thumbnail")
                video_publish = form_data.get(f"video_{i}_publish_date")
                
                if not video_title or not video_slug or not video_file:
                    continue
                
                # Get tags for this video
                video_tags_list = video_tags_dict.get(str(i), [])
                all_used_tags.update(video_tags_list)
                
                # Save video file
                video_filename = f"{uuid4()}_{video_file.filename}"
                video_path = Path("uploads/videos") / video_filename
                video_path.parent.mkdir(parents=True, exist_ok=True)
                
                with open(video_path, "wb") as buffer:
                    content = await video_file.read()
                    buffer.write(content)
                
                # Save thumbnail if provided
                thumbnail_url = None
                if video_thumbnail and video_thumbnail.filename:
                    thumbnail_filename = f"{uuid4()}_{video_thumbnail.filename}"
                    thumbnail_path = Path("uploads/thumbnails") / thumbnail_filename
                    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(thumbnail_path, "wb") as buffer:
                        content = await video_thumbnail.read()
                        buffer.write(content)
                    
                    thumbnail_url = f"thumbnails/{thumbnail_filename}"
                
                # Create series video entry
                series_video = SeriesVideo(
                    id=uuid4(),
                    series_id=series.id,
                    title=video_title,
                    subtitle=video_subtitle or None,
                    slug=video_slug,
                    description=video_description or None,
                    video_url=f"/uploads/videos/{video_filename}",
                    thumbnail_url=thumbnail_url,
                    position=video_episode,  # Use custom episode number
                    tags=video_tags_list,
                    hashtags=video_hashtags or None,
                    publish_date=datetime.fromisoformat(video_publish) if video_publish else None,
                    views=0
                )
                session.add(series_video)
                videos_created.append(video_title)
            
            # Auto-save new custom tags to database
            if all_used_tags:
                # Get existing tags from database
                existing_tags_result = await session.execute(
                    select(VideoTag.name)
                )
                existing_tag_names = {tag for (tag,) in existing_tags_result.fetchall()}
                
                # Find new tags that don't exist in database
                new_tags = all_used_tags - existing_tag_names
                
                # Add new tags to database
                for tag_name in new_tags:
                    new_tag = VideoTag(
                        id=uuid4(),
                        name=tag_name,
                        usage_count=1
                    )
                    session.add(new_tag)
                
                # Increment usage count for existing tags
                for tag_name in all_used_tags & existing_tag_names:
                    await session.execute(
                        text("UPDATE video_tags SET usage_count = usage_count + 1 WHERE name = :tag_name"),
                        {"tag_name": tag_name}
                    )
            
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": f"Series '{title}' created successfully with {len(videos_created)} videos!",
                "series_id": str(series.id),
                "redirect": f"/admin/videos/series/{series.id}"
            })
            
    except Exception as e:
        print(f"Error creating series: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": f"Error creating series: {str(e)}"}
        )


@router.post("/videos/upload")
async def upload_video(
    request: Request,
    video: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    photographer: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    thumbnail: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload a new video"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Validate file type
        if not video.content_type or not video.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/videos")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        file_extension = os.path.splitext(video.filename)[1]
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename
        
        # Save video file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        # Handle thumbnail if provided
        thumbnail_url = None
        if thumbnail and thumbnail.filename:
            thumb_dir = Path("uploads/thumbnails")
            thumb_dir.mkdir(parents=True, exist_ok=True)
            thumb_filename = f"{uuid4()}{os.path.splitext(thumbnail.filename)[1]}"
            thumb_path = thumb_dir / thumb_filename
            
            with open(thumb_path, "wb") as buffer:
                shutil.copyfileobj(thumbnail.file, buffer)
            
            thumbnail_url = f"thumbnails/{thumb_filename}"
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create media record
        media = Media(
            media_type="video",
            file_url=f"/uploads/videos/{unique_filename}",
            thumbnail_url=thumbnail_url,
            filename=unique_filename,
            original_filename=video.filename,
            mime_type=video.content_type,
            title=title,
            description=description,
            photographer=photographer,
            national_park=location,
            file_size=file_size,
            uploaded_by=None  # Set to current admin user ID if needed
        )
        
        db.add(media)
        await db.commit()
        await db.refresh(media)
        
        return {
            "success": True,
            "message": "Video uploaded successfully",
            "video_id": str(media.id)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/videos/{video_id:uuid}")
async def get_video(
    request: Request,
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get video details"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await db.execute(
            select(Media).where(Media.id == UUID(video_id))
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        return {
            "id": str(video.id),
            "title": video.title,
            "description": video.description,
            "photographer": video.photographer,
            "national_park": video.national_park,
            "file_url": video.file_url,
            "thumbnail_url": video.thumbnail_url
        }
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video ID")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/{video_id}/edit")
async def edit_video(
    request: Request,
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Edit video details"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get request body
        body = await request.json()
        
        # Get video
        result = await db.execute(
            select(Media).where(Media.id == UUID(video_id))
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Update fields
        if 'title' in body:
            video.title = body['title']
        if 'description' in body:
            video.description = body['description']
        if 'photographer' in body:
            video.photographer = body['photographer']
        if 'national_park' in body:
            video.national_park = body['national_park']
        
        await db.commit()
        
        return {"success": True, "message": "Video updated successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video ID")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/{video_id}/delete")
async def delete_video(
    request: Request,
    video_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a video"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get video
        result = await db.execute(
            select(Media).where(Media.id == UUID(video_id))
        )
        video = result.scalar_one_or_none()
        
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Delete physical file
        if video.file_url:
            file_path = Path(video.file_url.lstrip('/'))
            if file_path.exists():
                file_path.unlink()
        
        # Delete thumbnail if exists
        if video.thumbnail_url:
            thumb_path = Path(video.thumbnail_url.lstrip('/'))
            if thumb_path.exists():
                thumb_path.unlink()
        
        # Delete from database
        await db.delete(video)
        await db.commit()
        
        return {"success": True, "message": "Video deleted successfully"}
        
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid video ID")
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TAG MANAGEMENT ROUTES ====================

@router.get("/videos/tags", response_class=HTMLResponse)
async def video_tags_management(request: Request):
    """Video tags management page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    async with get_db_session() as db:
        # Fetch all tags ordered by usage count
        tags_result = await db.execute(
            select(VideoTag).order_by(VideoTag.usage_count.desc(), VideoTag.name)
        )
        tags = tags_result.scalars().all()
    
    tags_html = ""
    for tag in tags:
        tags_html += f"""
        <tr>
            <td style="font-weight: 600; color: #2d3748;">{tag.name}</td>
            <td>
                <span style="display: inline-block; padding: 0.25rem 0.75rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 20px; font-size: 0.875rem; font-weight: 600;">
                    {tag.usage_count} uses
                </span>
            </td>
            <td>{tag.created_at.strftime('%b %d, %Y')}</td>
            <td>
                <div style="display: flex; gap: 0.5rem; justify-content: flex-end;">
                    <button class="btn-icon btn-edit" onclick="editTag('{tag.id}', '{tag.name}')" title="Edit tag">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-icon btn-delete" onclick="deleteTag('{tag.id}', '{tag.name}')" title="Delete tag">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
        """
    
    if not tags_html:
        tags_html = '<tr><td colspan="4" style="text-align: center; color: #718096; padding: 2rem;">No tags available. Add your first tag!</td></tr>'
    
    content = f"""
    <div class="page-header">
        <div>
            <h1 class="page-title">Video Tags Management</h1>
            <p class="page-subtitle">Manage predefined tags for video categorization</p>
        </div>
        <div style="display: flex; gap: 1rem;">
            <a href="/admin/videos" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to Videos
            </a>
            <button class="btn btn-primary" onclick="openAddTagModal()">
                <i class="fas fa-plus"></i> Add Tag
            </button>
        </div>
    </div>
    
    <div id="message-container"></div>
    
    <div class="content-card">
        <div style="overflow-x: auto;">
            <table class="data-table">
                <thead>
                    <tr>
                        <th>Tag Name</th>
                        <th>Usage Count</th>
                        <th>Created</th>
                        <th style="text-align: right;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {tags_html}
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Add Tag Modal -->
    <div id="add-tag-modal" class="modal">
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h2><i class="fas fa-plus"></i> Add New Tag</h2>
                <button class="modal-close" onclick="closeAddTagModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <form id="add-tag-form" onsubmit="submitAddTag(event)">
                    <div class="form-group">
                        <label for="tag-name">Tag Name *</label>
                        <input type="text" id="tag-name" name="tag_name" class="form-control" 
                               required placeholder="e.g., Wildlife, Conservation">
                    </div>
                    <div style="display: flex; gap: 1rem; justify-content: flex-end; margin-top: 1.5rem;">
                        <button type="button" class="btn btn-secondary" onclick="closeAddTagModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-check"></i> Add Tag
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <!-- Edit Tag Modal -->
    <div id="edit-tag-modal" class="modal">
        <div class="modal-content" style="max-width: 500px;">
            <div class="modal-header">
                <h2><i class="fas fa-edit"></i> Edit Tag</h2>
                <button class="modal-close" onclick="closeEditTagModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <div class="modal-body">
                <form id="edit-tag-form" onsubmit="submitEditTag(event)">
                    <input type="hidden" id="edit-tag-id" name="tag_id">
                    <div class="form-group">
                        <label for="edit-tag-name">Tag Name *</label>
                        <input type="text" id="edit-tag-name" name="tag_name" class="form-control" required>
                    </div>
                    <div style="display: flex; gap: 1rem; justify-content: flex-end; margin-top: 1.5rem;">
                        <button type="button" class="btn btn-secondary" onclick="closeEditTagModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-check"></i> Update Tag
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    
    <style>
        /* Modal Overlay */
        .modal {{
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            align-items: center;
            justify-content: center;
            backdrop-filter: blur(4px);
        }}
        
        .modal-content {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            animation: modalSlideIn 0.3s ease;
        }}
        
        @keyframes modalSlideIn {{
            from {{
                opacity: 0;
                transform: translateY(-50px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .modal-header {{
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        .modal-header h2 {{
            margin: 0;
            font-size: 1.5rem;
            color: #2d3748;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }}
        
        .modal-close {{
            background: none;
            border: none;
            font-size: 1.5rem;
            color: #a0aec0;
            cursor: pointer;
            padding: 0;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 8px;
            transition: all 0.2s ease;
        }}
        
        .modal-close:hover {{
            background: #f7fafc;
            color: #4a5568;
        }}
        
        .modal-body {{
            padding: 2rem;
        }}
    
        .data-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .data-table thead {{
            background: #f7fafc;
        }}
        
        .data-table th {{
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: #4a5568;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        .data-table td {{
            padding: 1rem;
            border-bottom: 1px solid #e2e8f0;
            color: #718096;
        }}
        
        .data-table tbody tr:hover {{
            background: #f7fafc;
        }}
        
        .btn-icon {{
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }}
        
        .btn-icon:hover {{
            transform: translateY(-2px);
        }}
        
        .btn-edit {{
            background: #edf2f7;
            color: #4299e1;
        }}
        
        .btn-edit:hover {{
            background: #4299e1;
            color: white;
        }}
        
        .btn-delete {{
            background: #fed7d7;
            color: #e53e3e;
        }}
        
        .btn-delete:hover {{
            background: #e53e3e;
            color: white;
        }}
    </style>
    
    <script>
        function openAddTagModal() {{
            document.getElementById('add-tag-modal').style.display = 'flex';
            document.getElementById('tag-name').value = '';
        }}
        
        function closeAddTagModal() {{
            document.getElementById('add-tag-modal').style.display = 'none';
        }}
        
        function openEditTagModal() {{
            document.getElementById('edit-tag-modal').style.display = 'flex';
        }}
        
        function closeEditTagModal() {{
            document.getElementById('edit-tag-modal').style.display = 'none';
        }}
        
        function editTag(tagId, tagName) {{
            document.getElementById('edit-tag-id').value = tagId;
            document.getElementById('edit-tag-name').value = tagName;
            openEditTagModal();
        }}
        
        async function submitAddTag(event) {{
            event.preventDefault();
            
            const formData = new FormData(event.target);
            
            try {{
                const response = await fetch('/admin/videos/tags/add', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    showMessage(result.message, 'success');
                    closeAddTagModal();
                    setTimeout(() => window.location.reload(), 1000);
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error adding tag: ' + error.message, 'error');
            }}
        }}
        
        async function submitEditTag(event) {{
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const tagId = formData.get('tag_id');
            
            try {{
                const response = await fetch(`/admin/videos/tags/${{tagId}}/edit`, {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    showMessage(result.message, 'success');
                    closeEditTagModal();
                    setTimeout(() => window.location.reload(), 1000);
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error updating tag: ' + error.message, 'error');
            }}
        }}
        
        async function deleteTag(tagId, tagName) {{
            if (!confirm(`Are you sure you want to delete the tag "${{tagName}}"?\\n\\nThis will not affect existing videos that use this tag.`)) {{
                return;
            }}
            
            try {{
                const response = await fetch(`/admin/videos/tags/${{tagId}}`, {{
                    method: 'DELETE'
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    showMessage(result.message, 'success');
                    setTimeout(() => window.location.reload(), 1000);
                }} else {{
                    showMessage(result.message, 'error');
                }}
            }} catch (error) {{
                showMessage('Error deleting tag: ' + error.message, 'error');
            }}
        }}
        
        function showMessage(message, type) {{
            const container = document.getElementById('message-container');
            const bgColor = type === 'success' ? '#48bb78' : '#f56565';
            
            container.innerHTML = `
                <div style="background: ${{bgColor}}; color: white; padding: 1rem 1.5rem; border-radius: 8px; margin-bottom: 1.5rem; display: flex; align-items: center; justify-content: space-between; animation: slideDown 0.3s ease;">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <i class="fas fa-${{type === 'success' ? 'check-circle' : 'exclamation-circle'}}" style="font-size: 1.25rem;"></i>
                        <span style="font-weight: 500;">${{message}}</span>
                    </div>
                    <button onclick="this.parentElement.remove()" style="background: none; border: none; color: white; cursor: pointer; font-size: 1.25rem; padding: 0; width: 24px; height: 24px;">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            setTimeout(() => {{
                container.innerHTML = '';
            }}, 5000);
        }}
        
        // Close modals on outside click
        window.onclick = function(event) {{
            const addModal = document.getElementById('add-tag-modal');
            const editModal = document.getElementById('edit-tag-modal');
            
            if (event.target === addModal) {{
                closeAddTagModal();
            }}
            if (event.target === editModal) {{
                closeEditTagModal();
            }}
        }}
    </script>
    """
    
    return create_html_page("Video Tags Management", content, "videos")


@router.post("/videos/tags/add")
async def add_video_tag(
    request: Request,
    tag_name: str = Form(...)
):
    """Add a new video tag"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as db:
            # Check if tag already exists
            existing_tag = await db.execute(
                select(VideoTag).where(VideoTag.name == tag_name.strip())
            )
            if existing_tag.scalar_one_or_none():
                return JSONResponse(
                    content={"status": False, "message": f"Tag '{tag_name}' already exists"}
                )
            
            # Create new tag
            new_tag = VideoTag(
                id=uuid4(),
                name=tag_name.strip(),
                usage_count=0
            )
            db.add(new_tag)
            await db.commit()
            
            return JSONResponse(
                content={"status": True, "message": f"Tag '{tag_name}' added successfully!"}
            )
            
    except Exception as e:
        print(f"Error adding tag: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": f"Error adding tag: {str(e)}"}
        )


@router.post("/videos/tags/{tag_id}/edit")
async def edit_video_tag(
    request: Request,
    tag_id: str,
    tag_name: str = Form(...)
):
    """Edit a video tag"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as db:
            # Get the tag
            tag_result = await db.execute(
                select(VideoTag).where(VideoTag.id == UUID(tag_id))
            )
            tag = tag_result.scalar_one_or_none()
            
            if not tag:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Tag not found"}
                )
            
            # Check if new name already exists (excluding current tag)
            existing_tag = await db.execute(
                select(VideoTag).where(
                    and_(VideoTag.name == tag_name.strip(), VideoTag.id != UUID(tag_id))
                )
            )
            if existing_tag.scalar_one_or_none():
                return JSONResponse(
                    content={"status": False, "message": f"Tag '{tag_name}' already exists"}
                )
            
            # Update tag
            tag.name = tag_name.strip()
            await db.commit()
            
            return JSONResponse(
                content={"status": True, "message": f"Tag updated successfully!"}
            )
            
    except Exception as e:
        print(f"Error updating tag: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": f"Error updating tag: {str(e)}"}
        )


@router.delete("/videos/tags/{tag_id}")
async def delete_video_tag(
    request: Request,
    tag_id: str
):
    """Delete a video tag and remove it from all videos"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as db:
            # Get the tag
            tag_result = await db.execute(
                select(VideoTag).where(VideoTag.id == UUID(tag_id))
            )
            tag = tag_result.scalar_one_or_none()
            
            if not tag:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Tag not found"}
                )
            
            tag_name = tag.name
            
            # Remove tag from all series videos
            series_videos_result = await db.execute(select(SeriesVideo))
            series_videos = series_videos_result.scalars().all()
            
            for video in series_videos:
                if video.tags:
                    try:
                        tags_list = json.loads(video.tags) if isinstance(video.tags, str) else video.tags
                        if tag_name in tags_list:
                            tags_list.remove(tag_name)
                            video.tags = json.dumps(tags_list)
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            # Remove tag from all general knowledge videos
            gk_videos_result = await db.execute(select(GeneralKnowledgeVideo))
            gk_videos = gk_videos_result.scalars().all()
            
            for video in gk_videos:
                if video.tags:
                    try:
                        tags_list = json.loads(video.tags) if isinstance(video.tags, str) else video.tags
                        if tag_name in tags_list:
                            tags_list.remove(tag_name)
                            video.tags = json.dumps(tags_list)
                    except (json.JSONDecodeError, ValueError):
                        continue
            
            # Delete tag
            await db.delete(tag)
            await db.commit()
            
            return JSONResponse(
                content={"status": True, "message": f"Tag '{tag_name}' deleted and removed from all videos!"}
            )
            
    except Exception as e:
        print(f"Error deleting tag: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": f"Error deleting tag: {str(e)}"}
        )


@router.get("/videos/general-knowledge/create", response_class=HTMLResponse)
async def create_general_knowledge_video(request: Request):
    """Create a general knowledge video"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Fetch channels and tags
    async with get_db_session() as session:
        # Get all active channels
        from app.models.video_channel import VideoChannel
        channels_result = await session.execute(
            select(VideoChannel)
            .where(VideoChannel.is_active == True)
            .order_by(VideoChannel.name)
        )
        channels = channels_result.scalars().all()
        
        channels_options = ''.join([
            f'<option value="{channel.id}">{channel.name}</option>'
            for channel in channels
        ])
        
        # Get all tags
        tags_result = await session.execute(
            select(VideoTag).order_by(VideoTag.name)
        )
        tags = tags_result.scalars().all()
        
        predefined_tags = [tag.name for tag in tags]
        predefined_tags_html = ' '.join([
            f'<span class="tag-option" onclick="toggleTag(this)" data-tag="{tag}">{tag}</span>'
            for tag in predefined_tags
        ])
    
    content = f"""
    <div class="page-header">
        <div>
            <h1 class="page-title">Upload General Knowledge Video</h1>
            <p class="page-subtitle">Add educational content to a channel</p>
        </div>
        <a href="/admin/videos" class="btn btn-secondary">
            <i class="fas fa-arrow-left"></i> Cancel
        </a>
    </div>
    
    <div id="message-container"></div>
    
    <form id="gk-video-form" enctype="multipart/form-data">
        <!-- Channel Selection -->
        <div class="form-section">
            <h3 class="section-title">
                <i class="fas fa-tv"></i> Channel Selection
            </h3>
            
            <div class="form-group">
                <label for="channel-select">Select Channel *</label>
                <select id="channel-select" name="channel_id" class="form-control" required>
                    <option value="">-- Choose a channel --</option>
                    {channels_options}
                </select>
                <small class="field-help">Choose which channel this video belongs to. <a href="/admin/videos/channels" target="_blank">Manage Channels</a></small>
            </div>
        </div>
        
        <!-- Video Information -->
        <div class="form-section">
            <h3 class="section-title">
                <i class="fas fa-info-circle"></i> Video Information
            </h3>
            
            <div class="form-row">
                <div class="form-group" style="flex: 2;">
                    <label for="video-title">Video Title *</label>
                    <input type="text" id="video-title" name="title" class="form-control" required onkeyup="formatVideoSlug()">
                </div>
                <div class="form-group">
                    <label for="video-subtitle">Subtitle</label>
                    <input type="text" id="video-subtitle" name="subtitle" class="form-control">
                </div>
            </div>
            
            <div class="form-group">
                <label for="video-slug">Video Slug *</label>
                <input type="text" id="video-slug" name="slug" class="form-control" required>
                <small class="field-help">URL-friendly identifier (lowercase, hyphens)</small>
            </div>
            
            <div class="form-group">
                <label for="video-description">Description</label>
                <textarea id="video-description" name="description" class="form-control" rows="4"></textarea>
            </div>
            <div class="form-group">
                <label for="video-publish-date">Publish Date (optional)</label>
                <input type="datetime-local" id="video-publish-date" name="publish_date" class="form-control">
                <small class="field-help">Leave empty to publish immediately.</small>
            </div>
        </div>
        
        <!-- Video Upload -->
        <div class="form-section">
            <h3 class="section-title">
                <i class="fas fa-video"></i> Video File
            </h3>
            
            <div class="form-group">
                <label for="video-file">Upload Video *</label>
                <input type="file" id="video-file" name="video_file" class="form-control" accept="video/*" required onchange="handleVideoUpload()">
                <small class="field-help">Supported formats: MP4, WebM, MOV (Max 50MB)</small>
            </div>
            
            <div id="video-preview" style="display: none; margin-top: 1rem;">
                <video id="video-player" controls style="width: 100%; max-width: 600px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);"></video>
            </div>
        </div>
        
        <!-- Thumbnail -->
        <div class="form-section">
            <h3 class="section-title">
                <i class="fas fa-image"></i> Thumbnail
            </h3>
            
            <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                <button type="button" class="btn btn-secondary" onclick="document.getElementById('thumbnail-file').click()">
                    <i class="fas fa-upload"></i> Upload Thumbnail
                </button>
                <button type="button" class="btn btn-secondary" onclick="captureFrame()">
                    <i class="fas fa-camera"></i> Capture from Video
                </button>
            </div>
            
            <input type="file" id="thumbnail-file" name="thumbnail_file" accept="image/*" style="display: none;" onchange="handleThumbnailUpload()">
            
            <div id="thumbnail-preview" style="display: none; margin-top: 1rem;">
                <img id="thumbnail-image" src="" alt="Thumbnail preview" style="max-width: 400px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
            </div>
            
            <canvas id="capture-canvas" style="display: none;"></canvas>
        </div>
        
        <!-- Tags -->
        <div class="form-section">
            <h3 class="section-title">
                <i class="fas fa-tags"></i> Tags & Hashtags
            </h3>
            
            <div class="form-group">
                <label>Tags</label>
                <div class="tags-container" id="tags-container">
                    {predefined_tags_html}
                </div>
                <div class="custom-tag-input" style="margin-top: 1rem;">
                    <input type="text" id="custom-tag-input" class="form-control" 
                           placeholder="💡 Type custom tag and press Enter" 
                           onkeypress="addCustomTag(event)">
                </div>
                <div class="selected-tags" id="selected-tags" style="margin-top: 1rem;">
                    <p style="color: #a0aec0; font-style: italic;">No tags selected</p>
                </div>
            </div>
            
            <div class="form-group">
                <label for="hashtags">Hashtags</label>
                <input type="text" id="hashtags" name="hashtags" class="form-control" placeholder="e.g., #wildlife #tigers #conservation">
                <small class="field-help">Separate hashtags with spaces</small>
            </div>
        </div>
        
        <!-- Submit -->
        <div class="form-actions">
            <a href="/admin/videos" class="btn btn-secondary">
                <i class="fas fa-times"></i> Cancel
            </a>
            <button type="submit" class="btn btn-primary">
                <i class="fas fa-save"></i> Upload Video
            </button>
        </div>
    </form>
    
    <style>
        .form-section {{
            background: white;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
        
        .section-title {{
            font-size: 1.25rem;
            font-weight: 700;
            color: #2d3748;
            margin: 0 0 1.5rem 0;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #e2e8f0;
        }}
        
        .section-title i {{
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 10px;
            font-size: 1rem;
        }}
        
        .form-row {{
            display: flex;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .form-group {{
            flex: 1;
            margin-bottom: 1.5rem;
        }}
        
        .form-group label {{
            display: block;
            font-size: 0.95rem;
            font-weight: 600;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }}
        
        .form-control {{
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 0.95rem;
            transition: border-color 0.2s;
        }}
        
        .form-control:focus {{
            outline: none;
            border-color: #f093fb;
        }}
        
        .field-help {{
            display: block;
            margin-top: 0.5rem;
            font-size: 0.85rem;
            color: #718096;
        }}
        
        .tags-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        
        .tag-option {{
            padding: 0.5rem 1rem;
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        .tag-option:hover {{
            border-color: #f093fb;
            background: #fef5ff;
        }}
        
        .tag-option.selected {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-color: transparent;
        }}
        
        .selected-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        
        .selected-tag {{
            padding: 0.5rem 1rem;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 20px;
            font-size: 0.9rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .selected-tag i {{
            cursor: pointer;
            opacity: 0.8;
        }}
        
        .selected-tag i:hover {{
            opacity: 1;
        }}
        
        .form-actions {{
            display: flex;
            justify-content: flex-end;
            gap: 1rem;
            padding: 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }}
    </style>
    
    <script>
        let selectedTags = [];
        
        function formatVideoSlug() {{
            const title = document.getElementById('video-title').value;
            const slug = document.getElementById('video-slug');
            slug.value = title.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/^-+|-+$/g, '');
        }}
        
        function handleVideoUpload() {{
            const file = document.getElementById('video-file').files[0];
            if (file) {{
                const preview = document.getElementById('video-preview');
                const player = document.getElementById('video-player');
                player.src = URL.createObjectURL(file);
                preview.style.display = 'block';
            }}
        }}
        
        function handleThumbnailUpload() {{
            const file = document.getElementById('thumbnail-file').files[0];
            if (file) {{
                const preview = document.getElementById('thumbnail-preview');
                const img = document.getElementById('thumbnail-image');
                img.src = URL.createObjectURL(file);
                preview.style.display = 'block';
            }}
        }}
        
        function captureFrame() {{
            const video = document.getElementById('video-player');
            if (!video.src) {{
                alert('Please upload a video first');
                return;
            }}
            
            const canvas = document.getElementById('capture-canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            
            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            
            canvas.toBlob(function(blob) {{
                const file = new File([blob], 'thumbnail.jpg', {{ type: 'image/jpeg' }});
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                document.getElementById('thumbnail-file').files = dataTransfer.files;
                
                const preview = document.getElementById('thumbnail-preview');
                const img = document.getElementById('thumbnail-image');
                img.src = URL.createObjectURL(blob);
                preview.style.display = 'block';
            }}, 'image/jpeg', 0.9);
        }}
        
        function toggleTag(element) {{
            const tag = element.getAttribute('data-tag');
            element.classList.toggle('selected');
            
            if (element.classList.contains('selected')) {{
                if (!selectedTags.includes(tag)) {{
                    selectedTags.push(tag);
                }}
            }} else {{
                selectedTags = selectedTags.filter(t => t !== tag);
            }}
            
            updateSelectedTagsDisplay();
        }}
        
        function addCustomTag(event) {{
            if (event.key === 'Enter') {{
                event.preventDefault();
                const input = document.getElementById('custom-tag-input');
                const tag = input.value.trim();
                
                if (tag && !selectedTags.includes(tag)) {{
                    selectedTags.push(tag);
                    updateSelectedTagsDisplay();
                    input.value = '';
                }}
            }}
        }}
        
        function removeTag(tag) {{
            selectedTags = selectedTags.filter(t => t !== tag);
            
            // Unselect predefined tag if it exists
            const container = document.getElementById('tags-container');
            const tagOptions = container.querySelectorAll('.tag-option');
            tagOptions.forEach(option => {{
                if (option.getAttribute('data-tag') === tag) {{
                    option.classList.remove('selected');
                }}
            }});
            
            updateSelectedTagsDisplay();
        }}
        
        function updateSelectedTagsDisplay() {{
            const container = document.getElementById('selected-tags');
            
            if (selectedTags.length === 0) {{
                container.innerHTML = '<p style="color: #a0aec0; font-style: italic;">No tags selected</p>';
            }} else {{
                container.innerHTML = selectedTags.map(tag => 
                    `<span class="selected-tag">
                        ${{tag}}
                        <i class="fas fa-times" onclick="removeTag('${{tag}}')"></i>
                    </span>`
                ).join('');
            }}
        }}
        
        document.getElementById('gk-video-form').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const formData = new FormData(this);
            formData.append('tags', selectedTags.join(','));
            
            try {{
                const response = await fetch('/admin/videos/general-knowledge/submit', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    const messageDiv = document.getElementById('message-container');
                    messageDiv.innerHTML = `
                        <div style="background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                            <i class="fas fa-check-circle"></i> ${{result.message}}
                        </div>
                    `;
                    
                    setTimeout(() => {{
                        window.location.href = '/admin/videos/channels/' + result.channel_id;
                    }}, 1500);
                }} else {{
                    throw new Error(result.message || 'Failed to upload video');
                }}
            }} catch (error) {{
                console.error('Error:', error);
                const messageDiv = document.getElementById('message-container');
                messageDiv.innerHTML = `
                    <div style="background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                        <i class="fas fa-exclamation-triangle"></i> ${{error.message}}
                    </div>
                `;
            }}
        }});
    </script>
    """
    
    return HTMLResponse(content=create_html_page("Upload General Knowledge Video", content, "videos"))


@router.post("/videos/general-knowledge/submit")
async def submit_general_knowledge_video(
    request: Request,
    channel_id: str = Form(...),
    title: str = Form(...),
    slug: str = Form(...),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    hashtags: Optional[str] = Form(None),
    publish_date: Optional[str] = Form(None),
    video_file: UploadFile = File(...),
    thumbnail_file: Optional[UploadFile] = File(None)
):
    """Submit a general knowledge video"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
        
        # Upload video to R2/local via file_upload_service
        upload_result = await file_upload_service.upload_file(
            file=video_file,
            file_category="videos",
            validate_content=False
        )
        
        video_url = upload_result["file_url"]  # e.g., "videos/abc.mp4"
        video_duration = upload_result.get("duration", 0)
        
        # Save thumbnail if provided
        thumbnail_url = None
        if thumbnail_file and thumbnail_file.filename:
            thumbnail_result = await file_upload_service.upload_file(
                file=thumbnail_file,
                file_category="thumbnails",
                validate_content=False
            )
            thumbnail_url = thumbnail_result["file_url"]  # e.g., "thumbnails/xyz.jpg"
        
        # Parse tags - handle comma-separated string
        tags_list = []
        if tags:
            try:
                # First try as JSON array
                tags_list = json.loads(tags)
            except (json.JSONDecodeError, ValueError):
                # Fall back to comma-separated string
                tags_list = [t.strip() for t in tags.split(',') if t.strip()]
        
        # Create video in database
        async with get_db_session() as session:
            video = GeneralKnowledgeVideo(
                channel_id=UUID(channel_id),
                title=title,
                slug=slug,
                subtitle=subtitle,
                description=description,
                video_url=video_url,
                thumbnail_url=thumbnail_url,
                duration=video_duration,
                tags=json.dumps(tags_list),
                hashtags=hashtags,
                publish_date=datetime.fromisoformat(publish_date) if publish_date else None
            )
            
            session.add(video)
            
            # Update channel video count
            channel = await session.get(VideoChannel, UUID(channel_id))
            if channel:
                channel.total_videos += 1
            
            await session.commit()
        
        return JSONResponse(content={
            "status": True,
            "message": "Video uploaded successfully!",
            "channel_id": channel_id
        })
    
    except Exception as e:
        print(f"Error uploading video: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.get("/videos/general-knowledge/{video_id}/edit", response_class=HTMLResponse)
async def edit_general_knowledge_video(request: Request, video_id: str):
    """Show form to edit a general knowledge video"""
    
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
        
        async with get_db_session() as session:
            # Get video
            video_result = await session.execute(
                select(GeneralKnowledgeVideo).where(GeneralKnowledgeVideo.id == UUID(video_id))
            )
            video = video_result.scalar_one_or_none()
            
            if not video:
                raise HTTPException(status_code=404, detail="Video not found")
            
            # Get all channels for dropdown
            channels_result = await session.execute(
                select(VideoChannel).where(VideoChannel.is_active == True).order_by(VideoChannel.name)
            )
            channels = channels_result.scalars().all()
            
            channel_options = ""
            for ch in channels:
                selected = "selected" if str(ch.id) == str(video.channel_id) else ""
                channel_options += f'<option value="{ch.id}" {selected}>{ch.name}</option>'
            
            # Get tags
            tags_result = await session.execute(
                select(VideoTag).order_by(VideoTag.name)
            )
            tags = tags_result.scalars().all()
            predefined_tags = [tag.name for tag in tags]
            
            video_tags = video.tags.split(',') if video.tags else []
            predefined_tags_html = ' '.join([
                f'<span class="tag-option {"selected" if tag in video_tags else ""}" onclick="toggleTag(this)" data-tag="{tag}">{tag}</span>'
                for tag in predefined_tags
            ])
            
            content = f"""
            <div class="page-header">
                <div>
                    <h1 class="page-title"><i class="fas fa-edit"></i> Edit Video</h1>
                    <p class="page-subtitle">Update video information and media files</p>
                </div>
                <a href="/admin/videos/channels/{video.channel_id}" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back to Channel
                </a>
            </div>
            
            <form id="editVideoForm" onsubmit="submitEditVideo(event)" enctype="multipart/form-data">
                <!-- Channel Selection -->
                <div class="form-section">
                    <h3 class="section-title">
                        <i class="fas fa-tv"></i> Channel Selection
                    </h3>
                    
                    <div class="form-group">
                        <label for="channelSelect">Select Channel *</label>
                        <select id="channelSelect" name="channel_id" required class="form-control">
                            {channel_options}
                        </select>
                        <small class="field-help">Choose which channel this video belongs to</small>
                    </div>
                </div>
                
                <!-- Video Information -->
                <div class="form-section">
                    <h3 class="section-title">
                        <i class="fas fa-info-circle"></i> Video Information
                    </h3>
                    
                    <div class="form-row">
                        <div class="form-group" style="flex: 2;">
                            <label for="videoTitle">Video Title *</label>
                            <input type="text" id="videoTitle" name="title" value="{video.title}" required class="form-control">
                        </div>
                        <div class="form-group">
                            <label for="videoSubtitle">Subtitle</label>
                            <input type="text" id="videoSubtitle" name="subtitle" value="{video.subtitle or ''}" class="form-control">
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="videoSlug">Video Slug *</label>
                        <input type="text" id="videoSlug" name="slug" value="{video.slug}" required class="form-control">
                        <small class="field-help">URL-friendly identifier (lowercase, hyphens)</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="videoDescription">Description</label>
                        <textarea id="videoDescription" name="description" class="form-control" rows="4">{video.description or ''}</textarea>
                    </div>
                    <div class="form-group">
                        <label for="videoPublishDate">Publish Date (optional)</label>
                        <input type="datetime-local" id="videoPublishDate" name="publish_date" class="form-control" value="{video.publish_date.strftime('%Y-%m-%dT%H:%M') if video.publish_date else ''}">
                        <small class="field-help">Leave empty to keep current visibility rules (immediate if none).</small>
                    </div>
                </div>
                
                <!-- Video Upload -->
                <div class="form-section">
                    <h3 class="section-title">
                        <i class="fas fa-video"></i> Video File
                    </h3>
                    
                    <div class="form-group">
                        <label>Current Video</label>
                        <video controls style="width: 100%; max-width: 600px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                            <source src="/uploads/{video.video_url}" type="video/mp4">
                            Your browser does not support the video tag.
                        </video>
                    </div>
                    
                    <div class="form-group">
                        <label for="videoFile">Replace Video File (optional)</label>
                        <div class="file-upload-box" onclick="document.getElementById('videoFile').click()">
                            <i class="fas fa-cloud-upload-alt"></i>
                            <p>Click to upload new video file</p>
                            <small>Leave empty to keep current video</small>
                        </div>
                        <input type="file" id="videoFile" name="video_file" accept="video/*" style="display: none;" onchange="handleVideoUpload()">
                        
                        <div id="video-preview" style="display: none; margin-top: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                                <i class="fas fa-eye"></i> New Video Preview
                            </label>
                            <video id="video-player" controls style="width: 100%; max-width: 600px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                                Your browser does not support the video tag.
                            </video>
                        </div>
                    </div>
                </div>
                
                <!-- Thumbnail -->
                <div class="form-section">
                    <h3 class="section-title">
                        <i class="fas fa-image"></i> Thumbnail
                    </h3>
                    
                    <div class="form-group">
                        <label>Current Thumbnail</label>
                        {'<img src="/uploads/' + video.thumbnail_url + '" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="Current thumbnail">' if video.thumbnail_url else '<p style="color: #a0aec0; font-style: italic;">No thumbnail set</p>'}
                    </div>
                    
                    <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
                        <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="document.getElementById('thumbnailFile').click()">
                            <i class="fas fa-upload"></i> Upload Thumbnail
                        </button>
                        <button type="button" class="btn btn-secondary" style="flex: 1;" onclick="captureFrame()">
                            <i class="fas fa-camera"></i> Capture from Video
                        </button>
                    </div>
                    
                    <input type="file" id="thumbnailFile" name="thumbnail_file" accept="image/*" style="display: none;" onchange="handleThumbnailUpload()">
                    
                    <div id="thumbnail-preview" style="display: none; margin-top: 1rem;">
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                            <i class="fas fa-image"></i> New Thumbnail Preview
                        </label>
                        <img id="thumbnail-image" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="Thumbnail preview">
                    </div>
                    
                    <canvas id="capture-canvas" style="display: none;"></canvas>
                </div>
                
                <!-- Tags -->
                <div class="form-section">
                    <h3 class="section-title">
                        <i class="fas fa-tags"></i> Tags & Hashtags
                    </h3>
                    
                    <div class="form-group">
                        <label>Tags</label>
                        <div class="tags-container" id="tags-container">
                            {predefined_tags_html}
                        </div>
                        <div class="custom-tag-input" style="margin-top: 1rem;">
                            <input type="text" id="custom-tag-input" class="form-control" 
                                   style="border: 2px solid #e2e8f0; border-radius: 8px; padding: 0.75rem; font-size: 0.875rem;" 
                                   placeholder="💡 Type custom tag and press Enter" 
                                   onkeypress="addCustomTag(event)">
                        </div>
                        <div class="selected-tags" id="selected-tags" style="margin-top: 1rem;">
                            <!-- Will be populated by JS -->
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="videoHashtags">Hashtags</label>
                        <input type="text" id="videoHashtags" name="hashtags" value="{video.hashtags or ''}" class="form-control" placeholder="e.g., #wildlife #tigers #conservation">
                        <small class="field-help">Separate hashtags with spaces</small>
                    </div>
                </div>
                
                <!-- Submit -->
                <div class="form-actions">
                    <a href="/admin/videos/channels/{video.channel_id}" class="btn btn-secondary">
                        <i class="fas fa-times"></i> Cancel
                    </a>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Update Video
                    </button>
                </div>
            </form>
            
            <style>
                .form-section {{
                    background: white;
                    padding: 2rem;
                    border-radius: 12px;
                    margin-bottom: 2rem;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }}
                
                .section-title {{
                    font-size: 1.25rem;
                    font-weight: 700;
                    color: #2d3748;
                    margin: 0 0 1.5rem 0;
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                    padding-bottom: 1rem;
                    border-bottom: 2px solid #e2e8f0;
                }}
                
                .section-title i {{
                    width: 40px;
                    height: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                    border-radius: 10px;
                    font-size: 1rem;
                }}
                
                .form-row {{
                    display: flex;
                    gap: 1.5rem;
                    margin-bottom: 1.5rem;
                }}
                
                .form-group {{
                    flex: 1;
                    margin-bottom: 1.5rem;
                }}
                
                .form-group label {{
                    display: block;
                    font-size: 0.95rem;
                    font-weight: 600;
                    color: #2d3748;
                    margin-bottom: 0.5rem;
                }}
                
                .form-control {{
                    width: 100%;
                    padding: 0.75rem;
                    border: 2px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 0.95rem;
                    transition: border-color 0.2s;
                }}
                
                .form-control:focus {{
                    outline: none;
                    border-color: #f093fb;
                }}
                
                .field-help {{
                    display: block;
                    margin-top: 0.5rem;
                    font-size: 0.85rem;
                    color: #718096;
                }}
                
                .file-upload-box {{
                    border: 2px dashed #cbd5e0;
                    border-radius: 8px;
                    padding: 1.5rem;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.3s ease;
                    background: #f7fafc;
                }}
                
                .file-upload-box:hover {{
                    border-color: #f093fb;
                    background: white;
                }}
                
                .file-upload-box i {{
                    font-size: 2rem;
                    color: #f093fb;
                    margin-bottom: 0.5rem;
                }}
                
                .tags-container {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                }}
                
                .tag-option {{
                    padding: 0.625rem 1rem;
                    background: white;
                    border: 2px solid #e2e8f0;
                    border-radius: 24px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.875rem;
                    font-weight: 500;
                }}
                
                .tag-option:hover {{
                    border-color: #f093fb;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 6px rgba(240, 147, 251, 0.2);
                }}
                
                .tag-option.selected {{
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    border-color: #f093fb;
                    color: white;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(240, 147, 251, 0.4);
                }}
                
                .tag-option.selected:hover {{
                    transform: translateY(-3px);
                    box-shadow: 0 6px 16px rgba(240, 147, 251, 0.5);
                }}
                
                .selected-tags {{
                    display: flex;
                    flex-wrap: wrap;
                    gap: 0.5rem;
                    min-height: 40px;
                }}
                
                .selected-tag {{
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.625rem 1rem;
                    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                    color: white;
                    border-radius: 24px;
                    font-size: 0.875rem;
                    font-weight: 500;
                    box-shadow: 0 2px 8px rgba(240, 147, 251, 0.3);
                    animation: slideIn 0.3s ease;
                }}
                
                @keyframes slideIn {{
                    from {{
                        opacity: 0;
                        transform: translateY(-10px);
                    }}
                    to {{
                        opacity: 1;
                        transform: translateY(0);
                    }}
                }}
                
                .selected-tag i {{
                    cursor: pointer;
                    opacity: 0.8;
                    transition: all 0.2s ease;
                    width: 18px;
                    height: 18px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 50%%;
                    background: rgba(255, 255, 255, 0.2);
                }}
                
                .selected-tag i:hover {{
                    opacity: 1;
                    background: rgba(255, 255, 255, 0.3);
                    transform: rotate(90deg);
                }}
                
                .form-actions {{
                    display: flex;
                    gap: 1rem;
                    justify-content: flex-end;
                    padding: 1.5rem 2rem;
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
                    border-top: 3px solid #f093fb;
                    position: sticky;
                    bottom: 0;
                    z-index: 10;
                }}
            </style>
            
            <script>
                let selectedTags = {json.dumps(video_tags)};
                
                function handleVideoUpload() {{
                    const file = document.getElementById('videoFile').files[0];
                    if (file) {{
                        const preview = document.getElementById('video-preview');
                        const player = document.getElementById('video-player');
                        player.src = URL.createObjectURL(file);
                        preview.style.display = 'block';
                    }}
                }}
                
                function handleThumbnailUpload() {{
                    const file = document.getElementById('thumbnailFile').files[0];
                    if (file) {{
                        const preview = document.getElementById('thumbnail-preview');
                        const img = document.getElementById('thumbnail-image');
                        img.src = URL.createObjectURL(file);
                        preview.style.display = 'block';
                    }}
                }}
                
                function captureFrame() {{
                    const video = document.getElementById('video-player');
                    const currentVideo = document.querySelector('video[controls]');
                    const sourceVideo = video.src ? video : currentVideo;
                    
                    if (!sourceVideo || !sourceVideo.src) {{
                        alert('Please upload a video first or use the current video');
                        return;
                    }}
                    
                    const canvas = document.getElementById('capture-canvas');
                    canvas.width = sourceVideo.videoWidth;
                    canvas.height = sourceVideo.videoHeight;
                    
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(sourceVideo, 0, 0, canvas.width, canvas.height);
                    
                    canvas.toBlob(function(blob) {{
                        const file = new File([blob], 'thumbnail.jpg', {{ type: 'image/jpeg' }});
                        const dataTransfer = new DataTransfer();
                        dataTransfer.items.add(file);
                        document.getElementById('thumbnailFile').files = dataTransfer.files;
                        
                        const preview = document.getElementById('thumbnail-preview');
                        const img = document.getElementById('thumbnail-image');
                        img.src = URL.createObjectURL(blob);
                        preview.style.display = 'block';
                    }}, 'image/jpeg', 0.9);
                }}
                
                function toggleTag(element) {{
                    const tag = element.getAttribute('data-tag');
                    element.classList.toggle('selected');
                    
                    if (element.classList.contains('selected')) {{
                        if (!selectedTags.includes(tag)) {{
                            selectedTags.push(tag);
                        }}
                    }} else {{
                        selectedTags = selectedTags.filter(t => t !== tag);
                    }}
                    
                    updateSelectedTagsDisplay();
                }}
                
                function addCustomTag(event) {{
                    if (event.key === 'Enter') {{
                        event.preventDefault();
                        const input = document.getElementById('custom-tag-input');
                        const tag = input.value.trim();
                        
                        if (tag && !selectedTags.includes(tag)) {{
                            selectedTags.push(tag);
                            updateSelectedTagsDisplay();
                            input.value = '';
                        }}
                    }}
                }}
                
                function removeTag(tag) {{
                    selectedTags = selectedTags.filter(t => t !== tag);
                    
                    // Unselect predefined tag if it exists
                    const container = document.getElementById('tags-container');
                    const tagOptions = container.querySelectorAll('.tag-option');
                    tagOptions.forEach(option => {{
                        if (option.getAttribute('data-tag') === tag) {{
                            option.classList.remove('selected');
                        }}
                    }});
                    
                    updateSelectedTagsDisplay();
                }}
                
                function updateSelectedTagsDisplay() {{
                    const container = document.getElementById('selected-tags');
                    
                    if (selectedTags.length === 0) {{
                        container.innerHTML = '<p style="color: #a0aec0; font-style: italic;">No tags selected</p>';
                    }} else {{
                        container.innerHTML = selectedTags.map(tag => 
                            `<span class="selected-tag">
                                ${{tag}}
                                <i class="fas fa-times" onclick="removeTag('${{tag}}')"></i>
                            </span>`
                        ).join('');
                    }}
                }}
                
                // Initialize display
                updateSelectedTagsDisplay();
                
                async function submitEditVideo(event) {{
                    event.preventDefault();
                    
                    const formData = new FormData(event.target);
                    formData.append('tags', selectedTags.join(','));
                    
                    try {{
                        const response = await fetch('/admin/videos/general-knowledge/{video.id}/update', {{
                            method: 'POST',
                            body: formData
                        }});
                        
                        const result = await response.json();
                        
                        if (result.status) {{
                            alert(result.message);
                            window.location.href = '/admin/videos/channels/' + result.channel_id;
                        }} else {{
                            alert('Error: ' + result.message);
                        }}
                    }} catch (error) {{
                        console.error('Error:', error);
                        alert('Error updating video');
                    }}
                }}
            </script>
            """
            
            return HTMLResponse(content=create_html_page(f"Edit: {video.title}", content, "videos"))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading edit page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/general-knowledge/{video_id}/update")
async def update_general_knowledge_video(
    request: Request,
    video_id: str,
    channel_id: str = Form(...),
    title: str = Form(...),
    slug: str = Form(...),
    subtitle: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    hashtags: Optional[str] = Form(None),
    video_file: Optional[UploadFile] = File(None),
    thumbnail_file: Optional[UploadFile] = File(None)
):
    """Update a general knowledge video"""
    
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
        
        async with get_db_session() as session:
            # Get existing video
            video_result = await session.execute(
                select(GeneralKnowledgeVideo).where(GeneralKnowledgeVideo.id == UUID(video_id))
            )
            video = video_result.scalar_one_or_none()
            
            if not video:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Video not found"}
                )
            
            old_channel_id = video.channel_id
            new_channel_id = UUID(channel_id)
            
            # Parse tags from JSON string
            tags_list = json.loads(tags) if tags else []
            
            # Update basic fields
            video.title = title
            video.slug = slug
            video.subtitle = subtitle
            video.description = description
            video.tags = json.dumps(tags_list)
            video.hashtags = hashtags
            # Update publish date if provided
            if 'publish_date' in (await request.form()):
                # We prefer the explicit form value if present
                publish_date_val = (await request.form()).get('publish_date')
                video.publish_date = datetime.fromisoformat(publish_date_val) if publish_date_val else None
            
            # Update video file if provided
            if video_file and video_file.filename:
                upload_result = await file_upload_service.upload_file(
                    file=video_file,
                    file_category="videos",
                    validate_content=False
                )
                
                video.video_url = upload_result["file_url"]  # e.g., "videos/abc.mp4"
                video.duration = upload_result.get("duration", 0)
            
            # Update thumbnail if provided
            if thumbnail_file and thumbnail_file.filename:
                thumbnail_result = await file_upload_service.upload_file(
                    file=thumbnail_file,
                    file_category="thumbnails",
                    validate_content=False
                )
                
                video.thumbnail_url = thumbnail_result["file_url"]  # e.g., "thumbnails/xyz.jpg"
            
            # Update channel if changed
            if old_channel_id != new_channel_id:
                video.channel_id = new_channel_id
                
                # Update old channel count
                old_channel = await session.get(VideoChannel, old_channel_id)
                if old_channel and old_channel.total_videos > 0:
                    old_channel.total_videos -= 1
                
                # Update new channel count
                new_channel = await session.get(VideoChannel, new_channel_id)
                if new_channel:
                    new_channel.total_videos += 1
            
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": "Video updated successfully!",
                "channel_id": channel_id
            })
    except Exception as e:
        print(f"Error updating video: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.delete("/videos/general-knowledge/{video_id}")
async def delete_general_knowledge_video(request: Request, video_id: str):
    """Delete a general knowledge video"""
    
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
        
        async with get_db_session() as session:
            # Get video
            video_result = await session.execute(
                select(GeneralKnowledgeVideo).where(GeneralKnowledgeVideo.id == UUID(video_id))
            )
            video = video_result.scalar_one_or_none()
            
            if not video:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Video not found"}
                )
            
            channel_id = video.channel_id
            
            # Delete video
            await session.delete(video)
            
            # Update channel video count
            channel = await session.get(VideoChannel, channel_id)
            if channel and channel.total_videos > 0:
                channel.total_videos -= 1
            
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": "Video deleted successfully!"
            })
    except Exception as e:
        print(f"Error deleting video: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.get("/video/{slug}/details", response_class=HTMLResponse)
async def video_details(request: Request, slug: str):
    """Detailed view of a specific video with analytics and comments"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
        from app.models.video_engagement import VideoComment, VideoLike
        from app.models.user import User
        
        async with get_db_session() as session:
            # Try to find in series first
            series_result = await session.execute(
                select(SeriesVideo, VideoSeries)
                .join(VideoSeries, SeriesVideo.series_id == VideoSeries.id)
                .where(SeriesVideo.slug == slug)
            )
            series_data = series_result.first()
            
            video = None
            video_type = None
            parent_name = None
            
            if series_data:
                video, parent = series_data
                video_type = "series"
                parent_name = parent.title
            else:
                # Try channel video
                channel_result = await session.execute(
                    select(GeneralKnowledgeVideo, VideoChannel)
                    .join(VideoChannel, GeneralKnowledgeVideo.channel_id == VideoChannel.id)
                    .where(GeneralKnowledgeVideo.slug == slug)
                )
                channel_data = channel_result.first()
                
                if channel_data:
                    video, parent = channel_data
                    video_type = "channel"
                    parent_name = parent.name
            
            if not video:
                raise HTTPException(status_code=404, detail="Video not found")
            
            # Get comments with user info
            comments_result = await session.execute(
                select(VideoComment, User)
                .join(User, VideoComment.user_id == User.id)
                .where(
                    VideoComment.video_slug == slug,
                    VideoComment.is_deleted == 0
                )
                .order_by(desc(VideoComment.created_at))
            )
            comments_data = comments_result.all()
            
            # Get likes/dislikes
            likes_result = await session.execute(
                select(func.count(VideoLike.id))
                .where(VideoLike.video_slug == slug, VideoLike.vote == 1)
            )
            likes_count = likes_result.scalar() or 0
            
            dislikes_result = await session.execute(
                select(func.count(VideoLike.id))
                .where(VideoLike.video_slug == slug, VideoLike.vote == -1)
            )
            dislikes_count = dislikes_result.scalar() or 0
        
        # Build comments HTML
        comments_html = ""
        for comment, user in comments_data:
            comment_html = f"""
            <div class="comment-item" id="comment-{comment.id}" style="padding: 1rem; background: #f7fafc; border-radius: 8px; margin-bottom: 1rem;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                            {user.username[:2].upper()}
                        </div>
                        <div>
                            <strong style="color: #2d3748;">{user.username}</strong>
                            <p style="margin: 0; font-size: 0.85rem; color: #718096;">{comment.created_at.strftime('%Y-%m-%d %H:%M')}</p>
                        </div>
                    </div>
                    <button onclick="deleteComment('{comment.id}')" class="btn btn-danger" style="padding: 0.5rem 1rem;">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
                <p style="margin: 0.5rem 0 0 0; color: #2d3748;">{comment.content}</p>
                <div style="display: flex; gap: 1rem; margin-top: 0.5rem; font-size: 0.85rem; color: #718096;">
                    <span><i class="fas fa-thumbs-up"></i> {comment.likes_count} likes</span>
                    {f'<span><i class="fas fa-reply"></i> {comment.replies_count} replies</span>' if comment.replies_count > 0 else ''}
                </div>
            </div>
            """
            comments_html += comment_html
        
        if not comments_html:
            comments_html = '<p style="text-align: center; color: #718096; padding: 2rem;">No comments yet</p>'
        
        content = f"""
        <div class="page-header">
            <div>
                <h1 class="page-title"><i class="fas fa-video"></i> {video.title}</h1>
                <p class="page-subtitle">{video_type.title()} Video • {parent_name}</p>
            </div>
            <a href="/admin/videos/all" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to All Videos
            </a>
        </div>
        
        <!-- Video Stats Cards -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-eye" style="font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <p style="margin: 0; opacity: 0.9; font-size: 0.85rem;">Views</p>
                        <h3 style="margin: 0.25rem 0 0 0; font-size: 1.75rem; font-weight: 700;">{video.views:,}</h3>
                    </div>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-comments" style="font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <p style="margin: 0; opacity: 0.9; font-size: 0.85rem;">Comments</p>
                        <h3 style="margin: 0.25rem 0 0 0; font-size: 1.75rem; font-weight: 700;">{len(comments_data)}</h3>
                    </div>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-thumbs-up" style="font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <p style="margin: 0; opacity: 0.9; font-size: 0.85rem;">Likes</p>
                        <h3 style="margin: 0.25rem 0 0 0; font-size: 1.75rem; font-weight: 700;">{likes_count}</h3>
                    </div>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); border-radius: 12px; padding: 1.5rem; color: white;">
                <div style="display: flex; align-items: center; gap: 1rem;">
                    <div style="width: 50px; height: 50px; background: rgba(255, 255, 255, 0.2); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
                        <i class="fas fa-thumbs-down" style="font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <p style="margin: 0; opacity: 0.9; font-size: 0.85rem;">Dislikes</p>
                        <h3 style="margin: 0.25rem 0 0 0; font-size: 1.75rem; font-weight: 700;">{dislikes_count}</h3>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Video Information -->
        <div class="card" style="margin-bottom: 2rem;">
            <h3 style="margin: 0 0 1rem 0; color: var(--primary-color);"><i class="fas fa-info-circle"></i> Video Information</h3>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                <div>
                    <p style="margin: 0; color: #718096; font-size: 0.85rem;">Title</p>
                    <p style="margin: 0.25rem 0 0 0; font-weight: 600;">{video.title}</p>
                </div>
                <div>
                    <p style="margin: 0; color: #718096; font-size: 0.85rem;">Slug</p>
                    <p style="margin: 0.25rem 0 0 0; font-weight: 600;">{video.slug}</p>
                </div>
                <div>
                    <p style="margin: 0; color: #718096; font-size: 0.85rem;">Duration</p>
                    <p style="margin: 0.25rem 0 0 0; font-weight: 600;">{video.duration} seconds</p>
                </div>
                <div>
                    <p style="margin: 0; color: #718096; font-size: 0.85rem;">Created</p>
                    <p style="margin: 0.25rem 0 0 0; font-weight: 600;">{video.created_at.strftime('%Y-%m-%d %H:%M')}</p>
                </div>
            </div>
            {f'<div style="margin-top: 1rem;"><p style="margin: 0; color: #718096; font-size: 0.85rem;">Description</p><p style="margin: 0.25rem 0 0 0;">{video.description or "No description"}</p></div>' if hasattr(video, 'description') else ''}
        </div>
        
        <!-- Comments Section -->
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="margin: 0; color: var(--primary-color);"><i class="fas fa-comments"></i> Comments ({len(comments_data)})</h3>
            </div>
            <div id="comments-container">
                {comments_html}
            </div>
        </div>
        
        <script>
            async function deleteComment(commentId) {{
                if (!confirm('Are you sure you want to delete this comment?')) return;
                
                try {{
                    const response = await fetch(`/admin/video/comment/${{commentId}}/delete`, {{
                        method: 'POST'
                    }});
                    
                    if (response.ok) {{
                        document.getElementById(`comment-${{commentId}}`).remove();
                        showNotification('Comment deleted successfully', 'success');
                    }} else {{
                        showNotification('Failed to delete comment', 'error');
                    }}
                }} catch (err) {{
                    console.error(err);
                    showNotification('Error deleting comment', 'error');
                }}
            }}
            
            function showNotification(message, type) {{
                const notification = document.createElement('div');
                notification.style.cssText = `
                    position: fixed;
                    top: 2rem;
                    right: 2rem;
                    padding: 1rem 1.5rem;
                    background: ${{type === 'success' ? '#48bb78' : '#f56565'}};
                    color: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    z-index: 9999;
                `;
                notification.textContent = message;
                document.body.appendChild(notification);
                
                setTimeout(() => {{
                    notification.remove();
                }}, 3000);
            }}
        </script>
        """
        
        return create_html_page(f"Video Details - {video.title}", content)
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "message": str(e),
                "status": False,
                "error_type": "HTTPException",
                "detail": error_detail
            }
        )


@router.post("/video/comment/{comment_id}/delete")
async def delete_comment(request: Request, comment_id: str):
    """Delete a comment"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(status_code=401, content={"status": False, "message": "Unauthorized"})
    
    try:
        from app.models.video_engagement import VideoComment
        
        async with get_db_session() as session:
            # Find the comment
            result = await session.execute(
                select(VideoComment).where(VideoComment.id == comment_id)
            )
            comment = result.scalar_one_or_none()
            
            if not comment:
                return JSONResponse(status_code=404, content={"status": False, "message": "Comment not found"})
            
            # Soft delete
            comment.is_deleted = 1
            await session.commit()
            
            return JSONResponse(content={"status": True, "message": "Comment deleted successfully"})
            
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.get("/admin/videos/channels/thumbnails/{filename}")
async def get_channel_thumbnail(filename: str):
    file_path = Path("uploads/thumbnails") / filename
    if file_path.exists():
        return FileResponse(file_path)
    else:
        raise HTTPException(status_code=404, detail="Thumbnail not found")