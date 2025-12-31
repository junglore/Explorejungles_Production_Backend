"""
Conservation Effort management routes for admin panel
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from uuid import UUID, uuid4
from app.models.category import Category
from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
from app.admin.templates.base import create_html_page
from app.admin.templates.editor import get_quill_editor_html, get_quill_editor_js, get_upload_handlers_js
from app.db.database import get_db_session
from app.services.file_upload import file_upload_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/create/conservation", response_class=HTMLResponse)
async def create_conservation_form(request: Request):
    """Create conservation effort form with QuillJS editor"""
    
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
        categories = []
    
    # Generate category options
    category_options = ""
    for category in categories:
        category_options += f'<option value="{category.id}">{category.name}</option>'
    
    create_form = f"""
        <div class="page-header">
            <h1 class="page-title">Create Conservation Effort</h1>
            <p class="page-subtitle">Create conservation projects with location tracking and progress monitoring</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="createConservationForm" class="admin-form" enctype="multipart/form-data">
                <input type="hidden" name="type" value="conservation_effort">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="title">Project Title *</label>
                            <input type="text" id="title" name="title" required 
                                   placeholder="Enter conservation project title" 
                                   maxlength="500"
                                   class="form-control">
                            <div class="field-error" id="title-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="author_name">Author Name</label>
                            <input type="text" id="author_name" name="author_name" 
                                   placeholder="Enter author name" 
                                   maxlength="100"
                                   class="form-control"
                                   value="JUNGLORE">
                            <div class="field-error" id="author-name-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="location">Project Location *</label>
                            <input type="text" id="location" name="location" required 
                                   placeholder="e.g., Amazon Rainforest, Brazil" 
                                   class="form-control">
                            <div class="field-error" id="location-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="progress_percentage">Progress Percentage</label>
                            <input type="number" id="progress_percentage" name="progress_percentage" 
                                   min="0" max="100" placeholder="75" class="form-control">
                            <div class="field-error" id="progress-percentage-error"></div>
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
                        
                        <div class="form-group">
                            <label for="status">Status</label>
                            <select id="status" name="status" class="form-control">
                                <option value="draft">Draft</option>
                                <option value="published">Published</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="excerpt">Project Description</label>
                        <textarea id="excerpt" name="excerpt" 
                                  placeholder="Brief description of the conservation effort"
                                  class="form-control" rows="3"></textarea>
                        <div class="field-error" id="excerpt-error"></div>
                    </div>
                </div>
                
                <!-- Project Content -->
                <div class="form-section">
                    <h3 class="section-title">Project Details</h3>
                    
                    <div class="form-group">
                        <label for="content">Project Description & Methods *</label>
                        {get_quill_editor_html("content-editor-container", "content")}
                        <div class="field-error" id="content-error"></div>
                        <small>Provide detailed project description, methods, and implementation plan</small>
                    </div>
                </div>
                
                <!-- Media Section -->
                <div class="form-section">
                    <h3 class="section-title">Media</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="featured_image">Featured Image</label>
                            <input type="file" id="featured_image" name="featured_image" 
                                   accept="image/*,.avif" class="file-input">
                            <div class="file-upload-area" onclick="document.getElementById('featured_image').click()">
                                <i class="fas fa-image"></i>
                                <p>Click to upload featured image</p>
                                <small>JPEG, PNG, GIF, WebP, AVIF (Max: 50MB)</small>
                            </div>
                            <div id="featured-image-preview"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="banner">Banner Image</label>
                            <input type="file" id="banner" name="banner" 
                                   accept="image/*,.avif" class="file-input">
                            <div class="file-upload-area" onclick="document.getElementById('banner').click()">
                                <i class="fas fa-panorama"></i>
                                <p>Click to upload banner image</p>
                                <small>JPEG, PNG, GIF, WebP, AVIF (Max: 50MB)</small>
                            </div>
                            <div id="banner-preview"></div>
                        </div>
                    </div>
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i>
                        Create Conservation Effort
                    </button>
                    <button type="button" onclick="saveDraft()" class="btn btn-secondary">
                        <i class="fas fa-file-alt"></i>
                        Save as Draft
                    </button>
                </div>
            </form>
        </div>
        
        <script>
            {get_upload_handlers_js()}
            {get_quill_editor_js("content-editor-container", "content", "contentQuill")}
            
            // Initialize file upload handlers
            document.addEventListener('DOMContentLoaded', function() {{
                document.getElementById('featured_image').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'featured-image-preview', 'image');
                }});
                
                document.getElementById('banner').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'banner-preview', 'image');
                }});
            }});
            
            // Form submission
            document.getElementById('createConservationForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                console.log('Conservation form submission started');
                
                // Clear previous errors
                if (typeof clearAllErrors === 'function') {{
                    clearAllErrors();
                }}
                
                // Set loading state
                if (typeof setFormLoading === 'function') {{
                    setFormLoading('createConservationForm', true);
                }}
                
                // Validate form
                let isValid = true;
                
                // Check title
                const title = document.getElementById('title').value.trim();
                if (!title) {{
                    if (typeof showFieldError === 'function') {{
                        showFieldError('title-error', 'Title is required');
                    }}
                    isValid = false;
                }}
                
                // Check location
                const location = document.getElementById('location').value.trim();
                if (!location) {{
                    if (typeof showFieldError === 'function') {{
                        showFieldError('location-error', 'Location is required');
                    }}
                    isValid = false;
                }}
                
                // Check content
                let contentHtml = '';
                if (typeof contentQuill !== 'undefined' && contentQuill) {{
                    const contentText = contentQuill.getText().trim();
                    if (!contentText || contentText.length < 50) {{
                        if (typeof showFieldError === 'function') {{
                            showFieldError('content-error', 'Content must be at least 50 characters long');
                        }}
                        isValid = false;
                    }} else {{
                        contentHtml = contentQuill.root.innerHTML;
                    }}
                }} else {{
                    if (typeof showFieldError === 'function') {{
                        showFieldError('content-error', 'Content editor not initialized');
                    }}
                    isValid = false;
                }}
                
                if (!isValid) {{
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('createConservationForm', false);
                    }}
                    return;
                }}
                
                // Submit form
                try {{
                    // Create fresh FormData and manually add all fields
                    const formData = new FormData();
                    
                    // Add all form fields manually to ensure they're included
                    formData.append('title', title);
                    formData.append('content', contentHtml);
                    formData.append('location', location);
                    formData.append('author_name', document.getElementById('author_name')?.value || 'JUNGLORE');
                    formData.append('excerpt', document.getElementById('excerpt')?.value || '');
                    formData.append('status', document.getElementById('status')?.value || 'draft');
                    formData.append('category_id', document.getElementById('category_id')?.value || '');
                    formData.append('progress_percentage', document.getElementById('progress_percentage')?.value || '');
                    formData.append('type', 'conservation_effort');
                    
                    // Add file uploads if present
                    const featuredImage = document.getElementById('featured_image');
                    if (featuredImage && featuredImage.files[0]) {{
                        formData.append('featured_image', featuredImage.files[0]);
                        console.log('Added featured image:', featuredImage.files[0].name);
                    }}
                    
                    const banner = document.getElementById('banner');
                    if (banner && banner.files[0]) {{
                        formData.append('banner', banner.files[0]);
                        console.log('Added banner image:', banner.files[0].name);
                    }}
                    
                    console.log('Sending request to /admin/create/conservation');
                    console.log('Form data entries:');
                    for (let [key, value] of formData.entries()) {{
                        console.log(`${{key}}: ${{typeof value === 'string' ? value.substring(0, 100) : value}}`);
                    }}
                    
                    const response = await fetch('/admin/create/conservation', {{
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        if (typeof showMessage === 'function') {{
                            showMessage('Conservation effort created successfully!', 'success');
                        }}
                        setTimeout(() => {{
                            window.location.href = '/admin/manage/content?type=conservation_effort&created=1';
                        }}, 2000);
                    }} else {{
                        const error = await response.text();
                        if (typeof showMessage === 'function') {{
                            showMessage('Error creating conservation effort: ' + error, 'error');
                        }}
                    }}
                }} catch (error) {{
                    if (typeof showMessage === 'function') {{
                        showMessage('Error: ' + error.message, 'error');
                    }}
                }} finally {{
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('createConservationForm', false);
                    }}
                }}
            }});
            
            function saveDraft() {{
                document.getElementById('status').value = 'draft';
                document.getElementById('createConservationForm').dispatchEvent(new Event('submit'));
            }}
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Create Conservation Effort", create_form, "conservation"))

@router.post("/create/conservation")
async def create_conservation(request: Request):
    """Handle conservation effort creation"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Conservation effort creation started")
        
        # Debug enum values
        logger.info(f"ContentTypeEnum.CONSERVATION_EFFORT = {ContentTypeEnum.CONSERVATION_EFFORT}")
        logger.info(f"ContentTypeEnum.CONSERVATION_EFFORT.value = {ContentTypeEnum.CONSERVATION_EFFORT.value}")
        logger.info(f"Available enum values: {[e.value for e in ContentTypeEnum]}")
        from app.models.user import User
        from slugify import slugify
        
        # Configure for large form data
        import os
        os.environ["MAX_CONTENT_LENGTH"] = str(50 * 1024 * 1024)  # 50MB
        
        # Set request size limit
        request.scope["max_content_size"] = 50 * 1024 * 1024  # 50MB
        
        # Patch multipart library for this request
        try:
            import multipart
            multipart.FormParser.DEFAULT_CONFIG['MAX_MEMORY_FILE_SIZE'] = 50 * 1024 * 1024  # 50MB
            multipart.FormParser.DEFAULT_CONFIG['MAX_BODY_SIZE'] = 50 * 1024 * 1024  # 50MB
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not patch multipart for this request: {e}")

        # Handle form data with files using standard approach
        try:
            # Use a custom approach to bypass Starlette form parser limits
            from starlette.formparsers import MultiPartParser
            from starlette.requests import Request as StarletteRequest
            
            # Create a custom form parser with large limits
            headers = request.headers
            stream = request.stream()
            
            # Create parser with large limits
            parser = MultiPartParser(
                headers=headers,
                stream=stream,
                max_files=1000,
                max_fields=1000,
                max_part_size=50 * 1024 * 1024  # 50MB
            )
            
            # Parse the form data
            form_data = await parser.parse()
            
        except Exception as form_error:
            logger.error(f"Form parsing error: {form_error}")
            from fastapi.responses import JSONResponse
            return JSONResponse({
                "success": False, 
                "error": f"Form parsing error: {str(form_error)}"
            }, status_code=400)
        
        logger.info(f"Form data parsed successfully with {len(form_data)} items")
        data = {}
        uploaded_files = {}
        
        # Process form fields
        logger.info(f"Starting to process form data with {len(form_data)} items")
        try:
            for key, value in form_data.items():
                if hasattr(value, 'filename'):  # It's a file
                    if value.filename:  # File was actually uploaded
                        try:
                            file_info = await file_upload_service.upload_file(value)
                            uploaded_files[key] = file_info
                            # Store just the file URL path, not the full /uploads/ prefix
                            data[key] = file_info['file_url']
                            logger.info(f"Uploaded file {key}: {data[key]}")
                        except Exception as upload_error:
                            logger.error(f"File upload error for {key}: {upload_error}")
                            # Continue without the file
                            pass
                else:
                    data[key] = value
                    logger.info(f"Form field {key}: {str(value)[:100]}")
        except Exception as process_error:
            logger.error(f"Error processing form fields: {process_error}")
            import traceback
            logger.error(f"Form processing traceback: {traceback.format_exc()}")
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": f"Form processing error: {str(process_error)}"}, status_code=400)
        
        logger.info(f"Processed data: {dict(data)}")
        
        # Validate required fields
        if not data.get('title'):
            logger.error("Title is missing from form data")
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Title is required"}, status_code=400)
        
        if not data.get('content'):
            logger.error("Content is missing from form data")
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Content is required"}, status_code=400)
        
        if not data.get('location'):
            logger.error("Location is missing from form data")
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Location is required"}, status_code=400)
        
        # Get admin user and create content
        async with get_db_session() as db:
            result = await db.execute(
                select(User).where(User.email == "admin@junglore.com")
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                logger.error("Admin user not found")
                from fastapi.responses import JSONResponse
                return JSONResponse({"success": False, "error": "Admin user not found"}, status_code=500)
            
            logger.info(f"Found admin user: {admin_user.email}")
            
            # Generate unique slug
            try:
                base_slug = slugify(data['title'])
                if not base_slug:
                    base_slug = f"conservation-{uuid4().hex[:8]}"
                
                slug = base_slug
                counter = 1
                
                # Check for duplicate slugs and make them unique
                while True:
                    existing = await db.execute(
                        select(Content).where(Content.slug == slug)
                    )
                    if not existing.scalar_one_or_none():
                        break
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                logger.info(f"Generated unique slug: {slug}")
            except Exception as slug_error:
                logger.error(f"Error generating slug: {slug_error}")
                slug = f"conservation-{uuid4().hex[:8]}"
                logger.info(f"Using fallback slug: {slug}")
            
            # Create metadata for conservation specific fields
            metadata = {}
            if data.get('location'):
                metadata['location'] = data['location']
            if data.get('progress_percentage'):
                metadata['progress_percentage'] = data['progress_percentage']
            
            # Create content
            try:
                # Log the type being set
                content_type = ContentTypeEnum.CONSERVATION_EFFORT
                logger.info(f"Setting content type to: {content_type}")
                
                # Set published_at if status is published
                published_at = None
                if data.get('status') == 'published':
                    from datetime import datetime
                    published_at = datetime.utcnow()
                
                content = Content(
                    type=content_type,
                    title=data['title'],
                    content=data['content'],
                    author_name=data.get('author_name', 'JUNGLORE').strip() or 'JUNGLORE',
                    excerpt=data.get('excerpt'),
                    slug=slug,
                    author_id=admin_user.id,
                    category_id=UUID(data['category_id']) if data.get('category_id') and data['category_id'].strip() else None,
                    featured_image=data.get('featured_image'),
                    banner=data.get('banner'),
                    status=ContentStatusEnum(data.get('status', 'draft')),
                    published_at=published_at,
                    content_metadata=metadata
                )
                
                db.add(content)
                await db.commit()
                await db.refresh(content)
                
                logger.info(f"Conservation effort created successfully with ID: {content.id}")
                logger.info(f"Content type after creation: {content.type}")
                logger.info(f"Content title: {content.title}")
                
            except Exception as db_error:
                logger.error(f"Database error creating conservation effort: {db_error}")
                await db.rollback()
                from fastapi.responses import JSONResponse
                return JSONResponse({"success": False, "error": f"Database error: {str(db_error)}"}, status_code=500)
            
            return RedirectResponse(url="/admin/manage/content?type=conservation_effort&created=1", status_code=302)
            
    except Exception as e:
        import logging
        error_logger = logging.getLogger(__name__)
        error_logger.error(f"Conservation effort creation error: {e}")
        import traceback
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/edit/conservation/{content_id}", response_class=HTMLResponse)
async def edit_conservation_form(request: Request, content_id: str):
    """Edit conservation effort form"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get the content to edit
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(Content).where(Content.id == UUID(content_id))
            )
            content = result.scalar_one_or_none()
            
            if not content:
                return HTMLResponse(content=create_html_page("Content Not Found", 
                    "<div class='alert alert-danger'>Content not found</div>", "edit"))
            
            # Get categories for dropdown
            result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = result.scalars().all()
    
    except Exception as e:
        return HTMLResponse(content=create_html_page("Error", 
            f"<div class='alert alert-danger'>Error loading content: {str(e)}</div>", "edit"))
    
    # Generate category options
    category_options = ""
    for category in categories:
        selected = "selected" if content.category_id == category.id else ""
        category_options += f'<option value="{category.id}" {selected}>{category.name}</option>'
    
    # Get metadata
    metadata = content.content_metadata or {}
    location = metadata.get('location', '')
    progress_percentage = metadata.get('progress_percentage', '')

    # --- FIX START: Prepare variables OUTSIDE the f-string ---
    
    # 1. Prepare safe content for JS
    safe_content = content.content.replace('`', '\\`') if content.content else ''

    # 2. Prepare Featured Image HTML
    featured_preview_html = ""
    featured_btn_display = "none"
    if content.featured_image:
        featured_preview_html = f'<div id="current-featured-image" style="margin-top: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;"><strong>Current:</strong> <img src="/uploads/{content.featured_image}" alt="Featured Image" style="max-width: 200px; max-height: 150px; margin-left: 10px; border-radius: 4px;"></div>'
        featured_btn_display = "block"

    # 3. Prepare Banner HTML
    banner_preview_html = ""
    banner_btn_display = "none"
    if content.banner:
        banner_preview_html = f'<div id="current-banner" style="margin-top: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;"><strong>Current:</strong> <img src="/uploads/{content.banner}" alt="Banner Image" style="max-width: 200px; max-height: 150px; margin-left: 10px; border-radius: 4px;"></div>'
        banner_btn_display = "block"

    # --- FIX END ---
    
    edit_form = f"""
        <div class="page-header">
            <h1 class="page-title">Edit Conservation Effort</h1>
            <p class="page-subtitle">Update your conservation effort content</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="editConservationForm" class="admin-form" enctype="multipart/form-data">
                <input type="hidden" name="content_id" value="{content.id}">
                <input type="hidden" name="type" value="conservation_effort">
                
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="title">Project Title *</label>
                            <input type="text" id="title" name="title" required 
                                   placeholder="Enter conservation project title" 
                                   maxlength="500"
                                   class="form-control"
                                   value="{content.title}">
                            <div class="field-error" id="title-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="author_name">Author Name</label>
                            <input type="text" id="author_name" name="author_name" 
                                   placeholder="Enter author name" 
                                   maxlength="100"
                                   class="form-control"
                                   value="{content.author_name or 'JUNGLORE'}">
                            <div class="field-error" id="author-name-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="location">Project Location *</label>
                            <input type="text" id="location" name="location" required 
                                   placeholder="e.g., Amazon Rainforest, Brazil" 
                                   class="form-control"
                                   value="{location}">
                            <div class="field-error" id="location-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="progress_percentage">Progress Percentage</label>
                            <input type="number" id="progress_percentage" name="progress_percentage" 
                                   min="0" max="100" placeholder="75" class="form-control"
                                   value="{progress_percentage}">
                            <div class="field-error" id="progress-percentage-error"></div>
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
                        
                        <div class="form-group">
                            <label for="status">Status</label>
                            <select id="status" name="status" class="form-control">
                                <option value="draft" {"selected" if content.status.value == "draft" else ""}>Draft</option>
                                <option value="published" {"selected" if content.status.value == "published" else ""}>Published</option>
                            </select>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="excerpt">Project Description</label>
                        <textarea id="excerpt" name="excerpt" 
                                  placeholder="Brief description of the conservation effort"
                                  class="form-control" rows="3">{content.excerpt or ''}</textarea>
                        <div class="field-error" id="excerpt-error"></div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">Project Details</h3>
                    
                    <div class="form-group">
                        <label for="content">Project Description & Methods *</label>
                        {get_quill_editor_html("content-editor-container", "content")}
                        <div class="field-error" id="content-error"></div>
                        <small>Provide detailed project description, methods, and implementation plan</small>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">Media</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="featured_image">Featured Image</label>
                            <input type="file" id="featured_image" name="featured_image" 
                                   accept="image/*,.avif" class="file-input">
                            <div class="file-upload-area" onclick="document.getElementById('featured_image').click()">
                                <i class="fas fa-image"></i>
                                <p>Click to upload featured image</p>
                                <small>JPEG, PNG, GIF, WebP, AVIF (Max: 50MB)</small>
                            </div>
                            <div id="featured-image-preview">
                                {featured_preview_html}
                                <button type="button" onclick="removeCurrentImage('featured_image')" class="btn btn-danger" style="margin-top: 10px; display: {featured_btn_display};">
                                    <i class="fas fa-trash"></i> Remove Current Image
                                </button>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="banner">Banner Image</label>
                            <input type="file" id="banner" name="banner" 
                                   accept="image/*,.avif" class="file-input">
                            <div class="file-upload-area" onclick="document.getElementById('banner').click()">
                                <i class="fas fa-panorama"></i>
                                <p>Click to upload banner image</p>
                                <small>JPEG, PNG, GIF, WebP, AVIF (Max: 50MB)</small>
                            </div>
                            <div id="banner-preview">
                                {banner_preview_html}
                                <button type="button" onclick="removeCurrentImage('banner')" class="btn btn-danger" style="margin-top: 10px; display: {banner_btn_display};">
                                    <i class="fas fa-trash"></i> Remove Current Image
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="form-section">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i>
                        Update Conservation Effort
                    </button>
                    <a href="/admin/manage/content" class="btn btn-secondary">
                        <i class="fas fa-arrow-left"></i>
                        Back to Content
                    </a>
                </div>
            </form>
        </div>
        
        <script>
            {get_upload_handlers_js()}
            {get_quill_editor_js("content-editor-container", "content", "contentQuill")}
            
            // Set initial content
            document.addEventListener('DOMContentLoaded', function() {{
                if (typeof contentQuill !== 'undefined') {{
                    contentQuill.root.innerHTML = `{safe_content}`;
                }}
            }});
            
            // Initialize file upload handlers
            document.addEventListener('DOMContentLoaded', function() {{
                document.getElementById('featured_image').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'featured-image-preview', 'image');
                }});
                
                document.getElementById('banner').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'banner-preview', 'image');
                }});
                
                // Add click-to-reupload functionality
                const featuredImagePreview = document.getElementById('featured-image-preview');
                if (featuredImagePreview) {{
                    const currentDiv = featuredImagePreview.querySelector('div');
                    if (currentDiv) {{
                        currentDiv.style.cursor = 'pointer';
                        currentDiv.title = 'Click to change image';
                        currentDiv.addEventListener('click', function(e) {{
                            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'I' && !e.target.closest('button')) {{
                                e.preventDefault();
                                e.stopPropagation();
                                document.getElementById('featured_image').click();
                            }}
                        }});
                    }}
                }}
                
                const bannerPreview = document.getElementById('banner-preview');
                if (bannerPreview) {{
                    const currentDiv = bannerPreview.querySelector('div');
                    if (currentDiv) {{
                        currentDiv.style.cursor = 'pointer';
                        currentDiv.title = 'Click to change image';
                        currentDiv.addEventListener('click', function(e) {{
                            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'I' && !e.target.closest('button')) {{
                                e.preventDefault();
                                e.stopPropagation();
                                document.getElementById('banner').click();
                            }}
                        }});
                    }}
                }}
            }});
            
            function removeCurrentImage(fieldName) {{
                const previewDiv = document.getElementById(fieldName + '-preview');
                const removeBtn = previewDiv.querySelector('button');
                const currentDiv = previewDiv.querySelector('div');
                
                if (currentDiv) {{
                    currentDiv.style.display = 'none';
                }}
                if (removeBtn) {{
                    removeBtn.style.display = 'none';
                }}
                
                // Add hidden input to indicate removal
                const hiddenInput = document.createElement('input');
                hiddenInput.type = 'hidden';
                hiddenInput.name = 'remove_' + fieldName;
                hiddenInput.value = 'true';
                document.getElementById('editConservationForm').appendChild(hiddenInput);
            }}
            
            // Form submission
            document.getElementById('editConservationForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                // Clear previous errors
                if (typeof clearAllErrors === 'function') {{
                    clearAllErrors();
                }}
                
                // Set loading state
                if (typeof setFormLoading === 'function') {{
                    setFormLoading('editConservationForm', true);
                }}
                
                // Validate form
                let isValid = true;
                
                // Check title
                const title = document.getElementById('title').value.trim();
                if (!title) {{
                    if (typeof showFieldError === 'function') {{
                        showFieldError('title-error', 'Title is required');
                    }}
                    isValid = false;
                }}
                
                // Check location
                const location = document.getElementById('location').value.trim();
                if (!location) {{
                    if (typeof showFieldError === 'function') {{
                        showFieldError('location-error', 'Location is required');
                    }}
                    isValid = false;
                }}
                
                // Check content
                let contentHtml = '';
                if (typeof contentQuill !== 'undefined' && contentQuill) {{
                    const contentText = contentQuill.getText().trim();
                    if (!contentText || contentText.length < 50) {{
                        if (typeof showFieldError === 'function') {{
                            showFieldError('content-error', 'Content must be at least 50 characters long');
                        }}
                        isValid = false;
                    }} else {{
                        contentHtml = contentQuill.root.innerHTML;
                    }}
                }} else {{
                    if (typeof showFieldError === 'function') {{
                        showFieldError('content-error', 'Content editor not initialized');
                    }}
                    isValid = false;
                }}
                
                if (!isValid) {{
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('editConservationForm', false);
                    }}
                    return;
                }}
                
                // Submit form
                try {{
                    // Create fresh FormData and manually add all fields
                    const formData = new FormData();
                    
                    // Add all form fields manually to ensure they're included
                    formData.append('title', title);
                    formData.append('content', contentHtml);
                    formData.append('location', location);
                    formData.append('author_name', document.getElementById('author_name')?.value || 'JUNGLORE');
                    formData.append('excerpt', document.getElementById('excerpt')?.value || '');
                    formData.append('status', document.getElementById('status')?.value || 'draft');
                    formData.append('category_id', document.getElementById('category_id')?.value || '');
                    formData.append('progress_percentage', document.getElementById('progress_percentage')?.value || '');
                    formData.append('type', 'conservation_effort');
                    
                    // Add file uploads if present
                    const featuredImage = document.getElementById('featured_image');
                    if (featuredImage && featuredImage.files[0]) {{
                        formData.append('featured_image', featuredImage.files[0]);
                    }}
                    
                    const banner = document.getElementById('banner');
                    if (banner && banner.files[0]) {{
                        formData.append('banner', banner.files[0]);
                    }}
                    
                    const response = await fetch('/admin/edit/conservation/{content_id}', {{
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        if (typeof showMessage === 'function') {{
                            showMessage('Conservation effort updated successfully!', 'success');
                        }}
                        setTimeout(() => {{
                            window.location.href = '/admin/manage/content?updated=1';
                        }}, 1500);
                    }} else {{
                        const error = await response.text();
                        if (typeof showMessage === 'function') {{
                            showMessage('Error updating conservation effort: ' + error, 'error');
                        }}
                    }}
                }} catch (error) {{
                    if (typeof showMessage === 'function') {{
                        showMessage('Error: ' + error.message, 'error');
                    }}
                }} finally {{
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('editConservationForm', false);
                    }}
                }}
            }});
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Edit Conservation Effort", edit_form, "edit"))

@router.post("/edit/conservation/{content_id}")
async def update_conservation(request: Request, content_id: str):
    """Handle conservation effort update"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Conservation update started for ID: {content_id}")
        
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/admin/login", status_code=302)
        
        # Configure for large form data
        import os
        os.environ["MAX_CONTENT_LENGTH"] = str(50 * 1024 * 1024)  # 50MB
        
        # Set request size limit
        request.scope["max_content_size"] = 50 * 1024 * 1024  # 50MB
        
        # Patch multipart library for this request
        try:
            import multipart
            multipart.FormParser.DEFAULT_CONFIG['MAX_MEMORY_FILE_SIZE'] = 50 * 1024 * 1024  # 50MB
            multipart.FormParser.DEFAULT_CONFIG['MAX_BODY_SIZE'] = 50 * 1024 * 1024  # 50MB
        except Exception as e:
            logger.warning(f"Could not patch multipart for this request: {e}")

        # Handle form data using custom approach
        try:
            # Use a custom approach to bypass Starlette form parser limits
            from starlette.formparsers import MultiPartParser
            from starlette.requests import Request as StarletteRequest
            
            # Create a custom form parser with large limits
            headers = request.headers
            stream = request.stream()
            
            # Create parser with large limits
            parser = MultiPartParser(
                headers=headers,
                stream=stream,
                max_files=1000,
                max_fields=1000,
                max_part_size=50 * 1024 * 1024  # 50MB
            )
            
            # Parse the form data
            form_data = await parser.parse()
            
        except Exception as form_error:
            logger.error(f"Form parsing error: {form_error}")
            from fastapi.responses import JSONResponse
            return JSONResponse({
                "success": False, 
                "error": f"Form parsing error: {str(form_error)}"
            }, status_code=400)
        
        data = {}
        uploaded_files = {}
        
        # Process form fields
        for key, value in form_data.items():
            if hasattr(value, 'filename'):  # It's a file
                if value.filename:  # File was actually uploaded
                    try:
                        file_info = await file_upload_service.upload_file(value)
                        uploaded_files[key] = file_info
                        # Store just the file URL path, not the full /uploads/ prefix
                        data[key] = file_info['file_url']
                        logger.info(f"Uploaded file {key}: {data[key]}")
                    except Exception as upload_error:
                        logger.error(f"File upload error for {key}: {upload_error}")
                        # Continue without the file
                        pass
            else:
                data[key] = value
        
        # Validate required fields
        title = data.get('title', '').strip() if data.get('title') else ''
        content_html = data.get('content', '').strip() if data.get('content') else ''
        location = data.get('location', '').strip() if data.get('location') else ''
        
        if not title:
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Title is required"}, status_code=400)
        
        if not content_html:
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Content is required"}, status_code=400)
        
        if not location:
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Location is required"}, status_code=400)
        
        # Update content
        async with get_db_session() as db:
            result = await db.execute(
                select(Content).where(Content.id == UUID(content_id))
            )
            content_obj = result.scalar_one_or_none()
            
            if not content_obj:
                from fastapi.responses import JSONResponse
                return JSONResponse({"success": False, "error": "Content not found"}, status_code=404)
            
            # Update fields
            content_obj.title = title
            content_obj.content = content_html
            content_obj.author_name = data.get('author_name', 'JUNGLORE').strip() or 'JUNGLORE'
            content_obj.excerpt = data.get('excerpt', '')
            content_obj.status = ContentStatusEnum(data.get('status', 'draft'))
            
            if data.get('category_id'):
                content_obj.category_id = UUID(data['category_id'])
            
            # Handle file updates
            if data.get('featured_image'):
                content_obj.featured_image = data['featured_image']
            elif data.get('remove_featured_image'):
                content_obj.featured_image = None
            
            if data.get('banner'):
                content_obj.banner = data['banner']
            elif data.get('remove_banner'):
                content_obj.banner = None
            
            # Update metadata
            metadata = content_obj.content_metadata or {}
            metadata['location'] = location
            if data.get('progress_percentage'):
                metadata['progress_percentage'] = data['progress_percentage']
            content_obj.content_metadata = metadata

            # Flag the metadata field as modified so SQLAlchemy detects the change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(content_obj, 'content_metadata')
            
            await db.commit()
            
            logger.info(f"Conservation effort updated successfully with ID: {content_obj.id}")
            
            return RedirectResponse(url="/admin/manage/content?updated=1", status_code=302)
            
    except Exception as e:
        import traceback
        import logging
        error_logger = logging.getLogger(__name__)
        error_logger.error(f"Conservation update error: {e}")
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)