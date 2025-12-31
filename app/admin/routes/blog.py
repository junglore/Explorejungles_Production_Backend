
"""
Blog management routes for admin panel
"""

from fastapi import APIRouter, Request, Form, File, UploadFile, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.requests import Request as StarletteRequest
from sqlalchemy import select
from app.models.category import Category
from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
from app.models.user import User
from app.admin.templates.base import create_html_page
from app.admin.templates.editor import get_quill_editor_html, get_quill_editor_js, get_upload_handlers_js
from app.db.database import get_db_session
import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/create/blog", response_class=HTMLResponse)
async def create_blog_form(request: Request):
    """Create blog form with QuillJS editor"""
    
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
            <h1 class="page-title">Create Blog Post</h1>
            <p class="page-subtitle">Create engaging blog posts with rich content and media</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="createBlogForm" class="admin-form" enctype="multipart/form-data">
                <input type="hidden" name="type" value="blog">
                
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="title">Blog Title *</label>
                            <input type="text" id="title" name="title" required 
                                   placeholder="Enter blog title" 
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
                        <label for="excerpt">Excerpt</label>
                        <textarea id="excerpt" name="excerpt" 
                                  placeholder="Brief description of the blog post"
                                  class="form-control" rows="3"></textarea>
                        <div class="field-error" id="excerpt-error"></div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">Content</h3>
                    
                    <div class="form-group">
                        <label for="content">Blog Content *</label>
                        {get_quill_editor_html("editor-container", "content")}
                        <div class="field-error" id="content-error"></div>
                    </div>
                </div>
                
                <div class="form-section">
                    <h3 class="section-title">Media</h3>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="featured_image">Featured Image</label>
                            <input type="file" id="featured_image" name="featured_image" 
                                   accept="image/jpeg,image/png,image/gif,image/webp,image/avif" class="file-input">
                            <div class="file-upload-area" id="featured-image-upload-area">
                                <i class="fas fa-image"></i>
                                <p>Click to upload featured image</p>
                                <small>JPEG, PNG, GIF, WebP, AVIF (Max: 10MB)</small>
                            </div>
                            <div id="featured-image-preview"></div>
                        </div>
                        
                        <div class="form-group">
                            <label for="banner">Banner Image</label>
                            <input type="file" id="banner" name="banner" 
                                   accept="image/jpeg,image/png,image/gif,image/webp,image/avif" class="file-input">
                            <div class="file-upload-area" id="banner-upload-area">
                                <i class="fas fa-panorama"></i>
                                <p>Click to upload banner image</p>
                                <small>JPEG, PNG, GIF, WebP, AVIF (Max: 10MB)</small>
                            </div>
                            <div id="banner-preview"></div>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="video">Video</label>
                        <input type="file" id="video" name="video" 
                               accept="video/*" class="file-input">
                        <div class="file-upload-area" id="video-upload-area">
                            <i class="fas fa-video"></i>
                            <p>Click to upload video file</p>
                            <small>MP4, WebM, MOV, AVI (Max: 100MB)</small>
                        </div>
                        <div id="video-preview"></div>
                    </div>
                </div>
                
                <div class="form-section">
                    <button type="submit" class="btn btn-primary">
                        <i class="fas fa-save"></i>
                        Create Blog Post
                    </button>
                    <button type="button" id="save-draft-btn" class="btn btn-secondary">
                        <i class="fas fa-file-alt"></i>
                        Save as Draft
                    </button>
                </div>
            </form>
        </div>
        
        <script>
            {get_upload_handlers_js()}
            {get_quill_editor_js("editor-container", "content", "blogQuill")}
            
            // Initialize file upload handlers
            document.addEventListener('DOMContentLoaded', function() {{
                // File input change handlers
                document.getElementById('featured_image').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'featured-image-preview', 'image');
                }});
                
                document.getElementById('banner').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'banner-preview', 'image');
                }});
                
                document.getElementById('video').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'video-preview', 'video');
                }});
                
                // Upload area click handlers
                document.getElementById('featured-image-upload-area').addEventListener('click', function() {{
                    document.getElementById('featured_image').click();
                }});
                
                document.getElementById('banner-upload-area').addEventListener('click', function() {{
                    document.getElementById('banner').click();
                }});
                
                document.getElementById('video-upload-area').addEventListener('click', function() {{
                    document.getElementById('video').click();
                }});
                
                // Save draft button handler
                const saveDraftBtn = document.getElementById('save-draft-btn');
                if (saveDraftBtn) {{
                    saveDraftBtn.addEventListener('click', saveDraft);
                }}
            }});
            
            // Enhanced form submission handler
            function initFormSubmission() {{
                const form = document.getElementById('createBlogForm');
                if (!form) {{
                    return;
                }}
                
                form.addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    // Clear previous errors
                    if (typeof clearAllErrors === 'function') {{
                        clearAllErrors();
                    }}
                    
                    // Set loading state
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('createBlogForm', true);
                    }}
                    
                    // Validate form
                    let isValid = true;
                    
                    // Check title
                    const titleField = document.getElementById('title');
                    const titleValue = titleField ? titleField.value.trim() : '';
                    
                    if (!titleValue) {{
                        if (typeof showFieldError === 'function') {{
                            showFieldError('title-error', 'Title is required');
                        }}
                        isValid = false;
                    }}
                    
                    // Check content - wait for Quill editor to be ready
                    let contentHtml = '';
                    if (typeof window.blogQuill !== 'undefined' && window.blogQuill) {{
                        const textContent = window.blogQuill.getText().trim();

                        if (!textContent || textContent.length < 10) {{

                            if (typeof showFieldError === 'function') {{
                                showFieldError('content-error', 'Content must be at least 10 characters long');
                            }}
                            isValid = false;
                        }} else {{
                            contentHtml = window.blogQuill.root.innerHTML;
                        }}
                    }} else {{
                        // Fallback to textarea content
                        const contentTextarea = document.getElementById('content');
                        if (contentTextarea && contentTextarea.value.trim()) {{
                            contentHtml = contentTextarea.value;
                        }} else {{
                            if (typeof showFieldError === 'function') {{
                                showFieldError('content-error', 'Content is required');
                            }}
                            isValid = false;
                        }}
                    }}
                    
                    if (!isValid) {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('createBlogForm', false);
                        }}
                        return;
                    }}
                    
                    // Submit form
                    try {{
                        // Create fresh FormData and manually add all fields
                        const formData = new FormData();
                        
                        // Add all form fields manually to ensure they're included
                        formData.append('title', titleValue);
                        formData.append('content', contentHtml);
                        formData.append('author_name', document.getElementById('author_name')?.value || 'JUNGLORE');
                        formData.append('excerpt', document.getElementById('excerpt')?.value || '');
                        formData.append('status', document.getElementById('status')?.value || 'draft');
                        formData.append('category_id', document.getElementById('category_id')?.value || '');
                        formData.append('type', 'blog');
                        
                        // Add file uploads if present
                        const featuredImage = document.getElementById('featured_image');
                        if (featuredImage && featuredImage.files[0]) {{
                            formData.append('featured_image', featuredImage.files[0]);
                        }}
                        
                        const banner = document.getElementById('banner');
                        if (banner && banner.files[0]) {{
                            formData.append('banner', banner.files[0]);
                        }}
                        
                        const video = document.getElementById('video');
                        if (video && video.files[0]) {{
                            formData.append('video', video.files[0]);
                        }}
                        
                        const response = await fetch('/admin/create/blog', {{
                            method: 'POST',
                            body: formData,
                            credentials: 'same-origin'
                        }});
                        
                        if (response.ok) {{
                            if (typeof showMessage === 'function') {{
                                showMessage('Blog post created successfully!', 'success');
                            }}
                            setTimeout(() => {{
                                window.location.href = '/admin/manage/content?type=blog';
                            }}, 1500);
                        }} else {{
                            if (typeof showMessage === 'function') {{
                                showMessage('Server error: ' + response.status, 'error');
                            }}
                        }}
                    }} catch (error) {{
                        if (typeof showMessage === 'function') {{
                            showMessage('Network error: ' + error.message, 'error');
                        }}
                    }} finally {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('createBlogForm', false);
                        }}
                    }}
                }});
            }}
            
            // Initialize form submission when DOM is ready
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initFormSubmission);
            }} else {{
                initFormSubmission();
            }}
            
            function saveDraft() {{
                document.getElementById('status').value = 'draft';
                document.getElementById('createBlogForm').dispatchEvent(new Event('submit'));
            }}
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Create Blog Post", create_form, "blog"))

@router.post("/create/blog")
async def create_blog(request: Request):
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
    
    """Handle blog creation with proper error handling"""
    try:
        from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
        from app.services.file_upload import file_upload_service
        from slugify import slugify
        from uuid import UUID
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info("Blog creation started")
        
        # Check authentication
        if not request.session.get("authenticated"):
            return RedirectResponse(url="/admin/login", status_code=302)
        
        # Handle form data with files using standard approach with large limits
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
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            
            while True:
                existing = await db.execute(
                    select(Content).where(Content.slug == slug)
                )
                if not existing.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Create content
            content_obj = Content(
                type=ContentTypeEnum.BLOG,
                title=title,
                content=content_html,
                author_name=data.get('author_name', 'JUNGLORE').strip() or 'JUNGLORE',
                excerpt=data.get('excerpt', ''),
                slug=slug,
                author_id=admin_user.id,
                category_id=UUID(data['category_id']) if data.get('category_id') else None,
                featured_image=data.get('featured_image'),
                banner=data.get('banner'),
                video=data.get('video'),
                status=ContentStatusEnum(data.get('status', 'draft'))
            )
            
            db.add(content_obj)
            await db.commit()
            await db.refresh(content_obj)
            
            logger.info(f"Blog created successfully with ID: {content_obj.id}")
            
            return RedirectResponse(url="/admin/manage/content?type=blog&created=1", status_code=302)
            
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Blog creation error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)

@router.get("/edit/blog/{content_id}", response_class=HTMLResponse)
async def edit_blog_form(request: Request, content_id: str):
    """Edit blog form"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get the content to edit
    try:
        from uuid import UUID
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
    
    # Determine content type and form
    if content.type == ContentTypeEnum.BLOG:
        # Prepare safe content string for JS
        safe_content = content.content.replace('`', '\\`') if content.content else ''
        
        # --- PRE-CALCULATE HTML FRAGMENTS ---
        # Moving these outside f-string to prevent SyntaxError with backslashes
        
        featured_image_html = ""
        if content.featured_image:
            featured_image_html = f"""
                <div class="current-image" id="current-featured-image">
                    <img src="/uploads/{content.featured_image}" alt="Current featured image" style="max-width: 200px; max-height: 150px; border-radius: 8px;">
                    <button type="button" onclick="removeCurrentImage('featured_image', 'current-featured-image')" class="btn btn-danger btn-sm" style="margin-top: 8px;">
                        <i class="fas fa-trash"></i> Remove Image
                    </button>
                </div>
            """

        banner_html = ""
        if content.banner:
            banner_html = f"""
                <div class="current-image" id="current-banner-image">
                    <img src="/uploads/{content.banner}" alt="Current banner image" style="max-width: 200px; max-height: 150px; border-radius: 8px;">
                    <button type="button" onclick="removeCurrentImage('banner', 'current-banner-image')" class="btn btn-danger btn-sm" style="margin-top: 8px;">
                        <i class="fas fa-trash"></i> Remove Image
                    </button>
                </div>
            """

        video_html = ""
        if content.video:
            video_html = f"""
                <div class="current-video" id="current-video">
                    <video controls style="max-width: 300px; max-height: 200px; border-radius: 8px;">
                        <source src="/uploads/{content.video}" type="video/mp4">
                        Your browser does not support the video tag.
                    </video>
                    <button type="button" onclick="removeCurrentImage('video', 'current-video')" class="btn btn-danger btn-sm" style="margin-top: 8px;">
                        <i class="fas fa-trash"></i> Remove Video
                    </button>
                </div>
            """
        
        edit_form = f"""
            <div class="page-header">
                <h1 class="page-title">Edit Blog Post</h1>
                <p class="page-subtitle">Update your blog post content</p>
            </div>
            
            <div id="message-container"></div>
            
            <div class="form-container">
                <form id="editBlogForm" class="admin-form" enctype="multipart/form-data">
                    <input type="hidden" name="content_id" value="{content.id}">
                    <input type="hidden" name="type" value="blog">
                    
                    <div class="form-section">
                        <h3 class="section-title">Basic Information</h3>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="title">Blog Title *</label>
                                <input type="text" id="title" name="title" required 
                                       placeholder="Enter blog title" 
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
                            <label for="excerpt">Excerpt</label>
                            <textarea id="excerpt" name="excerpt" 
                                      placeholder="Brief description of the blog post"
                                      class="form-control" rows="3">{content.excerpt or ''}</textarea>
                            <div class="field-error" id="excerpt-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-section">
                        <h3 class="section-title">Content</h3>
                        
                        <div class="form-group">
                            <label for="content">Blog Content *</label>
                            {get_quill_editor_html("editor-container", "content")}
                            <div class="field-error" id="content-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-section">
                        <h3 class="section-title">Media</h3>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="featured_image">Featured Image</label>
                                <div class="file-upload-area" id="featured-image-upload-area">
                                    <input type="file" id="featured_image" name="featured_image" 
                                           accept="image/jpeg,image/png,image/gif,image/webp,image/avif" 
                                           class="file-input">
                                    <div class="upload-text">
                                        <i class="fas fa-cloud-upload-alt"></i>
                                        <p>Click to upload or drag and drop</p>
                                        <small>JPEG, PNG, GIF, WebP, AVIF up to 50MB</small>
                                    </div>
                                </div>
                                <div id="featured-image-preview"></div>
                                {featured_image_html}
                                <div class="field-error" id="featured-image-error"></div>
                            </div>
                            
                            <div class="form-group">
                                <label for="banner">Banner Image</label>
                                <div class="file-upload-area" id="banner-upload-area">
                                    <input type="file" id="banner" name="banner" 
                                           accept="image/jpeg,image/png,image/gif,image/webp,image/avif" 
                                           class="file-input">
                                    <div class="upload-text">
                                        <i class="fas fa-cloud-upload-alt"></i>
                                        <p>Click to upload or drag and drop</p>
                                        <small>JPEG, PNG, GIF, WebP, AVIF up to 50MB</small>
                                    </div>
                                </div>
                                <div id="banner-preview"></div>
                                {banner_html}
                                <div class="field-error" id="banner-error"></div>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="video">Video (Optional)</label>
                            <div class="file-upload-area" id="video-upload-area">
                                <input type="file" id="video" name="video" 
                                       accept="video/mp4,video/avi,video/mov,video/wmv,video/flv" 
                                       class="file-input">
                                <div class="upload-text">
                                    <i class="fas fa-cloud-upload-alt"></i>
                                    <p>Click to upload or drag and drop</p>
                                    <small>MP4, AVI, MOV, WMV, FLV up to 200MB</small>
                                </div>
                            </div>
                            <div id="video-preview"></div>
                            {video_html}
                            <div class="field-error" id="video-error"></div>
                        </div>
                    </div>
                    
                    <div class="form-section">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Update Blog Post
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
                {get_quill_editor_js("editor-container", "content", "blogQuill")}
                
                // Set initial content and add click handlers
                document.addEventListener('DOMContentLoaded', function() {{

                    if (typeof window.blogQuill !== 'undefined') {{
                        window.blogQuill.root.innerHTML = `{safe_content}`;
                    }}
                    
                    // Add click handlers for upload areas
                    const featuredImageUpload = document.getElementById('featured-image-upload-area');
                    if (featuredImageUpload) {{

                        featuredImageUpload.addEventListener('click', function(e) {{

                            const fileInput = document.getElementById('featured_image');
                            if (fileInput) {{
                                fileInput.click();
                            }}
                        }});
                    }}
                    
                    const bannerUpload = document.getElementById('banner-upload-area');
                    if (bannerUpload) {{

                        bannerUpload.addEventListener('click', function(e) {{

                            const fileInput = document.getElementById('banner');
                            if (fileInput) {{
                                fileInput.click();
                            }}
                        }});
                    }}
                    
                    const videoUpload = document.getElementById('video-upload-area');
                    if (videoUpload) {{

                        videoUpload.addEventListener('click', function(e) {{

                            const fileInput = document.getElementById('video');
                            if (fileInput) {{
                                fileInput.click();
                            }}
                        }});
                    }}
                    
                    // Add file input change handlers
                    const featuredImageInput = document.getElementById('featured_image');
                    if (featuredImageInput) {{
                        featuredImageInput.addEventListener('change', function(e) {{

                            handleFileUpload(e, 'featured-image-preview', 'image');
                        }});
                    }}
                    
                    const bannerInput = document.getElementById('banner');
                    if (bannerInput) {{
                        bannerInput.addEventListener('change', function(e) {{

                            handleFileUpload(e, 'banner-preview', 'image');
                        }});
                    }}
                    
                    const videoInput = document.getElementById('video');
                    if (videoInput) {{
                        videoInput.addEventListener('change', function(e) {{

                            handleFileUpload(e, 'video-preview', 'video');
                        }});
                    }}
                    
                    // Add click-to-reupload functionality for current images
                    const currentFeaturedImage = document.getElementById('current-featured-image');
                    if (currentFeaturedImage) {{

                        const img = currentFeaturedImage.querySelector('img');
                        if (img) {{

                            img.style.cursor = 'pointer';
                            img.title = 'Click to change image';
                            img.addEventListener('click', function(e) {{

                                e.preventDefault();
                                e.stopPropagation();
                                const fileInput = document.getElementById('featured_image');
                                if (fileInput) {{
                                    fileInput.click();
                                }}
                            }});
                        }}
                        // Also make the container clickable (except buttons)
                        currentFeaturedImage.addEventListener('click', function(e) {{
                            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'I' && !e.target.closest('button')) {{

                                const fileInput = document.getElementById('featured_image');
                                if (fileInput) {{
                                    fileInput.click();
                                }}
                            }}
                        }});
                    }} else {{

                    }}
                    
                    const currentBannerImage = document.getElementById('current-banner-image');
                    if (currentBannerImage) {{

                        const img = currentBannerImage.querySelector('img');
                        if (img) {{

                            img.style.cursor = 'pointer';
                            img.title = 'Click to change image';
                            img.addEventListener('click', function(e) {{

                                e.preventDefault();
                                e.stopPropagation();
                                const fileInput = document.getElementById('banner');
                                if (fileInput) {{
                                    fileInput.click();
                                }}
                            }});
                        }}
                        // Also make the container clickable (except buttons)
                        currentBannerImage.addEventListener('click', function(e) {{
                            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'I' && !e.target.closest('button')) {{

                                const fileInput = document.getElementById('banner');
                                if (fileInput) {{
                                    fileInput.click();
                                }}
                            }}
                        }});
                    }} else {{

                    }}
                }});
                
                // Remove current image function
                function removeCurrentImage(inputId, containerId) {{
                    const container = document.getElementById(containerId);
                    const uploadArea = document.querySelector(`#${{inputId.replace('_', '-')}}-upload`);
                    
                    if (container) {{
                        container.style.display = 'none';
                        // Add hidden input to mark for removal
                        const removeInput = document.createElement('input');
                        removeInput.type = 'hidden';
                        removeInput.name = `remove_${{inputId}}`;
                        removeInput.value = 'true';
                        container.parentNode.appendChild(removeInput);
                    }}
                    
                    if (uploadArea) {{
                        uploadArea.style.display = 'block';
                    }}
                }}
                
                // Form submission
                document.getElementById('editBlogForm').addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    // Clear previous errors
                    if (typeof clearAllErrors === 'function') {{
                        clearAllErrors();
                    }}
                    
                    // Set loading state
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('editBlogForm', true);
                    }}
                    
                    // Validate form
                    let isValid = true;
                    const titleField = document.getElementById('title');
                    if (!titleField || !titleField.value.trim()) {{
                        if (typeof showFieldError === 'function') {{
                            showFieldError('title-error', 'Title is required');
                        }}
                        isValid = false;
                    }}
                    
                    let contentHtml = '';
                    if (typeof window.blogQuill !== 'undefined' && window.blogQuill) {{
                        const textContent = window.blogQuill.getText().trim();
                        if (!textContent || textContent.length < 10) {{
                            if (typeof showFieldError === 'function') {{
                                showFieldError('content-error', 'Content must be at least 10 characters long');
                            }}
                            isValid = false;
                        }} else {{
                            contentHtml = window.blogQuill.root.innerHTML;
                        }}
                    }}
                    
                    if (!isValid) {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('editBlogForm', false);
                        }}
                        return;
                    }}
                    
                    // Submit form
                    try {{
                        const formData = new FormData();
                        formData.append('title', titleField.value.trim());
                        formData.append('content', contentHtml);
                        formData.append('author_name', document.getElementById('author_name')?.value || 'JUNGLORE');
                        formData.append('excerpt', document.getElementById('excerpt')?.value || '');
                        formData.append('status', document.getElementById('status')?.value || 'draft');
                        formData.append('category_id', document.getElementById('category_id')?.value || '');
                        
                        // Add file uploads if present
                        const featuredImage = document.getElementById('featured_image');
                        if (featuredImage && featuredImage.files[0]) {{
                            formData.append('featured_image', featuredImage.files[0]);
                        }}
                        
                        const banner = document.getElementById('banner');
                        if (banner && banner.files[0]) {{
                            formData.append('banner', banner.files[0]);
                        }}
                        
                        const video = document.getElementById('video');
                        if (video && video.files[0]) {{
                            formData.append('video', video.files[0]);
                        }}
                        
                        // Add image removal flags if present
                        const removeFeaturedImage = document.querySelector('input[name="remove_featured_image"]');
                        if (removeFeaturedImage) {{
                            formData.append('remove_featured_image', 'true');
                        }}
                        
                        const removeBanner = document.querySelector('input[name="remove_banner"]');
                        if (removeBanner) {{
                            formData.append('remove_banner', 'true');
                        }}
                        
                        const removeVideo = document.querySelector('input[name="remove_video"]');
                        if (removeVideo) {{
                            formData.append('remove_video', 'true');
                        }}
                        
                        const response = await fetch('/admin/edit/blog/{content_id}', {{
                            method: 'POST',
                            body: formData,
                            credentials: 'same-origin'
                        }});
                        
                        if (response.ok) {{
                            if (typeof showMessage === 'function') {{
                                showMessage('Blog post updated successfully!', 'success');
                            }}
                            setTimeout(() => {{
                                window.location.href = '/admin/manage/content';
                            }}, 1500);
                        }} else {{
                            const errorText = await response.text();
                            if (typeof showMessage === 'function') {{
                                showMessage('Error updating blog post', 'error');
                            }}
                        }}
                    }} catch (error) {{
                        if (typeof showMessage === 'function') {{
                            showMessage('Network error: ' + error.message, 'error');
                        }}
                    }} finally {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('editBlogForm', false);
                        }}
                    }}
                }});
            </script>
        """
        
        return HTMLResponse(content=create_html_page("Edit Blog Post", edit_form, "edit"))
    
    else:
        type_value = content.type.value
        return HTMLResponse(content=create_html_page("Edit Not Supported", 
            f"<div class='alert alert-warning'>Editing {type_value} is not yet supported</div>", "edit"))

@router.post("/edit/blog/{content_id}")
async def update_blog(request: Request, content_id: str):
    """Handle blog update"""
    try:
        from uuid import UUID
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Blog update started for ID: {content_id}")
        
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

        # Handle form data using standard FastAPI approach
        try:
            from fastapi import Form, File, UploadFile
            
            # Parse form data manually
            form_data = await request.form()
            
            data = {}
            files = {}
            
            for key, value in form_data.items():
                if hasattr(value, 'filename') and hasattr(value, 'file'):
                    # This is a file upload
                    files[key] = value
                else:
                    # This is regular form data
                    data[key] = value
                    
        except Exception as form_error:
            logger.error(f"Form parsing error: {form_error}")
            from fastapi.responses import JSONResponse
            return JSONResponse({
                "success": False, 
                "error": f"Form parsing error: {str(form_error)}"
            }, status_code=400)
        
        # Validate required fields
        title = data.get('title', '').strip() if data.get('title') else ''
        content_html = data.get('content', '').strip() if data.get('content') else ''
        
        if not title:
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Title is required"}, status_code=400)
        
        if not content_html:
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Content is required"}, status_code=400)
        
        # Handle file uploads
        try:
            from app.services.file_upload import file_upload_service
        except ImportError as import_error:
            logger.error(f"Failed to import file upload service: {import_error}")
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": f"File upload service not available: {str(import_error)}"}, status_code=500)
        
        # Update content
        async with get_db_session() as db:
            result = await db.execute(
                select(Content).where(Content.id == UUID(content_id))
            )
            content_obj = result.scalar_one_or_none()
            
            if not content_obj:
                from fastapi.responses import JSONResponse
                return JSONResponse({"success": False, "error": "Content not found"}, status_code=404)
            
            # Handle file uploads
            if 'featured_image' in files and files['featured_image'].filename:
                try:
                    uploaded_file = await file_upload_service.upload_file(files['featured_image'])
                    content_obj.featured_image = uploaded_file['file_url']
                except Exception as upload_error:
                    logger.error(f"Featured image upload error: {upload_error}")
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"success": False, "error": f"Featured image upload failed: {str(upload_error)}"}, status_code=400)
            
            if 'banner' in files and files['banner'].filename:
                try:
                    uploaded_file = await file_upload_service.upload_file(files['banner'])
                    content_obj.banner = uploaded_file['file_url']
                except Exception as upload_error:
                    logger.error(f"Banner image upload error: {upload_error}")
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"success": False, "error": f"Banner image upload failed: {str(upload_error)}"}, status_code=400)
            
            if 'video' in files and files['video'].filename:
                try:
                    uploaded_file = await file_upload_service.upload_file(files['video'])
                    content_obj.video = uploaded_file['file_url']
                except Exception as upload_error:
                    logger.error(f"Video upload error: {upload_error}")
                    from fastapi.responses import JSONResponse
                    return JSONResponse({"success": False, "error": f"Video upload failed: {str(upload_error)}"}, status_code=400)
            
            # Handle image removals (check for remove_* fields)
            if data.get('remove_featured_image') == 'true':
                # Delete old file if it exists
                if content_obj.featured_image:
                    try:
                        await file_upload_service.delete_file(content_obj.featured_image)
                    except Exception as delete_error:
                        logger.warning(f"Failed to delete old featured image: {delete_error}")
                    content_obj.featured_image = None
            
            if data.get('remove_banner') == 'true':
                # Delete old file if it exists
                if content_obj.banner:
                    try:
                        await file_upload_service.delete_file(content_obj.banner)
                    except Exception as delete_error:
                        logger.warning(f"Failed to delete old banner image: {delete_error}")
                    content_obj.banner = None
            
            if data.get('remove_video') == 'true':
                # Delete old file if it exists
                if content_obj.video:
                    try:
                        await file_upload_service.delete_file(content_obj.video)
                    except Exception as delete_error:
                        logger.warning(f"Failed to delete old video: {delete_error}")
                    content_obj.video = None
            
            # Update fields
            content_obj.title = title
            content_obj.content = content_html
            content_obj.author_name = data.get('author_name', 'JUNGLORE').strip() or 'JUNGLORE'
            content_obj.excerpt = data.get('excerpt', '')
            content_obj.status = ContentStatusEnum(data.get('status', 'draft'))
            
            if data.get('category_id'):
                content_obj.category_id = UUID(data['category_id'])
            
            await db.commit()
            
            logger.info(f"Blog updated successfully with ID: {content_obj.id}")
            
            return RedirectResponse(url="/admin/manage/content?updated=1", status_code=302)
            
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Blog update error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)