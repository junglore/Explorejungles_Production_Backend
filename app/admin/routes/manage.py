"""
Content management routes for admin panel
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, desc
from app.models.content import Content
from app.admin.templates.base import create_html_page
from app.db.database import get_db_session

router = APIRouter()

@router.get("/manage/content", response_class=HTMLResponse)
async def manage_content(request: Request):
    """Content management page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Get content from database
    content_items = []
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(Content).order_by(desc(Content.created_at)).limit(50)
            )
            content_items = result.scalars().all()
    except Exception as e:
        content_items = []
    
    # Generate content table
    content_rows = ""
    for item in content_items:
        status_color = "#10b981" if item.status.value == "published" else "#f59e0b"
        
        # --- FIX START: Precompute HTML with backslashes outside f-string ---
        status_style = f'background: {status_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem;'
        edit_link_style = 'color: #3b82f6; text-decoration: none; margin-right: 1rem;'
        delete_link_style = 'color: #ef4444; text-decoration: none;'
        # --- FIX END ---
        
        content_rows += f"""
        <tr>
            <td>{item.title[:50]}{'...' if len(item.title) > 50 else ''}</td>
            <td>{item.type.value.replace('_', ' ').title()}</td>
            <td>{item.author_name or 'JUNGLORE'}</td>
            <td><span style="{status_style}">{item.status.value.title()}</span></td>
            <td>{item.created_at.strftime('%b %d, %Y') if item.created_at else 'Unknown'}</td>
            <td>
                <a href="/admin/edit/{'conservation' if item.type.value == 'conservation_effort' else item.type.value.replace('_', '-')}/{item.id}" style="{edit_link_style}">Edit</a>
                <a href="#" onclick="deleteContent('{item.id}')" style="{delete_link_style}">Delete</a>
            </td>
        </tr>
        """
    
    manage_content_page = f"""
        <div class="page-header">
            <h1 class="page-title">Manage Content</h1>
            <p class="page-subtitle">View and manage all your content</p>
        </div>
        
        <div id="message-container"></div>
        
        <div style="background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="color: #1e293b; margin: 0;">All Content</h3>
                <div style="display: flex; gap: 1rem;">
                    <select id="typeFilter" style="padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px;">
                        <option value="">All Types</option>
                        <option value="blog">Blog Posts</option>
                        <option value="case_study">Case Studies</option>
                        <option value="conservation_effort">Conservation Efforts</option>
                        <option value="daily_update">Daily Updates</option>
                    </select>
                    <select id="statusFilter" style="padding: 0.5rem; border: 1px solid #d1d5db; border-radius: 6px;">
                        <option value="">All Status</option>
                        <option value="published">Published</option>
                        <option value="draft">Draft</option>
                    </select>
                </div>
            </div>
            
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: #f8fafc; border-bottom: 1px solid #e2e8f0;">
                            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #374151;">Title</th>
                            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #374151;">Type</th>
                            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #374151;">Author</th>
                            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #374151;">Status</th>
                            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #374151;">Created</th>
                            <th style="padding: 0.75rem; text-align: left; font-weight: 600; color: #374151;">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {content_rows if content_rows else '<tr><td colspan="6" style="padding: 2rem; text-align: center; color: #64748b;">No content found</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
            async function deleteContent(contentId) {{
                if (confirm('Are you sure you want to delete this content? This action cannot be undone.')) {{
                    try {{
                        const response = await fetch(`/admin/delete/${{contentId}}`, {{
                            method: 'POST',
                            headers: {{
                                'Content-Type': 'application/json',
                            }}
                        }});
                        
                        if (response.ok) {{
                            // Reload the page to show updated content list
                            window.location.reload();
                        }} else {{
                            const error = await response.json();
                            alert('Error deleting content: ' + (error.error || 'Unknown error'));
                        }}
                    }} catch (error) {{
                        alert('Network error: ' + error.message);
                    }}
                }}
            }}
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Manage Content", manage_content_page, "content"))

@router.post("/delete/{content_id}")
async def delete_content(request: Request, content_id: str):
    """Delete content"""
    try:
        from uuid import UUID
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"Content deletion started for ID: {content_id}")
        
        # Check authentication
        if not request.session.get("authenticated"):
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": False, "error": "Not authenticated"}, status_code=401)
        
        # Delete content
        async with get_db_session() as db:
            result = await db.execute(
                select(Content).where(Content.id == UUID(content_id))
            )
            content = result.scalar_one_or_none()
            
            if not content:
                from fastapi.responses import JSONResponse
                return JSONResponse({"success": False, "error": "Content not found"}, status_code=404)
            
            await db.delete(content)
            await db.commit()
            
            logger.info(f"Content deleted successfully with ID: {content_id}")
            
            from fastapi.responses import JSONResponse
            return JSONResponse({"success": True, "message": "Content deleted successfully"})
            
    except Exception as e:
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(f"Content deletion error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        from fastapi.responses import JSONResponse
        return JSONResponse({"success": False, "error": f"Server error: {str(e)}"}, status_code=500)