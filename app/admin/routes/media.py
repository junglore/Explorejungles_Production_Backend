"""
Media management admin routes - Clean template-based version with dynamic functionality
"""

from fastapi import APIRouter, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from typing import Optional
from uuid import UUID
import os
from pathlib import Path
import json

from app.db.database import get_db_session
from app.models.media import Media
from app.models.content import Content
from app.models.user import User
from app.admin.templates.base import create_html_page
from app.services.file_upload import file_upload_service
from app.api.endpoints.media import get_media_type_from_mimetype, create_thumbnail
from app.core.config import settings
from PIL import Image


router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def media_dashboard(request: Request):
    """Media management dashboard"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get basic stats for dashboard
    async with get_db_session() as db:
        # Get total media count
        result = await db.execute(select(func.count(Media.id)))
        total_media = result.scalar()
        
        # Get featured images count (you can customize this logic)
        result = await db.execute(select(func.count(Media.id)).where(Media.media_type == 'IMAGE'))
        featured_count = result.scalar()
        
        # Get total file size
        result = await db.execute(select(func.sum(Media.file_size)))
        total_size = result.scalar() or 0
        
        # Get latest upload
        result = await db.execute(select(Media).order_by(desc(Media.created_at)).limit(1))
        latest_media = result.scalar_one_or_none()
    
    # Load dashboard template and inject stats
    try:
        template_path = Path(__file__).parent.parent / "templates" / "media" / "dashboard.html"
        with open(template_path, 'r') as f:
            dashboard_content = f.read()
            
        # Replace placeholder stats with real data
        dashboard_content = dashboard_content.replace('id="totalMedia">-</h4>', f'id="totalMedia">{total_media}</h4>')
        dashboard_content = dashboard_content.replace('id="featuredCount">-</h4>', f'id="featuredCount">{featured_count}</h4>')
        dashboard_content = dashboard_content.replace('id="totalSize">-</h4>', f'id="totalSize">{format_file_size(total_size)}</h4>')
        
        if latest_media:
            dashboard_content = dashboard_content.replace('id="lastUpload">-</h4>', f'id="lastUpload">{latest_media.created_at.strftime("%Y-%m-%d")}</h4>')
        else:
            dashboard_content = dashboard_content.replace('id="lastUpload">-</h4>', 'id="lastUpload">No uploads</h4>')
            
    except FileNotFoundError:
        dashboard_content = f"""
        <div class="page-header">
            <h1 class="page-title">Media Management Dashboard</h1>
            <p class="page-subtitle">Template file not found. Please check the template directory.</p>
        </div>
        <div class="dashboard-section">
            <div class="section-header">
                <h3><i class="fas fa-chart-bar"></i> Quick Stats</h3>
                <p>Media collection overview</p>
            </div>
            <div class="stats-section">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-image"></i></div>
                        <div class="stat-content">
                            <h4>{total_media}</h4>
                            <p>Total Media Files</p>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-star"></i></div>
                        <div class="stat-content">
                            <h4>{featured_count}</h4>
                            <p>Featured Images</p>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-hdd"></i></div>
                        <div class="stat-content">
                            <h4>{format_file_size(total_size)}</h4>
                            <p>Total Storage Used</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """
    
    return HTMLResponse(content=create_html_page("Media Management", dashboard_content, "media"))

@router.get("/upload", response_class=HTMLResponse)
async def upload_media_page(request: Request):
    """Media upload page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Load upload template
    try:
        template_path = Path(__file__).parent.parent / "templates" / "media" / "upload.html"
        with open(template_path, 'r') as f:
            upload_content = f.read()
    except FileNotFoundError:
        upload_content = """
        <div class="page-header">
            <h1 class="page-title">Upload Media</h1>
            <p class="page-subtitle">Template file not found. Please check the template directory.</p>
        </div>
        """
    
    return HTMLResponse(content=create_html_page("Upload Media", upload_content, "media"))

@router.post("/upload")
async def upload_media_file_admin(
    request: Request,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photographer: Optional[str] = Form(None),
    national_park: Optional[str] = Form(None),
    content_id: Optional[str] = Form(None)
):
    """Upload media file from admin panel"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        # Get database session
        async with get_db_session() as db:
            # Validate content_id if provided
            content_uuid = None
            if content_id:
                try:
                    content_uuid = UUID(content_id)
                    result = await db.execute(select(Content).where(Content.id == content_uuid))
                    content_obj = result.scalar_one_or_none()
                    if not content_obj:
                        raise HTTPException(
                            status_code=400,
                            detail="Invalid content ID"
                        )
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid content ID format"
                    )
            
            # Upload file using enhanced service
            upload_result = await file_upload_service.upload_file(
                file=file,
                validate_content=True
            )
            
            # Determine media type from MIME type
            media_type = get_media_type_from_mimetype(upload_result["mime_type"])
            
            # Get image dimensions if it's an image
            width = height = None
            if media_type == 'IMAGE' and upload_result["category"] == "images":
                try:
                    file_path = Path(upload_result["file_path"])
                    with Image.open(file_path) as img:
                        width, height = img.size
                except Exception:
                    pass
            
            # Create thumbnail for images
            thumbnail_url = None
            if media_type == 'IMAGE':
                thumbnail_url = await create_thumbnail(Path(upload_result["file_path"]), media_type)
            
            # Create media record
            media = Media(
                media_type=media_type,
                file_url=f"/uploads/{upload_result['file_url']}",
                thumbnail_url=thumbnail_url,
                title=title or upload_result["original_filename"],
                description=description,
                photographer=photographer,
                national_park=national_park,
                content_id=content_uuid,
                file_size=upload_result["file_size"],
                width=width,
                height=height,
                filename=upload_result["filename"],
                original_filename=upload_result["original_filename"],
                mime_type=upload_result["mime_type"],
                file_metadata={
                    "original_filename": upload_result["original_filename"],
                    "mimetype": upload_result["mime_type"],
                    "uploaded_by": "admin",
                    "file_hash": upload_result["file_hash"],
                    "secure_filename": upload_result["filename"]
                }
            )
            
            db.add(media)
            await db.commit()
            await db.refresh(media)
            
            # Redirect to media library with success message
            return RedirectResponse(
                url="/admin/media/library?upload_success=true&media_id=" + str(media.id),
                status_code=302
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/library", response_class=HTMLResponse)
async def media_library_page(request: Request, page: int = 1, limit: int = 20):
    """Media library page"""
    
    print(f"🔍 Media library route called - Page: {page}, Limit: {limit}")
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get media from database and render server-side for reliability
    async with get_db_session() as db:
        skip = (page - 1) * limit
        
        print(f"📊 Fetching media from database - Skip: {skip}, Limit: {limit}")
        
        # Get total count
        result = await db.execute(select(func.count(Media.id)))
        total_count = result.scalar()
        
        # Get media items
        result = await db.execute(
            select(Media).order_by(desc(Media.created_at)).offset(skip).limit(limit)
        )
        media_items = result.scalars().all()
        
        print(f"✅ Database query completed - Total: {total_count}, Retrieved: {len(media_items)}")
    
    # Generate media grid HTML server-side for reliability
    if media_items:
        media_grid_html = ""
        for media in media_items:
            # Build proper image URL
            image_url = media.file_url
            if image_url.startswith('/uploads/'):
                image_url = f"{settings.BACKEND_URL}{image_url}"
            
            # --- FIX START: Prepare media preview HTML outside f-string ---
            if media.media_type == 'IMAGE':
                media_preview_html = f'<img src="{image_url}" alt="{media.title or "Media"}" style="width: 100%; height: 200px; object-fit: cover;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';" /><div style="width: 100%; height: 200px; background: #f0f0f0; display: none; align-items: center; justify-content: center; flex-direction: column;"><i class="fas fa-image" style="font-size: 2rem; color: #999; margin-bottom: 0.5rem;"></i><span style="color: #666;">Image</span></div>'
            else:
                media_preview_html = f'<div style="width: 100%; height: 200px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; flex-direction: column;"><i class="fas fa-{get_media_icon(media.media_type)}" style="font-size: 2rem; color: #999; margin-bottom: 0.5rem;"></i><span style="color: #666;">{media.media_type}</span></div>'
            
            photographer_html = f'<p style="margin: 0.25rem 0; font-size: 0.875rem; color: #666;"><strong>Photographer:</strong> {media.photographer}</p>' if media.photographer else ''
            national_park_html = f'<p style="margin: 0.25rem 0; font-size: 0.875rem; color: #666;"><strong>National Park:</strong> {media.national_park}</p>' if media.national_park else ''
            # --- FIX END ---
            
            media_grid_html += f"""
                <div class="media-item">
                    <div class="media-preview">
                        {media_preview_html}
                    </div>
                    <div class="media-info" style="padding: 1rem;">
                        <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem; color: #333;">{media.title or "Untitled"}</h4>
                        <p style="margin: 0.25rem 0; font-size: 0.875rem; color: #666;"><strong>Type:</strong> {media.media_type}</p>
                        <p style="margin: 0.25rem 0; font-size: 0.875rem; color: #666;"><strong>Size:</strong> {format_file_size(media.file_size) if media.file_size else "Unknown"}</p>
                        <p style="margin: 0.25rem 0; font-size: 0.875rem; color: #666;"><strong>Uploaded:</strong> {media.created_at.strftime('%Y-%m-%d %H:%M')}</p>
                        {photographer_html}
                        {national_park_html}
                        <div class="media-actions" style="margin-top: 1rem; display: flex; gap: 0.5rem;">
                            <button class="btn btn-sm btn-primary" onclick="editMedia('{media.id}')" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteMedia('{media.id}')" style="padding: 0.25rem 0.5rem; font-size: 0.75rem; background: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;" data-media-id="{media.id}">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                </div>
            """
    else:
        media_grid_html = """
            <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #666;">
                <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                <h3>No media files found</h3>
                <p>Upload some media files to get started</p>
                <a href="/admin/media/upload" style="display: inline-block; margin-top: 1rem; padding: 0.5rem 1rem; background: #007bff; color: white; text-decoration: none; border-radius: 4px;">
                    <i class="fas fa-upload"></i> Upload Media
                </a>
            </div>
        """
    
    # Generate pagination
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1
    pagination_html = ""
    if total_pages > 1:
        pagination_html = '<div style="display: flex; justify-content: center; margin-top: 2rem; gap: 0.5rem;">'
        
        # Previous page
        if page > 1:
            pagination_html += f'<a href="/admin/media/library?page={page - 1}" style="padding: 0.5rem 1rem; background: #f8f9fa; border: 1px solid #dee2e6; text-decoration: none; color: #007bff; border-radius: 4px;">‹ Previous</a>'
        
        # Page numbers
        for p in range(max(1, page - 2), min(total_pages + 1, page + 3)):
            if p == page:
                pagination_html += f'<span style="padding: 0.5rem 1rem; background: #007bff; color: white; border-radius: 4px;">{p}</span>'
            else:
                pagination_html += f'<a href="/admin/media/library?page={p}" style="padding: 0.5rem 1rem; background: #f8f9fa; border: 1px solid #dee2e6; text-decoration: none; color: #007bff; border-radius: 4px;">{p}</a>'
        
        # Next page
        if page < total_pages:
            pagination_html += f'<a href="/admin/media/library?page={page + 1}" style="padding: 0.5rem 1rem; background: #f8f9fa; border: 1px solid #dee2e6; text-decoration: none; color: #007bff; border-radius: 4px;">Next ›</a>'
        
        pagination_html += '</div>'
    
    # Create the complete page content
    library_content = f"""
        <div class="page-header">
            <h1 class="page-title">Media Library</h1>
            <p class="page-subtitle">Browse and manage your uploaded media files ({total_count} total)</p>
        </div>
        
        <div style="margin-bottom: 2rem;">
            <a href="/admin/media/upload" style="display: inline-block; padding: 0.75rem 1.5rem; background: #28a745; color: white; text-decoration: none; border-radius: 8px; font-weight: 600;">
                <i class="fas fa-upload"></i> Upload New Media
            </a>
            <a href="/admin/media/featured" style="display: inline-block; margin-left: 1rem; padding: 0.75rem 1.5rem; background: #ffc107; color: #212529; text-decoration: none; border-radius: 8px; font-weight: 600;">
                <i class="fas fa-star"></i> Manage Featured
            </a>
        </div>
        
        <div class="media-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 1.5rem; margin-bottom: 2rem;">
            {media_grid_html}
        </div>
        
        <!-- Debug section for development -->
        <div style="margin-top: 2rem; padding: 1rem; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; font-family: monospace; font-size: 0.875rem;">
            <h4>Debug Info:</h4>
            <p><strong>Total Media Items:</strong> {len(media_items) if media_items else 0}</p>
            <p><strong>Current Page:</strong> {page}</p>
            <p><strong>Items Per Page:</strong> {limit}</p>
            <p><strong>Total Count:</strong> {total_count}</p>
            {f'<p><strong>Sample Media ID:</strong> {media_items[0].id if media_items else "None"}</p>' if media_items else ''}
        </div>
        
        {pagination_html}
        
        <script>
            async function deleteMedia(mediaId) {{
                console.log('deleteMedia called with ID:', mediaId);
                
                if (!confirm('Are you sure you want to delete this media file? This action cannot be undone.')) {{
                    return;
                }}
                
                try {{
                    console.log('Sending DELETE request to:', `/admin/media/delete/${{mediaId}}`);
                    const response = await fetch(`/admin/media/delete/${{mediaId}}`, {{
                        method: 'DELETE'
                    }});
                    
                    console.log('Response status:', response.status);
                    console.log('Response ok:', response.ok);
                    
                    if (response.ok) {{
                        const result = await response.json();
                        console.log('Delete successful:', result);
                        alert('Media deleted successfully');
                        location.reload();
                    }} else {{
                        const errorText = await response.text();
                        console.error('Delete failed:', errorText);
                        alert('Failed to delete media: ' + errorText);
                    }}
                }} catch (error) {{
                    console.error('Error deleting media:', error);
                    alert('Error deleting media: ' + error.message);
                }}
            }}
            
            function editMedia(mediaId) {{
                window.location.href = `/admin/media/edit/${{mediaId}}`;
            }}
        </script>
        
        <style>
            .media-item {{
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                overflow: hidden;
                background: white;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                transition: all 0.3s ease;
            }}
            
            .media-item:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1);
            }}
            
            .btn:hover {{
                opacity: 0.8;
                transform: translateY(-1px);
            }}
        </style>
    """
    
    print("🚀 Returning HTML response with server-side rendered content")
    return HTMLResponse(content=create_html_page("Media Library", library_content, "media"))

@router.get("/featured", response_class=HTMLResponse)
async def featured_images_page(request: Request):
    """Featured images management page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get current featured images and all available images
    async with get_db_session() as db:
        # Get featured images
        result = await db.execute(
            select(Media).where(Media.is_featured > 0, Media.media_type == 'IMAGE')
            .order_by(Media.is_featured)
        )
        featured_images = result.scalars().all()
        
        # Get all images for selection
        result = await db.execute(
            select(Media).where(Media.media_type == 'IMAGE')
            .order_by(desc(Media.created_at))
            .limit(50)
        )
        all_images = result.scalars().all()
    
    # Generate featured images HTML
    featured_html = ""
    for i in range(6):  # 6 featured positions
        if i < len(featured_images):
            media = featured_images[i]
            # Build proper image URL
            image_url = media.file_url
            if image_url.startswith('/uploads/'):
                image_url = f"{settings.BACKEND_URL}{image_url}"
            
            featured_html += f"""
                <div class="featured-slot filled" data-position="{i+1}">
                    <img src="{image_url}" alt="{media.title or 'Featured'}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjEyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkZlYXR1cmVkPC90ZXh0Pjwvc3ZnPg=='" />
                    <div class="featured-info">
                        <h4>{media.title or 'Untitled'}</h4>
                        <p>{media.photographer or 'Unknown'}</p>
                        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                            <button class="btn btn-sm btn-danger" onclick="removeFeatured('{media.id}')" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">Remove</button>
                        </div>
                    </div>
                </div>
            """
        else:
            featured_html += f"""
                <div class="featured-slot empty" data-position="{i+1}">
                    <div class="empty-placeholder">
                        <i class="fas fa-plus"></i>
                        <p>Add Featured Image</p>
                        <small>Position {i+1}</small>
                    </div>
                </div>
            """
    
    # Generate available images HTML
    available_html = ""
    for media in all_images:
        if media.is_featured == 0:  # Only show non-featured images
            # Build proper image URL
            image_url = media.file_url
            if image_url.startswith('/uploads/'):
                image_url = f"{settings.BACKEND_URL}{image_url}"
            
            available_html += f"""
                <div class="available-image" data-id="{media.id}">
                    <img src="{image_url}" alt="{media.title or 'Image'}" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjEyMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg=='" />
                    <div class="image-info">
                        <h5>{media.title or 'Untitled'}</h5>
                        <p><strong>Photographer:</strong> {media.photographer or 'Unknown'}</p>
                        <p><strong>Park:</strong> {media.national_park or 'Unknown'}</p>
                        <p><strong>Size:</strong> {media.width}x{media.height} px</p>
                        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                            <button class="btn btn-sm btn-primary" onclick="setFeatured('{media.id}')" style="padding: 0.25rem 0.5rem; font-size: 0.75rem;">Set Featured</button>
                        </div>
                    </div>
                </div>
            """
    
    featured_content = f"""
        <div class="page-header">
            <h1 class="page-title">Featured Images Management</h1>
            <p class="page-subtitle">Manage the featured images displayed on the homepage carousel</p>
        </div>
        
        <div class="dashboard-section">
            <div class="section-header">
                <h3><i class="fas fa-star"></i> Current Featured Images</h3>
                <p>Drag and drop to reorder, or click to remove</p>
            </div>
            <div class="featured-grid">
                {featured_html}
            </div>
        </div>
        
        <div class="dashboard-section">
            <div class="section-header">
                <h3><i class="fas fa-images"></i> Available Images</h3>
                <p>Click "Set Featured" to add to the carousel</p>
            </div>
            <div class="available-grid">
                {available_html}
            </div>
        </div>
        
        <style>
            .featured-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
                margin-bottom: 40px;
            }}
            
            .featured-slot {{
                border: 2px dashed #ddd;
                border-radius: 8px;
                padding: 20px;
                text-align: center;
                min-height: 200px;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }}
            
            .featured-slot.filled {{
                border: 2px solid #4CAF50;
                background: #f9fff9;
            }}
            
            .featured-slot img {{
                max-width: 100%;
                max-height: 120px;
                object-fit: cover;
                border-radius: 4px;
                margin-bottom: 10px;
            }}
            
            .available-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                gap: 15px;
            }}
            
            .available-image {{
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px;
                text-align: center;
                background: white;
            }}
            
            .available-image img {{
                max-width: 100%;
                height: 120px;
                object-fit: cover;
                border-radius: 4px;
                margin-bottom: 10px;
            }}
            
            .image-info h5 {{
                margin: 5px 0;
                font-size: 14px;
            }}
            
            .image-info p {{
                margin: 5px 0;
                font-size: 12px;
                color: #666;
            }}
        </style>
        
        <script>
            async function setFeatured(mediaId) {{
                try {{
                    const response = await fetch('/admin/media/set-featured', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ media_id: mediaId }})
                    }});
                    
                    if (response.ok) {{
                        location.reload();
                    }} else {{
                        alert('Failed to set featured image');
                    }}
                }} catch (error) {{
                    alert('Error: ' + error.message);
                }}
            }}
            
            async function removeFeatured(mediaId) {{
                try {{
                    const response = await fetch('/admin/media/remove-featured', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{ media_id: mediaId }})
                    }});
                    
                    if (response.ok) {{
                        location.reload();
                    }} else {{
                        alert('Failed to remove featured image');
                    }}
                }} catch (error) {{
                    alert('Error: ' + error.message);
                }}
            }}
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Featured Images", featured_content, "media"))

@router.post("/set-featured")
async def set_featured_image(request: Request):
    """Set an image as featured"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        body = await request.json()
        media_id = body.get('media_id')
        
        if not media_id:
            raise HTTPException(status_code=400, detail="Media ID required")
        
        async with get_db_session() as db:
            # Find next available featured position
            result = await db.execute(
                select(func.max(Media.is_featured)).where(Media.is_featured > 0)
            )
            max_featured = result.scalar() or 0
            
            if max_featured >= 6:
                raise HTTPException(status_code=400, detail="Maximum 6 featured images allowed")
            
            # Set the image as featured
            try:
                from uuid import UUID
                media_uuid = UUID(media_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid media ID format")
            
            result = await db.execute(
                select(Media).where(Media.id == media_uuid)
            )
            media = result.scalar_one_or_none()
            
            if not media:
                raise HTTPException(status_code=404, detail="Media not found")
            
            media.is_featured = max_featured + 1
            await db.commit()
            
            return {"success": True, "message": "Image set as featured"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/remove-featured")
async def remove_featured_image(request: Request):
    """Remove an image from featured"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        body = await request.json()
        media_id = body.get('media_id')
        
        if not media_id:
            raise HTTPException(status_code=400, detail="Media ID required")
        
        async with get_db_session() as db:
            # Remove featured status
            try:
                from uuid import UUID
                media_uuid = UUID(media_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid media ID format")
            
            result = await db.execute(
                select(Media).where(Media.id == media_uuid)
            )
            media = result.scalar_one_or_none()
            
            if not media:
                raise HTTPException(status_code=404, detail="Media not found")
            
            old_position = media.is_featured
            media.is_featured = 0
            
            # Reorder remaining featured images
            if old_position > 0:
                result = await db.execute(
                    select(Media).where(Media.is_featured > old_position)
                )
                higher_featured = result.scalars().all()
                
                for featured_media in higher_featured:
                    featured_media.is_featured -= 1
            
            await db.commit()
            
            return {"success": True, "message": "Featured image removed"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/collage", response_class=HTMLResponse)
async def media_collage_page(request: Request):
    """Media collage page for 'View All' functionality"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Load collage template
    try:
        template_path = Path(__file__).parent.parent / "templates" / "media" / "collage.html"
        with open(template_path, 'r') as f:
            collage_content = f.read()
    except FileNotFoundError:
        collage_content = """
        <div class="page-header">
            <h1 class="page-title">Media Collage Management</h1>
            <p class="page-subtitle">Template file not found. Please check the template directory.</p>
        </div>
        """
    
    return HTMLResponse(content=create_html_page("Media Collage", collage_content, "media-collage"))

@router.get("/edit/{media_id}", response_class=HTMLResponse)
async def edit_media_page(request: Request, media_id: str):
    """Edit media page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get media item
    async with get_db_session() as db:
        try:
            from uuid import UUID
            media_uuid = UUID(media_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid media ID format")
        
        result = await db.execute(select(Media).where(Media.id == media_uuid))
        media = result.scalar_one_or_none()
        
        if not media:
            raise HTTPException(status_code=404, detail="Media not found")
    
    # Build proper image URL for preview
    image_url = media.file_url
    if image_url.startswith('/uploads/'):
        image_url = f"{settings.BACKEND_URL}{image_url}"
    
    # --- FIX START: Prepare variables OUTSIDE the f-string ---
    
    # 1. Prepare media preview HTML
    if media.media_type == 'IMAGE':
        media_preview_html = f'<img src="{image_url}" alt="{media.title or "Media"}" style="width: 100%; max-width: 300px; height: auto; border-radius: 8px; border: 1px solid #ddd;" onerror="this.style.display=\'none\'; this.nextElementSibling.style.display=\'flex\';" /><div style="width: 100%; height: 200px; background: #f0f0f0; display: none; align-items: center; justify-content: center; flex-direction: column; border-radius: 8px; border: 1px solid #ddd;"><i class="fas fa-image" style="font-size: 2rem; color: #999; margin-bottom: 0.5rem;"></i><span style="color: #666;">Media Preview</span></div>'
    else:
        media_preview_html = f'<div style="width: 100%; height: 200px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; flex-direction: column; border-radius: 8px; border: 1px solid #ddd;"><i class="fas fa-{get_media_icon(media.media_type)}" style="font-size: 2rem; color: #999; margin-bottom: 0.5rem;"></i><span style="color: #666;">{media.media_type}</span></div>'
    
    # 2. Prepare dimensions HTML
    dimensions_html = f'<p><strong>Dimensions:</strong> {media.width}x{media.height} px</p>' if media.width and media.height else ''
    
    # --- FIX END ---
    
    edit_content = f"""
        <div class="page-header">
            <h1 class="page-title">Edit Media</h1>
            <p class="page-subtitle">Update media information and metadata</p>
        </div>
        
        <div class="dashboard-section">
            <div class="section-header">
                <h3><i class="fas fa-edit"></i> Media Information</h3>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 2fr; gap: 2rem; margin-bottom: 2rem;">
                <div class="media-preview">
                    <h4>Preview</h4>
                    {media_preview_html}
                    <div style="margin-top: 1rem; font-size: 0.875rem; color: #666;">
                        <p><strong>Type:</strong> {media.media_type}</p>
                        <p><strong>Size:</strong> {format_file_size(media.file_size) if media.file_size else "Unknown"}</p>
                        <p><strong>Uploaded:</strong> {media.created_at.strftime('%Y-%m-%d %H:%M')}</p>
                        {dimensions_html}
                    </div>
                </div>
                
                <div class="edit-form">
                    <form id="editMediaForm" onsubmit="updateMedia(event, '{media.id}')">
                        <div style="margin-bottom: 1rem;">
                            <label for="title" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Title</label>
                            <input type="text" id="title" name="title" value="{media.title or ''}" style="width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem;" />
                        </div>
                        
                        <div style="margin-bottom: 1rem;">
                            <label for="description" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Description</label>
                            <textarea id="description" name="description" rows="3" style="width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem; resize: vertical;">{media.description or ''}</textarea>
                        </div>
                        
                        <div style="margin-bottom: 1rem;">
                            <label for="photographer" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Photographer</label>
                            <input type="text" id="photographer" name="photographer" value="{media.photographer or ''}" style="width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem;" />
                        </div>
                        
                        <div style="margin-bottom: 1rem;">
                            <label for="national_park" style="display: block; margin-bottom: 0.5rem; font-weight: 600;">National Park</label>
                            <input type="text" id="national_park" name="national_park" value="{media.national_park or ''}" style="width: 100%; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem;" />
                        </div>
                        
                        <div style="display: flex; gap: 1rem; margin-top: 2rem;">
                            <button type="submit" style="padding: 0.75rem 1.5rem; background: #28a745; color: white; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; font-weight: 600;">
                                <i class="fas fa-save"></i> Update Media
                            </button>
                            <a href="/admin/media/library" style="display: inline-block; padding: 0.75rem 1.5rem; background: #6c757d; color: white; text-decoration: none; border-radius: 4px; font-size: 1rem; font-weight: 600;">
                                <i class="fas fa-arrow-left"></i> Back to Library
                            </a>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        
        <script>
            async function updateMedia(event, mediaId) {{
                event.preventDefault();
                
                const form = event.target;
                const formData = new FormData(form);
                
                try {{
                    const response = await fetch(`/admin/media/update/${{mediaId}}`, {{
                        method: 'PUT',
                        headers: {{
                            'Content-Type': 'application/json',
                        }},
                        body: JSON.stringify({{
                            title: formData.get('title'),
                            description: formData.get('description'),
                            photographer: formData.get('photographer'),
                            national_park: formData.get('national_park')
                        }})
                    }});
                    
                    if (response.ok) {{
                        alert('Media updated successfully');
                        window.location.href = '/admin/media/library';
                    }} else {{
                        const error = await response.json();
                        alert('Failed to update media: ' + (error.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    console.error('Error updating media:', error);
                    alert('Error updating media: ' + error.message);
                }}
            }}
        </script>
        
        <style>
            .edit-form input:focus,
            .edit-form textarea:focus {{
                outline: none;
                border-color: #007bff;
                box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
            }}
            
            .edit-form button:hover {{
                opacity: 0.9;
                transform: translateY(-1px);
            }}
        </style>
    """
    
    return HTMLResponse(content=create_html_page("Edit Media", edit_content, "media"))

@router.put("/update/{media_id}")
async def update_media_admin(request: Request, media_id: str):
    """Update media information"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        body = await request.json()
        
        async with get_db_session() as db:
            # Get media item
            try:
                from uuid import UUID
                media_uuid = UUID(media_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid media ID format")
            
            result = await db.execute(select(Media).where(Media.id == media_uuid))
            media = result.scalar_one_or_none()
            
            if not media:
                raise HTTPException(status_code=404, detail="Media not found")
            
            # Update fields
            if 'title' in body:
                media.title = body['title']
            if 'description' in body:
                media.description = body['description']
            if 'photographer' in body:
                media.photographer = body['photographer']
            if 'national_park' in body:
                media.national_park = body['national_park']
            
            await db.commit()
            
            return {"success": True, "message": "Media updated successfully"}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.delete("/delete/{media_id}")
async def delete_media_admin(request: Request, media_id: str):
    """Delete media file from admin panel"""
    
    print(f"🗑️ Delete request received for media ID: {media_id}")
    print(f"🔐 Session data: {dict(request.session)}")
    
    # Check authentication
    if not request.session.get("authenticated"):
        print("❌ Authentication failed")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    print("✅ Authentication successful")
    
    try:
        # Get database session
        async with get_db_session() as db:
            print(f"🔍 Looking up media item in database")
            
            # Convert string media_id to UUID for proper database comparison
            try:
                from uuid import UUID
                media_uuid = UUID(media_id)
            except ValueError:
                print(f"❌ Invalid media ID format: {media_id}")
                raise HTTPException(status_code=400, detail="Invalid media ID format")
            
            # Get media item
            result = await db.execute(select(Media).where(Media.id == media_uuid))
            media = result.scalar_one_or_none()
            
            if not media:
                print(f"❌ Media item not found: {media_id}")
                raise HTTPException(status_code=404, detail="Media not found")
            
            print(f"✅ Media item found: {media.title or 'Untitled'} ({media.media_type})")
            
            # Delete file from storage
            try:
                file_path = Path(f"uploads/{media.file_url.replace('/uploads/', '')}")
                if file_path.exists():
                    print(f"🗂️ Deleting file from storage: {file_path}")
                    file_path.unlink()
                    print("✅ File deleted from storage")
                else:
                    print(f"⚠️ File not found in storage: {file_path}")
            except Exception as e:
                # Log error but continue with database deletion
                print(f"⚠️ Error deleting file: {e}")
            
            # Delete from database
            print("🗄️ Deleting media record from database")
            await db.delete(media)
            await db.commit()
            print("✅ Media record deleted from database")
            
            return {"success": True, "message": "Media deleted successfully"}
            
    except Exception as e:
        print(f"❌ Delete failed: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

# Helper functions
def get_media_icon(media_type: str) -> str:
    """Get FontAwesome icon for media type"""
    icon_map = {
        'IMAGE': "image",
        'VIDEO': "video",
        'AUDIO': "music",
        'PODCAST': "podcast",
        'DOCUMENT': "file"
    }
    return icon_map.get(media_type, "file")

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def generate_pagination(current_page: int, total_pages: int, base_url: str) -> str:
    """Generate pagination HTML"""
    if total_pages <= 1:
        return ""
    
    pagination = '<div class="pagination">'
    
    # Previous page
    if current_page > 1:
        pagination += f'<a href="{base_url}?page={current_page - 1}">‹ Previous</a>'
    
    # Page numbers
    for page in range(max(1, current_page - 2), min(total_pages + 1, current_page + 3)):
        if page == current_page:
            pagination += f'<span class="current">{page}</span>'
        else:
            pagination += f'<a href="{base_url}?page={page}">{page}</a>'
    
    # Next page
    if current_page < total_pages:
        pagination += f'<a href="{base_url}?page={current_page + 1}">Next ›</a>'
    
    pagination += '</div>'
    return pagination
