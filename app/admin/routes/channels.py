"""
Video Channels admin routes
Handles channel creation, editing, and management for general knowledge videos
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, or_
from typing import Optional
from uuid import UUID, uuid4
import os
from pathlib import Path

from app.db.database import get_db_session
from app.models.video_channel import VideoChannel, GeneralKnowledgeVideo
from app.admin.templates.base import create_html_page

router = APIRouter()


@router.get("/videos/channels", response_class=HTMLResponse)
async def channels_list(request: Request):
    """List all video channels"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Fetch channels from database
    async with get_db_session() as session:
        result = await session.execute(
            select(VideoChannel)
            .order_by(desc(VideoChannel.created_at))
        )
        all_channels = result.scalars().all()
        
        channels_data = [
            {
                'id': str(channel.id),
                'name': channel.name,
                'slug': channel.slug,
                'description': channel.description or '',
                'video_count': channel.total_videos,
                'views': channel.total_views,
                'is_active': channel.is_active,
                'thumbnail_url': channel.thumbnail_url
            }
            for channel in all_channels
        ]
    
    content = f"""
    <div class="page-header">
        <div>
            <h1 class="page-title">Video Channels</h1>
            <p class="page-subtitle">Manage channels for general knowledge videos</p>
        </div>
        <div style="display: flex; gap: 1rem;">
            <a href="/admin/videos" class="btn btn-secondary">
                <i class="fas fa-arrow-left"></i> Back to Library
            </a>
            <button class="btn btn-primary" onclick="openCreateChannelModal()">
                <i class="fas fa-plus"></i> Create Channel
            </button>
        </div>
    </div>
    
    <div id="channels-container">
        {generate_channels_cards(channels_data)}
    </div>
    
    <!-- Create Channel Modal -->
    <div id="create-channel-modal" class="modal">
        <div class="modal-content" style="max-width: 600px;">
            <div class="modal-header">
                <h2><i class="fas fa-tv"></i> Create New Channel</h2>
                <button class="modal-close" onclick="closeCreateChannelModal()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            <form id="create-channel-form" onsubmit="submitCreateChannel(event)" enctype="multipart/form-data">
                <div class="modal-body">
                    <div class="form-group">
                        <label for="channel-name">Channel Name *</label>
                        <input type="text" id="channel-name" name="name" class="form-control" required onkeyup="formatChannelSlug()">
                    </div>
                    
                    <div class="form-group">
                        <label for="channel-slug">Channel Slug *</label>
                        <input type="text" id="channel-slug" name="slug" class="form-control" required>
                        <small class="field-help">URL-friendly identifier (lowercase, hyphens)</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="channel-description">Description</label>
                        <textarea id="channel-description" name="description" class="form-control" rows="3"></textarea>
                    </div>
                    
                    <div class="form-group">
                        <label for="channel-thumbnail">Channel Photo/Thumbnail</label>
                        <input type="file" id="channel-thumbnail" name="thumbnail" class="form-control" accept="image/*" onchange="previewChannelThumbnail()">
                        <small class="field-help">Optional - Upload a photo to represent this channel</small>
                    </div>
                    
                    <div id="thumbnail-preview-container" style="display: none; margin-top: 1rem;">
                        <img id="thumbnail-preview" src="" alt="Thumbnail preview" style="max-width: 100%; max-height: 200px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeCreateChannelModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Create Channel
                    </button>
                </div>
            </form>
        </div>
    </div>
    
    <style>
        .modal {{
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
        }}
        
        .modal.active {{
            display: flex;
        }}
        
        .modal-content {{
            background: white;
            border-radius: 12px;
            max-width: 90%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: modalSlideIn 0.3s ease-out;
        }}
        
        @keyframes modalSlideIn {{
            from {{
                opacity: 0;
                transform: translateY(-20px);
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
            justify-content: space-between;
            align-items: center;
        }}
        
        .modal-header h2 {{
            margin: 0;
            color: #2d3748;
            font-size: 1.5rem;
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
            padding: 0.25rem;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 6px;
            transition: all 0.2s ease;
        }}
        
        .modal-close:hover {{
            background: #f7fafc;
            color: #2d3748;
        }}
        
        .modal-body {{
            padding: 2rem;
        }}
        
        .modal-footer {{
            padding: 1.5rem 2rem;
            border-top: 1px solid #e2e8f0;
            display: flex;
            justify-content: flex-end;
            gap: 1rem;
        }}
        
        .form-group {{
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
        
        .channels-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-top: 2rem;
        }}
        
        .channel-card {{
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            cursor: pointer;
        }}
        
        .channel-card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.15);
        }}
        
        .channel-header {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            padding: 1.5rem;
            color: white;
        }}
        
        .channel-title {{
            font-size: 1.25rem;
            font-weight: 700;
            margin: 0 0 0.5rem 0;
        }}
        
        .channel-description {{
            font-size: 0.95rem;
            opacity: 0.9;
            margin: 0;
        }}
        
        .channel-body {{
            padding: 1.5rem;
        }}
        
        .channel-info {{
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        .channel-info-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #718096;
            font-size: 0.9rem;
        }}
        
        .channel-actions {{
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
    </style>
    
    <script>
        function openCreateChannelModal() {{
            document.getElementById('create-channel-modal').classList.add('active');
        }}
        
        function closeCreateChannelModal() {{
            document.getElementById('create-channel-modal').classList.remove('active');
            document.getElementById('create-channel-form').reset();
            document.getElementById('thumbnail-preview-container').style.display = 'none';
        }}
        
        function formatChannelSlug() {{
            const name = document.getElementById('channel-name').value;
            const slug = document.getElementById('channel-slug');
            slug.value = name.toLowerCase()
                .replace(/[^a-z0-9]+/g, '-')
                .replace(/^-+|-+$/g, '');
        }}
        
        function previewChannelThumbnail() {{
            const file = document.getElementById('channel-thumbnail').files[0];
            if (file) {{
                const preview = document.getElementById('thumbnail-preview');
                const container = document.getElementById('thumbnail-preview-container');
                preview.src = URL.createObjectURL(file);
                container.style.display = 'block';
            }}
        }}
        
        async function submitCreateChannel(e) {{
            e.preventDefault();
            
            const formData = new FormData(e.target);
            
            try {{
                const response = await fetch('/admin/videos/channels/create', {{
                    method: 'POST',
                    body: formData
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    alert(result.message);
                    window.location.reload();
                }} else {{
                    alert('Error: ' + result.message);
                }}
            }} catch (error) {{
                console.error('Error:', error);
                alert('Error creating channel');
            }}
        }}
        
        function editChannel(channelId) {{
            window.location.href = `/admin/videos/channels/${{channelId}}/edit-page`;
        }}
        
        async function deleteChannel(channelId, channelName) {{
            if (!confirm(`Are you sure you want to delete "${{channelName}}"? This will delete all videos in this channel.`)) {{
                return;
            }}
            
            try {{
                const response = await fetch(`/admin/videos/channels/${{channelId}}`, {{
                    method: 'DELETE'
                }});
                
                const result = await response.json();
                
                if (result.status) {{
                    alert(result.message);
                    window.location.reload();
                }} else {{
                    alert('Error: ' + result.message);
                }}
            }} catch (error) {{
                console.error('Error:', error);
                alert('Error deleting channel');
            }}
        }}
        
        // Close modal on outside click
        window.onclick = function(event) {{
            const modal = document.getElementById('create-channel-modal');
            if (event.target === modal) {{
                closeCreateChannelModal();
            }}
        }}
    </script>
    """
    
    return HTMLResponse(content=create_html_page("Video Channels", content, "videos"))


def generate_channels_cards(channels_data):
    """Generate HTML for channel cards"""
    if not channels_data:
        return """
        <div class="empty-state">
            <i class="fas fa-tv"></i>
            <h3>No Channels Yet</h3>
            <p>Create your first video channel to get started</p>
            <button class="btn btn-primary" onclick="openCreateChannelModal()">
                <i class="fas fa-plus"></i> Create Channel
            </button>
        </div>
        """
    
    cards_html = '<div class="channels-grid">'
    for channel in channels_data:
        status_badge = '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; background: #48bb78; color: white;">Active</span>' if channel.get('is_active') else '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.8rem; font-weight: 600; background: #cbd5e0; color: #4a5568;">Inactive</span>'
        
        cards_html += f"""
        <div class="channel-card" onclick="window.location.href='/admin/videos/channels/{channel['id']}'">
            <div class="channel-header">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <h3 class="channel-title" style="margin: 0; flex: 1;">{channel['name']}</h3>
                    {status_badge}
                </div>
                <p class="channel-description">{channel.get('description', 'No description')[:100]}</p>
            </div>
            <div class="channel-body">
                <div class="channel-info">
                    <div class="channel-info-item">
                        <i class="fas fa-video"></i>
                        <span>{channel['video_count']} videos</span>
                    </div>
                    <div class="channel-info-item">
                        <i class="fas fa-eye"></i>
                        <span>{channel.get('views', 0)} views</span>
                    </div>
                </div>
                <div class="channel-actions">
                    <a href="/admin/videos/channels/{channel['id']}" class="btn btn-sm btn-secondary" onclick="event.stopPropagation()">
                        <i class="fas fa-eye"></i> View
                    </a>
                    <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); editChannel('{channel['id']}')">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteChannel('{channel['id']}', '{channel['name']}')">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        </div>
        """
    cards_html += '</div>'
    return cards_html


@router.post("/videos/channels/create")
async def create_channel(
    request: Request,
    name: str = Form(...),
    slug: str = Form(...),
    description: Optional[str] = Form(None),
    thumbnail: Optional[UploadFile] = File(None)
):
    """Create a new video channel"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        # Save thumbnail if provided
        thumbnail_url = None
        if thumbnail and thumbnail.filename:
            thumbnails_dir = Path("uploads/channel_thumbnails")
            thumbnails_dir.mkdir(parents=True, exist_ok=True)
            
            thumbnail_filename = f"{uuid4()}_{thumbnail.filename}"
            thumbnail_path = thumbnails_dir / thumbnail_filename
            
            with open(thumbnail_path, "wb") as f:
                content = await thumbnail.read()
                f.write(content)
            
            thumbnail_url = f"/uploads/channel_thumbnails/{thumbnail_filename}"
        
        async with get_db_session() as session:
            # Check if slug already exists
            existing = await session.execute(
                select(VideoChannel).where(VideoChannel.slug == slug)
            )
            if existing.scalar_one_or_none():
                return JSONResponse(content={
                    "status": False,
                    "message": f"Channel with slug '{slug}' already exists"
                })
            
            # Create channel
            channel = VideoChannel(
                name=name,
                slug=slug,
                description=description,
                thumbnail_url=thumbnail_url
            )
            
            session.add(channel)
            await session.commit()
        
        return JSONResponse(content={
            "status": True,
            "message": "Channel created successfully!"
        })
    
    except Exception as e:
        print(f"Error creating channel: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.get("/videos/channels/{channel_id}", response_class=HTMLResponse)
async def view_channel(request: Request, channel_id: str):
    """View a specific channel and its videos"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as session:
            # Get channel
            channel_result = await session.execute(
                select(VideoChannel).where(VideoChannel.id == UUID(channel_id))
            )
            channel = channel_result.scalar_one_or_none()
            
            if not channel:
                raise HTTPException(status_code=404, detail="Channel not found")
            
            # Get videos in channel
            videos_result = await session.execute(
                select(GeneralKnowledgeVideo)
                .where(GeneralKnowledgeVideo.channel_id == channel.id)
                .order_by(desc(GeneralKnowledgeVideo.created_at))
            )
            videos = videos_result.scalars().all()
            
            videos_data = [
                {
                    'id': str(video.id),
                    'title': video.title,
                    'subtitle': video.subtitle or '',
                    'slug': video.slug,
                    'video_url': video.video_url,
                    'thumbnail_url': video.thumbnail_url,
                    'views': video.views,
                    'is_published': video.is_published
                }
                for video in videos
            ]
        
        content = f"""
        <div class="page-header">
            <div>
                <h1 class="page-title">{channel.name}</h1>
                <p class="page-subtitle">{channel.description or 'No description'}</p>
            </div>
            <div style="display: flex; gap: 1rem;">
                <a href="/admin/videos/channels" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back to Channels
                </a>
                <a href="/admin/videos/general-knowledge/create?channel_id={channel_id}" class="btn btn-primary">
                    <i class="fas fa-plus"></i> Add Video
                </a>
                <button class="btn btn-primary" onclick="editChannel('{channel_id}')">
                    <i class="fas fa-edit"></i> Edit Channel
                </button>
                <button class="btn btn-danger" onclick="deleteChannel('{channel_id}', '{channel.name}')">
                    <i class="fas fa-trash"></i> Delete Channel
                </button>
            </div>
        </div>
        
        <div style="background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);">
            <h3 style="font-size: 1.1rem; font-weight: 700; color: #2d3748; margin: 0 0 1rem 0;">
                <i class="fas fa-info-circle"></i> Channel Details
            </h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div>
                    <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Slug</label>
                    <span style="font-weight: 600; color: #2d3748;">{channel.slug}</span>
                </div>
                <div>
                    <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Total Videos</label>
                    <span style="font-weight: 600; color: #2d3748;">{channel.total_videos}</span>
                </div>
                <div>
                    <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Total Views</label>
                    <span style="font-weight: 600; color: #2d3748;">{channel.total_views}</span>
                </div>
                <div>
                    <label style="font-size: 0.85rem; color: #718096; display: block; margin-bottom: 0.25rem;">Status</label>
                    <span style="font-weight: 600; color: {'#48bb78' if channel.is_active else '#cbd5e0'};">{'Active' if channel.is_active else 'Inactive'}</span>
                </div>
            </div>
        </div>
        
        <h2 style="font-size: 1.25rem; font-weight: 700; color: #2d3748; margin-bottom: 1rem;">
            <i class="fas fa-video"></i> Videos in Channel ({len(videos_data)})
        </h2>
        
        <div id="videos-grid">
            {generate_videos_grid(videos_data)}
        </div>
        
        <style>
            .videos-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 1.5rem;
            }}
            
            .video-card {{
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                cursor: pointer;
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
            
            .video-content {{
                padding: 1.5rem;
            }}
            
            .video-title {{
                font-size: 1.1rem;
                font-weight: 600;
                color: #2d3748;
                margin: 0 0 0.5rem 0;
            }}
            
            .video-subtitle {{
                font-size: 0.9rem;
                color: #718096;
                margin: 0 0 1rem 0;
            }}
            
            .video-stats {{
                display: flex;
                align-items: center;
                gap: 1rem;
                font-size: 0.85rem;
                color: #a0aec0;
            }}
            
            .video-stat {{
                display: flex;
                align-items: center;
                gap: 0.25rem;
            }}
            
            .empty-videos {{
                text-align: center;
                padding: 4rem 2rem;
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
            function viewVideoDetails(slug) {{
                window.location.href = `/admin/video/${{slug}}/stats`;
            }}
            
            function editChannel(channelId) {{
                window.location.href = `/admin/videos/channels/${{channelId}}/edit-page`;
            }}
            
            async function deleteChannel(channelId, channelName) {{
                if (!confirm(`Are you sure you want to delete "${{channelName}}"? This will delete all videos in this channel.`)) {{
                    return;
                }}
                
                try {{
                    const response = await fetch(`/admin/videos/channels/${{channelId}}`, {{
                        method: 'DELETE'
                    }});
                    
                    const result = await response.json();
                    
                    if (result.status) {{
                        alert(result.message);
                        window.location.href = '/admin/videos/channels';
                    }} else {{
                        alert('Error: ' + result.message);
                    }}
                }} catch (error) {{
                    console.error('Error:', error);
                    alert('Error deleting channel');
                }}
            }}
            
            function editVideo(videoId) {{
                window.location.href = `/admin/videos/general-knowledge/${{videoId}}/edit`;
            }}
            
            async function deleteVideo(videoId, videoTitle) {{
                if (!confirm(`Are you sure you want to delete "${{videoTitle}}"?`)) {{
                    return;
                }}
                
                try {{
                    const response = await fetch(`/admin/videos/general-knowledge/${{videoId}}`, {{
                        method: 'DELETE'
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
                    alert('Error deleting video');
                }}
            }}
        </script>
        """
        
        return HTMLResponse(content=create_html_page(f"Channel: {channel.name}", content, "videos"))
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error viewing channel: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def generate_videos_grid(videos_data):
    """Generate HTML for videos grid"""
    if not videos_data:
        return """
        <div class="empty-videos">
            <i class="fas fa-video-slash"></i>
            <h3 style="color: #2d3748; margin: 0 0 0.5rem 0;">No Videos Yet</h3>
            <p style="color: #718096; margin: 0 0 1rem 0;">Add videos to this channel to get started</p>
            <a href="/admin/videos/general-knowledge/create" class="btn btn-primary">
                <i class="fas fa-plus"></i> Add Video
            </a>
        </div>
        """
    
    videos_html = '<div class="videos-grid">'
    for video in videos_data:
        thumbnail = video.get('thumbnail_url') or '/static/images/video-placeholder.jpg'
        status_badge = '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; background: #48bb78; color: white;">Published</span>' if video.get('is_published') else '<span style="display: inline-block; padding: 0.25rem 0.75rem; border-radius: 12px; font-size: 0.75rem; font-weight: 600; background: #ed8936; color: white;">Draft</span>'
        
        videos_html += f"""
        <div class="video-card" onclick="viewVideoDetails('{video['slug']}')">
            <img src="{thumbnail}" alt="{video['title']}" class="video-thumbnail">
            <div class="video-content">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                    <h3 class="video-title" style="margin: 0; flex: 1;">{video['title']}</h3>
                    {status_badge}
                </div>
                <p class="video-subtitle">{video.get('subtitle', '')}</p>
                <div class="video-stats">
                    <div class="video-stat">
                        <i class="fas fa-eye"></i>
                        <span>{video.get('views', 0)} views</span>
                    </div>
                </div>
                <div style="margin-top: 1rem; display: flex; gap: 0.5rem;">
                    <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation(); window.location.href='/admin/video/{video['slug']}/stats'">
                        <i class="fas fa-chart-line"></i> Stats
                    </button>
                    <button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); editVideo('{video['id']}')" style="flex: 1;">
                        <i class="fas fa-edit"></i> Edit
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); deleteVideo('{video['id']}', '{video['title']}')" style="flex: 1;">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </div>
        </div>
        """
    videos_html += '</div>'
    return videos_html


@router.get("/videos/channels/{channel_id}/edit")
async def get_channel_for_edit(request: Request, channel_id: str):
    """Get channel data for editing (JSON response for modal)"""
    
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as session:
            channel_result = await session.execute(
                select(VideoChannel).where(VideoChannel.id == UUID(channel_id))
            )
            channel = channel_result.scalar_one_or_none()
            
            if not channel:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Channel not found"}
                )
            
            return JSONResponse(content={
                "status": True,
                "channel": {
                    "id": str(channel.id),
                    "name": channel.name,
                    "slug": channel.slug,
                    "description": channel.description,
                    "thumbnail_url": channel.thumbnail_url
                }
            })
    except Exception as e:
        print(f"Error getting channel: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.get("/videos/channels/{channel_id}/edit-page", response_class=HTMLResponse)
async def edit_channel_page(request: Request, channel_id: str):
    """Show channel edit form page"""
    
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as session:
            channel_result = await session.execute(
                select(VideoChannel).where(VideoChannel.id == UUID(channel_id))
            )
            channel = channel_result.scalar_one_or_none()
            
            if not channel:
                raise HTTPException(status_code=404, detail="Channel not found")
            
            content = f"""
            <div class="page-header">
                <div>
                    <h1 class="page-title"><i class="fas fa-edit"></i> Edit Channel</h1>
                    <p class="page-subtitle">Update channel information and settings</p>
                </div>
                <a href="/admin/videos/channels/{channel_id}" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back to Channel
                </a>
            </div>
            
            <form id="editChannelForm" onsubmit="submitEditChannel(event)" enctype="multipart/form-data">
                <!-- Channel Information -->
                <div class="form-section">
                    <h3 class="section-title">
                        <i class="fas fa-info-circle"></i> Channel Information
                    </h3>
                    
                    <div class="form-group">
                        <label for="channelName">Channel Name *</label>
                        <input type="text" id="channelName" name="name" value="{channel.name}" required class="form-control" placeholder="Enter channel name">
                    </div>
                    
                    <div class="form-group">
                        <label for="channelSlug">URL Slug *</label>
                        <input type="text" id="channelSlug" name="slug" value="{channel.slug}" required class="form-control" placeholder="channel-slug">
                        <small class="field-help">URL-friendly identifier (e.g., wildlife-wonders, lowercase with hyphens)</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="channelDescription">Description</label>
                        <textarea id="channelDescription" name="description" class="form-control" rows="4" placeholder="Enter channel description...">{channel.description or ''}</textarea>
                        <small class="field-help">Brief description of what this channel is about</small>
                    </div>
                </div>
                
                <!-- Channel Thumbnail -->
                <div class="form-section">
                    <h3 class="section-title">
                        <i class="fas fa-image"></i> Channel Thumbnail
                    </h3>
                    
                    <div class="form-group">
                        <label>Current Thumbnail</label>
                        {'<img src="' + channel.thumbnail_url + '" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="Current thumbnail">' if channel.thumbnail_url else '<p style="color: #a0aec0; font-style: italic;">No thumbnail set</p>'}
                    </div>
                    
                    <div class="form-group">
                        <label for="channelThumbnail">Upload New Thumbnail</label>
                        <div class="file-upload-box" onclick="document.getElementById('channelThumbnail').click()">
                            <i class="fas fa-cloud-upload-alt"></i>
                            <p>Click to upload channel thumbnail</p>
                            <small>Recommended size: 1200x675px (16:9 ratio)</small>
                        </div>
                        <input type="file" id="channelThumbnail" name="thumbnail" accept="image/*" style="display: none;" onchange="previewThumbnail()">
                        
                        <div id="thumbnailPreviewContainer" style="display: none; margin-top: 1rem;">
                            <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #2d3748;">
                                <i class="fas fa-eye"></i> New Thumbnail Preview
                            </label>
                            <img id="thumbnailPreview" style="max-width: 300px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);" alt="New thumbnail preview">
                        </div>
                    </div>
                </div>
                
                <!-- Submit -->
                <div class="form-actions">
                    <a href="/admin/videos/channels/{channel_id}" class="btn btn-secondary">
                        <i class="fas fa-times"></i> Cancel
                    </a>
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i> Update Channel
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
                
                .form-group {{
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
                    box-sizing: border-box;
                }}
                
                .form-control:focus {{
                    outline: none;
                    border-color: #f093fb;
                }}
                
                textarea.form-control {{
                    resize: vertical;
                    min-height: 120px;
                    font-family: inherit;
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
                function previewThumbnail() {{
                    const file = document.getElementById('channelThumbnail').files[0];
                    if (file) {{
                        const reader = new FileReader();
                        reader.onload = function(e) {{
                            document.getElementById('thumbnailPreview').src = e.target.result;
                            document.getElementById('thumbnailPreviewContainer').style.display = 'block';
                        }};
                        reader.readAsDataURL(file);
                    }}
                }}
                
                async function submitEditChannel(event) {{
                    event.preventDefault();
                    
                    const formData = new FormData(event.target);
                    
                    try {{
                        const response = await fetch('/admin/videos/channels/{channel_id}/update', {{
                            method: 'POST',
                            body: formData
                        }});
                        
                        const result = await response.json();
                        
                        if (result.status) {{
                            alert(result.message);
                            window.location.href = '/admin/videos/channels/{channel_id}';
                        }} else {{
                            alert('Error: ' + result.message);
                        }}
                    }} catch (error) {{
                        console.error('Error:', error);
                        alert('Error updating channel');
                    }}
                }}
            </script>
            """
            
            return HTMLResponse(content=create_html_page(f"Edit: {channel.name}", content, "videos"))
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error loading edit page: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/videos/channels/{channel_id}/update")
async def update_channel(request: Request, channel_id: str, name: str = Form(...), slug: str = Form(...), description: str = Form(None), thumbnail: UploadFile = File(None)):
    """Update channel details"""
    
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as session:
            # Get existing channel
            channel_result = await session.execute(
                select(VideoChannel).where(VideoChannel.id == UUID(channel_id))
            )
            channel = channel_result.scalar_one_or_none()
            
            if not channel:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Channel not found"}
                )
            
            # Update basic fields
            channel.name = name
            channel.slug = slug
            channel.description = description
            
            # Handle thumbnail upload
            if thumbnail and thumbnail.filename:
                # Create upload directory if it doesn't exist
                upload_dir = Path("uploads/channel_thumbnails")
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate unique filename
                file_ext = Path(thumbnail.filename).suffix
                unique_filename = f"{uuid4()}{file_ext}"
                file_path = upload_dir / unique_filename
                
                # Save file
                with open(file_path, "wb") as f:
                    content = await thumbnail.read()
                    f.write(content)
                
                channel.thumbnail_url = f"/uploads/channel_thumbnails/{unique_filename}"
            
            await session.commit()
            
            return JSONResponse(content={
                "status": True,
                "message": "Channel updated successfully"
            })
    except Exception as e:
        print(f"Error updating channel: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )


@router.delete("/videos/channels/{channel_id}")
async def delete_channel(request: Request, channel_id: str):
    """Delete a video channel"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"status": False, "message": "Unauthorized"}
        )
    
    try:
        async with get_db_session() as session:
            result = await session.execute(
                select(VideoChannel).where(VideoChannel.id == UUID(channel_id))
            )
            channel = result.scalar_one_or_none()
            
            if not channel:
                return JSONResponse(
                    status_code=404,
                    content={"status": False, "message": "Channel not found"}
                )
            
            await session.delete(channel)
            await session.commit()
        
        return JSONResponse(content={
            "status": True,
            "message": "Channel deleted successfully"
        })
    
    except Exception as e:
        print(f"Error deleting channel: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": False, "message": str(e)}
        )