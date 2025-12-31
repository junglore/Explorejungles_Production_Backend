"""
Podcast management routes for admin panel
"""

from fastapi import APIRouter, Request, Form, File, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID, uuid4
from typing import Optional
import logging
from pathlib import Path

from app.models.media import Media
from app.models.category import Category
from app.models.user import User
from app.admin.templates.base import create_html_page
from app.db.database import get_db_session
from app.services.file_upload import file_upload_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def podcast_dashboard(request: Request):
    """Podcast management dashboard"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Get podcast statistics
            result = await db.execute(
                select(func.count(Media.id)).where(Media.media_type == 'PODCAST')
            )
            total_podcasts = result.scalar()
            
            # Get total podcast file size
            result = await db.execute(
                select(func.sum(Media.file_size)).where(Media.media_type == 'PODCAST')
            )
            total_size = result.scalar() or 0
            
            # Get latest podcast
            result = await db.execute(
                select(Media).where(Media.media_type == 'PODCAST')
                .order_by(desc(Media.created_at)).limit(1)
            )
            latest_podcast = result.scalar_one_or_none()
            
    except Exception as e:
        logger.error(f"Error loading podcast dashboard: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Error", 
                f"<div class='message error'>Error loading dashboard: {str(e)}</div>", 
                "podcasts"
            )
        )
    
    # Format file size helper function
    def format_file_size(size_bytes):
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    # Load dashboard template
    try:
        template_path = Path(__file__).parent.parent / "templates" / "podcasts" / "dashboard.html"
        with open(template_path, 'r') as f:
            dashboard_content = f.read()
            
        # Replace placeholder stats with real data
        dashboard_content = dashboard_content.replace('id="totalPodcasts">-</h4>', f'id="totalPodcasts">{total_podcasts}</h4>')
        dashboard_content = dashboard_content.replace('id="totalSize">-</h4>', f'id="totalSize">{format_file_size(total_size)}</h4>')
        
        if latest_podcast:
            dashboard_content = dashboard_content.replace('id="lastUpload">-</h4>', f'id="lastUpload">{latest_podcast.created_at.strftime("%Y-%m-%d")}</h4>')
        else:
            dashboard_content = dashboard_content.replace('id="lastUpload">-</h4>', 'id="lastUpload">No podcasts</h4>')
            
    except FileNotFoundError:
        dashboard_content = f"""
        <div class="page-header">
            <h1 class="page-title">Podcast Management Dashboard</h1>
            <p class="page-subtitle">Manage your podcast collection</p>
        </div>
        <div class="dashboard-section">
            <div class="section-header">
                <h3><i class="fas fa-podcast"></i> Quick Stats</h3>
                <p>Podcast collection overview</p>
            </div>
            <div class="stats-section">
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-podcast"></i></div>
                        <div class="stat-content">
                            <h4>{total_podcasts}</h4>
                            <p>Total Podcasts</p>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-hdd"></i></div>
                        <div class="stat-content">
                            <h4>{format_file_size(total_size)}</h4>
                            <p>Total Storage Used</p>
                        </div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon"><i class="fas fa-clock"></i></div>
                        <div class="stat-content">
                            <h4>{latest_podcast.created_at.strftime("%Y-%m-%d") if latest_podcast else "No uploads"}</h4>
                            <p>Last Upload</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="dashboard-actions">
                <a href="/admin/podcasts/create" class="btn btn-primary">
                    <i class="fas fa-plus"></i> Create New Podcast
                </a>
                <a href="/admin/podcasts/list" class="btn btn-secondary">
                    <i class="fas fa-list"></i> View All Podcasts
                </a>
            </div>
        </div>
        """
    
    return HTMLResponse(content=create_html_page("Podcast Management", dashboard_content, "podcasts"))


@router.get("/create", response_class=HTMLResponse)
async def create_podcast_form(request: Request):
    """Create podcast form"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get categories for dropdown
    categories = []
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = result.scalars().all()
    except Exception as e:
        logger.error(f"Error loading categories: {e}")
        categories = []
    
    # Generate category options
    category_options = ""
    for category in categories:
        category_options += f'<option value="{category.id}">{category.name}</option>'
    
    # Load create template
    try:
        template_path = Path(__file__).parent.parent / "templates" / "podcasts" / "create.html"
        with open(template_path, 'r') as f:
            create_content = f.read()
            # Replace category options placeholder
            create_content = create_content.replace('{{category_options}}', category_options)
    except FileNotFoundError:
        create_content = f"""
        <div class="page-header">
            <h1 class="page-title">Create New Podcast</h1>
            <p class="page-subtitle">Upload and configure a new podcast episode</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="createPodcastForm" class="admin-form" enctype="multipart/form-data">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-group">
                        <label for="title">Podcast Title *</label>
                        <input type="text" id="title" name="title" required 
                               placeholder="Enter podcast episode title" 
                               maxlength="500"
                               class="form-control">
                        <div class="field-error" id="title-error"></div>
                        <small class="field-help">A clear, engaging title for this podcast episode</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea id="description" name="description"
                                  placeholder="Describe the podcast content, topics covered, and key takeaways..."
                                  class="form-control content-textarea" rows="6"></textarea>
                        <small class="field-help">Detailed description of the podcast content and topics</small>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="photographer">Host Name</label>
                            <input type="text" id="photographer" name="photographer" 
                                   placeholder="Enter host name" 
                                   class="form-control">
                            <small class="field-help">Name of the podcast host or presenter</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="national_park">Show Name</label>
                            <input type="text" id="national_park" name="national_park" 
                                   placeholder="Enter show or series name" 
                                   class="form-control">
                            <small class="field-help">Name of the podcast show or series</small>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                <option value="">Select category...</option>
                                {category_options}
                            </select>
                            <small class="field-help">Optional: Categorize this podcast for better organization</small>
                        </div>
                    </div>
                </div>
                
                <!-- Audio File Upload -->
                <div class="form-section">
                    <h3 class="section-title">Audio File</h3>
                    
                    <div class="form-group">
                        <label for="audio_file">Audio File *</label>
                        <input type="file" id="audio_file" name="audio_file" required
                               accept="audio/*,.mp3,.wav,.ogg,.m4a" class="file-input">
                        <div class="file-upload-area" id="audio-upload-area">
                            <i class="fas fa-microphone"></i>
                            <p>Click to upload audio file</p>
                            <small>MP3, WAV, OGG, M4A (Max: 100MB)</small>
                        </div>
                        <div id="audio-preview"></div>
                        <div class="field-error" id="audio-file-error"></div>
                        <small class="field-help">Upload the main podcast audio file</small>
                    </div>
                </div>
                
                <!-- Cover Image Upload -->
                <div class="form-section">
                    <h3 class="section-title">Cover Image</h3>
                    
                    <div class="form-group">
                        <label for="cover_image">Cover Image</label>
                        <input type="file" id="cover_image" name="cover_image" 
                               accept="image/*,.avif" class="file-input">
                        <div class="file-upload-area" id="image-upload-area">
                            <i class="fas fa-image"></i>
                            <p>Click to upload cover image</p>
                            <small>JPEG, PNG, GIF, WebP, AVIF (Max: 50MB)</small>
                        </div>
                        <div id="image-preview"></div>
                        <small class="field-help">Optional: Add a cover image for the podcast</small>
                    </div>
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Create Podcast
                        </button>
                        <a href="/admin/podcasts" class="btn btn-secondary">
                            <i class="fas fa-times"></i>
                            Cancel
                        </a>
                    </div>
                </div>
            </form>
        </div>
        """
    
    return HTMLResponse(content=create_html_page("Create Podcast", create_content, "podcasts"))


@router.post("/create")
async def create_podcast(
    request: Request,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    photographer: Optional[str] = Form(None),  # Host name
    national_park: Optional[str] = Form(None),  # Show name
    category_id: Optional[str] = Form(None),
    audio_file: UploadFile = File(...),
    cover_image: Optional[UploadFile] = File(None)
):
    """Create new podcast"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        async with get_db_session() as db:
            # Validate category_id if provided
            category_uuid = None
            if category_id:
                try:
                    category_uuid = UUID(category_id)
                    result = await db.execute(select(Category).where(Category.id == category_uuid))
                    category_obj = result.scalar_one_or_none()
                    if not category_obj:
                        raise HTTPException(status_code=400, detail="Invalid category ID")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid category ID format")
            
            # Upload audio file
            audio_upload_result = await file_upload_service.upload_file(
                file=audio_file,
                validate_content=True
            )
            
            # Validate it's an audio file
            if audio_upload_result["category"] != "audio":
                raise HTTPException(status_code=400, detail="Invalid audio file type")
            
            # Upload cover image if provided
            thumbnail_url = None
            if cover_image and cover_image.filename:
                try:
                    image_upload_result = await file_upload_service.upload_file(
                        file=cover_image,
                        validate_content=True
                    )
                    
                    if image_upload_result["category"] == "images":
                        thumbnail_url = f"/uploads/{image_upload_result['file_url']}"
                except Exception as e:
                    logger.warning(f"Cover image upload failed: {e}")
                    # Continue without cover image
            
            # Create podcast record
            podcast = Media(
                media_type="PODCAST",
                file_url=f"/uploads/{audio_upload_result['file_url']}",
                thumbnail_url=thumbnail_url,
                title=title,
                description=description,
                photographer=photographer,  # Host name
                national_park=national_park,  # Show name
                # Removed: category_id - Media model doesn't have this field
                file_size=audio_upload_result["file_size"],
                filename=audio_upload_result["filename"],
                original_filename=audio_upload_result["original_filename"],
                mime_type=audio_upload_result["mime_type"],
                file_metadata={
                    "original_filename": audio_upload_result["original_filename"],
                    "mimetype": audio_upload_result["mime_type"],
                    "uploaded_by": "admin",
                    "file_hash": audio_upload_result["file_hash"],
                    "secure_filename": audio_upload_result["filename"],
                    "cover_image_uploaded": thumbnail_url is not None,
                    "category_id": str(category_uuid) if category_uuid else None  # Store in metadata instead
                }
            )
            
            db.add(podcast)
            await db.commit()
            await db.refresh(podcast)
            
            # Redirect to podcast list with success message
            return RedirectResponse(
                url=f"/admin/podcasts/list?upload_success=true&podcast_id={podcast.id}",
                status_code=302
            )
            
    except Exception as e:
        logger.error(f"Error creating podcast: {e}")
        raise HTTPException(status_code=500, detail=f"Podcast creation failed: {str(e)}")


@router.get("/edit/{podcast_id}", response_class=HTMLResponse)
async def edit_podcast_form(request: Request, podcast_id: str):
    """Edit podcast form"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        podcast_uuid = UUID(podcast_id)
        
        async with get_db_session() as db:
            # Get podcast
            result = await db.execute(
                select(Media).where(Media.id == podcast_uuid, Media.media_type == 'PODCAST')
            )
            podcast = result.scalar_one_or_none()
            
            if not podcast:
                raise HTTPException(status_code=404, detail="Podcast not found")
            
            # Get categories for dropdown
            result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = result.scalars().all()
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid podcast ID")
    except Exception as e:
        logger.error(f"Error loading podcast for edit: {e}")
        raise HTTPException(status_code=500, detail="Error loading podcast")
    
    # Generate category options
    category_options = ""
    # Get current category from metadata
    current_category_id = None
    if podcast.file_metadata and podcast.file_metadata.get("category_id"):
        try:
            current_category_id = UUID(podcast.file_metadata["category_id"])
        except (ValueError, TypeError):
            pass
    
    for category in categories:
        selected = "selected" if current_category_id == category.id else ""
        category_options += f'<option value="{category.id}" {selected}>{category.name}</option>'
    
    # Load edit template
    try:
        template_path = Path(__file__).parent.parent / "templates" / "podcasts" / "edit.html"
        with open(template_path, 'r') as f:
            edit_content = f.read()
            # Replace placeholders with podcast data
            edit_content = edit_content.replace('{{podcast_id}}', str(podcast.id))
            edit_content = edit_content.replace('{{title}}', podcast.title or '')
            edit_content = edit_content.replace('{{description}}', podcast.description or '')
            edit_content = edit_content.replace('{{photographer}}', podcast.photographer or '')
            edit_content = edit_content.replace('{{national_park}}', podcast.national_park or '')
            edit_content = edit_content.replace('{{category_options}}', category_options)
            edit_content = edit_content.replace('{{current_audio_url}}', podcast.file_url or '')
            edit_content = edit_content.replace('{{current_image_url}}', podcast.thumbnail_url or '')
    except FileNotFoundError:
        # Fallback template if file doesn't exist
        current_audio_display = f'<p><strong>Current audio:</strong> <a href="{podcast.file_url}" target="_blank">Listen</a></p>' if podcast.file_url else ''
        current_image_display = f'<img src="{podcast.thumbnail_url}" alt="Current cover" style="max-width: 200px; border-radius: 8px;">' if podcast.thumbnail_url else ''
        
        edit_content = f"""
        <div class="page-header">
            <h1 class="page-title">Edit Podcast</h1>
            <p class="page-subtitle">Update podcast information and files</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="editPodcastForm" class="admin-form" enctype="multipart/form-data">
                <input type="hidden" name="podcast_id" value="{podcast.id}">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-group">
                        <label for="title">Podcast Title *</label>
                        <input type="text" id="title" name="title" required 
                               value="{podcast.title or ''}"
                               placeholder="Enter podcast episode title" 
                               maxlength="500"
                               class="form-control">
                        <div class="field-error" id="title-error"></div>
                    </div>
                    
                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea id="description" name="description"
                                  placeholder="Describe the podcast content..."
                                  class="form-control content-textarea" rows="6">{podcast.description or ''}</textarea>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="photographer">Host Name</label>
                            <input type="text" id="photographer" name="photographer" 
                                   value="{podcast.photographer or ''}"
                                   placeholder="Enter host name" 
                                   class="form-control">
                        </div>
                        
                        <div class="form-group">
                            <label for="national_park">Show Name</label>
                            <input type="text" id="national_park" name="national_park" 
                                   value="{podcast.national_park or ''}"
                                   placeholder="Enter show or series name" 
                                   class="form-control">
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                <option value="">Select category...</option>
                                {category_options}
                            </select>
                        </div>
                    </div>
                </div>
                
                <!-- Current Audio File -->
                <div class="form-section">
                    <h3 class="section-title">Audio File</h3>
                    
                    <div class="current-file">
                        {current_audio_display}
                    </div>
                    
                    <div class="form-group">
                        <label for="audio_file">Replace Audio File</label>
                        <input type="file" id="audio_file" name="audio_file"
                               accept="audio/*,.mp3,.wav,.ogg,.m4a" class="file-input">
                        <div class="file-upload-area" id="audio-upload-area">
                            <i class="fas fa-microphone"></i>
                            <p>Click to replace audio file</p>
                            <small>MP3, WAV, OGG, M4A (Max: 100MB)</small>
                        </div>
                        <div id="audio-preview"></div>
                        <small class="field-help">Leave empty to keep current audio file</small>
                    </div>
                </div>
                
                <!-- Current Cover Image -->
                <div class="form-section">
                    <h3 class="section-title">Cover Image</h3>
                    
                    <div class="current-file">
                        {current_image_display}
                    </div>
                    
                    <div class="form-group">
                        <label for="cover_image">Replace Cover Image</label>
                        <input type="file" id="cover_image" name="cover_image" 
                               accept="image/*,.avif" class="file-input">
                        <div class="file-upload-area" id="image-upload-area">
                            <i class="fas fa-image"></i>
                            <p>Click to replace cover image</p>
                            <small>JPEG, PNG, GIF, WebP, AVIF (Max: 50MB)</small>
                        </div>
                        <div id="image-preview"></div>
                        <small class="field-help">Leave empty to keep current cover image</small>
                    </div>
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Update Podcast
                        </button>
                        <a href="/admin/podcasts/list" class="btn btn-secondary">
                            <i class="fas fa-times"></i>
                            Cancel
                        </a>
                    </div>
                </div>
            </form>
        </div>
        """
    
    return HTMLResponse(content=create_html_page("Edit Podcast", edit_content, "podcasts"))


@router.post("/edit/{podcast_id}")
async def update_podcast(
    request: Request,
    podcast_id: str,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    photographer: Optional[str] = Form(None),
    national_park: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    cover_image: Optional[UploadFile] = File(None)
):
    """Update existing podcast"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        podcast_uuid = UUID(podcast_id)
        
        async with get_db_session() as db:
            # Get existing podcast
            result = await db.execute(
                select(Media).where(Media.id == podcast_uuid, Media.media_type == 'PODCAST')
            )
            podcast = result.scalar_one_or_none()
            
            if not podcast:
                raise HTTPException(status_code=404, detail="Podcast not found")
            
            # Validate category_id if provided
            category_uuid = None
            if category_id:
                try:
                    category_uuid = UUID(category_id)
                    result = await db.execute(select(Category).where(Category.id == category_uuid))
                    category_obj = result.scalar_one_or_none()
                    if not category_obj:
                        raise HTTPException(status_code=400, detail="Invalid category ID")
                except ValueError:
                    raise HTTPException(status_code=400, detail="Invalid category ID format")
            
            # Update basic fields
            podcast.title = title
            podcast.description = description
            podcast.photographer = photographer
            podcast.national_park = national_park
            # Removed: podcast.category_id - Media model doesn't have this field
            
            # Update category in metadata if provided
            if not podcast.file_metadata:
                podcast.file_metadata = {}
            podcast.file_metadata["category_id"] = str(category_uuid) if category_uuid else None
            
            # Handle audio file replacement
            if audio_file and audio_file.filename:
                try:
                    audio_upload_result = await file_upload_service.upload_file(
                        file=audio_file,
                        validate_content=True
                    )
                    
                    if audio_upload_result["category"] != "audio":
                        raise HTTPException(status_code=400, detail="Invalid audio file type")
                    
                    # Update audio file fields
                    podcast.file_url = f"/uploads/{audio_upload_result['file_url']}"
                    podcast.file_size = audio_upload_result["file_size"]
                    podcast.filename = audio_upload_result["filename"]
                    podcast.original_filename = audio_upload_result["original_filename"]
                    podcast.mime_type = audio_upload_result["mime_type"]
                    
                    # Update metadata
                    if not podcast.file_metadata:
                        podcast.file_metadata = {}
                    podcast.file_metadata.update({
                        "original_filename": audio_upload_result["original_filename"],
                        "mimetype": audio_upload_result["mime_type"],
                        "file_hash": audio_upload_result["file_hash"],
                        "secure_filename": audio_upload_result["filename"],
                        "updated_by": "admin"
                    })
                    
                except Exception as e:
                    logger.error(f"Audio file upload failed: {e}")
                    raise HTTPException(status_code=400, detail=f"Audio upload failed: {str(e)}")
            
            # Handle cover image replacement
            if cover_image and cover_image.filename:
                try:
                    image_upload_result = await file_upload_service.upload_file(
                        file=cover_image,
                        validate_content=True
                    )
                    
                    if image_upload_result["category"] == "images":
                        podcast.thumbnail_url = f"/uploads/{image_upload_result['file_url']}"
                        
                        # Update metadata
                        if not podcast.file_metadata:
                            podcast.file_metadata = {}
                        podcast.file_metadata["cover_image_updated"] = True
                        
                except Exception as e:
                    logger.warning(f"Cover image upload failed: {e}")
                    # Continue without updating cover image
            
            await db.commit()
            await db.refresh(podcast)
            
            # Redirect to podcast list with success message
            return RedirectResponse(
                url=f"/admin/podcasts/list?update_success=true&podcast_id={podcast.id}",
                status_code=302
            )
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid podcast ID")
    except Exception as e:
        logger.error(f"Error updating podcast: {e}")
        raise HTTPException(status_code=500, detail=f"Podcast update failed: {str(e)}")


@router.delete("/delete/{podcast_id}")
async def delete_podcast(request: Request, podcast_id: str):
    """Delete podcast"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        podcast_uuid = UUID(podcast_id)
        
        async with get_db_session() as db:
            # Get podcast
            result = await db.execute(
                select(Media).where(Media.id == podcast_uuid, Media.media_type == 'PODCAST')
            )
            podcast = result.scalar_one_or_none()
            
            if not podcast:
                raise HTTPException(status_code=404, detail="Podcast not found")
            
            # Delete the podcast record
            await db.delete(podcast)
            await db.commit()
            
            return JSONResponse(content={"message": "Podcast deleted successfully"})
            
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid podcast ID")
    except Exception as e:
        logger.error(f"Error deleting podcast: {e}")
        raise HTTPException(status_code=500, detail=f"Podcast deletion failed: {str(e)}")


@router.get("/list", response_class=HTMLResponse)
async def podcast_list(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    category_id: Optional[str] = Query(None, description="Filter by category")
):
    """Admin list view for podcasts with pagination and search"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Build base query
            query = select(Media).where(Media.media_type == 'PODCAST')
            
            # Apply filters
            filters = []
            
            # Search filter
            if search and search.strip():
                search_term = f"%{search.strip()}%"
                filters.append(
                    or_(
                        Media.title.ilike(search_term),
                        Media.description.ilike(search_term),
                        Media.photographer.ilike(search_term),  # Host name
                        Media.national_park.ilike(search_term)  # Show name
                    )
                )
            
            # Category filter - search in metadata
            if category_id and category_id.strip():
                try:
                    category_uuid = UUID(category_id)
                    filters.append(Media.file_metadata.op('->>')('category_id') == str(category_uuid))
                except ValueError:
                    pass  # Invalid UUID, ignore filter
            
            # Apply filters to query
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count for pagination
            count_query = select(func.count(Media.id)).where(Media.media_type == 'PODCAST')
            if filters:
                count_query = count_query.where(and_(*filters))
            
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(Media.created_at)).offset(offset).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            podcasts = result.scalars().all()
            
            # Get categories for filter dropdown
            categories_result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = categories_result.scalars().all()
            
    except Exception as e:
        logger.error(f"Error loading podcast list: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Error", 
                f"<div class='message error'>Error loading podcasts: {str(e)}</div>", 
                "podcasts"
            )
        )
    
    # Format file size helper function
    def format_file_size(size_bytes):
        if size_bytes == 0:
            return "0 B"
        size_names = ["B", "KB", "MB", "GB"]
        i = 0
        while size_bytes >= 1024 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        return f"{size_bytes:.1f} {size_names[i]}"
    
    # Calculate pagination info
    total_pages = (total + limit - 1) // limit if total > 0 else 0
    has_prev = page > 1
    has_next = page < total_pages
    
    # Generate category options for filter
    category_options = '<option value="">All Categories</option>'
    for category in categories:
        selected = "selected" if category_id == str(category.id) else ""
        category_options += f'<option value="{category.id}" {selected}>{category.name}</option>'
    
    # Generate table rows
    table_rows = ""
    for podcast in podcasts:
        # Get category name from metadata
        category_name = 'No Category'
        if podcast.file_metadata and podcast.file_metadata.get("category_id"):
            try:
                category_uuid = UUID(podcast.file_metadata["category_id"])
                # Find category name from loaded categories
                for cat in categories:
                    if cat.id == category_uuid:
                        category_name = cat.name
                        break
            except (ValueError, TypeError):
                pass
        
        host_name = podcast.photographer or 'Unknown Host'
        show_name = podcast.national_park or 'Unknown Show'
        
        # Truncate description for display
        description_preview = (podcast.description[:100] + '...') if podcast.description and len(podcast.description) > 100 else (podcast.description or 'No description')
        
        table_rows += f"""
        <tr>
            <td>
                <div class="content-title">{podcast.title}</div>
                <div class="content-meta">
                    <small class="text-muted">Created: {podcast.created_at.strftime('%Y-%m-%d %H:%M') if podcast.created_at else 'Unknown'}</small>
                </div>
            </td>
            <td>
                <div class="podcast-info">
                    <p><strong>Host:</strong> {host_name}</p>
                    <p><strong>Show:</strong> {show_name}</p>
                    <p><strong>Size:</strong> {format_file_size(podcast.file_size) if podcast.file_size else 'Unknown'}</p>
                </div>
            </td>
            <td>
                <div class="content-preview">
                    {description_preview}
                </div>
            </td>
            <td>{category_name}</td>
            <td>
                <div class="action-buttons">
                    <a href="{podcast.file_url}" target="_blank" class="btn btn-sm btn-info">
                        <i class="fas fa-play"></i> Listen
                    </a>
                    <a href="/admin/podcasts/edit/{podcast.id}" class="btn btn-sm btn-primary">
                        <i class="fas fa-edit"></i> Edit
                    </a>
                    <button onclick="confirmDelete('{podcast.id}', '{podcast.title}')" class="btn btn-sm btn-danger">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </div>
            </td>
        </tr>
        """
    
    # Generate pagination controls
    pagination_html = ""
    if total_pages > 1:
        pagination_html = f"""
        <div class="pagination-container">
            <div class="pagination-info">
                Showing {offset + 1}-{min(offset + limit, total)} of {total} entries
            </div>
            <div class="pagination">
        """
        
        # Previous button
        if has_prev:
            pagination_html += f'<a href="?page={page-1}&limit={limit}&search={search or ""}&category_id={category_id or ""}" class="btn btn-sm btn-secondary">Previous</a>'
        
        # Page numbers
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        
        for p in range(start_page, end_page + 1):
            active_class = "btn-primary" if p == page else "btn-secondary"
            pagination_html += f'<a href="?page={p}&limit={limit}&search={search or ""}&category_id={category_id or ""}" class="btn btn-sm {active_class}">{p}</a>'
        
        # Next button
        if has_next:
            pagination_html += f'<a href="?page={page+1}&limit={limit}&search={search or ""}&category_id={category_id or ""}" class="btn btn-sm btn-secondary">Next</a>'
        
        pagination_html += """
            </div>
        </div>
        """
    
    # Load list template
    try:
        template_path = Path(__file__).parent.parent / "templates" / "podcasts" / "list.html"
        with open(template_path, 'r') as f:
            list_content = f.read()
            # Replace placeholders
            list_content = list_content.replace('{{category_options}}', category_options)
            list_content = list_content.replace('{{table_rows}}', table_rows if table_rows else '<tr><td colspan="5" class="text-center">No podcasts found</td></tr>')
            list_content = list_content.replace('{{pagination_html}}', pagination_html)
            list_content = list_content.replace('{{search_value}}', search or '')
            list_content = list_content.replace('{{limit_10_selected}}', 'selected' if limit == 10 else '')
            list_content = list_content.replace('{{limit_25_selected}}', 'selected' if limit == 25 else '')
            list_content = list_content.replace('{{limit_50_selected}}', 'selected' if limit == 50 else '')
    except FileNotFoundError:
        list_content = f"""
        <div class="page-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 class="page-title">Podcast Management</h1>
                    <p class="page-subtitle">Manage your podcast collection</p>
                </div>
                <a href="/admin/podcasts/create" class="btn btn-primary">
                    <i class="fas fa-plus"></i> Create New Podcast
                </a>
            </div>
        </div>
        
        <div id="message-container"></div>
        
        <div class="content-container">
            <!-- Filters -->
            <div class="filters-section">
                <form method="get" class="filters-form">
                    <div class="filter-row">
                        <div class="filter-group">
                            <label for="search">Search</label>
                            <input type="text" id="search" name="search" value="{search or ''}" 
                                   placeholder="Search title, description, host, or show..." class="form-control">
                        </div>
                        <div class="filter-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                {category_options}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label for="limit">Per Page</label>
                            <select id="limit" name="limit" class="form-control">
                                <option value="10" {"selected" if limit == 10 else ""}>10</option>
                                <option value="25" {"selected" if limit == 25 else ""}>25</option>
                                <option value="50" {"selected" if limit == 50 else ""}>50</option>
                            </select>
                        </div>
                    </div>
                    <div class="filter-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-search"></i> Filter
                        </button>
                        <a href="/admin/podcasts/list" class="btn btn-secondary">
                            <i class="fas fa-times"></i> Clear
                        </a>
                    </div>
                </form>
            </div>
            
            <!-- Results Table -->
            <div class="table-container">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>Title</th>
                            <th>Podcast Info</th>
                            <th>Description</th>
                            <th>Category</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows if table_rows else '<tr><td colspan="5" class="text-center">No podcasts found</td></tr>'}
                    </tbody>
                </table>
            </div>
            
            {pagination_html}
        </div>
        
        <!-- Delete Confirmation Modal -->
        <div id="deleteModal" class="modal" style="display: none;">
            <div class="modal-content">
                <h3>Confirm Delete</h3>
                <p>Are you sure you want to delete "<span id="deleteItemTitle"></span>"?</p>
                <p class="text-danger">This action cannot be undone.</p>
                <div class="modal-actions">
                    <button onclick="closeDeleteModal()" class="btn btn-secondary">Cancel</button>
                    <button onclick="executeDelete()" class="btn btn-danger">Delete</button>
                </div>
            </div>
        </div>
        
        <script>
            let deleteItemId = null;
            
            function confirmDelete(id, title) {{
                deleteItemId = id;
                document.getElementById('deleteItemTitle').textContent = title;
                document.getElementById('deleteModal').style.display = 'flex';
            }}
            
            function closeDeleteModal() {{
                deleteItemId = null;
                document.getElementById('deleteModal').style.display = 'none';
            }}
            
            async function executeDelete() {{
                if (!deleteItemId) return;
                
                try {{
                    const response = await fetch(`/admin/podcasts/delete/${{deleteItemId}}`, {{
                        method: 'DELETE',
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        alert('Podcast deleted successfully!');
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 1000);
                    }} else {{
                        const errorText = await response.text();
                        alert('Error deleting podcast: ' + response.status);
                    }}
                }} catch (error) {{
                    alert('Network error: ' + error.message);
                }} finally {{
                    closeDeleteModal();
                }}
            }}
            
            // Close modal when clicking outside
            document.getElementById('deleteModal').addEventListener('click', function(e) {{
                if (e.target === this) {{
                    closeDeleteModal();
                }}
            }});
        </script>
        """
    
    return HTMLResponse(content=create_html_page("Podcast Management", list_content, "podcasts"))