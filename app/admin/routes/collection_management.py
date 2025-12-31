"""
Collection Management routes for admin panel
Provides comprehensive collection CRUD operations and analytics
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from uuid import UUID, uuid4
from typing import Optional, List
import logging
import json

from app.models.myth_fact_collection import MythFactCollection, CollectionMythFact, UserCollectionProgress
from app.models.myth_fact import MythFact
from app.models.category import Category
from app.models.user import User
from app.admin.templates.base import create_html_page
from app.db.database import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/collections", response_class=HTMLResponse)
async def collection_list(
    request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    category: Optional[str] = Query(None, description="Filter by category"),
    difficulty: Optional[str] = Query(None, description="Filter by difficulty"),
    active_only: bool = Query(False, description="Show only active collections")
):
    """Admin list view for myth fact collections with pagination and search"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Build base query
            query = select(MythFactCollection)
            
            # Apply filters
            filters = []
            
            # Search filter
            if search:
                search_term = f"%{search}%"
                filters.append(
                    or_(
                        MythFactCollection.name.ilike(search_term),
                        MythFactCollection.description.ilike(search_term)
                    )
                )
            
            # Category filter
            if category and category != "all":
                filters.append(MythFactCollection.category == category)
            
            # Difficulty filter
            if difficulty and difficulty != "all":
                filters.append(MythFactCollection.difficulty_level == difficulty)
            
            # Active filter
            if active_only:
                filters.append(MythFactCollection.is_active == True)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_count = (await db.execute(count_query)).scalar()
            
            # Apply pagination and ordering
            collections_query = query.order_by(desc(MythFactCollection.created_at)).offset((page - 1) * limit).limit(limit)
            result = await db.execute(collections_query)
            collections = result.scalars().all()
            
            # Calculate pagination info
            total_pages = (total_count + limit - 1) // limit
            has_prev = page > 1
            has_next = page < total_pages
            
            # Get statistics for each collection
            collection_stats = {}
            for collection in collections:
                # Get myth/fact count
                content_count_query = select(func.count()).select_from(
                    select(CollectionMythFact).where(CollectionMythFact.collection_id == collection.id).subquery()
                )
                content_count = (await db.execute(content_count_query)).scalar()
                
                # Get user progress count
                progress_count_query = select(func.count()).select_from(
                    select(UserCollectionProgress).where(UserCollectionProgress.collection_id == collection.id).subquery()
                )
                progress_count = (await db.execute(progress_count_query)).scalar()
                
                collection_stats[str(collection.id)] = {
                    'content_count': content_count,
                    'user_progress_count': progress_count
                }

    except Exception as e:
        logger.error(f"Error fetching collections: {e}")
        # Return error page
        error_content = f"""
        <div style="text-align: center; padding: 2rem;">
            <h2 style="color: #dc3545;">Error Loading Collections</h2>
            <p>An error occurred while loading the collections list.</p>
            <a href="/admin" style="color: #007bff; text-decoration: none;">← Back to Dashboard</a>
        </div>
        """
        return create_html_page("Error - Collections", error_content)

    # Generate collection list HTML
    collection_items = ""
    for collection in collections:
        stats = collection_stats.get(str(collection.id), {'content_count': 0, 'user_progress_count': 0})
        
        status_badge = """
        <span style="background: #28a745; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
            Active
        </span>
        """ if collection.is_active else """
        <span style="background: #6c757d; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
            Inactive
        </span>
        """
        
        difficulty_color = {
            'BEGINNER': '#28a745',
            'INTERMEDIATE': '#ffc107', 
            'ADVANCED': '#dc3545'
        }.get(collection.difficulty_level, '#6c757d')
        
        collection_items += f"""
        <tr style="border-bottom: 1px solid #dee2e6;">
            <td style="padding: 1rem;">
                <div>
                    <strong style="color: #2d3748; font-size: 1rem;">{collection.name}</strong>
                    <div style="color: #718096; font-size: 0.875rem; margin-top: 0.25rem;">
                        {collection.description[:100]}{'...' if len(collection.description) > 100 else ''}
                    </div>
                </div>
            </td>
            <td style="padding: 1rem;">
                <span style="background: {difficulty_color}; color: white; padding: 0.25rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem;">
                    {collection.difficulty_level}
                </span>
            </td>
            <td style="padding: 1rem; text-align: center;">{stats['content_count']}</td>
            <td style="padding: 1rem; text-align: center;">{stats['user_progress_count']}</td>
            <td style="padding: 1rem; text-align: center;">{status_badge}</td>
            <td style="padding: 1rem;">
                <div style="display: flex; gap: 0.5rem;">
                    <a href="/admin/collections/{collection.id}/edit" style="background: #007bff; color: white; padding: 0.375rem 0.75rem; border-radius: 0.25rem; text-decoration: none; font-size: 0.875rem;">
                        Edit
                    </a>
                    <a href="/admin/collections/{collection.id}/analytics" style="background: #17a2b8; color: white; padding: 0.375rem 0.75rem; border-radius: 0.25rem; text-decoration: none; font-size: 0.875rem;">
                        Analytics
                    </a>
                    <button onclick="deleteCollection('{collection.id}')" style="background: #dc3545; color: white; padding: 0.375rem 0.75rem; border-radius: 0.25rem; border: none; cursor: pointer; font-size: 0.875rem;">
                        Delete
                    </button>
                </div>
            </td>
        </tr>
        """

    # Generate pagination HTML
    pagination_html = ""
    if total_pages > 1:
        pagination_html = f"""
        <div style="display: flex; justify-content: center; align-items: center; gap: 0.5rem; margin-top: 2rem;">
            {"" if not has_prev else f'<a href="/admin/collections?page={page-1}&search={search or ""}&category={category or ""}&difficulty={difficulty or ""}" style="padding: 0.5rem 1rem; background: #007bff; color: white; text-decoration: none; border-radius: 0.25rem;">Previous</a>'}
            <span style="color: #6c757d;">Page {page} of {total_pages}</span>
            {"" if not has_next else f'<a href="/admin/collections?page={page+1}&search={search or ""}&category={category or ""}&difficulty={difficulty or ""}" style="padding: 0.5rem 1rem; background: #007bff; color: white; text-decoration: none; border-radius: 0.25rem;">Next</a>'}
        </div>
        """

    content = f"""
    <div style="max-width: 1200px; margin: 0 auto; padding: 2rem;">
        <div style="display: flex; justify-content: between; align-items: center; margin-bottom: 2rem;">
            <div>
                <h1 style="color: #2d3748; margin-bottom: 0.5rem;">Collection Management</h1>
                <p style="color: #718096;">Manage Myths vs Facts collections and organize content</p>
            </div>
            <a href="/admin/collections/create" style="background: #28a745; color: white; padding: 0.75rem 1.5rem; border-radius: 0.5rem; text-decoration: none; font-weight: 600;">
                + Create Collection
            </a>
        </div>

        <!-- Filters -->
        <div style="background: white; padding: 1.5rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 2rem;">
            <form method="get" style="display: grid; grid-template-columns: 1fr 1fr 1fr auto; gap: 1rem; align-items: end;">
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Search</label>
                    <input type="text" name="search" value="{search or ""}" placeholder="Search collections..." 
                           style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                </div>
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Category</label>
                    <select name="category" style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                        <option value="">All Categories</option>
                        <option value="Wildlife" {'selected' if category == 'Wildlife' else ''}>Wildlife</option>
                        <option value="Marine" {'selected' if category == 'Marine' else ''}>Marine Life</option>
                        <option value="Forest" {'selected' if category == 'Forest' else ''}>Forest Conservation</option>
                        <option value="Climate" {'selected' if category == 'Climate' else ''}>Climate Change</option>
                    </select>
                </div>
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Difficulty</label>
                    <select name="difficulty" style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                        <option value="">All Levels</option>
                        <option value="BEGINNER" {'selected' if difficulty == 'BEGINNER' else ''}>Beginner</option>
                        <option value="INTERMEDIATE" {'selected' if difficulty == 'INTERMEDIATE' else ''}>Intermediate</option>
                        <option value="ADVANCED" {'selected' if difficulty == 'ADVANCED' else ''}>Advanced</option>
                    </select>
                </div>
                <button type="submit" style="background: #007bff; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 0.375rem; cursor: pointer;">
                    Filter
                </button>
            </form>
        </div>

        <!-- Collections Table -->
        <div style="background: white; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow: hidden;">
            <table style="width: 100%; border-collapse: collapse;">
                <thead style="background: #f8f9fa;">
                    <tr>
                        <th style="text-align: left; padding: 1rem; font-weight: 600; color: #374151;">Collection</th>
                        <th style="text-align: left; padding: 1rem; font-weight: 600; color: #374151;">Difficulty</th>
                        <th style="text-align: center; padding: 1rem; font-weight: 600; color: #374151;">Content</th>
                        <th style="text-align: center; padding: 1rem; font-weight: 600; color: #374151;">Users</th>
                        <th style="text-align: center; padding: 1rem; font-weight: 600; color: #374151;">Status</th>
                        <th style="text-align: left; padding: 1rem; font-weight: 600; color: #374151;">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {collection_items if collections else '<tr><td colspan="6" style="text-align: center; padding: 2rem; color: #6c757d;">No collections found</td></tr>'}
                </tbody>
            </table>
        </div>

        {pagination_html}

        <!-- Quick Stats -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 2rem;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 0.5rem;">
                <h3 style="margin: 0 0 0.5rem 0;">Total Collections</h3>
                <div style="font-size: 2rem; font-weight: bold;">{total_count}</div>
            </div>
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 1.5rem; border-radius: 0.5rem;">
                <h3 style="margin: 0 0 0.5rem 0;">Active Collections</h3>
                <div style="font-size: 2rem; font-weight: bold;">{len([c for c in collections if c.is_active])}</div>
            </div>
        </div>
    </div>

    <script>
    function deleteCollection(collectionId) {{
        if (confirm('Are you sure you want to delete this collection? This action cannot be undone.')) {{
            fetch('/admin/collections/' + collectionId + '/delete', {{
                method: 'POST',
                headers: {{
                    'Content-Type': 'application/json',
                }},
            }})
            .then(response => {{
                if (response.ok) {{
                    location.reload();
                }} else {{
                    alert('Error deleting collection');
                }}
            }})
            .catch(error => {{
                console.error('Error:', error);
                alert('Error deleting collection');
            }});
        }}
    }}
    </script>
    """

    return create_html_page("Collection Management", content)


@router.get("/collections/create", response_class=HTMLResponse)
async def collection_create_form(request: Request):
    """Show collection creation form"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)

    content = f"""
    <div style="max-width: 800px; margin: 0 auto; padding: 2rem;">
        <div style="margin-bottom: 2rem;">
            <h1 style="color: #2d3748; margin-bottom: 0.5rem;">Create New Collection</h1>
            <a href="/admin/collections" style="color: #007bff; text-decoration: none;">← Back to Collections</a>
        </div>

        <form method="post" action="/admin/collections/create" style="background: white; padding: 2rem; border-radius: 0.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
            <div style="display: grid; gap: 1.5rem;">
                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Collection Name *</label>
                    <input type="text" name="name" required maxlength="200"
                           style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                </div>

                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Description *</label>
                    <textarea name="description" required rows="4"
                              style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem; resize: vertical;"></textarea>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div>
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Category *</label>
                        <select name="category" required style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                            <option value="">Select Category</option>
                            <option value="Wildlife">Wildlife</option>
                            <option value="Marine">Marine Life</option>
                            <option value="Forest">Forest Conservation</option>
                            <option value="Climate">Climate Change</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Difficulty Level *</label>
                        <select name="difficulty_level" required style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                            <option value="">Select Difficulty</option>
                            <option value="BEGINNER">Beginner</option>
                            <option value="INTERMEDIATE">Intermediate</option>
                            <option value="ADVANCED">Advanced</option>
                        </select>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div>
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Custom Points Reward</label>
                        <input type="number" name="custom_points_reward" min="0" 
                               style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                        <small style="color: #6c757d;">Leave empty to use default scoring</small>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Custom Credits Reward</label>
                        <input type="number" name="custom_credits_reward" min="0"
                               style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                        <small style="color: #6c757d;">Leave empty to use default scoring</small>
                    </div>
                </div>

                <div>
                    <label style="display: block; margin-bottom: 0.5rem; font-weight: 600; color: #374151;">Estimated Duration (minutes)</label>
                    <input type="number" name="estimated_duration_minutes" min="1" value="10"
                           style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;">
                </div>

                <div>
                    <label style="display: flex; align-items: center; gap: 0.5rem; font-weight: 600; color: #374151;">
                        <input type="checkbox" name="is_active" value="true" checked style="margin: 0;">
                        Active Collection
                    </label>
                    <small style="color: #6c757d;">Inactive collections won't appear in the frontend</small>
                </div>

                <div style="display: flex; gap: 1rem; justify-content: flex-end; margin-top: 1rem;">
                    <a href="/admin/collections" style="padding: 0.75rem 1.5rem; border: 1px solid #d1d5db; color: #374151; text-decoration: none; border-radius: 0.375rem;">
                        Cancel
                    </a>
                    <button type="submit" style="background: #28a745; color: white; padding: 0.75rem 1.5rem; border: none; border-radius: 0.375rem; cursor: pointer; font-weight: 600;">
                        Create Collection
                    </button>
                </div>
            </div>
        </form>
    </div>
    """

    return create_html_page("Create Collection", content)


@router.post("/collections/create")
async def collection_create(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    difficulty_level: str = Form(...),
    custom_points_reward: Optional[int] = Form(None),
    custom_credits_reward: Optional[int] = Form(None),
    estimated_duration_minutes: int = Form(10),
    is_active: Optional[str] = Form(None)
):
    """Handle collection creation"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)

    try:
        async with get_db_session() as db:
            collection = MythFactCollection(
                id=uuid4(),
                name=name,
                description=description,
                category=category,
                difficulty_level=difficulty_level,
                custom_points_reward=custom_points_reward,
                custom_credits_reward=custom_credits_reward,
                estimated_duration_minutes=estimated_duration_minutes,
                is_active=is_active == "true"
            )
            
            db.add(collection)
            await db.commit()
            
            return RedirectResponse(url="/admin/collections", status_code=302)
            
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        # Redirect back with error
        return RedirectResponse(url="/admin/collections/create?error=creation_failed", status_code=302)


@router.post("/collections/{collection_id}/delete")
async def collection_delete(request: Request, collection_id: UUID):
    """Delete a collection"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        async with get_db_session() as db:
            # Get collection
            result = await db.execute(select(MythFactCollection).where(MythFactCollection.id == collection_id))
            collection = result.scalar_one_or_none()
            
            if not collection:
                return JSONResponse({"error": "Collection not found"}, status_code=404)
            
            # Delete related data first
            await db.execute(select(CollectionMythFact).where(CollectionMythFact.collection_id == collection_id).delete())
            await db.execute(select(UserCollectionProgress).where(UserCollectionProgress.collection_id == collection_id).delete())
            
            # Delete collection
            await db.delete(collection)
            await db.commit()
            
            return JSONResponse({"success": True})
            
    except Exception as e:
        logger.error(f"Error deleting collection: {e}")
        return JSONResponse({"error": "Deletion failed"}, status_code=500)