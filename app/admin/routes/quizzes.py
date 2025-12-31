"""
Quiz management routes for admin panel
"""

from fastapi import APIRouter, Request, Form, File, UploadFile, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID, uuid4
from typing import Optional, List
import logging
import json

from app.models import Quiz, UserQuizResult
from app.models.category import Category
from app.models.user import User
from app.admin.templates.base import create_html_page
from app.admin.templates.editor import get_quill_editor_html, get_quill_editor_js, get_upload_handlers_js
from app.db.database import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/quizzes", response_class=HTMLResponse)
async def quiz_list(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    category_id: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[int] = Query(None, ge=1, le=3, description="Filter by difficulty"),
    active_only: bool = Query(False, description="Show only active quizzes")
):
    """Admin list view for quizzes with pagination and search"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Build base query
            query = select(Quiz).options(
                selectinload(Quiz.category)
            )
            
            # Apply filters
            filters = []
            
            # Search filter
            if search and search.strip():
                search_term = f"%{search.strip()}%"
                filters.append(
                    or_(
                        Quiz.title.ilike(search_term),
                        Quiz.description.ilike(search_term)
                    )
                )
            
            # Category filter
            if category_id and category_id.strip():
                try:
                    category_uuid = UUID(category_id)
                    filters.append(Quiz.category_id == category_uuid)
                except ValueError:
                    pass  # Invalid UUID, ignore filter
            
            # Difficulty filter
            if difficulty:
                filters.append(Quiz.difficulty_level == difficulty)
            
            # Active filter
            if active_only:
                filters.append(Quiz.is_active == True)
            
            # Apply filters to query
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count for pagination
            count_query = select(func.count(Quiz.id))
            if filters:
                count_query = count_query.where(and_(*filters))
            
            total_result = await db.execute(count_query)
            total = total_result.scalar()
            
            # Apply pagination and ordering
            offset = (page - 1) * limit
            query = query.order_by(desc(Quiz.created_at)).offset(offset).limit(limit)
            
            # Execute query
            result = await db.execute(query)
            quizzes = result.scalars().all()
            
            # Get categories for filter dropdown
            categories_result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = categories_result.scalars().all()
            
    except Exception as e:
        logger.error(f"Error loading quiz list: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Error", 
                f"<div class='message error'>Error loading quizzes: {str(e)}</div>", 
                "quizzes"
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
    
    # Generate difficulty options
    difficulty_options = '<option value="">All Difficulties</option>'
    for diff_level in [1, 2, 3]:
        diff_name = {1: "Easy", 2: "Medium", 3: "Hard"}[diff_level]
        selected = "selected" if difficulty == diff_level else ""
        difficulty_options += f'<option value="{diff_level}" {selected}>{diff_name}</option>'
    
    # Generate table rows
    table_rows = ""
    for quiz in quizzes:
        active_badge = '<span class="badge badge-success">Active</span>' if quiz.is_active else '<span class="badge badge-secondary">Inactive</span>'
        category_name = quiz.category.name if quiz.category else 'No Category'
        difficulty_name = {1: "Easy", 2: "Medium", 3: "Hard"}.get(quiz.difficulty_level, "Unknown")
        
        # Calculate quiz stats
        question_count = len(quiz.questions) if quiz.questions else 0
        total_points = sum(q.get('points', 1) for q in quiz.questions) if quiz.questions else 0
        
        # Truncate description for display
        description_preview = (quiz.description[:100] + '...') if quiz.description and len(quiz.description) > 100 else (quiz.description or 'No description')
        
        # --- FIX START: Precompute HTML with backslashes outside f-string ---
        time_limit_html = f'<div><strong>{quiz.time_limit}</strong> min</div>' if quiz.time_limit else '<div>No time limit</div>'
        toggle_btn_style = 'margin-left: 0.5rem;'
        toggle_btn_class = 'btn-warning' if quiz.is_active else 'btn-success'
        toggle_icon = 'eye-slash' if quiz.is_active else 'eye'
        toggle_text = 'Deactivate' if quiz.is_active else 'Activate'
        # --- FIX END ---
        
        table_rows += f"""
        <tr>
            <td>
                <input type="checkbox" class="quiz-checkbox" value="{quiz.id}" onchange="updateBulkActions()">
            </td>
            <td>
                <div class="content-title">{quiz.title}</div>
                <div class="content-meta">
                    <small class="text-muted">Created: {quiz.created_at.strftime('%Y-%m-%d %H:%M') if quiz.created_at else 'Unknown'}</small>
                </div>
                <div class="content-preview">{description_preview}</div>
            </td>
            <td>{category_name}</td>
            <td>
                <span class="difficulty-badge difficulty-{quiz.difficulty_level}">{difficulty_name}</span>
            </td>
            <td>
                <div class="quiz-stats">
                    <div><strong>{question_count}</strong> questions</div>
                    <div><strong>{total_points}</strong> points</div>
                    {time_limit_html}
                </div>
            </td>
            <td>
                {active_badge}
                <button onclick="toggleQuizActive('{quiz.id}', {str(quiz.is_active).lower()})" 
                        class="btn btn-xs {toggle_btn_class}" 
                        style="{toggle_btn_style}">
                    <i class="fas fa-{toggle_icon}"></i>
                    {toggle_text}
                </button>
            </td>
            <td>
                <div class="action-buttons">
                    <a href="/admin/quizzes/edit/{quiz.id}" class="btn btn-sm btn-primary">
                        <i class="fas fa-edit"></i> Edit
                    </a>
                    <button onclick="confirmDelete('{quiz.id}', '{quiz.title}')" class="btn btn-sm btn-danger">
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
            pagination_html += f'<a href="?page={page-1}&limit={limit}&search={search or ""}&category_id={category_id or ""}&difficulty={difficulty or ""}&active_only={active_only}" class="btn btn-sm btn-secondary">Previous</a>'
        
        # Page numbers
        start_page = max(1, page - 2)
        end_page = min(total_pages, page + 2)
        
        for p in range(start_page, end_page + 1):
            active_class = "btn-primary" if p == page else "btn-secondary"
            pagination_html += f'<a href="?page={p}&limit={limit}&search={search or ""}&category_id={category_id or ""}&difficulty={difficulty or ""}&active_only={active_only}" class="btn btn-sm {active_class}">{p}</a>'
        
        # Next button
        if has_next:
            pagination_html += f'<a href="?page={page+1}&limit={limit}&search={search or ""}&category_id={category_id or ""}&difficulty={difficulty or ""}&active_only={active_only}" class="btn btn-sm btn-secondary">Next</a>'
        
        pagination_html += """
            </div>
        </div>
        """
    
    list_content = f"""
        <div class="page-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 class="page-title">Quizzes</h1>
                    <p class="page-subtitle">Manage interactive wildlife quizzes</p>
                </div>
                <a href="/admin/quizzes/create" class="btn btn-primary">
                    <i class="fas fa-plus"></i> Create New Quiz
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
                                   placeholder="Search quiz titles and descriptions..." class="form-control">
                        </div>
                        <div class="filter-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                {category_options}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label for="difficulty">Difficulty</label>
                            <select id="difficulty" name="difficulty" class="form-control">
                                {difficulty_options}
                            </select>
                        </div>
                        <div class="filter-group">
                            <label for="active_only">Active Only</label>
                            <input type="checkbox" id="active_only" name="active_only" value="true" 
                                   {"checked" if active_only else ""} class="form-checkbox">
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
                        <a href="/admin/quizzes" class="btn btn-secondary">
                            <i class="fas fa-times"></i> Clear
                        </a>
                    </div>
                </form>
            </div>
            
            <!-- Bulk Actions -->
            <div id="bulk-actions" class="bulk-actions" style="display: none;">
                <div class="bulk-actions-content">
                    <span id="selected-count">0 selected</span>
                    <div class="bulk-buttons">
                        <button onclick="performBulkAction('activate')" class="btn btn-sm btn-success">
                            <i class="fas fa-eye"></i> Activate
                        </button>
                        <button onclick="performBulkAction('deactivate')" class="btn btn-sm btn-warning">
                            <i class="fas fa-eye-slash"></i> Deactivate
                        </button>
                        <button onclick="confirmBulkDelete()" class="btn btn-sm btn-danger">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                        <button onclick="clearSelection()" class="btn btn-sm btn-secondary">
                            <i class="fas fa-times"></i> Clear
                        </button>
                    </div>
                </div>
            </div>
            
            <!-- Results Table -->
            <div class="table-container">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th>
                                <input type="checkbox" id="select-all" onchange="toggleSelectAll()">
                            </th>
                            <th>Quiz Details</th>
                            <th>Category</th>
                            <th>Difficulty</th>
                            <th>Stats</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows if table_rows else '<tr><td colspan="7" class="text-center">No quizzes found</td></tr>'}
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
                <p class="text-danger">This action will also delete all user results for this quiz and cannot be undone.</p>
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
                grid-template-columns: 2fr 1fr 1fr auto 100px;
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
                margin-bottom: 0.5rem;
            }}
            
            .content-preview {{
                font-size: 0.9rem;
                line-height: 1.4;
                color: #4a5568;
            }}
            
            .difficulty-badge {{
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .difficulty-1 {{
                background: #c6f6d5;
                color: #22543d;
            }}
            
            .difficulty-2 {{
                background: #fed7aa;
                color: #9c4221;
            }}
            
            .difficulty-3 {{
                background: #fecaca;
                color: #991b1b;
            }}
            
            .quiz-stats {{
                font-size: 0.875rem;
                line-height: 1.4;
            }}
            
            .quiz-stats div {{
                margin-bottom: 0.25rem;
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
            
            .bulk-actions {{
                background: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }}
            
            .bulk-actions-content {{
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .bulk-buttons {{
                display: flex;
                gap: 0.5rem;
            }}
            
            .btn-xs {{
                padding: 0.25rem 0.5rem;
                font-size: 0.75rem;
            }}
            
            .btn-warning {{
                background: linear-gradient(135deg, #d69e2e 0%, #b7791f 100%);
                color: white;
            }}
            
            .btn-warning:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(214, 158, 46, 0.3);
            }}
            
            .quiz-checkbox {{
                width: 18px;
                height: 18px;
                cursor: pointer;
            }}
            
            #select-all {{
                width: 18px;
                height: 18px;
                cursor: pointer;
            }}
            
            .message {{
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                border: 1px solid;
            }}
            
            .message.success {{
                background: #f0fff4;
                color: #22543d;
                border-color: #9ae6b4;
            }}
            
            .message.error {{
                background: #fed7d7;
                color: #742a2a;
                border-color: #feb2b2;
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
                    const response = await fetch(`/admin/quizzes/delete/${{deleteItemId}}`, {{
                        method: 'DELETE',
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        showMessage('Quiz deleted successfully!', 'success');
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 1500);
                    }} else {{
                        const errorText = await response.text();
                        showMessage('Error deleting quiz: ' + response.status, 'error');
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
            
            // Message display function
            function showMessage(message, type) {{
                const container = document.getElementById('message-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${{type}}`;
                messageDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>${{message}}</span>
                        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; cursor: pointer;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                container.appendChild(messageDiv);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {{
                    if (messageDiv.parentElement) {{
                        messageDiv.remove();
                    }}
                }}, 5000);
            }}
            
            // Bulk actions functionality
            function toggleSelectAll() {{
                const selectAll = document.getElementById('select-all');
                const checkboxes = document.querySelectorAll('.quiz-checkbox');
                
                checkboxes.forEach(checkbox => {{
                    checkbox.checked = selectAll.checked;
                }});
                
                updateBulkActions();
            }}
            
            function updateBulkActions() {{
                const checkboxes = document.querySelectorAll('.quiz-checkbox:checked');
                const bulkActions = document.getElementById('bulk-actions');
                const selectedCount = document.getElementById('selected-count');
                const selectAll = document.getElementById('select-all');
                
                const count = checkboxes.length;
                selectedCount.textContent = `${{count}} selected`;
                
                if (count > 0) {{
                    bulkActions.style.display = 'block';
                }} else {{
                    bulkActions.style.display = 'none';
                }}
                
                // Update select all checkbox state
                const allCheckboxes = document.querySelectorAll('.quiz-checkbox');
                if (count === 0) {{
                    selectAll.indeterminate = false;
                    selectAll.checked = false;
                }} else if (count === allCheckboxes.length) {{
                    selectAll.indeterminate = false;
                    selectAll.checked = true;
                }} else {{
                    selectAll.indeterminate = true;
                }}
            }}
            
            function clearSelection() {{
                const checkboxes = document.querySelectorAll('.quiz-checkbox');
                const selectAll = document.getElementById('select-all');
                
                checkboxes.forEach(checkbox => {{
                    checkbox.checked = false;
                }});
                selectAll.checked = false;
                selectAll.indeterminate = false;
                
                updateBulkActions();
            }}
            
            function getSelectedQuizIds() {{
                const checkboxes = document.querySelectorAll('.quiz-checkbox:checked');
                return Array.from(checkboxes).map(cb => cb.value);
            }}
            
            async function performBulkAction(action) {{
                const quizIds = getSelectedQuizIds();
                
                if (quizIds.length === 0) {{
                    showMessage('No quizzes selected', 'error');
                    return;
                }}
                
                try {{
                    const formData = new FormData();
                    formData.append('action', action);
                    formData.append('quiz_ids', quizIds.join(','));
                    
                    const response = await fetch('/admin/quizzes/bulk-action', {{
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    }});
                    
                    const result = await response.json();
                    
                    if (response.ok) {{
                        showMessage(result.message, 'success');
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 1500);
                    }} else {{
                        showMessage(result.error || 'Error performing bulk action', 'error');
                    }}
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
                }}
            }}
            
            function confirmBulkDelete() {{
                const quizIds = getSelectedQuizIds();
                
                if (quizIds.length === 0) {{
                    showMessage('No quizzes selected', 'error');
                    return;
                }}
                
                if (confirm(`Are you sure you want to delete ${{quizIds.length}} quiz(es)? This action cannot be undone and will also delete all user results.`)) {{
                    performBulkAction('delete');
                }}
            }}
            
            // Individual quiz toggle
            async function toggleQuizActive(quizId, currentStatus) {{
                try {{
                    const response = await fetch(`/admin/quizzes/toggle-active/${{quizId}}`, {{
                        method: 'POST',
                        credentials: 'same-origin'
                    }});
                    
                    const result = await response.json();
                    
                    if (response.ok) {{
                        showMessage(result.message, 'success');
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 1000);
                    }} else {{
                        showMessage(result.error || 'Error updating quiz status', 'error');
                    }}
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
                }}
            }}
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Quizzes", list_content, "quizzes"))


@router.get("/quizzes/create", response_class=HTMLResponse)
async def create_quiz_form(request: Request):
    """Create quiz form with dynamic question builder"""
    
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
            <h1 class="page-title">Create Quiz</h1>
            <p class="page-subtitle">Create an interactive wildlife quiz with multiple questions</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="createQuizForm" class="admin-form">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-group">
                        <label for="title">Quiz Title *</label>
                        <input type="text" id="title" name="title" required 
                               placeholder="Enter a compelling title for this quiz" 
                               maxlength="500"
                               class="form-control">
                        <div class="field-error" id="title-error"></div>
                        <small class="field-help">A clear, engaging title that describes the quiz topic</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea id="description" name="description"
                                  placeholder="Provide a brief description of what this quiz covers..."
                                  class="form-control" rows="3"></textarea>
                        <small class="field-help">Optional: Brief description to help users understand the quiz content</small>
                    </div>
                    
                    <!-- Cover Image Upload -->
                    <div class="form-group">
                        <label for="cover_image">Cover Image</label>
                        <div class="file-upload-container">
                            <div class="file-upload-area" onclick="document.getElementById('cover_image').click()">
                                <i class="fas fa-cloud-upload-alt"></i>
                                <p>Click to upload cover image</p>
                                <small>Recommended: 1200x600px, JPG or PNG, max 5MB</small>
                            </div>
                            <input type="file" id="cover_image" name="cover_image" 
                                   accept="image/*" class="file-input" 
                                   onchange="handleImageUpload(this, 'cover-image-preview')">
                            <div id="cover-image-preview" class="image-preview" style="display: none;">
                                <img id="cover-image-img" src="" alt="Cover preview" style="max-width: 300px; max-height: 200px; border-radius: 8px;">
                                <button type="button" onclick="removeImage('cover_image', 'cover-image-preview')" class="btn btn-secondary btn-sm" style="margin-top: 0.5rem;">
                                    <i class="fas fa-times"></i> Remove
                                </button>
                            </div>
                        </div>
                        <small class="field-help">Optional: Upload an engaging cover image for the quiz</small>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                <option value="">Select category...</option>
                                {category_options}
                            </select>
                            <small class="field-help">Optional: Categorize this quiz for better organization</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="difficulty_level">Difficulty Level *</label>
                            <select id="difficulty_level" name="difficulty_level" required class="form-control">
                                <option value="1">Easy</option>
                                <option value="2">Medium</option>
                                <option value="3">Hard</option>
                            </select>
                            <small class="field-help">Choose the appropriate difficulty level for your audience</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="time_limit">Time Limit (minutes)</label>
                            <input type="number" id="time_limit" name="time_limit" 
                                   min="1" max="120" placeholder="Optional"
                                   class="form-control">
                            <small class="field-help">Optional: Set a time limit for the entire quiz</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="credits_on_completion">Credits on Completion</label>
                            <input type="number" id="credits_on_completion" name="credits_on_completion" 
                                   value="10" min="0" max="50"
                                   class="form-control">
                            <small class="field-help">Credits awarded to users when they complete this quiz (business-safe: 10 default)</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="is_active">Status</label>
                            <div class="checkbox-wrapper">
                                <input type="checkbox" id="is_active" name="is_active" value="true" checked class="form-checkbox">
                                <label for="is_active" class="checkbox-label">Active (visible to users)</label>
                            </div>
                            <small class="field-help">Uncheck to save as draft</small>
                        </div>
                    </div>
                </div>
                
                <!-- Questions Section -->
                <div class="form-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 class="section-title">Questions</h3>
                        <button type="button" onclick="addQuestion()" class="btn btn-secondary">
                            <i class="fas fa-plus"></i> Add Question
                        </button>
                    </div>
                    
                    <div id="questions-container">
                        <!-- Questions will be added dynamically -->
                    </div>
                    
                    <div id="no-questions-message" class="text-center" style="padding: 2rem; color: #718096;">
                        <i class="fas fa-question-circle" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                        <p style="font-size: 1.125rem; font-weight: 500;">No questions added yet</p>
                        <p style="font-size: 0.95rem;">Click "Add Question" to start building your quiz</p>
                    </div>
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Create Quiz
                        </button>
                        <a href="/admin/quizzes" class="btn btn-secondary">
                            <i class="fas fa-times"></i>
                            Cancel
                        </a>
                    </div>
                </div>
            </form>
        </div>
        
        <style>
            .form-container {{
                background: white;
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .form-section {{
                margin-bottom: 2rem;
                padding: 1.5rem;
                background: #f8fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            .section-title {{
                color: #2d3748;
                margin-bottom: 1rem;
                font-size: 1.25rem;
                font-weight: 700;
            }}
            
            .form-group {{
                margin-bottom: 1.5rem;
            }}
            
            .form-row {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr 1fr;
                gap: 1rem;
            }}
            
            .form-group label {{
                display: block;
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.5rem;
            }}
            
            .form-control {{
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 0.95rem;
                transition: border-color 0.2s, box-shadow 0.2s;
            }}
            
            .form-control:focus {{
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
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
            
            .field-error {{
                color: #e53e3e;
                font-size: 0.875rem;
                margin-top: 0.5rem;
                display: none;
            }}
            
            .form-actions {{
                display: flex;
                gap: 1rem;
                justify-content: flex-start;
            }}
            
            .question-card {{
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                position: relative;
            }}
            
            .question-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }}
            
            .question-number {{
                font-weight: 700;
                color: #3b82f6;
                font-size: 1.1rem;
            }}
            
            .question-actions {{
                display: flex;
                gap: 0.5rem;
            }}
            
            .btn-icon {{
                padding: 0.5rem;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .option-group {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 0.75rem;
            }}
            
            .option-input {{
                flex: 1;
            }}
            
            .correct-radio {{
                width: 20px;
                height: 20px;
            }}
            
            .remove-option {{
                background: #fee2e2;
                color: #dc2626;
                border: 1px solid #fecaca;
                padding: 0.5rem;
                border-radius: 6px;
                cursor: pointer;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .remove-option:hover {{
                background: #fecaca;
            }}
            
            .add-option {{
                background: #eff6ff;
                color: #2563eb;
                border: 1px solid #dbeafe;
                padding: 0.5rem 1rem;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.875rem;
            }}
            
            .add-option:hover {{
                background: #dbeafe;
            }}
            
            .text-center {{
                text-align: center;
            }}
            
            /* Image Upload Styles */
            .file-upload-container {{
                margin-top: 0.5rem;
            }}
            
            .file-upload-area {{
                border: 2px dashed #cbd5e0;
                border-radius: 12px;
                padding: 2rem;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                background: #f8fafc;
            }}
            
            .file-upload-area:hover {{
                border-color: #3b82f6;
                background: #eff6ff;
            }}
            
            .file-upload-area i {{
                font-size: 2rem;
                color: #3b82f6;
                margin-bottom: 0.5rem;
                display: block;
            }}
            
            .file-upload-area p {{
                font-weight: 600;
                color: #374151;
                margin-bottom: 0.25rem;
            }}
            
            .file-upload-area small {{
                color: #6b7280;
            }}
            
            .file-input {{
                display: none;
            }}
            
            .image-preview {{
                text-align: center;
                margin-top: 1rem;
            }}
            
            .current-image-preview {{
                text-align: center;
                margin-bottom: 1rem;
                padding: 1rem;
                background: #f8fafc;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }}
            
            @media (max-width: 768px) {{
                .form-row {{
                    grid-template-columns: 1fr;
                }}
                
                .question-header {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 1rem;
                }}
            }}
        </style>
        
        <script>
            let questionCount = 0;
            
            function addQuestion() {{
                questionCount++;
                const container = document.getElementById('questions-container');
                const noQuestionsMessage = document.getElementById('no-questions-message');
                
                const questionHtml = `
                    <div class="question-card" id="question-${{questionCount}}">
                        <div class="question-header">
                            <span class="question-number">Question ${{questionCount}}</span>
                            <div class="question-actions">
                                <button type="button" onclick="removeQuestion(${{questionCount}})" class="btn btn-danger btn-icon">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="question_${{questionCount}}_text">Question Text *</label>
                            <textarea id="question_${{questionCount}}_text" name="questions[${{questionCount}}][question]" required
                                      placeholder="Enter your question here..."
                                      class="form-control" rows="2"></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Answer Options *</label>
                            <div id="options_${{questionCount}}">
                                <div class="option-group">
                                    <input type="radio" name="questions[${{questionCount}}][correct_answer]" value="0" class="correct-radio" required>
                                    <input type="text" name="questions[${{questionCount}}][options][]" placeholder="Option A" class="form-control option-input" required>
                                    <button type="button" onclick="removeOption(this)" class="remove-option" style="display: none;">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <div class="option-group">
                                    <input type="radio" name="questions[${{questionCount}}][correct_answer]" value="1" class="correct-radio" required>
                                    <input type="text" name="questions[${{questionCount}}][options][]" placeholder="Option B" class="form-control option-input" required>
                                    <button type="button" onclick="removeOption(this)" class="remove-option" style="display: none;">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                            </div>
                            <button type="button" onclick="addOption(${{questionCount}})" class="add-option">
                                <i class="fas fa-plus"></i> Add Option
                            </button>
                            <small class="field-help">Select the correct answer by clicking the radio button next to it</small>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="question_${{questionCount}}_explanation">Explanation</label>
                                <textarea id="question_${{questionCount}}_explanation" name="questions[${{questionCount}}][explanation]"
                                          placeholder="Explain why this is the correct answer..."
                                          class="form-control" rows="2"></textarea>
                                <small class="field-help">Optional: Provide educational explanation</small>
                            </div>
                            
                            <div class="form-group">
                                <label for="question_${{questionCount}}_points">Points</label>
                                <input type="number" id="question_${{questionCount}}_points" name="questions[${{questionCount}}][points]" 
                                       value="1" min="1" max="10" class="form-control">
                                <small class="field-help">Points awarded for correct answer</small>
                            </div>
                            
                            <div class="form-group">
                                <label for="question_${{questionCount}}_time_limit">Time Limit (seconds)</label>
                                <input type="number" id="question_${{questionCount}}_time_limit" name="questions[${{questionCount}}][time_limit]" 
                                       min="10" max="300" placeholder="Optional" class="form-control">
                                <small class="field-help">Optional: Time limit for this question</small>
                            </div>
                        </div>
                    </div>
                `;
                
                container.insertAdjacentHTML('beforeend', questionHtml);
                noQuestionsMessage.style.display = 'none';
                updateOptionVisibility(questionCount);
            }}
            
            function removeQuestion(questionId) {{
                const questionElement = document.getElementById(`question-${{questionId}}`);
                if (questionElement) {{
                    questionElement.remove();
                }}
                
                // Show no questions message if no questions left
                const container = document.getElementById('questions-container');
                const noQuestionsMessage = document.getElementById('no-questions-message');
                if (container.children.length === 0) {{
                    noQuestionsMessage.style.display = 'block';
                }}
                
                // Renumber remaining questions
                renumberQuestions();
            }}
            
            function addOption(questionId) {{
                const optionsContainer = document.getElementById(`options_${{questionId}}`);
                const optionCount = optionsContainer.children.length;
                const optionLetter = String.fromCharCode(65 + optionCount); // A, B, C, D, etc.
                
                if (optionCount >= 6) {{
                    alert('Maximum 6 options allowed per question');
                    return;
                }}
                
                const optionHtml = `
                    <div class="option-group">
                        <input type="radio" name="questions[${{questionId}}][correct_answer]" value="${{optionCount}}" class="correct-radio" required>
                        <input type="text" name="questions[${{questionId}}][options][]" placeholder="Option ${{optionLetter}}" class="form-control option-input" required>
                        <button type="button" onclick="removeOption(this)" class="remove-option">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                
                optionsContainer.insertAdjacentHTML('beforeend', optionHtml);
                updateOptionVisibility(questionId);
            }}
            
            function removeOption(button) {{
                const optionGroup = button.parentElement;
                const optionsContainer = optionGroup.parentElement;
                
                if (optionsContainer.children.length <= 2) {{
                    alert('Minimum 2 options required per question');
                    return;
                }}
                
                optionGroup.remove();
                
                // Update radio button values and option visibility
                const questionId = optionsContainer.id.split('_')[1];
                updateRadioValues(questionId);
                updateOptionVisibility(questionId);
            }}
            
            function updateRadioValues(questionId) {{
                const optionsContainer = document.getElementById(`options_${{questionId}}`);
                const radioButtons = optionsContainer.querySelectorAll('input[type="radio"]');
                
                radioButtons.forEach((radio, index) => {{
                    radio.value = index;
                }});
            }}
            
            function updateOptionVisibility(questionId) {{
                const optionsContainer = document.getElementById(`options_${{questionId}}`);
                const removeButtons = optionsContainer.querySelectorAll('.remove-option');
                
                removeButtons.forEach(button => {{
                    button.style.display = optionsContainer.children.length > 2 ? 'flex' : 'none';
                }});
            }}
            
            function renumberQuestions() {{
                const questionCards = document.querySelectorAll('.question-card');
                questionCards.forEach((card, index) => {{
                    const questionNumber = index + 1;
                    const numberSpan = card.querySelector('.question-number');
                    if (numberSpan) {{
                        numberSpan.textContent = `Question ${{questionNumber}}`;
                    }}
                }});
            }}
            
            // Form submission handler
            document.getElementById('createQuizForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                // Validate that at least one question exists
                const questionCards = document.querySelectorAll('.question-card');
                if (questionCards.length === 0) {{
                    showMessage('Please add at least one question to the quiz', 'error');
                    return;
                }}
                
                // Collect form data
                const formData = new FormData();
                
                // Basic quiz data
                formData.append('title', document.getElementById('title').value);
                formData.append('description', document.getElementById('description').value);
                formData.append('category_id', document.getElementById('category_id').value);
                formData.append('difficulty_level', document.getElementById('difficulty_level').value);
                formData.append('time_limit', document.getElementById('time_limit').value);
                formData.append('credits_on_completion', document.getElementById('credits_on_completion').value);
                formData.append('is_active', document.getElementById('is_active').checked);
                
                // Add cover image if selected
                const coverImageFile = document.getElementById('cover_image').files[0];
                if (coverImageFile) {{
                    formData.append('cover_image', coverImageFile);
                }}
                
                // Collect questions data
                const questions = [];
                questionCards.forEach((card, index) => {{
                    const questionData = {{
                        question: card.querySelector(`textarea[name*="[question]"]`).value,
                        options: [],
                        correct_answer: 0,
                        explanation: card.querySelector(`textarea[name*="[explanation]"]`).value,
                        points: parseInt(card.querySelector(`input[name*="[points]"]`).value) || 1,
                        time_limit: parseInt(card.querySelector(`input[name*="[time_limit]"]`).value) || null
                    }};
                    
                    // Collect options
                    const optionInputs = card.querySelectorAll(`input[name*="[options]"]`);
                    optionInputs.forEach(input => {{
                        if (input.value.trim()) {{
                            questionData.options.push(input.value.trim());
                        }}
                    }});
                    
                    // Get correct answer
                    const correctRadio = card.querySelector(`input[name*="[correct_answer]"]:checked`);
                    if (correctRadio) {{
                        questionData.correct_answer = parseInt(correctRadio.value);
                    }}
                    
                    questions.push(questionData);
                }});
                
                formData.append('questions', JSON.stringify(questions));
                
                try {{
                    const response = await fetch('/admin/quizzes/create', {{
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        showMessage('Quiz created successfully!', 'success');
                        setTimeout(() => {{
                            window.location.href = '/admin/quizzes';
                        }}, 1500);
                    }} else {{
                        const errorText = await response.text();
                        showMessage('Error creating quiz: ' + response.status, 'error');
                    }}
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
                }}
            }});
            
            // Message display function
            function showMessage(message, type) {{
                const container = document.getElementById('message-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${{type}}`;
                messageDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>${{message}}</span>
                        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; cursor: pointer;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                container.appendChild(messageDiv);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {{
                    if (messageDiv.parentElement) {{
                        messageDiv.remove();
                    }}
                }}, 5000);
            }}
            
            // Image upload functions
            function handleImageUpload(input, previewId) {{
                const file = input.files[0];
                if (file) {{
                    // Validate file type
                    if (!file.type.startsWith('image/')) {{
                        showMessage('Please select a valid image file', 'error');
                        input.value = '';
                        return;
                    }}
                    
                    // Validate file size (5MB max)
                    if (file.size > 5 * 1024 * 1024) {{
                        showMessage('Image file size must be less than 5MB', 'error');
                        input.value = '';
                        return;
                    }}
                    
                    // Show preview
                    const reader = new FileReader();
                    reader.onload = function(e) {{
                        const preview = document.getElementById(previewId);
                        const img = document.getElementById(previewId.replace('-preview', '-img'));
                        img.src = e.target.result;
                        preview.style.display = 'block';
                        
                        // Hide upload area
                        const uploadArea = input.parentElement.querySelector('.file-upload-area');
                        if (uploadArea) {{
                            uploadArea.style.display = 'none';
                        }}
                    }};
                    reader.readAsDataURL(file);
                }}
            }}
            
            function removeImage(inputId, previewId) {{
                const input = document.getElementById(inputId);
                const preview = document.getElementById(previewId);
                const uploadArea = input.parentElement.querySelector('.file-upload-area');
                
                input.value = '';
                preview.style.display = 'none';
                if (uploadArea) {{
                    uploadArea.style.display = 'block';
                }}
            }}
            
            // Add first question by default
            document.addEventListener('DOMContentLoaded', function() {{
                addQuestion();
            }});
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Create Quiz", create_form, "quizzes"))


@router.post("/quizzes/create")
async def create_quiz(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    category_id: str = Form(""),
    difficulty_level: int = Form(...),
    time_limit: str = Form(""),
    credits_on_completion: int = Form(50),
    is_active: bool = Form(False),
    questions: str = Form(...),
    cover_image: Optional[UploadFile] = File(None)
):
    """Handle quiz creation form submission"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Parse questions JSON
            questions_data = json.loads(questions)
            
            if not questions_data:
                return JSONResponse(
                    status_code=400,
                    content={"error": "At least one question is required"}
                )
            
            # Validate category if provided
            category_uuid = None
            if category_id and category_id.strip():
                try:
                    category_uuid = UUID(category_id)
                    result = await db.execute(select(Category).where(Category.id == category_uuid))
                    category = result.scalar_one_or_none()
                    if not category:
                        return JSONResponse(
                            status_code=400,
                            content={"error": "Invalid category ID"}
                        )
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid category ID format"}
                    )
            
            # Parse time limit
            time_limit_int = None
            if time_limit and time_limit.strip():
                try:
                    time_limit_int = int(time_limit)
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid time limit format"}
                    )
            
            # Validate questions data
            for i, question_data in enumerate(questions_data):
                if not question_data.get('question', '').strip():
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Question {i+1} text is required"}
                    )
                
                options = question_data.get('options', [])
                if len(options) < 2:
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Question {i+1} must have at least 2 options"}
                    )
                
                correct_answer = question_data.get('correct_answer', 0)
                if correct_answer >= len(options):
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Question {i+1} has invalid correct answer index"}
                    )
            
            # Handle cover image upload
            cover_image_url = None
            if cover_image and cover_image.filename:
                try:
                    from app.services.file_upload import file_upload_service
                    
                    # Upload using file_upload_service (handles R2 automatically)
                    upload_result = await file_upload_service.upload_file(
                        file=cover_image,
                        file_category="quiz_covers",
                        validate_content=True
                    )
                    
                    # Store the relative path (e.g., "quiz_covers/abc123.jpg")
                    cover_image_url = upload_result['file_url']
                    logger.info(f"Quiz cover uploaded: {cover_image_url}")
                    
                except Exception as e:
                    logger.error(f"Error uploading cover image: {e}")
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"Failed to upload cover image: {str(e)}"}
                    )
            
            # Create quiz
            quiz = Quiz(
                title=title.strip(),
                description=description.strip() if description else None,
                category_id=category_uuid,
                cover_image=cover_image_url,
                questions=questions_data,
                difficulty_level=difficulty_level,
                time_limit=time_limit_int,
                credits_on_completion=credits_on_completion,
                is_active=is_active
            )
            
            db.add(quiz)
            await db.commit()
            await db.refresh(quiz)
            
            return JSONResponse(
                status_code=200,
                content={"message": "Quiz created successfully", "quiz_id": str(quiz.id)}
            )
            
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid questions data format"}
        )
    except Exception as e:
        logger.error(f"Error creating quiz: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error creating quiz: {str(e)}"}
        )


@router.get("/quizzes/edit/{quiz_id}", response_class=HTMLResponse)
async def edit_quiz_form(request: Request, quiz_id: UUID):
    """Edit quiz form with pre-populated data"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Get quiz
            result = await db.execute(
                select(Quiz).options(selectinload(Quiz.category)).where(Quiz.id == quiz_id)
            )
            quiz = result.scalar_one_or_none()
            
            if not quiz:
                return HTMLResponse(
                    content=create_html_page(
                        "Error", 
                        "<div class='message error'>Quiz not found</div>", 
                        "quizzes"
                    )
                )
            
            # Get categories for dropdown
            categories_result = await db.execute(
                select(Category).where(Category.is_active == True).order_by(Category.name)
            )
            categories = categories_result.scalars().all()
            
    except Exception as e:
        logger.error(f"Error loading quiz for edit: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Error", 
                f"<div class='message error'>Error loading quiz: {str(e)}</div>", 
                "quizzes"
            )
        )
    
    # Generate category options
    category_options = ""
    for category in categories:
        selected = "selected" if quiz.category_id and str(quiz.category_id) == str(category.id) else ""
        category_options += f'<option value="{category.id}" {selected}>{category.name}</option>'
    
    # Generate questions HTML
    questions_html = ""
    if quiz.questions:
        for i, question in enumerate(quiz.questions):
            question_num = i + 1
            options_html = ""
            
            for j, option in enumerate(question.get('options', [])):
                checked = "checked" if j == question.get('correct_answer', 0) else ""
                remove_style = "display: none;" if len(question.get('options', [])) <= 2 else ""
                
                options_html += f"""
                    <div class="option-group">
                        <input type="radio" name="questions[{question_num}][correct_answer]" value="{j}" class="correct-radio" {checked} required>
                        <input type="text" name="questions[{question_num}][options][]" value="{option}" placeholder="Option {chr(65+j)}" class="form-control option-input" required>
                        <button type="button" onclick="removeOption(this)" class="remove-option" style="{remove_style}">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                """
            
            questions_html += f"""
                <div class="question-card" id="question-{question_num}">
                    <div class="question-header">
                        <span class="question-number">Question {question_num}</span>
                        <div class="question-actions">
                            <button type="button" onclick="removeQuestion({question_num})" class="btn btn-danger btn-icon">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </div>
                    
                    <div class="form-group">
                        <label for="question_{question_num}_text">Question Text *</label>
                        <textarea id="question_{question_num}_text" name="questions[{question_num}][question]" required
                                  placeholder="Enter your question here..."
                                  class="form-control" rows="2">{question.get('question', '')}</textarea>
                    </div>
                    
                    <div class="form-group">
                        <label>Answer Options *</label>
                        <div id="options_{question_num}">
                            {options_html}
                        </div>
                        <button type="button" onclick="addOption({question_num})" class="add-option">
                            <i class="fas fa-plus"></i> Add Option
                        </button>
                        <small class="field-help">Select the correct answer by clicking the radio button next to it</small>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="question_{question_num}_explanation">Explanation</label>
                            <textarea id="question_{question_num}_explanation" name="questions[{question_num}][explanation]"
                                      placeholder="Explain why this is the correct answer..."
                                      class="form-control" rows="2">{question.get('explanation', '')}</textarea>
                            <small class="field-help">Optional: Provide educational explanation</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="question_{question_num}_points">Points</label>
                            <input type="number" id="question_{question_num}_points" name="questions[{question_num}][points]" 
                                   value="{question.get('points', 1)}" min="1" max="10" class="form-control">
                            <small class="field-help">Points awarded for correct answer</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="question_{question_num}_time_limit">Time Limit (seconds)</label>
                            <input type="number" id="question_{question_num}_time_limit" name="questions[{question_num}][time_limit]" 
                                   value="{question.get('time_limit', '') if question.get('time_limit') else ''}" 
                                   min="10" max="300" placeholder="Optional" class="form-control">
                            <small class="field-help">Optional: Time limit for this question</small>
                        </div>
                    </div>
                </div>
            """
    
    edit_form = f"""
        <div class="page-header">
            <h1 class="page-title">Edit Quiz</h1>
            <p class="page-subtitle">Modify quiz details and questions</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="editQuizForm" class="admin-form">
                <input type="hidden" id="quiz_id" value="{quiz.id}">
                
                <!-- Basic Information -->
                <div class="form-section">
                    <h3 class="section-title">Basic Information</h3>
                    
                    <div class="form-group">
                        <label for="title">Quiz Title *</label>
                        <input type="text" id="title" name="title" required 
                               value="{quiz.title}"
                               placeholder="Enter a compelling title for this quiz" 
                               maxlength="500"
                               class="form-control">
                        <div class="field-error" id="title-error"></div>
                        <small class="field-help">A clear, engaging title that describes the quiz topic</small>
                    </div>
                    
                    <div class="form-group">
                        <label for="description">Description</label>
                        <textarea id="description" name="description"
                                  placeholder="Provide a brief description of what this quiz covers..."
                                  class="form-control" rows="3">{quiz.description or ''}</textarea>
                        <small class="field-help">Optional: Brief description to help users understand the quiz content</small>
                    </div>
                    
                    <!-- Cover Image Upload -->
                    <div class="form-group">
                        <label for="cover_image">Cover Image</label>
                        <div class="file-upload-container">
                            {"" if not quiz.cover_image else f'''
                            <div id="current-cover-image" class="current-image-preview">
                                <img src="{quiz.cover_image if quiz.cover_image.startswith('/uploads/') else f'/uploads/{quiz.cover_image}'}" alt="Current cover" style="max-width: 300px; max-height: 200px; border-radius: 8px; margin-bottom: 0.5rem;">
                                <div>
                                    <button type="button" onclick="removeCoverImage()" class="btn btn-secondary btn-sm">
                                        <i class="fas fa-times"></i> Remove Current Image
                                    </button>
                                </div>
                            </div>
                            '''}
                            <div class="file-upload-area" onclick="document.getElementById('cover_image').click()" {"style='display: none;'" if quiz.cover_image else ""}>
                                <i class="fas fa-cloud-upload-alt"></i>
                                <p>Click to upload new cover image</p>
                                <small>Recommended: 1200x600px, JPG or PNG, max 5MB</small>
                            </div>
                            <input type="file" id="cover_image" name="cover_image" 
                                   accept="image/*" class="file-input" 
                                   onchange="handleImageUpload(this, 'cover-image-preview')">
                            <div id="cover-image-preview" class="image-preview" style="display: none;">
                                <img id="cover-image-img" src="" alt="Cover preview" style="max-width: 300px; max-height: 200px; border-radius: 8px;">
                                <button type="button" onclick="removeImage('cover_image', 'cover-image-preview')" class="btn btn-secondary btn-sm" style="margin-top: 0.5rem;">
                                    <i class="fas fa-times"></i> Remove
                                </button>
                            </div>
                        </div>
                        <small class="field-help">Optional: Upload an engaging cover image for the quiz</small>
                    </div>
                    
                    <div class="form-row">
                        <div class="form-group">
                            <label for="category_id">Category</label>
                            <select id="category_id" name="category_id" class="form-control">
                                <option value="">Select category...</option>
                                {category_options}
                            </select>
                            <small class="field-help">Optional: Categorize this quiz for better organization</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="difficulty_level">Difficulty Level *</label>
                            <select id="difficulty_level" name="difficulty_level" required class="form-control">
                                <option value="1" {"selected" if quiz.difficulty_level == 1 else ""}>Easy</option>
                                <option value="2" {"selected" if quiz.difficulty_level == 2 else ""}>Medium</option>
                                <option value="3" {"selected" if quiz.difficulty_level == 3 else ""}>Hard</option>
                            </select>
                            <small class="field-help">Choose the appropriate difficulty level for your audience</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="time_limit">Time Limit (minutes)</label>
                            <input type="number" id="time_limit" name="time_limit" 
                                   value="{quiz.time_limit if quiz.time_limit else ''}"
                                   min="1" max="120" placeholder="Optional"
                                   class="form-control">
                            <small class="field-help">Optional: Set a time limit for the entire quiz</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="credits_on_completion">Credits on Completion</label>
                            <input type="number" id="credits_on_completion" name="credits_on_completion" 
                                   value="{quiz.credits_on_completion if hasattr(quiz, 'credits_on_completion') else 10}"
                                   min="0" max="50"
                                   class="form-control">
                            <small class="field-help">Credits awarded to users when they complete this quiz</small>
                        </div>
                        
                        <div class="form-group">
                            <label for="is_active">Status</label>
                            <div class="checkbox-wrapper">
                                <input type="checkbox" id="is_active" name="is_active" value="true" 
                                       {"checked" if quiz.is_active else ""} class="form-checkbox">
                                <label for="is_active" class="checkbox-label">Active (visible to users)</label>
                            </div>
                            <small class="field-help">Uncheck to save as draft</small>
                        </div>
                    </div>
                </div>
                
                <!-- Questions Section -->
                <div class="form-section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                        <h3 class="section-title">Questions</h3>
                        <button type="button" onclick="addQuestion()" class="btn btn-secondary">
                            <i class="fas fa-plus"></i> Add Question
                        </button>
                    </div>
                    
                    <div id="questions-container">
                        {questions_html}
                    </div>
                    
                    <div id="no-questions-message" class="text-center" style="padding: 2rem; color: #718096; {'display: none;' if questions_html else ''}">
                        <i class="fas fa-question-circle" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                        <p style="font-size: 1.125rem; font-weight: 500;">No questions added yet</p>
                        <p style="font-size: 0.95rem;">Click "Add Question" to start building your quiz</p>
                    </div>
                </div>
                
                <!-- Submit Buttons -->
                <div class="form-section">
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Update Quiz
                        </button>
                        <a href="/admin/quizzes" class="btn btn-secondary">
                            <i class="fas fa-times"></i>
                            Cancel
                        </a>
                    </div>
                </div>
            </form>
        </div>
        
        <style>
            /* Same styles as create form */
            .form-container {{
                background: white;
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                max-width: 1200px;
                margin: 0 auto;
            }}
            
            .form-section {{
                margin-bottom: 2rem;
                padding: 1.5rem;
                background: #f8fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            .section-title {{
                color: #2d3748;
                margin-bottom: 1rem;
                font-size: 1.25rem;
                font-weight: 700;
            }}
            
            .form-group {{
                margin-bottom: 1.5rem;
            }}
            
            .form-row {{
                display: grid;
                grid-template-columns: 1fr 1fr 1fr 1fr;
                gap: 1rem;
            }}
            
            .form-group label {{
                display: block;
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.5rem;
            }}
            
            .form-control {{
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 0.95rem;
                transition: border-color 0.2s, box-shadow 0.2s;
            }}
            
            .form-control:focus {{
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
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
            
            .field-error {{
                color: #e53e3e;
                font-size: 0.875rem;
                margin-top: 0.5rem;
                display: none;
            }}
            
            .form-actions {{
                display: flex;
                gap: 1rem;
                justify-content: flex-start;
            }}
            
            .question-card {{
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 1.5rem;
                margin-bottom: 1rem;
                position: relative;
            }}
            
            .question-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }}
            
            .question-number {{
                font-weight: 700;
                color: #3b82f6;
                font-size: 1.1rem;
            }}
            
            .question-actions {{
                display: flex;
                gap: 0.5rem;
            }}
            
            .btn-icon {{
                padding: 0.5rem;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .option-group {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-bottom: 0.75rem;
            }}
            
            .option-input {{
                flex: 1;
            }}
            
            .correct-radio {{
                width: 20px;
                height: 20px;
            }}
            
            .remove-option {{
                background: #fee2e2;
                color: #dc2626;
                border: 1px solid #fecaca;
                padding: 0.5rem;
                border-radius: 6px;
                cursor: pointer;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .remove-option:hover {{
                background: #fecaca;
            }}
            
            .add-option {{
                background: #eff6ff;
                color: #2563eb;
                border: 1px solid #dbeafe;
                padding: 0.5rem 1rem;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.875rem;
            }}
            
            .add-option:hover {{
                background: #dbeafe;
            }}
            
            .text-center {{
                text-align: center;
            }}
            
            .message {{
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                border: 1px solid;
            }}
            
            .message.success {{
                background: #f0fff4;
                color: #22543d;
                border-color: #9ae6b4;
            }}
            
            .message.error {{
                background: #fed7d7;
                color: #742a2a;
                border-color: #feb2b2;
            }}
            
            @media (max-width: 768px) {{
                .form-row {{
                    grid-template-columns: 1fr;
                }}
                
                .question-header {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 1rem;
                }}
            }}
            
            /* Image Upload Styles */
            .file-upload-container {{
                margin-top: 0.5rem;
            }}
            
            .file-upload-area {{
                border: 2px dashed #cbd5e0;
                border-radius: 12px;
                padding: 2rem;
                text-align: center;
                cursor: pointer;
                transition: all 0.3s ease;
                background: #f8fafc;
            }}
            
            .file-upload-area:hover {{
                border-color: #3b82f6;
                background: #eff6ff;
            }}
            
            .file-upload-area i {{
                font-size: 2rem;
                color: #3b82f6;
                margin-bottom: 0.5rem;
                display: block;
            }}
            
            .file-upload-area p {{
                font-weight: 600;
                color: #374151;
                margin-bottom: 0.25rem;
            }}
            
            .file-upload-area small {{
                color: #6b7280;
            }}
            
            .file-input {{
                display: none;
            }}
            
            .image-preview {{
                text-align: center;
                margin-top: 1rem;
            }}
            
            .current-image-preview {{
                text-align: center;
                margin-bottom: 1rem;
                padding: 1rem;
                background: #f8fafc;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }}
        </style>
        
        <script>
            let questionCount = {len(quiz.questions) if quiz.questions else 0};
            
            // Same JavaScript functions as create form
            function addQuestion() {{
                questionCount++;
                const container = document.getElementById('questions-container');
                const noQuestionsMessage = document.getElementById('no-questions-message');
                
                const questionHtml = `
                    <div class="question-card" id="question-${{questionCount}}">
                        <div class="question-header">
                            <span class="question-number">Question ${{questionCount}}</span>
                            <div class="question-actions">
                                <button type="button" onclick="removeQuestion(${{questionCount}})" class="btn btn-danger btn-icon">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                        
                        <div class="form-group">
                            <label for="question_${{questionCount}}_text">Question Text *</label>
                            <textarea id="question_${{questionCount}}_text" name="questions[${{questionCount}}][question]" required
                                      placeholder="Enter your question here..."
                                      class="form-control" rows="2"></textarea>
                        </div>
                        
                        <div class="form-group">
                            <label>Answer Options *</label>
                            <div id="options_${{questionCount}}">
                                <div class="option-group">
                                    <input type="radio" name="questions[${{questionCount}}][correct_answer]" value="0" class="correct-radio" required>
                                    <input type="text" name="questions[${{questionCount}}][options][]" placeholder="Option A" class="form-control option-input" required>
                                    <button type="button" onclick="removeOption(this)" class="remove-option" style="display: none;">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                                <div class="option-group">
                                    <input type="radio" name="questions[${{questionCount}}][correct_answer]" value="1" class="correct-radio" required>
                                    <input type="text" name="questions[${{questionCount}}][options][]" placeholder="Option B" class="form-control option-input" required>
                                    <button type="button" onclick="removeOption(this)" class="remove-option" style="display: none;">
                                        <i class="fas fa-times"></i>
                                    </button>
                                </div>
                            </div>
                            <button type="button" onclick="addOption(${{questionCount}})" class="add-option">
                                <i class="fas fa-plus"></i> Add Option
                            </button>
                            <small class="field-help">Select the correct answer by clicking the radio button next to it</small>
                        </div>
                        
                        <div class="form-row">
                            <div class="form-group">
                                <label for="question_${{questionCount}}_explanation">Explanation</label>
                                <textarea id="question_${{questionCount}}_explanation" name="questions[${{questionCount}}][explanation]"
                                          placeholder="Explain why this is the correct answer..."
                                          class="form-control" rows="2"></textarea>
                                <small class="field-help">Optional: Provide educational explanation</small>
                            </div>
                            
                            <div class="form-group">
                                <label for="question_${{questionCount}}_points">Points</label>
                                <input type="number" id="question_${{questionCount}}_points" name="questions[${{questionCount}}][points]" 
                                       value="1" min="1" max="10" class="form-control">
                                <small class="field-help">Points awarded for correct answer</small>
                            </div>
                            
                            <div class="form-group">
                                <label for="question_${{questionCount}}_time_limit">Time Limit (seconds)</label>
                                <input type="number" id="question_${{questionCount}}_time_limit" name="questions[${{questionCount}}][time_limit]" 
                                       min="10" max="300" placeholder="Optional" class="form-control">
                                <small class="field-help">Optional: Time limit for this question</small>
                            </div>
                        </div>
                    </div>
                `;
                
                container.insertAdjacentHTML('beforeend', questionHtml);
                noQuestionsMessage.style.display = 'none';
                updateOptionVisibility(questionCount);
            }}
            
            function removeQuestion(questionId) {{
                const questionElement = document.getElementById(`question-${{questionId}}`);
                if (questionElement) {{
                    questionElement.remove();
                }}
                
                // Show no questions message if no questions left
                const container = document.getElementById('questions-container');
                const noQuestionsMessage = document.getElementById('no-questions-message');
                if (container.children.length === 0) {{
                    noQuestionsMessage.style.display = 'block';
                }}
                
                // Renumber remaining questions
                renumberQuestions();
            }}
            
            function addOption(questionId) {{
                const optionsContainer = document.getElementById(`options_${{questionId}}`);
                const optionCount = optionsContainer.children.length;
                const optionLetter = String.fromCharCode(65 + optionCount); // A, B, C, D, etc.
                
                if (optionCount >= 6) {{
                    alert('Maximum 6 options allowed per question');
                    return;
                }}
                
                const optionHtml = `
                    <div class="option-group">
                        <input type="radio" name="questions[${{questionId}}][correct_answer]" value="${{optionCount}}" class="correct-radio" required>
                        <input type="text" name="questions[${{questionId}}][options][]" placeholder="Option ${{optionLetter}}" class="form-control option-input" required>
                        <button type="button" onclick="removeOption(this)" class="remove-option">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                
                optionsContainer.insertAdjacentHTML('beforeend', optionHtml);
                updateOptionVisibility(questionId);
            }}
            
            function removeOption(button) {{
                const optionGroup = button.parentElement;
                const optionsContainer = optionGroup.parentElement;
                
                if (optionsContainer.children.length <= 2) {{
                    alert('Minimum 2 options required per question');
                    return;
                }}
                
                optionGroup.remove();
                
                // Update radio button values and option visibility
                const questionId = optionsContainer.id.split('_')[1];
                updateRadioValues(questionId);
                updateOptionVisibility(questionId);
            }}
            
            function updateRadioValues(questionId) {{
                const optionsContainer = document.getElementById(`options_${{questionId}}`);
                const radioButtons = optionsContainer.querySelectorAll('input[type="radio"]');
                
                radioButtons.forEach((radio, index) => {{
                    radio.value = index;
                }});
            }}
            
            function updateOptionVisibility(questionId) {{
                const optionsContainer = document.getElementById(`options_${{questionId}}`);
                const removeButtons = optionsContainer.querySelectorAll('.remove-option');
                
                removeButtons.forEach(button => {{
                    button.style.display = optionsContainer.children.length > 2 ? 'flex' : 'none';
                }});
            }}
            
            function renumberQuestions() {{
                const questionCards = document.querySelectorAll('.question-card');
                questionCards.forEach((card, index) => {{
                    const questionNumber = index + 1;
                    const numberSpan = card.querySelector('.question-number');
                    if (numberSpan) {{
                        numberSpan.textContent = `Question ${{questionNumber}}`;
                    }}
                }});
            }}
            
            // Form submission handler for edit
            document.getElementById('editQuizForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                // Validate that at least one question exists
                const questionCards = document.querySelectorAll('.question-card');
                if (questionCards.length === 0) {{
                    showMessage('Please add at least one question to the quiz', 'error');
                    return;
                }}
                
                // Collect form data
                const formData = new FormData();
                
                // Basic quiz data
                formData.append('title', document.getElementById('title').value);
                formData.append('description', document.getElementById('description').value);
                formData.append('category_id', document.getElementById('category_id').value);
                formData.append('difficulty_level', document.getElementById('difficulty_level').value);
                formData.append('time_limit', document.getElementById('time_limit').value);
                formData.append('credits_on_completion', document.getElementById('credits_on_completion').value);
                formData.append('is_active', document.getElementById('is_active').checked);
                
                // Add cover image if selected
                const coverImageFile = document.getElementById('cover_image').files[0];
                if (coverImageFile) {{
                    formData.append('cover_image', coverImageFile);
                }}
                
                // Collect questions data
                const questions = [];
                questionCards.forEach((card, index) => {{
                    const questionData = {{
                        question: card.querySelector(`textarea[name*="[question]"]`).value,
                        options: [],
                        correct_answer: 0,
                        explanation: card.querySelector(`textarea[name*="[explanation]"]`).value,
                        points: parseInt(card.querySelector(`input[name*="[points]"]`).value) || 1,
                        time_limit: parseInt(card.querySelector(`input[name*="[time_limit]"]`).value) || null
                    }};
                    
                    // Collect options
                    const optionInputs = card.querySelectorAll(`input[name*="[options]"]`);
                    optionInputs.forEach(input => {{
                        if (input.value.trim()) {{
                            questionData.options.push(input.value.trim());
                        }}
                    }});
                    
                    // Get correct answer
                    const correctRadio = card.querySelector(`input[name*="[correct_answer]"]:checked`);
                    if (correctRadio) {{
                        questionData.correct_answer = parseInt(correctRadio.value);
                    }}
                    
                    questions.push(questionData);
                }});
                
                formData.append('questions', JSON.stringify(questions));
                
                const quizId = document.getElementById('quiz_id').value;
                
                try {{
                    const response = await fetch(`/admin/quizzes/edit/${{quizId}}`, {{
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    }});
                    
                    if (response.ok) {{
                        showMessage('Quiz updated successfully!', 'success');
                        setTimeout(() => {{
                            window.location.href = '/admin/quizzes';
                        }}, 1500);
                    }} else {{
                        const errorText = await response.text();
                        showMessage('Error updating quiz: ' + response.status, 'error');
                    }}
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
                }}
            }});
            
            // Message display function
            function showMessage(message, type) {{
                const container = document.getElementById('message-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${{type}}`;
                messageDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>${{message}}</span>
                        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; cursor: pointer;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                container.appendChild(messageDiv);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {{
                    if (messageDiv.parentElement) {{
                        messageDiv.remove();
                    }}
                }}, 5000);
            }}
            
            // Image upload functions
            function handleImageUpload(input, previewId) {{
                const file = input.files[0];
                if (file) {{
                    // Validate file type
                    if (!file.type.startsWith('image/')) {{
                        showMessage('Please select a valid image file', 'error');
                        input.value = '';
                        return;
                    }}
                    
                    // Validate file size (5MB max)
                    if (file.size > 5 * 1024 * 1024) {{
                        showMessage('Image file size must be less than 5MB', 'error');
                        input.value = '';
                        return;
                    }}
                    
                    // Show preview
                    const reader = new FileReader();
                    reader.onload = function(e) {{
                        const preview = document.getElementById(previewId);
                        const img = document.getElementById(previewId.replace('-preview', '-img'));
                        img.src = e.target.result;
                        preview.style.display = 'block';
                        
                        // Hide upload area and current image
                        const uploadArea = input.parentElement.querySelector('.file-upload-area');
                        const currentImage = document.getElementById('current-cover-image');
                        if (uploadArea) uploadArea.style.display = 'none';
                        if (currentImage) currentImage.style.display = 'none';
                    }};
                    reader.readAsDataURL(file);
                }}
            }}
            
            function removeImage(inputId, previewId) {{
                const input = document.getElementById(inputId);
                const preview = document.getElementById(previewId);
                const uploadArea = input.parentElement.querySelector('.file-upload-area');
                const currentImage = document.getElementById('current-cover-image');
                
                input.value = '';
                preview.style.display = 'none';
                if (uploadArea) uploadArea.style.display = 'block';
                if (currentImage) currentImage.style.display = 'block';
            }}
            
            function removeCoverImage() {{
                const currentImage = document.getElementById('current-cover-image');
                const uploadArea = document.querySelector('.file-upload-area');
                
                if (currentImage) currentImage.style.display = 'none';
                if (uploadArea) uploadArea.style.display = 'block';
                
                // Add a hidden input to indicate image removal
                const removeInput = document.createElement('input');
                removeInput.type = 'hidden';
                removeInput.name = 'remove_cover_image';
                removeInput.value = 'true';
                document.getElementById('editQuizForm').appendChild(removeInput);
            }}
            
            // Initialize option visibility for existing questions
            document.addEventListener('DOMContentLoaded', function() {{
                const questionCards = document.querySelectorAll('.question-card');
                questionCards.forEach((card, index) => {{
                    const questionId = index + 1;
                    updateOptionVisibility(questionId);
                }});
            }});
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Edit Quiz", edit_form, "quizzes"))


@router.post("/quizzes/edit/{quiz_id}")
async def update_quiz(
    request: Request,
    quiz_id: UUID,
    title: str = Form(...),
    description: str = Form(""),
    category_id: str = Form(""),
    difficulty_level: int = Form(...),
    time_limit: str = Form(""),
    credits_on_completion: int = Form(50),
    is_active: bool = Form(False),
    questions: str = Form(...),
    cover_image: Optional[UploadFile] = File(None),
    remove_cover_image: Optional[str] = Form(None)
):
    """Handle quiz update form submission"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Get existing quiz
            result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
            quiz = result.scalar_one_or_none()
            
            if not quiz:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Quiz not found"}
                )
            
            # Parse questions JSON
            questions_data = json.loads(questions)
            
            if not questions_data:
                return JSONResponse(
                    status_code=400,
                    content={"error": "At least one question is required"}
                )
            
            # Validate category if provided
            category_uuid = None
            if category_id and category_id.strip():
                try:
                    category_uuid = UUID(category_id)
                    result = await db.execute(select(Category).where(Category.id == category_uuid))
                    category = result.scalar_one_or_none()
                    if not category:
                        return JSONResponse(
                            status_code=400,
                            content={"error": "Invalid category ID"}
                        )
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid category ID format"}
                    )
            
            # Parse time limit
            time_limit_int = None
            if time_limit and time_limit.strip():
                try:
                    time_limit_int = int(time_limit)
                except ValueError:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid time limit format"}
                    )
            
            # Validate questions data
            for i, question_data in enumerate(questions_data):
                if not question_data.get('question', '').strip():
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Question {i+1} text is required"}
                    )
                
                options = question_data.get('options', [])
                if len(options) < 2:
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Question {i+1} must have at least 2 options"}
                    )
                
                correct_answer = question_data.get('correct_answer', 0)
                if correct_answer >= len(options):
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Question {i+1} has invalid correct answer index"}
                    )
            
            # Handle cover image update
            if remove_cover_image == 'true':
                # Remove existing cover image
                if quiz.cover_image:
                    # Optionally delete the file from filesystem
                    try:
                        import os
                        if quiz.cover_image.startswith('/static/'):
                            file_path = quiz.cover_image[1:]  # Remove leading slash
                            if os.path.exists(file_path):
                                os.remove(file_path)
                    except Exception as e:
                        logger.warning(f"Could not delete old cover image file: {e}")
                quiz.cover_image = None
            elif cover_image and cover_image.filename:
                try:
                    from app.services.file_upload import file_upload_service
                    
                    # Delete old image if exists (only from local disk, R2 files can stay)
                    if quiz.cover_image:
                        try:
                            import os
                            # Only delete if it's a local file path
                            if not quiz.cover_image.startswith('/uploads/'):
                                old_file_path = quiz.cover_image[1:] if quiz.cover_image.startswith('/') else quiz.cover_image
                                if os.path.exists(old_file_path):
                                    os.remove(old_file_path)
                        except Exception as e:
                            logger.warning(f"Could not delete old cover image file: {e}")
                    
                    # Upload using file_upload_service (handles R2 automatically)
                    upload_result = await file_upload_service.upload_file(
                        file=cover_image,
                        file_category="quiz_covers",
                        validate_content=True
                    )
                    
                    # Store the relative path (e.g., "quiz_covers/abc123.jpg")
                    quiz.cover_image = upload_result['file_url']
                    logger.info(f"Quiz cover updated: {quiz.cover_image}")
                    
                except Exception as e:
                    logger.error(f"Error uploading cover image: {e}")
                    return JSONResponse(
                        status_code=500,
                        content={"error": f"Failed to upload cover image: {str(e)}"}
                    )
            
            # Update quiz
            quiz.title = title.strip()
            quiz.description = description.strip() if description else None
            quiz.category_id = category_uuid
            quiz.questions = questions_data
            quiz.difficulty_level = difficulty_level
            quiz.time_limit = time_limit_int
            quiz.credits_on_completion = credits_on_completion
            quiz.is_active = is_active
            
            await db.commit()
            await db.refresh(quiz)
            
            return JSONResponse(
                status_code=200,
                content={"message": "Quiz updated successfully", "quiz_id": str(quiz.id)}
            )
            
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid questions data format"}
        )
    except Exception as e:
        logger.error(f"Error updating quiz: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error updating quiz: {str(e)}"}
        )


@router.delete("/quizzes/delete/{quiz_id}")
async def delete_quiz(request: Request, quiz_id: UUID):
    """Delete quiz with cascade deletion of user results"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )
    
    try:
        async with get_db_session() as db:
            # Get quiz
            result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
            quiz = result.scalar_one_or_none()
            
            if not quiz:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Quiz not found"}
                )
            
            # Delete associated user results first (cascade deletion)
            user_results_result = await db.execute(
                select(UserQuizResult).where(UserQuizResult.quiz_id == quiz_id)
            )
            user_results = user_results_result.scalars().all()
            
            for result in user_results:
                await db.delete(result)
            
            # Delete the quiz
            await db.delete(quiz)
            await db.commit()
            
            logger.info(f"Quiz {quiz_id} deleted successfully with {len(user_results)} user results")
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": "Quiz deleted successfully", 
                    "deleted_results": len(user_results)
                }
            )
            
    except Exception as e:
        logger.error(f"Error deleting quiz {quiz_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error deleting quiz: {str(e)}"}
        )


@router.get("/quizzes/analytics", response_class=HTMLResponse)
async def quiz_analytics(request: Request):
    """Quiz analytics and statistics dashboard"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Overall quiz statistics
            total_quizzes_result = await db.execute(select(func.count(Quiz.id)))
            total_quizzes = total_quizzes_result.scalar() or 0
            
            active_quizzes_result = await db.execute(
                select(func.count(Quiz.id)).where(Quiz.is_active == True)
            )
            active_quizzes = active_quizzes_result.scalar() or 0
            
            # Total quiz attempts
            total_attempts_result = await db.execute(select(func.count(UserQuizResult.id)))
            total_attempts = total_attempts_result.scalar() or 0
            
            # Average score across all quizzes
            avg_score_result = await db.execute(select(func.avg(UserQuizResult.percentage)))
            avg_score = avg_score_result.scalar() or 0
            avg_score = round(float(avg_score), 1) if avg_score else 0
            
            # Quiz performance statistics
            quiz_stats_query = select(
                Quiz.id,
                Quiz.title,
                Quiz.difficulty_level,
                func.count(UserQuizResult.id).label('attempt_count'),
                func.avg(UserQuizResult.percentage).label('avg_score'),
                func.min(UserQuizResult.percentage).label('min_score'),
                func.max(UserQuizResult.percentage).label('max_score'),
                func.avg(UserQuizResult.time_taken).label('avg_time')
            ).select_from(
                Quiz
            ).outerjoin(
                UserQuizResult, Quiz.id == UserQuizResult.quiz_id
            ).group_by(
                Quiz.id, Quiz.title, Quiz.difficulty_level
            ).order_by(
                desc(func.count(UserQuizResult.id))
            ).limit(10)
            
            quiz_stats_result = await db.execute(quiz_stats_query)
            quiz_stats = quiz_stats_result.all()
            
            # Difficulty level distribution
            difficulty_stats_query = select(
                Quiz.difficulty_level,
                func.count(Quiz.id).label('quiz_count'),
                func.count(UserQuizResult.id).label('attempt_count'),
                func.avg(UserQuizResult.percentage).label('avg_score')
            ).select_from(
                Quiz
            ).outerjoin(
                UserQuizResult, Quiz.id == UserQuizResult.quiz_id
            ).group_by(
                Quiz.difficulty_level
            ).order_by(
                Quiz.difficulty_level
            )
            
            difficulty_stats_result = await db.execute(difficulty_stats_query)
            difficulty_stats = difficulty_stats_result.all()
            
            # Recent quiz activity (last 30 days)
            from datetime import datetime, timedelta
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_activity_query = select(
                func.date(UserQuizResult.completed_at).label('date'),
                func.count(UserQuizResult.id).label('attempts'),
                func.avg(UserQuizResult.percentage).label('avg_score')
            ).where(
                UserQuizResult.completed_at >= thirty_days_ago
            ).group_by(
                func.date(UserQuizResult.completed_at)
            ).order_by(
                func.date(UserQuizResult.completed_at)
            )
            
            recent_activity_result = await db.execute(recent_activity_query)
            recent_activity = recent_activity_result.all()
            
            # Most challenging questions (questions with lowest success rates)
            # This requires analyzing the answers JSON field
            challenging_questions_query = select(
                Quiz.id,
                Quiz.title,
                UserQuizResult.answers
            ).select_from(
                Quiz
            ).join(
                UserQuizResult, Quiz.id == UserQuizResult.quiz_id
            ).where(
                UserQuizResult.answers.isnot(None)
            )
            
            challenging_questions_result = await db.execute(challenging_questions_query)
            all_results = challenging_questions_result.all()
            
            # Process question difficulty analysis
            question_stats = {}
            for result in all_results:
                quiz_id = str(result.id)
                quiz_title = result.title
                answers = result.answers
                
                if not answers or not isinstance(answers, list):
                    continue
                
                for answer in answers:
                    if not isinstance(answer, dict):
                        continue
                    
                    question_text = answer.get('question', 'Unknown Question')
                    is_correct = answer.get('is_correct', False)
                    
                    key = f"{quiz_id}_{question_text[:50]}"  # Truncate for key
                    
                    if key not in question_stats:
                        question_stats[key] = {
                            'quiz_title': quiz_title,
                            'question': question_text,
                            'total_attempts': 0,
                            'correct_attempts': 0,
                            'success_rate': 0
                        }
                    
                    question_stats[key]['total_attempts'] += 1
                    if is_correct:
                        question_stats[key]['correct_attempts'] += 1
            
            # Calculate success rates and sort by difficulty
            for stats in question_stats.values():
                if stats['total_attempts'] > 0:
                    stats['success_rate'] = (stats['correct_attempts'] / stats['total_attempts']) * 100
            
            # Get top 10 most challenging questions (lowest success rate, min 5 attempts)
            challenging_questions = sorted(
                [stats for stats in question_stats.values() if stats['total_attempts'] >= 5],
                key=lambda x: x['success_rate']
            )[:10]
            
    except Exception as e:
        logger.error(f"Error loading quiz analytics: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Quiz Analytics - Error", 
                f"<div class='message error'>Error loading analytics: {str(e)}</div>", 
                "quizzes"
            )
        )
    
    # Generate difficulty level names
    difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard"}
    
    # Generate quiz performance table
    quiz_performance_rows = ""
    for stat in quiz_stats:
        difficulty_name = difficulty_names.get(stat.difficulty_level, "Unknown")
        avg_score = round(float(stat.avg_score), 1) if stat.avg_score else 0
        min_score = int(stat.min_score) if stat.min_score else 0
        max_score = int(stat.max_score) if stat.max_score else 0
        avg_time = round(float(stat.avg_time), 1) if stat.avg_time else 0
        
        quiz_performance_rows += f"""
        <tr>
            <td>
                <div class="quiz-title">{stat.title}</div>
                <span class="difficulty-badge difficulty-{stat.difficulty_level}">{difficulty_name}</span>
            </td>
            <td class="text-center">{stat.attempt_count}</td>
            <td class="text-center">{avg_score}%</td>
            <td class="text-center">{min_score}% - {max_score}%</td>
            <td class="text-center">{avg_time}s</td>
        </tr>
        """
    
    # Generate difficulty distribution cards
    difficulty_cards = ""
    for stat in difficulty_stats:
        difficulty_name = difficulty_names.get(stat.difficulty_level, "Unknown")
        avg_score = round(float(stat.avg_score), 1) if stat.avg_score else 0
        
        difficulty_cards += f"""
        <div class="stat-card">
            <div class="stat-header">
                <h4>{difficulty_name} Quizzes</h4>
                <span class="difficulty-badge difficulty-{stat.difficulty_level}">Level {stat.difficulty_level}</span>
            </div>
            <div class="stat-metrics">
                <div class="metric">
                    <span class="metric-value">{stat.quiz_count}</span>
                    <span class="metric-label">Quizzes</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{stat.attempt_count}</span>
                    <span class="metric-label">Attempts</span>
                </div>
                <div class="metric">
                    <span class="metric-value">{avg_score}%</span>
                    <span class="metric-label">Avg Score</span>
                </div>
            </div>
        </div>
        """
    
    # Generate challenging questions list
    challenging_questions_html = ""
    for i, question in enumerate(challenging_questions, 1):
        success_rate = round(question['success_rate'], 1)
        difficulty_class = "high" if success_rate < 30 else "medium" if success_rate < 60 else "low"
        
        challenging_questions_html += f"""
        <div class="question-stat">
            <div class="question-rank">#{i}</div>
            <div class="question-details">
                <div class="question-text">{question['question'][:100]}{'...' if len(question['question']) > 100 else ''}</div>
                <div class="question-meta">
                    <span class="quiz-name">{question['quiz_title']}</span>
                    <span class="attempts-count">{question['total_attempts']} attempts</span>
                </div>
            </div>
            <div class="success-rate difficulty-{difficulty_class}">
                {success_rate}%
            </div>
        </div>
        """
    
    # Generate activity chart data for JavaScript (limit to 30 days max)
    activity_data = []
    activity_labels = []
    for activity in recent_activity[-30:]:  # Limit to last 30 days
        activity_labels.append(activity.date.strftime('%m/%d'))
        activity_data.append(int(activity.attempts))
    
    # Ensure we don't have more than 30 data points
    if len(activity_data) > 30:
        activity_data = activity_data[-30:]
        activity_labels = activity_labels[-30:]
    
    analytics_content = f"""
        <div class="page-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1 class="page-title">Quiz Analytics</h1>
                    <p class="page-subtitle">Performance insights and statistics</p>
                </div>
                <a href="/admin/quizzes" class="btn btn-secondary">
                    <i class="fas fa-arrow-left"></i> Back to Quizzes
                </a>
            </div>
        </div>
        
        <!-- Overview Cards -->
        <div class="overview-cards">
            <div class="stat-card primary">
                <div class="stat-icon">
                    <i class="fas fa-question-circle"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{total_quizzes}</div>
                    <div class="stat-label">Total Quizzes</div>
                    <div class="stat-sublabel">{active_quizzes} active</div>
                </div>
            </div>
            
            <div class="stat-card success">
                <div class="stat-icon">
                    <i class="fas fa-users"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{total_attempts}</div>
                    <div class="stat-label">Total Attempts</div>
                    <div class="stat-sublabel">All time</div>
                </div>
            </div>
            
            <div class="stat-card info">
                <div class="stat-icon">
                    <i class="fas fa-chart-line"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{avg_score}%</div>
                    <div class="stat-label">Average Score</div>
                    <div class="stat-sublabel">Across all quizzes</div>
                </div>
            </div>
            
            <div class="stat-card warning">
                <div class="stat-icon">
                    <i class="fas fa-clock"></i>
                </div>
                <div class="stat-content">
                    <div class="stat-value">{len(recent_activity)}</div>
                    <div class="stat-label">Active Days</div>
                    <div class="stat-sublabel">Last 30 days</div>
                </div>
            </div>
        </div>
        
        <!-- Activity Summary -->
        <div class="section">
            <h3 class="section-title">Recent Activity Summary</h3>
            <div class="activity-summary">
                <p>Total quiz attempts in the last 30 days: <strong>{len(recent_activity)}</strong></p>
                <p>Most active day had <strong>{max([a.attempts for a in recent_activity] + [0])}</strong> attempts</p>
                <p>Average daily attempts: <strong>{sum([a.attempts for a in recent_activity]) // max(len(recent_activity), 1)}</strong></p>
            </div>
        </div>
        
        <!-- Difficulty Distribution -->
        <div class="section">
            <h3 class="section-title">Performance by Difficulty</h3>
            <div class="difficulty-grid">
                {difficulty_cards}
            </div>
        </div>
        
        <!-- Quiz Performance Table -->
        <div class="section">
            <h3 class="section-title">Top Quiz Performance</h3>
            <div class="table-container">
                <table class="analytics-table">
                    <thead>
                        <tr>
                            <th>Quiz</th>
                            <th>Attempts</th>
                            <th>Avg Score</th>
                            <th>Score Range</th>
                            <th>Avg Time</th>
                        </tr>
                    </thead>
                    <tbody>
                        {quiz_performance_rows if quiz_performance_rows else '<tr><td colspan="5" class="text-center">No quiz data available</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Challenging Questions -->
        <div class="section">
            <h3 class="section-title">Most Challenging Questions</h3>
            <div class="challenging-questions">
                {challenging_questions_html if challenging_questions_html else '<div class="text-center text-muted">No question data available</div>'}
            </div>
        </div>
        
        <style>
            .overview-cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                display: flex;
                align-items: center;
                gap: 1rem;
            }}
            
            .stat-card.primary {{
                border-left: 4px solid #3182ce;
            }}
            
            .stat-card.success {{
                border-left: 4px solid #38a169;
            }}
            
            .stat-card.info {{
                border-left: 4px solid #00b4d8;
            }}
            
            .stat-card.warning {{
                border-left: 4px solid #d69e2e;
            }}
            
            .stat-icon {{
                font-size: 2rem;
                color: #718096;
                min-width: 60px;
                text-align: center;
            }}
            
            .stat-content {{
                flex: 1;
            }}
            
            .stat-value {{
                font-size: 2rem;
                font-weight: 700;
                color: #2d3748;
                line-height: 1;
            }}
            
            .stat-label {{
                font-size: 0.9rem;
                font-weight: 600;
                color: #4a5568;
                margin-top: 0.25rem;
            }}
            
            .stat-sublabel {{
                font-size: 0.8rem;
                color: #718096;
                margin-top: 0.25rem;
            }}
            

            
            .chart-container {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
            }}
            
            .chart-container h3 {{
                margin-bottom: 1rem;
                color: #2d3748;
                font-size: 1.1rem;
                font-weight: 600;
            }}
            
            .section {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                margin-bottom: 2rem;
            }}
            
            .section-title {{
                margin-bottom: 1.5rem;
                color: #2d3748;
                font-size: 1.2rem;
                font-weight: 600;
            }}
            
            .difficulty-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
            }}
            
            .stat-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }}
            
            .stat-header h4 {{
                margin: 0;
                color: #2d3748;
                font-size: 1.1rem;
            }}
            
            .stat-metrics {{
                display: flex;
                justify-content: space-between;
                gap: 1rem;
            }}
            
            .metric {{
                text-align: center;
            }}
            
            .metric-value {{
                display: block;
                font-size: 1.5rem;
                font-weight: 700;
                color: #2d3748;
                line-height: 1;
            }}
            
            .metric-label {{
                font-size: 0.8rem;
                color: #718096;
                margin-top: 0.25rem;
            }}
            
            .analytics-table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            .analytics-table th {{
                background: #f8fafc;
                padding: 1rem;
                text-align: left;
                font-weight: 600;
                color: #4a5568;
                border-bottom: 2px solid #e2e8f0;
            }}
            
            .analytics-table td {{
                padding: 1rem;
                border-bottom: 1px solid #e2e8f0;
            }}
            
            .analytics-table tr:hover {{
                background: #f8fafc;
            }}
            
            .quiz-title {{
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 0.5rem;
            }}
            
            .challenging-questions {{
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }}
            
            .question-stat {{
                display: flex;
                align-items: center;
                gap: 1rem;
                padding: 1rem;
                background: #f8fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            .question-rank {{
                font-size: 1.2rem;
                font-weight: 700;
                color: #718096;
                min-width: 40px;
                text-align: center;
            }}
            
            .question-details {{
                flex: 1;
            }}
            
            .question-text {{
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 0.5rem;
                line-height: 1.4;
            }}
            
            .question-meta {{
                display: flex;
                gap: 1rem;
                font-size: 0.8rem;
                color: #718096;
            }}
            
            .quiz-name {{
                font-weight: 500;
            }}
            
            .success-rate {{
                font-size: 1.1rem;
                font-weight: 700;
                padding: 0.5rem 1rem;
                border-radius: 20px;
                min-width: 80px;
                text-align: center;
            }}
            
            .difficulty-high {{
                background: #fecaca;
                color: #991b1b;
            }}
            
            .difficulty-medium {{
                background: #fed7aa;
                color: #9c4221;
            }}
            
            .difficulty-low {{
                background: #c6f6d5;
                color: #22543d;
            }}
            
            .difficulty-badge {{
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .difficulty-1 {{
                background: #c6f6d5;
                color: #22543d;
            }}
            
            .difficulty-2 {{
                background: #fed7aa;
                color: #9c4221;
            }}
            
            .difficulty-3 {{
                background: #fecaca;
                color: #991b1b;
            }}
            
            .text-center {{
                text-align: center;
            }}
            
            .text-muted {{
                color: #718096;
            }}
            
            .table-container {{
                overflow-x: auto;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            @media (max-width: 768px) {{
                .overview-cards {{
                    grid-template-columns: 1fr;
                }}
                
                .difficulty-grid {{
                    grid-template-columns: 1fr;
                }}
                
                .question-stat {{
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 0.5rem;
                }}
                
                .question-meta {{
                    flex-direction: column;
                    gap: 0.25rem;
                }}
            }}
        </style>
        
        <script>
            // Simple activity display - no charts to avoid infinite rendering
            console.log('Quiz analytics loaded successfully');
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Quiz Analytics", analytics_content, "quizzes"))


@router.post("/quizzes/toggle-active/{quiz_id}")
async def toggle_quiz_active(request: Request, quiz_id: UUID):
    """Toggle quiz active status"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )
    
    try:
        async with get_db_session() as db:
            # Get quiz
            result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
            quiz = result.scalar_one_or_none()
            
            if not quiz:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Quiz not found"}
                )
            
            # Toggle active status
            quiz.is_active = not quiz.is_active
            await db.commit()
            await db.refresh(quiz)
            
            status_text = "activated" if quiz.is_active else "deactivated"
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": f"Quiz {status_text} successfully",
                    "is_active": quiz.is_active
                }
            )
            
    except Exception as e:
        logger.error(f"Error toggling quiz active status {quiz_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error updating quiz status: {str(e)}"}
        )


@router.post("/quizzes/bulk-action")
async def bulk_quiz_action(request: Request):
    """Handle bulk actions on multiple quizzes"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )
    
    try:
        # Get form data
        form_data = await request.form()
        action = form_data.get("action")
        quiz_ids_str = form_data.get("quiz_ids", "")
        
        if not action or not quiz_ids_str:
            return JSONResponse(
                status_code=400,
                content={"error": "Action and quiz IDs are required"}
            )
        
        # Parse quiz IDs
        try:
            quiz_ids = [UUID(id_str.strip()) for id_str in quiz_ids_str.split(",") if id_str.strip()]
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid quiz ID format"}
            )
        
        if not quiz_ids:
            return JSONResponse(
                status_code=400,
                content={"error": "No valid quiz IDs provided"}
            )
        
        async with get_db_session() as db:
            # Get quizzes
            result = await db.execute(
                select(Quiz).where(Quiz.id.in_(quiz_ids))
            )
            quizzes = result.scalars().all()
            
            if not quizzes:
                return JSONResponse(
                    status_code=404,
                    content={"error": "No quizzes found"}
                )
            
            success_count = 0
            error_count = 0
            
            # Perform bulk action
            if action == "activate":
                for quiz in quizzes:
                    try:
                        quiz.is_active = True
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error activating quiz {quiz.id}: {e}")
                        error_count += 1
                        
            elif action == "deactivate":
                for quiz in quizzes:
                    try:
                        quiz.is_active = False
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error deactivating quiz {quiz.id}: {e}")
                        error_count += 1
                        
            elif action == "delete":
                for quiz in quizzes:
                    try:
                        # Delete associated user results first
                        user_results_result = await db.execute(
                            select(UserQuizResult).where(UserQuizResult.quiz_id == quiz.id)
                        )
                        user_results = user_results_result.scalars().all()
                        
                        for result in user_results:
                            await db.delete(result)
                        
                        # Delete the quiz
                        await db.delete(quiz)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting quiz {quiz.id}: {e}")
                        error_count += 1
            else:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unknown action: {action}"}
                )
            
            # Commit changes
            await db.commit()
            
            # Prepare response message
            action_past_tense = {
                "activate": "activated",
                "deactivate": "deactivated", 
                "delete": "deleted"
            }.get(action, action)
            
            message = f"Successfully {action_past_tense} {success_count} quiz(es)"
            if error_count > 0:
                message += f", {error_count} failed"
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": message,
                    "success_count": success_count,
                    "error_count": error_count
                }
            )
            
    except Exception as e:
        logger.error(f"Error performing bulk action: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error performing bulk action: {str(e)}"}
        )


@router.get("/quizzes/quick-stats")
async def quiz_quick_stats(request: Request):
    """Get quick statistics for admin dashboard integration"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )
    
    try:
        async with get_db_session() as db:
            # Total quizzes
            total_quizzes_result = await db.execute(select(func.count(Quiz.id)))
            total_quizzes = total_quizzes_result.scalar() or 0
            
            # Active quizzes
            active_quizzes_result = await db.execute(
                select(func.count(Quiz.id)).where(Quiz.is_active == True)
            )
            active_quizzes = active_quizzes_result.scalar() or 0
            
            # Total attempts
            total_attempts_result = await db.execute(select(func.count(UserQuizResult.id)))
            total_attempts = total_attempts_result.scalar() or 0
            
            # Recent attempts (last 7 days)
            from datetime import datetime, timedelta
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            
            recent_attempts_result = await db.execute(
                select(func.count(UserQuizResult.id)).where(
                    UserQuizResult.completed_at >= seven_days_ago
                )
            )
            recent_attempts = recent_attempts_result.scalar() or 0
            
            # Average score
            avg_score_result = await db.execute(select(func.avg(UserQuizResult.percentage)))
            avg_score = avg_score_result.scalar() or 0
            avg_score = round(float(avg_score), 1) if avg_score else 0
            
            return JSONResponse(
                status_code=200,
                content={
                    "total_quizzes": total_quizzes,
                    "active_quizzes": active_quizzes,
                    "total_attempts": total_attempts,
                    "recent_attempts": recent_attempts,
                    "avg_score": avg_score
                }
            )
            
    except Exception as e:
        logger.error(f"Error getting quiz quick stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Error getting statistics: {str(e)}"}
        )