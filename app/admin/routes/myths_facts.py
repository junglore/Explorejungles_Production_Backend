"""
Myths vs Facts management routes for admin panel
"""

from fastapi import APIRouter, Request, Form, File, UploadFile, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID, uuid4
from typing import Optional
import logging

from app.models.myth_fact import MythFact
from app.models.category import Category
from app.models.user import User
from app.admin.templates.base import create_html_page
from app.admin.templates.editor import get_quill_editor_html, get_quill_editor_js, get_upload_handlers_js
from app.db.database import get_db_session
from app.services.file_upload import file_upload_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/myths-facts", response_class=HTMLResponse)
async def myths_facts_list(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    featured_only: bool = Query(False, description="Show only featured items")
):
    """Admin list view for myths vs facts with pagination and search"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Build base query
            query = select(MythFact).options(
                selectinload(MythFact.category)
            )
            
            # Apply filters
            filters = []
            
            # Search filter
            if search and search.strip():
                search_term = f"%{search.strip()}%"
                filters.append(
                    or_(
                        MythFact.title.ilike(search_term),
                        MythFact.myth_content.ilike(search_term),
                        MythFact.fact_content.ilike(search_term)
                    )
                )
            
            # Category filter
            if category_id and category_id.strip():
                try:
                    category_uuid = UUID(category_id)
                    filters.append(MythFact.category_id == category_uuid)
                except ValueError:
                    pass  # Invalid UUID, ignore filter
            
            # Featured filter
            if featured_only:
                filters.append(MythFact.is_featured == True)
            
            # Apply filters to query
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count for pagination
            count_query = select(func.count(MythFact.id))
            if filters:
                count_query = count_query.where(and_(*filters))
            
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(MythFact.created_at)).offset(offset).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            myths_facts = result.scalars().all()
            
            # Get categories for filter dropdown
            categories_result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = categories_result.scalars().all()
            
    except Exception as e:
        logger.error(f"Error loading myths vs facts list: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Error", 
                f"<div class='message error'>Error loading myths vs facts: {str(e)}</div>", 
                "myths-facts"
            )
        )
    
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
    for myth_fact in myths_facts:
        featured_badge = '<span class="badge badge-success">Featured</span>' if myth_fact.is_featured else ''
        category_name = myth_fact.category.name if myth_fact.category else 'No Category'
        
        # Truncate content for display
        myth_preview = (myth_fact.myth_content[:100] + '...') if len(myth_fact.myth_content) > 100 else myth_fact.myth_content
        fact_preview = (myth_fact.fact_content[:100] + '...') if len(myth_fact.fact_content) > 100 else myth_fact.fact_content
        
        table_rows += f"""
        <tr>
            <td>
                <div class="content-title">{myth_fact.title}</div>
                <div class="content-meta">
                    <small class="text-muted">Created: {myth_fact.created_at.strftime('%Y-%m-%d %H:%M') if myth_fact.created_at else 'Unknown'}</small>
                </div>
            </td>
            <td>
                <div class="content-preview">
                    <strong>Myth:</strong> {myth_preview}<br>
                    <strong>Fact:</strong> {fact_preview}
                </div>
            </td>
            <td>{category_name}</td>
            <td>{featured_badge}</td>
            <td>
                <div class="action-buttons">
                    <a href="/admin/myths-facts/edit/{myth_fact.id}" class="btn btn-sm btn-primary">
                        <i class="fas fa-edit"></i> Edit
                    </a>
                    <button onclick="confirmDelete('{myth_fact.id}', '{myth_fact.title}')" class="btn btn-sm btn-danger">
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
            pagination_html += f'<a href="?page={page-1}&limit={limit}&search={search or ""}&category_id={category_id or ""}&featured_only={featured_only}" class="btn btn-sm btn-secondary">Previous</a>'
        
        # Page numbers
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        
        for p in range(start_page, end_page + 1):
            active_class = "btn-primary" if p == page else "btn-secondary"
            pagination_html += f'<a href="?page={p}&limit={limit}&search={search or ""}&category_id={category_id or ""}&featured_only={featured_only}" class="btn btn-sm {active_class}">{p}</a>'
        
        # Next button
        if has_next:
            pagination_html += f'<a href="?page={page+1}&limit={limit}&search={search or ""}&category_id={category_id or ""}&featured_only={featured_only}" class="btn btn-sm btn-secondary">Next</a>'
        
        pagination_html += """
            </div>
        </div>
        """
    
    list_content = f"""
        <div class="page-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 class="page-title">Myths vs Facts</h1>
                    <p class="page-subtitle">Manage educational myth vs fact content</p>
                </div>
                <a href="/admin/myths-facts/create" class="btn btn-primary">
                    <i class="fas fa-plus"></i> Create New
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
                                   placeholder="Search title, myth, or fact content..." class="form-control">
                        </div>
                        <div class="filter-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                {category_options}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label for="featured_only">Featured Only</label>
                            <input type="checkbox" id="featured_only" name="featured_only" value="true" 
                                   {"checked" if featured_only else ""} class="form-checkbox">
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
                        <a href="/admin/myths-facts" class="btn btn-secondary">
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
                            <th>Content Preview</th>
                            <th>Category</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows if table_rows else '<tr><td colspan="5" class="text-center">No myths vs facts found</td></tr>'}
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
        
        <style>
            .content-container {{
                background: white;
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
            }}
            
            .filters-section {{
                margin-bottom: 2rem;
                padding: 1.5rem;
                background: #f8fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            .filters-form {{
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }}
            
            .filter-row {{
                display: grid;
                grid-template-columns: 2fr 1fr auto 100px;
                gap: 1rem;
                align-items: end;
            }}
            
            .filter-group {{
                display: flex;
                flex-direction: column;
            }}
            
            .filter-group label {{
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.5rem;
                font-size: 0.9rem;
            }}
            
            .filter-actions {{
                display: flex;
                gap: 0.5rem;
            }}
            
            .table-container {{
                overflow-x: auto;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            .admin-table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            
            .admin-table th {{
                background: #f8fafc;
                padding: 1rem;
                text-align: left;
                font-weight: 600;
                color: #4a5568;
                border-bottom: 2px solid #e2e8f0;
            }}
            
            .admin-table td {{
                padding: 1rem;
                border-bottom: 1px solid #e2e8f0;
                vertical-align: top;
            }}
            
            .admin-table tr:hover {{
                background: #f8fafc;
            }}
            
            .content-title {{
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 0.25rem;
            }}
            
            .content-meta {{
                color: #718096;
                font-size: 0.875rem;
            }}
            
            .content-preview {{
                font-size: 0.9rem;
                line-height: 1.4;
            }}
            
            .badge {{
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .badge-success {{
                background: #c6f6d5;
                color: #22543d;
            }}
            
            .action-buttons {{
                display: flex;
                gap: 0.5rem;
            }}
            
            .btn-sm {{
                padding: 0.5rem 1rem;
                font-size: 0.875rem;
            }}
            
            .btn-danger {{
                background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);
                color: white;
            }}
            
            .btn-danger:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(229, 62, 62, 0.3);
            }}
            
            .pagination-container {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-top: 2rem;
                padding-top: 1rem;
                border-top: 1px solid #e2e8f0;
            }}
            
            .pagination {{
                display: flex;
                gap: 0.5rem;
            }}
            
            .pagination-info {{
                color: #718096;
                font-size: 0.9rem;
            }}
            
            .modal {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }}
            
            .modal-content {{
                background: white;
                padding: 2rem;
                border-radius: 16px;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            }}
            
            .modal-actions {{
                display: flex;
                gap: 1rem;
                justify-content: flex-end;
                margin-top: 1.5rem;
            }}
            
            .text-center {{
                text-align: center;
            }}
            
            .text-muted {{
                color: #718096;
            }}
            
            .text-danger {{
                color: #e53e3e;
            }}
            
            .form-checkbox {{
                width: auto;
                margin-top: 0.5rem;
            }}
            
            @media (max-width: 768px) {{
                .filter-row {{
                    grid-template-columns: 1fr;
                }}
                
                .action-buttons {{
                    flex-direction: column;
                }}
                
                .pagination-container {{
                    flex-direction: column;
                    gap: 1rem;
                }}
            }}
        </style>
        
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
                    const response = await fetch(`/admin/myths-facts/delete/${{deleteItemId}}`, {{
                        method: 'DELETE',
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        showMessage('Myth vs fact deleted successfully!', 'success');
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 1500);
                    }} else {{
                        const errorText = await response.text();
                        showMessage('Error deleting myth vs fact: ' + response.status, 'error');
                    }}
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
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
    
    return HTMLResponse(content=create_html_page("Myths vs Facts", list_content, "myths-facts"))


@router.get("/myths-facts/create", response_class=HTMLResponse)
async def create_myth_fact_form(request: Request):
    """Create myth vs fact form with rich HTML interface"""
    
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
    
    create_form = f"""
        <div class="page-header">
            <h1 class="page-title">Create Myth vs Fact</h1>
            <p class="page-subtitle">Create engaging educational content about wildlife myths and facts</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="createMythFactForm" class="admin-form" enctype="multipart/form-data">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-group">
                        <label for="title">Title *</label>
                        <input type="text" id="title" name="title" required 
                               placeholder="Enter a compelling title for this myth vs fact" 
                               maxlength="500"
                               class="form-control">
                        <div class="field-error" id="title-error"></div>
                        <small class="field-help">A clear, engaging title that summarizes the myth being addressed</small>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                <option value="">Select category...</option>
                                {category_options}
                            </select>
                            <small class="field-help">Optional: Categorize this content for better organization</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="custom_points">Custom Points</label>
                            <input type="number" id="custom_points" name="custom_points" 
                                   placeholder="Leave empty for default points (5)"
                                   min="1" max="100"
                                   class="form-control">
                            <small class="field-help">Optional: Set custom points for this card (overrides default 5 points)</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="is_featured">Featured Content</label>
                            <div class="checkbox-wrapper">
                                <input type="checkbox" id="is_featured" name="is_featured" value="true" class="form-checkbox">
                                <label for="is_featured" class="checkbox-label">Mark as featured content</label>
                            </div>
                            <small class="field-help">Featured content appears prominently in the game</small>
                        </div>
                    </div>
                </div>
                
                <!-- Content Section -->
                <div class="form-section">
                    <h3 class="section-title">Content</h3>
                    
                    <div class="form-group">
                        <label for="myth_content">Myth Statement *</label>
                        <textarea id="myth_content" name="myth_content" required
                                  placeholder="Describe the common myth or misconception..."
                                  class="form-control content-textarea" rows="4"></textarea>
                        <div class="field-error" id="myth-content-error"></div>
                        <small class="field-help">Clearly state the myth or misconception that needs to be addressed</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="fact_content">Fact Explanation *</label>
                        <textarea id="fact_content" name="fact_content" required
                                  placeholder="Provide the accurate information and explanation..."
                                  class="form-control content-textarea" rows="6"></textarea>
                        <div class="field-error" id="fact-content-error"></div>
                        <small class="field-help">Provide accurate, educational information that corrects the myth</small>
                    </div>
                    
                    <!-- Card Type Selection -->
                    <div class="form-group">
                        <label for="type" style="font-weight: 700; font-size: 1rem; color: #2d3748;">
                            <i class="fas fa-eye" style="color: #16a34a;"></i> Which Card to Show to User? *
                        </label>
                        <div style="border: 2px solid #cbd5e0; border-radius: 12px; padding: 1.5rem; background: #f7fafc;">
                            <div style="margin-bottom: 1.25rem;">
                                <label style="display: flex; align-items: start; cursor: pointer; padding: 1rem; border-radius: 8px; border: 2px solid #e2e8f0; background: white; transition: all 0.2s;">
                                    <input type="radio" name="type" id="type_myth" value="myth" checked required 
                                           style="margin-top: 0.25rem; margin-right: 0.75rem; cursor: pointer;">
                                    <div style="flex: 1;">
                                        <div style="font-weight: 700; font-size: 1rem; color: #e53e3e; margin-bottom: 0.375rem;">
                                            🔴 Show Myth Card
                                        </div>
                                        <div style="font-size: 0.875rem; color: #718096; line-height: 1.5;">
                                            • Displays the <strong>myth statement</strong> (false claim)<br>
                                            • User should swipe <strong>LEFT</strong> to mark as false<br>
                                            • After answer, shows the fact explanation
                                        </div>
                                    </div>
                                </label>
                            </div>
                            
                            <div>
                                <label style="display: flex; align-items: start; cursor: pointer; padding: 1rem; border-radius: 8px; border: 2px solid #e2e8f0; background: white; transition: all 0.2s;">
                                    <input type="radio" name="type" id="type_fact" value="fact" required
                                           style="margin-top: 0.25rem; margin-right: 0.75rem; cursor: pointer;">
                                    <div style="flex: 1;">
                                        <div style="font-weight: 700; font-size: 1rem; color: #16a34a; margin-bottom: 0.375rem;">
                                            🟢 Show Fact Card
                                        </div>
                                        <div style="font-size: 0.875rem; color: #718096; line-height: 1.5;">
                                            • Displays the <strong>fact explanation</strong> (true statement)<br>
                                            • User should swipe <strong>RIGHT</strong> to mark as true<br>
                                            • After answer, shows the myth that people believe
                                        </div>
                                    </div>
                                </label>
                            </div>
                        </div>
                        <small class="field-help" style="color: #e53e3e; font-weight: 600; margin-top: 0.5rem; display: block;">
                            <i class="fas fa-info-circle"></i> This controls which text appears on the card during gameplay
                        </small>
                    </div>
                </div>
                
                <!-- Media Section -->
                <div class="form-section">
                    <h3 class="section-title">Media</h3>
                    
                                            <div class="form-group">
                            <label for="image">Supporting Image</label>
                            <input type="file" id="image" name="image" 
                                   accept="image/*,.avif" class="file-input">
                            <div class="file-upload-area" id="image-upload-area">
                                <i class="fas fa-image"></i>
                                <p>Click to upload supporting image</p>
                                <small>JPEG, PNG, GIF, WebP, AVIF (Max: 50MB)</small>
                            </div>
                            <div id="image-preview"></div>
                            <small class="field-help">Optional: Add a relevant image to support the educational content</small>
                        </div>
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Create Myth vs Fact
                        </button>
                        <a href="/admin/myths-facts" class="btn btn-secondary">
                            <i class="fas fa-times"></i>
                            Cancel
                        </a>
                    </div>
                </div>
            </form>
        </div>
        
        <style>
            .content-textarea {{
                min-height: 120px;
                resize: vertical;
            }}
            
            .checkbox-wrapper {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-top: 0.5rem;
            }}
            
            .checkbox-label {{
                font-weight: 500;
                color: #4a5568;
                cursor: pointer;
                margin-bottom: 0;
            }}
            
            .form-checkbox {{
                width: 18px;
                height: 18px;
                margin: 0;
            }}
            
            .field-help {{
                display: block;
                color: #718096;
                font-size: 0.875rem;
                margin-top: 0.5rem;
                font-style: italic;
            }}
            
            .form-actions {{
                display: flex;
                gap: 1rem;
                justify-content: flex-start;
            }}
            
            #image-preview {{
                margin-top: 1rem;
            }}
            
            .image-preview-item {{
                position: relative;
                display: inline-block;
                margin-right: 1rem;
            }}
            
            .image-preview-item img {{
                max-width: 200px;
                max-height: 150px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
            
            .image-preview-item .remove-image {{
                position: absolute;
                top: -8px;
                right: -8px;
                background: #e53e3e;
                color: white;
                border: none;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                cursor: pointer;
                font-size: 12px;
            }}
        </style>
        
        <script>
            {get_upload_handlers_js()}
            
            // Initialize file upload handlers
            document.addEventListener('DOMContentLoaded', function() {{
                // File input change handler
                document.getElementById('image').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'image-preview', 'image');
                }});
                
                // Upload area click handler
                document.getElementById('image-upload-area').addEventListener('click', function() {{
                    document.getElementById('image').click();
                }});
            }});
            
            // Form submission handler
            function initFormSubmission() {{
                const form = document.getElementById('createMythFactForm');
                if (!form) {{
                    console.error('Form not found: createMythFactForm');
                    return;
                }}
                
                form.addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    console.log('Myth vs fact form submission started');
                    
                    // Clear previous errors
                    if (typeof clearAllErrors === 'function') {{
                        clearAllErrors();
                    }}
                    
                    // Set loading state
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('createMythFactForm', true);
                    }}
                    
                    // Validate form
                    let isValid = true;
                    
                    // Check title
                    const titleField = document.getElementById('title');
                    const titleValue = titleField ? titleField.value.trim() : '';
                    
                    if (!titleValue) {{
                        console.error('Title validation failed - empty title');
                        if (typeof showFieldError === 'function') {{
                            showFieldError('title-error', 'Title is required');
                        }}
                        isValid = false;
                    }}
                    
                    // Check myth content
                    const mythField = document.getElementById('myth_content');
                    const mythValue = mythField ? mythField.value.trim() : '';
                    
                    if (!mythValue) {{
                        console.error('Myth content validation failed - empty content');
                        if (typeof showFieldError === 'function') {{
                            showFieldError('myth-content-error', 'Myth statement is required');
                        }}
                        isValid = false;
                    }}
                    
                    // Check fact content
                    const factField = document.getElementById('fact_content');
                    const factValue = factField ? factField.value.trim() : '';
                    
                    if (!factValue) {{
                        console.error('Fact content validation failed - empty content');
                        if (typeof showFieldError === 'function') {{
                            showFieldError('fact-content-error', 'Fact explanation is required');
                        }}
                        isValid = false;
                    }}
                    
                    if (!isValid) {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('createMythFactForm', false);
                        }}
                        return;
                    }}
                    
                    // Submit form
                    try {{
                        // Create FormData and add all fields
                        const formData = new FormData();
                        
                        formData.append('title', titleValue);
                        formData.append('myth_content', mythValue);
                        formData.append('fact_content', factValue);
                        formData.append('type', document.querySelector('input[name="type"]:checked')?.value || 'myth');
                        formData.append('category_id', document.getElementById('category_id')?.value || '');
                        formData.append('custom_points', document.getElementById('custom_points')?.value || '');
                        formData.append('is_featured', document.getElementById('is_featured')?.checked ? 'true' : 'false');
                        
                        // Add image if present
                        const imageFile = document.getElementById('image');
                        if (imageFile && imageFile.files[0]) {{
                            formData.append('image', imageFile.files[0]);
                        }}
                        
                        console.log('Sending request to /admin/myths-facts/create');
                        
                        const response = await fetch('/admin/myths-facts/create', {{
                            method: 'POST',
                            body: formData,
                            credentials: 'same-origin'
                        }});
                        
                        console.log('Response status:', response.status);
                        
                        if (response.ok) {{
                            if (typeof showMessage === 'function') {{
                                showMessage('Myth vs fact created successfully!', 'success');
                            }}
                            setTimeout(() => {{
                                window.location.href = '/admin/myths-facts';
                            }}, 1500);
                        }} else {{
                            const errorText = await response.text();
                            console.error('Server error:', errorText);
                            if (typeof showMessage === 'function') {{
                                showMessage('Server error: ' + response.status, 'error');
                            }}
                        }}
                    }} catch (error) {{
                        console.error('Network error:', error);
                        if (typeof showMessage === 'function') {{
                            showMessage('Network error: ' + error.message, 'error');
                        }}
                    }} finally {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('createMythFactForm', false);
                        }}
                    }}
                }});
            }}
            
            // Make function globally accessible for SPA navigation
            window.initFormSubmission = initFormSubmission;
            
            // Initialize form submission when DOM is ready
            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initFormSubmission);
            }} else {{
                initFormSubmission();
            }}
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Create Myth vs Fact", create_form, "myths-facts"))


@router.post("/myths-facts/create")
async def create_myth_fact(request: Request):
    """Handle myth vs fact creation with proper error handling and file uploads"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        # Parse form data with file uploads
        form_data = await request.form()
        
        logger.info(f"Form data keys: {list(form_data.keys())}")
        
        # Extract form fields
        title = form_data.get('title', '').strip()
        myth_content = form_data.get('myth_content', '').strip()
        fact_content = form_data.get('fact_content', '').strip()
        card_type = form_data.get('type', 'myth').strip()  # ✅ NEW: Get selected card type
        category_id = form_data.get('category_id', '').strip()
        is_featured = form_data.get('is_featured') == 'true'
        custom_points = form_data.get('custom_points', '').strip()
        
        # Validate required fields
        if not title:
            return JSONResponse({"success": False, "error": "Title is required"}, status_code=400)
        
        if not myth_content:
            return JSONResponse({"success": False, "error": "Myth statement is required"}, status_code=400)
        
        if not fact_content:
            return JSONResponse({"success": False, "error": "Fact explanation is required"}, status_code=400)
        
        # Handle file upload
        image_url = None
        image_file = form_data.get('image')
        if image_file and hasattr(image_file, 'filename') and image_file.filename:
            try:
                file_info = await file_upload_service.upload_file(image_file)
                image_url = file_info['file_url']
                logger.info(f"Uploaded image: {image_url}")
            except Exception as upload_error:
                logger.error(f"Image upload error: {upload_error}")
                return JSONResponse({"success": False, "error": f"Image upload failed: {str(upload_error)}"}, status_code=400)
        
        # Get admin user
        async with get_db_session() as db:
            result = await db.execute(
                select(User).where(User.email == "admin@junglore.com")
            )
            admin_user = result.scalar_one_or_none()
            
            if not admin_user:
                return JSONResponse({"success": False, "error": "Admin user not found"}, status_code=500)
            
            # Validate category if provided
            category_uuid = None
            if category_id:
                try:
                    category_uuid = UUID(category_id)
                    category_result = await db.execute(
                        select(Category).where(Category.id == category_uuid)
                    )
                    if not category_result.scalar_one_or_none():
                        return JSONResponse({"success": False, "error": f"Category not found"}, status_code=400)
                except ValueError:
                    return JSONResponse({"success": False, "error": "Invalid category ID"}, status_code=400)
            
            # Process custom points
            custom_points_value = None
            if custom_points:
                try:
                    custom_points_value = int(custom_points)
                    if custom_points_value < 1 or custom_points_value > 100:
                        return JSONResponse({"success": False, "error": "Custom points must be between 1 and 100"}, status_code=400)
                except ValueError:
                    return JSONResponse({"success": False, "error": "Invalid custom points value"}, status_code=400)
            
            # Create myth fact
            myth_fact = MythFact(
                title=title,
                myth_content=myth_content,
                fact_content=fact_content,
                type=card_type,  # ✅ NEW: Store selected card type
                image_url=image_url,
                category_id=category_uuid,
                is_featured=is_featured,
                custom_points=custom_points_value
            )
            
            db.add(myth_fact)
            await db.commit()
            await db.refresh(myth_fact)
            
            logger.info(f"Created myth vs fact with ID: {myth_fact.id}")
            
            return RedirectResponse(url="/admin/myths-facts?created=1", status_code=302)
            
    except Exception as e:
        import traceback
        logger.error(f"Myth vs fact creation error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)


@router.get("/myths-facts/edit/{myth_fact_id}", response_class=HTMLResponse)
async def edit_myth_fact_form(request: Request, myth_fact_id: str):
    """Edit myth vs fact form with pre-populated data"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get the myth fact to edit
    try:
        myth_fact_uuid = UUID(myth_fact_id)
        async with get_db_session() as db:
            result = await db.execute(
                select(MythFact).options(
                    selectinload(MythFact.category)
                ).where(MythFact.id == myth_fact_uuid)
            )
            myth_fact = result.scalar_one_or_none()
            
            if not myth_fact:
                return HTMLResponse(content=create_html_page("Myth vs Fact Not Found", 
                    "<div class='message error'>Myth vs fact not found</div>", "myths-facts"))
            
            # Get categories for dropdown
            categories_result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = categories_result.scalars().all()
    
    except ValueError:
        return HTMLResponse(content=create_html_page("Invalid ID", 
            "<div class='message error'>Invalid myth vs fact ID</div>", "myths-facts"))
    except Exception as e:
        logger.error(f"Error loading myth vs fact for edit: {e}")
        return HTMLResponse(content=create_html_page("Error", 
            f"<div class='message error'>Error loading myth vs fact: {str(e)}</div>", "myths-facts"))
    
    # Generate category options
    category_options = ""
    for category in categories:
        selected = "selected" if myth_fact.category_id == category.id else ""
        category_options += f'<option value="{category.id}" {selected}>{category.name}</option>'
    
    # Escape HTML content for form fields
    import html
    title_escaped = html.escape(myth_fact.title)
    myth_content_escaped = html.escape(myth_fact.myth_content)
    fact_content_escaped = html.escape(myth_fact.fact_content)
    
    # Current image display
    current_image_html = ""
    if myth_fact.image_url:
        current_image_html = f"""
        <div class="current-image">
            <label>Current Image</label>
            <div class="current-image-preview">
                <img src="/uploads/{myth_fact.image_url}" alt="Current image" style="max-width: 200px; max-height: 150px; border-radius: 8px;">
                <button type="button" onclick="removeCurrentImage()" class="btn btn-sm btn-danger">
                    <i class="fas fa-trash"></i> Remove Current Image
                </button>
            </div>
        </div>
        """
    
    edit_form = f"""
        <div class="page-header">
            <h1 class="page-title">Edit Myth vs Fact</h1>
            <p class="page-subtitle">Update educational content about wildlife myths and facts</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="editMythFactForm" class="admin-form" enctype="multipart/form-data">
                <input type="hidden" name="myth_fact_id" value="{myth_fact.id}">
                <input type="hidden" id="remove_image" name="remove_image" value="false">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-group">
                        <label for="title">Title *</label>
                        <input type="text" id="title" name="title" required 
                               placeholder="Enter a compelling title for this myth vs fact" 
                               maxlength="500"
                               class="form-control"
                               value="{title_escaped}">
                        <div class="field-error" id="title-error"></div>
                        <small class="field-help">A clear, engaging title that summarizes the myth being addressed</small>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                <option value="">Select category...</option>
                                {category_options}
                            </select>
                            <small class="field-help">Optional: Categorize this content for better organization</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="custom_points">Custom Points</label>
                            <input type="number" id="custom_points" name="custom_points" 
                                   placeholder="Leave empty for default points (5)"
                                   min="1" max="100"
                                   class="form-control"
                                   value="{myth_fact.custom_points or ''}">
                            <small class="field-help">Optional: Set custom points for this card (overrides default 5 points)</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="is_featured">Featured Content</label>
                            <div class="checkbox-wrapper">
                                <input type="checkbox" id="is_featured" name="is_featured" value="true" 
                                       class="form-checkbox" {"checked" if myth_fact.is_featured else ""}>
                                <label for="is_featured" class="checkbox-label">Mark as featured content</label>
                            </div>
                            <small class="field-help">Featured content appears prominently in the game</small>
                        </div>
                    </div>
                </div>
                
                <!-- Content Section -->
                <div class="form-section">
                    <h3 class="section-title">Content</h3>
                    
                    <div class="form-group">
                        <label for="myth_content">Myth Statement *</label>
                        <textarea id="myth_content" name="myth_content" required
                                  placeholder="Describe the common myth or misconception..."
                                  class="form-control content-textarea" rows="4">{myth_content_escaped}</textarea>
                        <div class="field-error" id="myth-content-error"></div>
                        <small class="field-help">Clearly state the myth or misconception that needs to be addressed</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="fact_content">Fact Explanation *</label>
                        <textarea id="fact_content" name="fact_content" required
                                  placeholder="Provide the accurate information and explanation..."
                                  class="form-control content-textarea" rows="6">{fact_content_escaped}</textarea>
                        <div class="field-error" id="fact-content-error"></div>
                        <small class="field-help">Provide accurate, educational information that corrects the myth</small>
                    </div>
                    
                    <!-- Card Type Selection -->
                    <div class="form-group">
                        <label for="type" style="font-weight: 700; font-size: 1rem; color: #2d3748;">
                            <i class="fas fa-eye" style="color: #16a34a;"></i> Which Card to Show to User? *
                        </label>
                        <div style="border: 2px solid #cbd5e0; border-radius: 12px; padding: 1.5rem; background: #f7fafc;">
                            <div style="margin-bottom: 1.25rem;">
                                <label style="display: flex; align-items: start; cursor: pointer; padding: 1rem; border-radius: 8px; border: 2px solid #e2e8f0; background: white; transition: all 0.2s;">
                                    <input type="radio" name="type" id="type_myth" value="myth" 
                                           {"checked" if myth_fact.type == "myth" or not myth_fact.type else ""} required
                                           style="margin-top: 0.25rem; margin-right: 0.75rem; cursor: pointer;">
                                    <div style="flex: 1;">
                                        <div style="font-weight: 700; font-size: 1rem; color: #e53e3e; margin-bottom: 0.375rem;">
                                            🔴 Show Myth Card
                                        </div>
                                        <div style="font-size: 0.875rem; color: #718096; line-height: 1.5;">
                                            • Displays the <strong>myth statement</strong> (false claim)<br>
                                            • User should swipe <strong>LEFT</strong> to mark as false<br>
                                            • After answer, shows the fact explanation
                                        </div>
                                    </div>
                                </label>
                            </div>
                            
                            <div>
                                <label style="display: flex; align-items: start; cursor: pointer; padding: 1rem; border-radius: 8px; border: 2px solid #e2e8f0; background: white; transition: all 0.2s;">
                                    <input type="radio" name="type" id="type_fact" value="fact"
                                           {"checked" if myth_fact.type == "fact" else ""} required
                                           style="margin-top: 0.25rem; margin-right: 0.75rem; cursor: pointer;">
                                    <div style="flex: 1;">
                                        <div style="font-weight: 700; font-size: 1rem; color: #16a34a; margin-bottom: 0.375rem;">
                                            🟢 Show Fact Card
                                        </div>
                                        <div style="font-size: 0.875rem; color: #718096; line-height: 1.5;">
                                            • Displays the <strong>fact explanation</strong> (true statement)<br>
                                            • User should swipe <strong>RIGHT</strong> to mark as true<br>
                                            • After answer, shows the myth that people believe
                                        </div>
                                    </div>
                                </label>
                            </div>
                        </div>
                        <small class="field-help" style="margin-top: 0.5rem; display: block;">
                            Current: <span style="padding: 0.25rem 0.75rem; border-radius: 6px; font-weight: 600; background: {"#fee2e2" if myth_fact.type == "myth" or not myth_fact.type else "#dcfce7"}; color: {"#991b1b" if myth_fact.type == "myth" or not myth_fact.type else "#166534"};">
                                {(myth_fact.type or "myth").upper()}
                            </span>
                        </small>
                        <small class="field-help" style="color: #e53e3e; font-weight: 600; margin-top: 0.5rem; display: block;">
                            <i class="fas fa-info-circle"></i> This controls which text appears on the card during gameplay
                        </small>
                    </div>
                </div>
                
                <!-- Media Section -->
                <div class="form-section">
                    <h3 class="section-title">Media</h3>
                    
                    {current_image_html}
                    
                    <div class="form-group">
                        <label for="image">{"Replace" if myth_fact.image_url else "Add"} Supporting Image</label>
                        <input type="file" id="image" name="image" 
                               accept="image/*" class="file-input">
                        <div class="file-upload-area" id="image-upload-area">
                            <i class="fas fa-image"></i>
                            <p>Click to {"replace" if myth_fact.image_url else "upload"} supporting image</p>
                            <small>JPEG, PNG, GIF, WebP (Max: 10MB)</small>
                        </div>
                        <div id="image-preview"></div>
                        <small class="field-help">Optional: Add a relevant image to support the educational content</small>
                    </div>
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Update Myth vs Fact
                        </button>
                        <a href="/admin/myths-facts" class="btn btn-secondary">
                            <i class="fas fa-times"></i>
                            Cancel
                        </a>
                    </div>
                </div>
            </form>
        </div>
        
        <style>
            .current-image {{
                margin-bottom: 1.5rem;
                padding: 1rem;
                background: #f8fafc;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }}
            
            .current-image label {{
                display: block;
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.75rem;
                font-size: 0.95rem;
            }}
            
            .current-image-preview {{
                display: flex;
                align-items: center;
                gap: 1rem;
            }}
            
            .current-image-preview img {{
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
            
            .content-textarea {{
                min-height: 120px;
                resize: vertical;
            }}
            
            .checkbox-wrapper {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-top: 0.5rem;
            }}
            
            .checkbox-label {{
                font-weight: 500;
                color: #4a5568;
                cursor: pointer;
                margin-bottom: 0;
            }}
            
            .form-checkbox {{
                width: 18px;
                height: 18px;
                margin: 0;
            }}
            
            .field-help {{
                display: block;
                color: #718096;
                font-size: 0.875rem;
                margin-top: 0.5rem;
                font-style: italic;
            }}
            
            .form-actions {{
                display: flex;
                gap: 1rem;
                justify-content: flex-start;
            }}
            
            #image-preview {{
                margin-top: 1rem;
            }}
            
            .image-preview-item {{
                position: relative;
                display: inline-block;
                margin-right: 1rem;
            }}
            
            .image-preview-item img {{
                max-width: 200px;
                max-height: 150px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            }}
            
            .image-preview-item .remove-image {{
                position: absolute;
                top: -8px;
                right: -8px;
                background: #e53e3e;
                color: white;
                border: none;
                border-radius: 50%;
                width: 24px;
                height: 24px;
                cursor: pointer;
                font-size: 12px;
            }}
        </style>
        
        <script>
            {get_upload_handlers_js()}
            
            // Initialize file upload handlers
            document.addEventListener('DOMContentLoaded', function() {{
                // File input change handler
                document.getElementById('image').addEventListener('change', function(e) {{
                    handleFileUpload(e, 'image-preview', 'image');
                }});
                
                // Upload area click handler
                document.getElementById('image-upload-area').addEventListener('click', function() {{
                    document.getElementById('image').click();
                }});
            }});
            
            // Remove current image function
            function removeCurrentImage() {{
                document.getElementById('remove_image').value = 'true';
                const currentImageDiv = document.querySelector('.current-image');
                if (currentImageDiv) {{
                    currentImageDiv.style.display = 'none';
                }}
                
                // Update upload area text
                const uploadArea = document.getElementById('image-upload-area');
                if (uploadArea) {{
                    uploadArea.querySelector('p').textContent = 'Click to upload supporting image';
                }}
                
                // Update label
                const imageLabel = document.querySelector('label[for="image"]');
                if (imageLabel) {{
                    imageLabel.textContent = 'Add Supporting Image';
                }}
            }}
            
            // Form submission handler
            function initFormSubmission() {{
                const form = document.getElementById('editMythFactForm');
                if (!form) {{
                    console.error('Form not found: editMythFactForm');
                    return;
                }}
                
                form.addEventListener('submit', async function(e) {{
                    e.preventDefault();
                    
                    console.log('Edit myth vs fact form submission started');
                    
                    // Clear previous errors
                    if (typeof clearAllErrors === 'function') {{
                        clearAllErrors();
                    }}
                    
                    // Set loading state
                    if (typeof setFormLoading === 'function') {{
                        setFormLoading('editMythFactForm', true);
                    }}
                    
                    // Validate form
                    let isValid = true;
                    
                    // Check title
                    const titleField = document.getElementById('title');
                    const titleValue = titleField ? titleField.value.trim() : '';
                    
                    if (!titleValue) {{
                        console.error('Title validation failed - empty title');
                        if (typeof showFieldError === 'function') {{
                            showFieldError('title-error', 'Title is required');
                        }}
                        isValid = false;
                    }}
                    
                    // Check myth content
                    const mythField = document.getElementById('myth_content');
                    const mythValue = mythField ? mythField.value.trim() : '';
                    
                    if (!mythValue) {{
                        console.error('Myth content validation failed - empty content');
                        if (typeof showFieldError === 'function') {{
                            showFieldError('myth-content-error', 'Myth statement is required');
                        }}
                        isValid = false;
                    }}
                    
                    // Check fact content
                    const factField = document.getElementById('fact_content');
                    const factValue = factField ? factField.value.trim() : '';
                    
                    if (!factValue) {{
                        console.error('Fact content validation failed - empty content');
                        if (typeof showFieldError === 'function') {{
                            showFieldError('fact-content-error', 'Fact explanation is required');
                        }}
                        isValid = false;
                    }}
                    
                    if (!isValid) {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('editMythFactForm', false);
                        }}
                        return;
                    }}
                    
                    // Submit form
                    try {{
                        // Create FormData and add all fields
                        const formData = new FormData();
                        
                        formData.append('myth_fact_id', document.querySelector('input[name="myth_fact_id"]').value);
                        formData.append('title', titleValue);
                        formData.append('myth_content', mythValue);
                        formData.append('fact_content', factValue);
                        formData.append('type', document.querySelector('input[name="type"]:checked')?.value || 'myth');
                        formData.append('category_id', document.getElementById('category_id')?.value || '');
                        formData.append('custom_points', document.getElementById('custom_points')?.value || '');
                        formData.append('is_featured', document.getElementById('is_featured')?.checked ? 'true' : 'false');
                        formData.append('remove_image', document.getElementById('remove_image')?.value || 'false');
                        
                        // Add image if present
                        const imageFile = document.getElementById('image');
                        if (imageFile && imageFile.files[0]) {{
                            formData.append('image', imageFile.files[0]);
                        }}
                        
                        console.log('Sending request to /admin/myths-facts/edit/{myth_fact_id}');
                        
                        const response = await fetch('/admin/myths-facts/edit/{myth_fact_id}', {{
                            method: 'POST',
                            body: formData,
                            credentials: 'same-origin'
                        }});
                        
                        console.log('Response status:', response.status);
                        
                        if (response.ok) {{
                            if (typeof showMessage === 'function') {{
                                showMessage('Myth vs fact updated successfully!', 'success');
                            }}
                            setTimeout(() => {{
                                window.location.href = '/admin/myths-facts';
                            }}, 1500);
                        }} else {{
                            const errorText = await response.text();
                            console.error('Server error:', errorText);
                            if (typeof showMessage === 'function') {{
                                showMessage('Server error: ' + response.status, 'error');
                            }}
                        }}
                    }} catch (error) {{
                        console.error('Network error:', error);
                        if (typeof showMessage === 'function') {{
                            showMessage('Network error: ' + error.message, 'error');
                        }}
                    }} finally {{
                        if (typeof setFormLoading === 'function') {{
                            setFormLoading('editMythFactForm', false);
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
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Edit Myth vs Fact", edit_form, "myths-facts"))


@router.post("/myths-facts/edit/{myth_fact_id}")
async def update_myth_fact(request: Request, myth_fact_id: str):
    """Handle myth vs fact update with proper validation and file handling"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        myth_fact_uuid = UUID(myth_fact_id)
        
        # Parse form data with file uploads
        form_data = await request.form()
        
        logger.info(f"Edit form data keys: {list(form_data.keys())}")
        
        # Extract form fields
        title = form_data.get('title', '').strip()
        myth_content = form_data.get('myth_content', '').strip()
        fact_content = form_data.get('fact_content', '').strip()
        card_type = form_data.get('type', 'myth').strip()  # ✅ NEW: Get selected card type
        category_id = form_data.get('category_id', '').strip()
        is_featured = form_data.get('is_featured') == 'true'
        remove_image = form_data.get('remove_image') == 'true'
        custom_points = form_data.get('custom_points', '').strip()
        
        # Validate required fields
        if not title:
            return JSONResponse({"success": False, "error": "Title is required"}, status_code=400)
        
        if not myth_content:
            return JSONResponse({"success": False, "error": "Myth statement is required"}, status_code=400)
        
        if not fact_content:
            return JSONResponse({"success": False, "error": "Fact explanation is required"}, status_code=400)
        
        async with get_db_session() as db:
            # Get existing myth fact
            result = await db.execute(
                select(MythFact).where(MythFact.id == myth_fact_uuid)
            )
            myth_fact = result.scalar_one_or_none()
            
            if not myth_fact:
                return JSONResponse({"success": False, "error": "Myth vs fact not found"}, status_code=404)
            
            # Validate category if provided
            category_uuid = None
            if category_id:
                try:
                    category_uuid = UUID(category_id)
                    category_result = await db.execute(
                        select(Category).where(Category.id == category_uuid)
                    )
                    if not category_result.scalar_one_or_none():
                        return JSONResponse({"success": False, "error": "Category not found"}, status_code=400)
                except ValueError:
                    return JSONResponse({"success": False, "error": "Invalid category ID"}, status_code=400)
            
            # Handle custom points validation
            custom_points_value = None
            if custom_points:
                try:
                    custom_points_value = int(custom_points)
                    if custom_points_value < 1 or custom_points_value > 100:
                        return JSONResponse({"success": False, "error": "Custom points must be between 1 and 100"}, status_code=400)
                except ValueError:
                    return JSONResponse({"success": False, "error": "Custom points must be a valid number"}, status_code=400)
            
            # Handle image updates
            new_image_url = myth_fact.image_url  # Keep existing by default
            
            # Remove current image if requested
            if remove_image:
                new_image_url = None
            
            # Handle new image upload
            image_file = form_data.get('image')
            if image_file and hasattr(image_file, 'filename') and image_file.filename:
                try:
                    file_info = await file_upload_service.upload_file(image_file)
                    new_image_url = file_info['file_url']
                    logger.info(f"Uploaded new image: {new_image_url}")
                except Exception as upload_error:
                    logger.error(f"Image upload error: {upload_error}")
                    return JSONResponse({"success": False, "error": f"Image upload failed: {str(upload_error)}"}, status_code=400)
            
            # Update myth fact fields
            myth_fact.title = title
            myth_fact.myth_content = myth_content
            myth_fact.fact_content = fact_content
            myth_fact.type = card_type  # ✅ NEW: Update card type
            myth_fact.category_id = category_uuid
            myth_fact.is_featured = is_featured
            myth_fact.image_url = new_image_url
            myth_fact.custom_points = custom_points_value
            
            await db.commit()
            await db.refresh(myth_fact)
            
            logger.info(f"Updated myth vs fact with ID: {myth_fact.id}")
            
            return RedirectResponse(url="/admin/myths-facts?updated=1", status_code=302)
            
    except ValueError:
        return JSONResponse({"success": False, "error": "Invalid myth vs fact ID"}, status_code=400)
    except Exception as e:
        import traceback
        logger.error(f"Myth vs fact update error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)

@router.delete("/myths-facts/delete/{myth_fact_id}")
async def delete_myth_fact(request: Request, myth_fact_id: str):
    """Delete a myth vs fact entry with proper authorization checks"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse({"success": False, "error": "Authentication required"}, status_code=401)
    
    try:
        myth_fact_uuid = UUID(myth_fact_id)
        
        async with get_db_session() as db:
            # Get existing myth fact
            result = await db.execute(
                select(MythFact).where(MythFact.id == myth_fact_uuid)
            )
            myth_fact = result.scalar_one_or_none()
            
            if not myth_fact:
                return JSONResponse({"success": False, "error": "Myth vs fact not found"}, status_code=404)
            
            # Store title for logging
            myth_fact_title = myth_fact.title
            
            # Delete the myth fact (hard delete)
            await db.delete(myth_fact)
            await db.commit()
            
            logger.info(f"Deleted myth vs fact: {myth_fact_title} (ID: {myth_fact_id})")
            
            return JSONResponse({
                "success": True, 
                "message": f"Myth vs fact '{myth_fact_title}' deleted successfully"
            })
            
    except ValueError:
        return JSONResponse({"success": False, "error": "Invalid myth vs fact ID"}, status_code=400)
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting myth vs fact {myth_fact_id}: {e}")
        return JSONResponse({"success": False, "error": "Database error occurred"}, status_code=500)
    except Exception as e:
        import traceback
        logger.error(f"Myth vs fact deletion error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)


@router.get("/myths-facts/view/{myth_fact_id}", response_class=HTMLResponse)
async def view_myth_fact(request: Request, myth_fact_id: str):
    """View a single myth vs fact entry (optional read-only view)"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        myth_fact_uuid = UUID(myth_fact_id)
        async with get_db_session() as db:
            result = await db.execute(
                select(MythFact).options(
                    selectinload(MythFact.category)
                ).where(MythFact.id == myth_fact_uuid)
            )
            myth_fact = result.scalar_one_or_none()
            
            if not myth_fact:
                return HTMLResponse(content=create_html_page("Myth vs Fact Not Found", 
                    "<div class='message error'>Myth vs fact not found</div>", "myths-facts"))
    
    except ValueError:
        return HTMLResponse(content=create_html_page("Invalid ID", 
            "<div class='message error'>Invalid myth vs fact ID</div>", "myths-facts"))
    except Exception as e:
        logger.error(f"Error loading myth vs fact for view: {e}")
        return HTMLResponse(content=create_html_page("Error", 
            f"<div class='message error'>Error loading myth vs fact: {str(e)}</div>", "myths-facts"))
    
    # Format content for display
    import html
    title_display = html.escape(myth_fact.title)
    myth_content_display = html.escape(myth_fact.myth_content).replace('\n', '<br>')
    fact_content_display = html.escape(myth_fact.fact_content).replace('\n', '<br>')
    
    # Image display
    image_html = ""
    if myth_fact.image_url:
        image_html = f"""
        <div class="image-section">
            <h4>Supporting Image</h4>
            <img src="{myth_fact.image_url}" alt="Supporting image" class="content-image">
        </div>
        """
    
    # Category display
    category_display = myth_fact.category.name if myth_fact.category else "No Category"
    
    # Featured badge
    featured_badge = '<span class="badge badge-success">Featured</span>' if myth_fact.is_featured else '<span class="badge badge-secondary">Regular</span>'
    
    view_content = f"""
        <div class="page-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 class="page-title">{title_display}</h1>
                    <p class="page-subtitle">Myth vs Fact Details</p>
                </div>
                <div class="header-actions">
                    <a href="/admin/myths-facts/edit/{myth_fact.id}" class="btn btn-primary">
                        <i class="fas fa-edit"></i> Edit
                    </a>
                    <a href="/admin/myths-facts" class="btn btn-secondary">
                        <i class="fas fa-arrow-left"></i> Back to List
                    </a>
                </div>
            </div>
        </div>
        
        <div class="content-container">
            <div class="content-section">
                <div class="meta-info">
                    <div class="meta-item">
                        <strong>Category:</strong> {category_display}
                    </div>
                    <div class="meta-item">
                        <strong>Status:</strong> {featured_badge}
                    </div>
                    <div class="meta-item">
                        <strong>Created:</strong> {myth_fact.created_at.strftime('%Y-%m-%d %H:%M') if myth_fact.created_at else 'Unknown'}
                    </div>
                </div>
            </div>
            
            <div class="content-section">
                <h3 class="section-title">
                    <i class="fas fa-exclamation-triangle text-warning"></i>
                    Myth Statement
                </h3>
                <div class="content-box myth-box">
                    {myth_content_display}
                </div>
            </div>
            
            <div class="content-section">
                <h3 class="section-title">
                    <i class="fas fa-check-circle text-success"></i>
                    Fact Explanation
                </h3>
                <div class="content-box fact-box">
                    {fact_content_display}
                </div>
            </div>
            
            {image_html}
        </div>
        
        <style>
            .content-container {{
                background: white;
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
            }}
            
            .header-actions {{
                display: flex;
                gap: 1rem;
            }}
            
            .content-section {{
                margin-bottom: 2rem;
            }}
            
            .meta-info {{
                display: flex;
                gap: 2rem;
                padding: 1rem;
                background: #f8fafc;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }}
            
            .meta-item {{
                font-size: 0.95rem;
            }}
            
            .section-title {{
                font-size: 1.25rem;
                font-weight: 700;
                color: #2d3748;
                margin-bottom: 1rem;
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }}
            
            .content-box {{
                padding: 1.5rem;
                border-radius: 12px;
                border: 2px solid;
                font-size: 1rem;
                line-height: 1.6;
            }}
            
            .myth-box {{
                background: #fef5e7;
                border-color: #f6ad55;
                color: #744210;
            }}
            
            .fact-box {{
                background: #f0fff4;
                border-color: #48bb78;
                color: #22543d;
            }}
            
            .image-section {{
                margin-top: 2rem;
            }}
            
            .image-section h4 {{
                font-size: 1.125rem;
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 1rem;
            }}
            
            .content-image {{
                max-width: 100%;
                height: auto;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            }}
            
            .badge {{
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .badge-success {{
                background: #c6f6d5;
                color: #22543d;
            }}
            
            .badge-secondary {{
                background: #e2e8f0;
                color: #4a5568;
            }}
            
            .text-warning {{
                color: #d69e2e;
            }}
            
            .text-success {{
                color: #38a169;
            }}
            
            @media (max-width: 768px) {{
                .header-actions {{
                    flex-direction: column;
                }}
                
                .meta-info {{
                    flex-direction: column;
                    gap: 0.5rem;
                }}
            }}
        </style>
    """
    
    return HTMLResponse(content=create_html_page("View Myth vs Fact", view_content, "myths-facts"))