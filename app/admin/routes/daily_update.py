"""
Daily Update management routes for admin panel
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from app.models.category import Category
from app.admin.templates.base import create_html_page
from app.admin.templates.editor import get_quill_editor_html, get_quill_editor_js, get_upload_handlers_js
from app.db.database import get_db_session
from app.services.file_upload import file_upload_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/create/daily-update", response_class=HTMLResponse)
async def create_daily_update_form(request: Request):
    """Create daily update form with QuillJS editor"""
    
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
            <h1 class="page-title">Create Daily Update</h1>
            <p class="page-subtitle">Create daily news updates and wildlife reports</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="createDailyUpdateForm" class="admin-form" enctype="multipart/form-data">
                <input type="hidden" name="type" value="daily_update">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="title">News Headline *</label>
                            <input type="text" id="title" name="title" required 
                                   placeholder="Enter news headline" 
                                   maxlength="500"
                                   class="form-control">
                            <div class="field-error" id="title-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="author_name">Display Author</label>
                            <input type="text" id="author_name" name="author_name" 
                                   placeholder="Enter display author name" 
                                   maxlength="100"
                                   class="form-control"
                                   value="JUNGLORE">
                            <div class="field-error" id="author-name-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="source">News Source</label>
                            <input type="text" id="source" name="source" 
                                   placeholder="e.g., Reuters, BBC, National Geographic" 
                                   class="form-control">
                            <div class="field-error" id="source-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="news_type">News Type</label>
                            <select id="news_type" name="news_type" class="form-control">
                                <option value="">Select news type...</option>
                                <option value="breaking">Breaking News</option>
                                <option value="research">Research Update</option>
                                <option value="conservation">Conservation News</option>
                                <option value="wildlife">Wildlife Report</option>
                                <option value="environmental">Environmental News</option>
                            </select>
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
                        <label for="excerpt">Summary</label>
                        <textarea id="excerpt" name="excerpt" 
                                  placeholder="Brief summary of the news update"
                                  class="form-control" rows="3"></textarea>
                        <div class="field-error" id="excerpt-error"></div>
                    </div>
                </div>
                
                <!-- Content Section -->
                <div class="form-section">
                    <h3 class="section-title">Article Content</h3>
                    
                    <div class="form-group">
                        <label for="content">Article Content *</label>
                        {get_quill_editor_html("content-editor-container", "content")}
                        <div class="field-error" id="content-error"></div>
                        <small>Write the full article content with details and context</small>
                    </div>
                </div>
                
                <!-- Media Section -->
                <div class="form-section">
                    <h3 class="section-title">Media</h3>
                    
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
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i>
                        Create Daily Update
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
            }});
            
            // Form submission
            document.getElementById('createDailyUpdateForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                // Validate form
                let isValid = true;
                
                // Check title
                const title = document.getElementById('title').value.trim();
                if (!title) {{
                    showFieldError('title-error', 'Title is required');
                    isValid = false;
                }}
                
                // Check content
                const contentText = contentQuill.getText().trim();
                if (!contentText || contentText.length < 30) {{
                    showFieldError('content-error', 'Content must be at least 30 characters long');
                    isValid = false;
                }}
                
                if (!isValid) return;
                
                // Submit form
                try {{
                    const formData = new FormData(this);
                    formData.set('content', contentQuill.root.innerHTML);
                    
                    const response = await fetch('/admin/create/daily-update', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    if (response.ok) {{
                        showMessage('Daily update created successfully!', 'success');
                        setTimeout(() => {{
                            window.location.href = '/admin/manage/content?type=daily_update';
                        }}, 2000);
                    }} else {{
                        const error = await response.text();
                        showMessage('Error creating daily update: ' + error, 'error');
                    }}
                }} catch (error) {{
                    showMessage('Error: ' + error.message, 'error');
                }}
            }});
            
            function saveDraft() {{
                document.getElementById('status').value = 'draft';
                document.getElementById('createDailyUpdateForm').dispatchEvent(new Event('submit'));
            }}
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Create Daily Update", create_form, "daily-update"))

@router.post("/create/daily-update")
async def create_daily_update(request: Request):
    """Handle daily update creation"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
        from app.models.user import User
        from app.services.file_upload import file_upload_service
        from slugify import slugify
        from uuid import UUID
        
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

        # Handle form data with files using custom approach
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
            import logging
            logger = logging.getLogger(__name__)
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
        if not data.get('title'):
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Title is required"}, status_code=400)
        
        if not data.get('content'):
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Content is required"}, status_code=400)
        
        # Get admin user
        async with get_db_session() as db:
            result = await db.execute(
                select(User).where(User.email == "admin@junglore.com")
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                from fastapi.responses import JSONResponse
                return JSONResponse({"success": False, "error": "Admin user not found"}, status_code=500)
            
            # Generate unique slug
            base_slug = slugify(data['title'])
            if not base_slug:
                from uuid import uuid4
                base_slug = f"daily-update-{uuid4().hex[:8]}"
            
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
            
            # Create metadata for daily update specific fields
            metadata = {}
            if data.get('source'):
                metadata['source'] = data['source']
            if data.get('news_type'):
                metadata['news_type'] = data['news_type']
            
            # Set published_at if status is published
            published_at = None
            if data.get('status') == 'published':
                from datetime import datetime
                published_at = datetime.utcnow()
            
            # Create content
            content = Content(
                type=ContentTypeEnum.DAILY_UPDATE,
                title=data['title'],
                content=data['content'],
                author_name=data.get('author_name', 'JUNGLORE').strip() or 'JUNGLORE',
                excerpt=data.get('excerpt'),
                slug=slug,
                author_id=admin_user.id,
                category_id=UUID(data['category_id']) if data.get('category_id') and data['category_id'].strip() else None,
                featured_image=data.get('featured_image'),
                status=ContentStatusEnum(data.get('status', 'draft')),
                published_at=published_at,
                content_metadata=metadata
            )
            
            db.add(content)
            await db.commit()
            await db.refresh(content)
            
            logger.info(f"Daily update created successfully with ID: {content.id}")
            
            return RedirectResponse(url="/admin/manage/content?type=daily_update&created=1", status_code=302)
            
    except Exception as e:
        import logging
        error_logger = logging.getLogger(__name__)
        error_logger.error(f"Daily update creation error: {e}")
        import traceback
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.get("/edit/daily-update/{content_id}", response_class=HTMLResponse)
async def edit_daily_update_form(request: Request, content_id: str):
    """Edit daily update form"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get the content to edit
    try:
        from uuid import UUID
        from app.models.content import Content
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
    source = metadata.get('source', '')
    news_type = metadata.get('news_type', '')
    
    # --- FIX START: Prepare variables OUTSIDE the f-string ---
    
    # 1. Prepare safe content for JS (escaping backticks)
    safe_content = content.content.replace('`', '\\`') if content.content else ''

    # 2. Prepare Featured Image HTML
    featured_preview_html = ""
    featured_btn_display = "none"
    if content.featured_image:
        featured_preview_html = f'<div id="current-featured-image" style="margin-top: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 8px; background: #f9f9f9;"><strong>Current:</strong> <img src="/uploads/{content.featured_image}" alt="Featured Image" style="max-width: 200px; max-height: 150px; margin-left: 10px; border-radius: 4px;"></div>'
        featured_btn_display = "block"

    # --- FIX END ---

    edit_form = f"""
        <div class="page-header">
            <h1 class="page-title">Edit Daily Update</h1>
            <p class="page-subtitle">Update your daily news content</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="editDailyUpdateForm" class="admin-form" enctype="multipart/form-data">
                <input type="hidden" name="content_id" value="{content.id}">
                <input type="hidden" name="type" value="daily_update">
                
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="title">News Headline *</label>
                            <input type="text" id="title" name="title" required 
                                   placeholder="Enter news headline" 
                                   maxlength="500"
                                   class="form-control"
                                   value="{content.title}">
                            <div class="field-error" id="title-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="author_name">Display Author</label>
                            <input type="text" id="author_name" name="author_name" 
                                   placeholder="Enter display author name" 
                                   maxlength="100"
                                   class="form-control"
                                   value="{content.author_name or 'JUNGLORE'}">
                            <div class="field-error" id="author-name-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="source">News Source</label>
                            <input type="text" id="source" name="source" 
                                   placeholder="e.g., Reuters, BBC, National Geographic" 
                                   class="form-control"
                                   value="{source}">
                            <div class="field-error" id="source-error"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="news_type">News Type</label>
                            <select id="news_type" name="news_type" class="form-control">
                                <option value="">Select news type...</option>
                                <option value="breaking" {"selected" if news_type == "breaking" else ""}>Breaking News</option>
                                <option value="research" {"selected" if news_type == "research" else ""}>Research Update</option>
                                <option value="conservation" {"selected" if news_type == "conservation" else ""}>Conservation News</option>
                                <option value="wildlife" {"selected" if news_type == "wildlife" else ""}>Wildlife Report</option>
                                <option value="environmental" {"selected" if news_type == "environmental" else ""}>Environmental News</option>
                            </select>
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
                        <label for="excerpt">Summary</label>
                        <textarea id="excerpt" name="excerpt" 
                                  placeholder="Brief summary of the news update"
                                  class="form-control" rows="3">{content.excerpt or ''}</textarea>
                        <div class="field-error" id="excerpt-error"></div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">Article Content</h3>
                    
                    <div class="form-group">
                        <label for="content">Article Content *</label>
                        {get_quill_editor_html("content-editor-container", "content")}
                        <div class="field-error" id="content-error"></div>
                        <small>Write the full article content with details and context</small>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">Media</h3>
                    
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
                </div>
                
                <div class="form-section">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i>
                        Update Daily Update
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
                document.getElementById('editDailyUpdateForm').appendChild(hiddenInput);
            }}
            
            // Form submission
            document.getElementById('editDailyUpdateForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                // Clear previous errors
                if (typeof clearAllErrors === 'function') {{
                    clearAllErrors();
                }}
                
                // Set loading state
                if (typeof setFormLoading === 'function') {{
                    setFormLoading('editDailyUpdateForm', true);
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
                
                // Check content
                let contentHtml = '';
                if (typeof contentQuill !== 'undefined' && contentQuill) {{
                    const contentText = contentQuill.getText().trim();
                    if (!contentText || contentText.length < 30) {{
                        if (typeof showFieldError === 'function') {{
                            showFieldError('content-error', 'Content must be at least 30 characters long');
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
                        setFormLoading('editDailyUpdateForm', false);
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
                    formData.append('author_name', document.getElementById('author_name')?.value || 'JUNGLORE');
                    formData.append('excerpt', document.getElementById('excerpt')?.value || '');
                    formData.append('source', document.getElementById('source')?.value || '');
                    formData.append('news_type', document.getElementById('news_type')?.value || '');
                    formData.append('status', document.getElementById('status')?.value || 'draft');
                    formData.append('category_id', document.getElementById('category_id')?.value || '');
                    formData.append('type', 'daily_update');
                    
                    // Add file uploads if present
                    const featuredImage = document.getElementById('featured_image');
                    if (featuredImage && featuredImage.files[0]) {{
                        formData.append('featured_image', featuredImage.files[0]);
                    }}
                    
                    // Add removal flags
                    const removeFeaturedInput = document.querySelector('input[name="remove_featured_image"]');
                    if (removeFeaturedInput) {{
                        formData.append('remove_featured_image', 'true');
                    }}
                    
                    const response = await fetch('/admin/edit/daily-update/{content_id}', {{
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        if (typeof showMessage === 'function') {{
                            showMessage('Daily update updated successfully!', 'success');
                        }}
                        setTimeout(() => {{
                            window.location.href = '/admin/manage/content?updated=1';
                        }}, 1500);
                    }} else {{
                        const error = await response.text();
                        if (typeof showMessage === 'function') {{
                            showMessage('Error updating daily update: ' + error, 'error');
                        }}
                    }}
                }} catch (error) {{
                    if (typeof showMessage === 'function') {{
                        showMessage('Error: ' + error.message, 'error');
                    }}
                }} finally {{
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('editDailyUpdateForm', false);
                    }}
                }}
            }});
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Edit Daily Update", edit_form, "edit"))

@router.post("/edit/daily-update/{content_id}")
async def update_daily_update(request: Request, content_id: str):
    """Handle daily update update"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        from uuid import UUID
        from app.models.content import Content, ContentStatusEnum
        from app.services.file_upload import file_upload_service
        
        logger.info(f"Daily update update started for ID: {content_id}")
        
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
                        # Use the full URL path for the file
                        data[key] = f"/uploads/{file_info['file_url']}"
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
        
        if not title:
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Title is required"}, status_code=400)
        
        if not content_html:
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Content is required"}, status_code=400)
        
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
            
            # Update metadata
            metadata = content_obj.content_metadata or {}
            metadata['source'] = data.get('source', '')
            metadata['news_type'] = data.get('news_type', '')
            content_obj.content_metadata = metadata

            # Flag the metadata field as modified so SQLAlchemy detects the change
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(content_obj, 'content_metadata')
            
            # Set published_at if status is published
            if data.get('status') == 'published' and not content_obj.published_at:
                from datetime import datetime
                content_obj.published_at = datetime.utcnow()
            
            await db.commit()
            
            logger.info(f"Daily update updated successfully with ID: {content_obj.id}")
            
            return RedirectResponse(url="/admin/manage/content?updated=1", status_code=302)
            
    except Exception as e:
        import traceback
        import logging
        error_logger = logging.getLogger(__name__)
        error_logger.error(f"Daily update update error: {e}")
        error_logger.error(f"Traceback: {traceback.format_exc()}")
        
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)