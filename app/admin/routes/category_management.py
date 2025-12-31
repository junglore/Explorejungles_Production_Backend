"""
Enhanced Category Management Routes for MVF System

This module provides comprehensive category management functionality for the
Myths vs Facts system, including:
- Category creation with custom credits and featured status
- Category editing and deletion with proper cascade handling
- MVF-specific features and analytics
- Integration with the admin panel interface

Features:
- Custom credits per category
- Featured category selection (only one at a time)
- MVF enable/disable toggle
- Category analytics (card count, play statistics)
- Proper error handling and validation
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, text
from sqlalchemy.orm import selectinload
from app.models.category import Category
from app.models.myth_fact import MythFact
from app.models.site_setting import SiteSetting
from app.admin.templates.base import create_html_page
from app.db.database import get_db
import logging
from typing import Optional
from uuid import UUID
import re

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/manage/categories", response_class=HTMLResponse)
async def manage_categories(request: Request, db: AsyncSession = Depends(get_db)):
    """Enhanced category management page with MVF features"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        # Get categories with myth fact counts
        result = await db.execute(
            select(
                Category,
                func.count(MythFact.id).label('myth_fact_count')
            )
            .outerjoin(MythFact, Category.id == MythFact.category_id)
            .group_by(Category.id)
            .order_by(desc(Category.is_featured), Category.name)
        )
        categories_with_counts = result.all()
        
        # Get current base scoring config
        config_result = await db.execute(
            select(SiteSetting).where(SiteSetting.key == 'mythsVsFacts_config')
        )
        config_setting = config_result.scalar_one_or_none()
        base_credits = 3  # Default
        base_points = 5   # Default
        
        if config_setting and config_setting.value:
            import json
            config_data = json.loads(config_setting.value)
            base_credits = config_data.get('baseCreditsPerGame', 3)
            base_points = config_data.get('basePointsPerCard', 5)
        
        # Generate category table rows
        category_rows = ""
        for category, myth_fact_count in categories_with_counts:
            # Status indicators
            status_badges = []
            if category.is_featured:
                status_badges.append('<span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-right: 4px;">⭐ Featured</span>')
            if category.mvf_enabled:
                status_badges.append('<span style="background: #10b981; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-right: 4px;">MVF Enabled</span>')
            if not category.is_active:
                status_badges.append('<span style="background: #ef4444; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; margin-right: 4px;">Inactive</span>')
            
            # Credits display (custom or base)
            credits_display = f"{category.custom_credits or base_credits} credits"
            if category.custom_credits:
                credits_display += f" <small style='color: #3b82f6;'>(custom)</small>"
            else:
                credits_display += f" <small style='color: #6b7280;'>(base)</small>"
            
            category_rows += f"""
            <tr style="border-bottom: 1px solid #e5e7eb;">
                <td style="padding: 1rem;">
                    <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">{category.name}</div>
                    <div style="font-size: 0.875rem; color: #6b7280;">{category.description[:100] + '...' if category.description and len(category.description) > 100 else category.description or 'No description'}</div>
                </td>
                <td style="padding: 1rem; text-align: center;">
                    <div style="font-weight: 600; color: #1f2937; font-size: 1.25rem;">{myth_fact_count}</div>
                    <div style="font-size: 0.75rem; color: #6b7280;">cards</div>
                </td>
                <td style="padding: 1rem; text-align: center;">
                    <div style="font-weight: 600; color: #1f2937;">{credits_display}</div>
                </td>
                <td style="padding: 1rem;">
                    {''.join(status_badges) if status_badges else '<span style="color: #9ca3af;">No special status</span>'}
                </td>
                <td style="padding: 1rem; text-align: center; color: #6b7280; font-size: 0.875rem;">
                    {category.created_at.strftime('%b %d, %Y') if category.created_at else 'Unknown'}
                </td>
                <td style="padding: 1rem;">
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <button onclick="editCategory('{category.id}')" 
                                style="background: #3b82f6; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.875rem;">
                            <i class="fas fa-edit"></i> Edit
                        </button>
                        <button onclick="deleteCategory('{category.id}', '{category.name}')" 
                                style="background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 0.875rem;"
                                {'disabled' if myth_fact_count > 0 else ''}>
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </td>
            </tr>
            """
        
        categories_page = f"""
            <div class="page-header">
                <h1 class="page-title">Category Management</h1>
                <p class="page-subtitle">Manage categories for Myths vs Facts system with custom rewards</p>
            </div>
            
            <div id="message-container"></div>
            
            <!-- Quick Stats -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; border-radius: 12px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 4px;">{len(categories_with_counts)}</div>
                            <div style="opacity: 0.9;">Total Categories</div>
                        </div>
                        <i class="fas fa-tags" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
                <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 1.5rem; border-radius: 12px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 4px;">{len([c for c, _ in categories_with_counts if c.mvf_enabled])}</div>
                            <div style="opacity: 0.9;">MVF Enabled</div>
                        </div>
                        <i class="fas fa-question-circle" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
                <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 1.5rem; border-radius: 12px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 4px;">{sum(count for _, count in categories_with_counts)}</div>
                            <div style="opacity: 0.9;">Total Cards</div>
                        </div>
                        <i class="fas fa-cards" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
                <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white; padding: 1.5rem; border-radius: 12px;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <div>
                            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 4px;">{len([c for c, _ in categories_with_counts if c.is_featured])}</div>
                            <div style="opacity: 0.9;">Featured</div>
                        </div>
                        <i class="fas fa-star" style="font-size: 2rem; opacity: 0.7;"></i>
                    </div>
                </div>
            </div>
            
            <!-- Actions Bar -->
            <div style="background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: gap: 1rem;">
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <h3 style="color: #1e293b; margin: 0;">Categories</h3>
                        <div style="font-size: 0.875rem; color: #64748b; background: #f1f5f9; padding: 4px 8px; border-radius: 6px;">
                            Base: {base_credits} credits, {base_points} points per card
                        </div>
                    </div>
                    <button onclick="showCreateForm()" 
                            style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600;">
                        <i class="fas fa-plus"></i> Create Category
                    </button>
                </div>
            </div>
            
            <!-- Categories Table -->
            <div style="background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);">
                <div style="overflow-x: auto;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f8fafc; border-bottom: 2px solid #e2e8f0;">
                                <th style="padding: 1rem; text-align: left; font-weight: 600; color: #374151;">Category</th>
                                <th style="padding: 1rem; text-align: center; font-weight: 600; color: #374151;">Cards</th>
                                <th style="padding: 1rem; text-align: center; font-weight: 600; color: #374151;">Credits</th>
                                <th style="padding: 1rem; text-align: left; font-weight: 600; color: #374151;">Status</th>
                                <th style="padding: 1rem; text-align: center; font-weight: 600; color: #374151;">Created</th>
                                <th style="padding: 1rem; text-align: left; font-weight: 600; color: #374151;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {category_rows if category_rows else '<tr><td colspan="6" style="padding: 3rem; text-align: center; color: #64748b;"><i class="fas fa-folder-open" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.3; display: block;"></i>No categories found<br><small>Create your first category to get started</small></td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>
            
            <!-- Create/Edit Form Modal -->
            <div id="categoryModal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); z-index: 1000;">
                <div style="position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 12px; padding: 2rem; width: 90%; max-width: 600px; max-height: 90vh; overflow-y: auto;">
                    <form id="categoryForm" onsubmit="submitCategory(event)">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                            <h2 id="modalTitle" style="color: #1e293b; margin: 0;">Create Category</h2>
                            <button type="button" onclick="closeModal()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6b7280;">×</button>
                        </div>
                        
                        <input type="hidden" id="categoryId" name="categoryId">
                        
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: #374151;">Category Name *</label>
                            <input type="text" id="categoryName" name="name" required 
                                   style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px;" 
                                   placeholder="e.g., Wildlife Safety">
                        </div>
                        
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: #374151;">Description</label>
                            <textarea id="categoryDescription" name="description" rows="3"
                                      style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px;" 
                                      placeholder="Brief description of this category..."></textarea>
                        </div>
                        
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: #374151;">Custom Credits</label>
                            <input type="number" id="categoryCredits" name="custom_credits" min="1" max="100"
                                   style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px;" 
                                   placeholder="Leave empty to use base credits ({base_credits})">
                            <small style="color: #6b7280;">Credits awarded when user completes this category</small>
                        </div>
                        
                        <div style="margin-bottom: 1rem;">
                            <label style="display: block; font-weight: 600; margin-bottom: 0.5rem; color: #374151;">Image URL</label>
                            <input type="url" id="categoryImage" name="image_url"
                                   style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px;" 
                                   placeholder="https://example.com/image.jpg">
                        </div>
                        
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem;">
                            <div>
                                <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                                    <input type="checkbox" id="categoryFeatured" name="is_featured" 
                                           style="width: 18px; height: 18px;">
                                    <span style="font-weight: 600; color: #374151;">Featured Category</span>
                                </label>
                                <small style="color: #6b7280; display: block; margin-top: 4px;">Auto-loads as default in MVF game</small>
                            </div>
                            <div>
                                <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                                    <input type="checkbox" id="categoryMvfEnabled" name="mvf_enabled" checked 
                                           style="width: 18px; height: 18px;">
                                    <span style="font-weight: 600; color: #374151;">MVF Enabled</span>
                                </label>
                                <small style="color: #6b7280; display: block; margin-top: 4px;">Show in Myths vs Facts game</small>
                            </div>
                        </div>
                        
                        <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                            <button type="button" onclick="closeModal()" 
                                    style="background: #6b7280; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer;">
                                Cancel
                            </button>
                            <button type="submit" 
                                    style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600;">
                                <span id="submitText">Create Category</span>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
            
            <script>
                function showCreateForm() {{
                    document.getElementById('modalTitle').textContent = 'Create Category';
                    document.getElementById('submitText').textContent = 'Create Category';
                    document.getElementById('categoryForm').reset();
                    document.getElementById('categoryId').value = '';
                    document.getElementById('categoryMvfEnabled').checked = true;
                    document.getElementById('categoryModal').style.display = 'block';
                }}
                
                async function editCategory(categoryId) {{
                    try {{
                        const response = await fetch(`/admin/categories/get/${{categoryId}}`);
                        const category = await response.json();
                        
                        document.getElementById('modalTitle').textContent = 'Edit Category';
                        document.getElementById('submitText').textContent = 'Update Category';
                        document.getElementById('categoryId').value = category.id;
                        document.getElementById('categoryName').value = category.name;
                        document.getElementById('categoryDescription').value = category.description || '';
                        document.getElementById('categoryCredits').value = category.custom_credits || '';
                        document.getElementById('categoryImage').value = category.image_url || '';
                        document.getElementById('categoryFeatured').checked = category.is_featured;
                        document.getElementById('categoryMvfEnabled').checked = category.mvf_enabled;
                        document.getElementById('categoryModal').style.display = 'block';
                    }} catch (error) {{
                        alert('Error loading category: ' + error.message);
                    }}
                }}
                
                async function deleteCategory(categoryId, categoryName) {{
                    if (confirm(`Are you sure you want to delete "${{categoryName}}"? This action cannot be undone.`)) {{
                        try {{
                            const response = await fetch(`/admin/categories/delete/${{categoryId}}`, {{
                                method: 'POST',
                                headers: {{ 'Content-Type': 'application/json' }}
                            }});
                            
                            const result = await response.json();
                            if (result.success) {{
                                showMessage('Category deleted successfully!', 'success');
                                setTimeout(() => window.location.reload(), 1000);
                            }} else {{
                                alert('Error: ' + result.error);
                            }}
                        }} catch (error) {{
                            alert('Network error: ' + error.message);
                        }}
                    }}
                }}
                
                async function submitCategory(event) {{
                    event.preventDefault();
                    
                    const formData = new FormData(event.target);
                    const categoryId = formData.get('categoryId');
                    const isEdit = !!categoryId;
                    
                    try {{
                        const response = await fetch(`/admin/categories/${{isEdit ? 'update' : 'create'}}`, {{
                            method: 'POST',
                            body: formData
                        }});
                        
                        const result = await response.json();
                        if (result.success) {{
                            showMessage(`Category ${{isEdit ? 'updated' : 'created'}} successfully!`, 'success');
                            closeModal();
                            setTimeout(() => window.location.reload(), 1000);
                        }} else {{
                            alert('Error: ' + result.error);
                        }}
                    }} catch (error) {{
                        alert('Network error: ' + error.message);
                    }}
                }}
                
                function closeModal() {{
                    document.getElementById('categoryModal').style.display = 'none';
                }}
                
                function showMessage(message, type) {{
                    const container = document.getElementById('message-container');
                    const bgColor = type === 'success' ? '#10b981' : '#ef4444';
                    container.innerHTML = `
                        <div style="background: ${{bgColor}}; color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                            ${{message}}
                        </div>
                    `;
                    setTimeout(() => container.innerHTML = '', 5000);
                }}
                
                // Close modal on outside click
                document.getElementById('categoryModal').onclick = function(e) {{
                    if (e.target === this) closeModal();
                }}
            </script>
        """
        
        return HTMLResponse(content=create_html_page("Category Management", categories_page, "categories"))
        
    except Exception as e:
        logger.error(f"Error in manage_categories: {e}")
        error_page = f"""
            <div style="text-align: center; padding: 2rem;">
                <h2 style="color: #ef4444;">Error Loading Categories</h2>
                <p style="color: #6b7280;">{str(e)}</p>
                <a href="/admin/" style="color: #3b82f6;">← Back to Dashboard</a>
            </div>
        """
        return HTMLResponse(content=create_html_page("Error", error_page, "error"))

@router.get("/categories/get/{category_id}")
async def get_category(category_id: str, db: AsyncSession = Depends(get_db)):
    """Get category data for editing"""
    try:
        result = await db.execute(
            select(Category).where(Category.id == UUID(category_id))
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        return {
            "id": str(category.id),
            "name": category.name,
            "description": category.description,
            "image_url": category.image_url,
            "custom_credits": category.custom_credits,
            "is_featured": category.is_featured,
            "mvf_enabled": category.mvf_enabled,
            "is_active": category.is_active
        }
        
    except Exception as e:
        logger.error(f"Error getting category {category_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/categories/create")
async def create_category(
    request: Request,
    name: str = Form(...),
    description: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    custom_credits: Optional[str] = Form(None),  # Changed to str to handle empty values
    is_featured: bool = Form(False),
    mvf_enabled: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """Create new category with MVF features"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse({"success": False, "error": "Not authenticated"}, status_code=401)
    
    try:
        # Handle custom_credits validation and conversion
        custom_credits_value = None
        if custom_credits and custom_credits.strip():
            try:
                custom_credits_value = int(custom_credits.strip())
                if custom_credits_value < 1 or custom_credits_value > 100:
                    return JSONResponse({"success": False, "error": "Custom credits must be between 1 and 100"}, status_code=400)
            except ValueError:
                return JSONResponse({"success": False, "error": "Custom credits must be a valid number"}, status_code=400)
        
        # Generate slug from name
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
        
        # If setting as featured, remove featured status from other categories
        if is_featured:
            await db.execute(
                text("UPDATE categories SET is_featured = FALSE WHERE is_featured = TRUE")
            )
        
        # Create new category
        new_category = Category(
            name=name,
            slug=slug,
            description=description,
            image_url=image_url,
            custom_credits=custom_credits_value,  # Use the validated value
            is_featured=is_featured,
            mvf_enabled=mvf_enabled,
            is_active=True
        )
        
        db.add(new_category)
        await db.commit()
        await db.refresh(new_category)
        
        logger.info(f"Category created: {name} (ID: {new_category.id})")
        return JSONResponse({"success": True, "id": str(new_category.id)})
        
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        await db.rollback()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/categories/update")
async def update_category(
    request: Request,
    categoryId: str = Form(...),
    name: str = Form(...),
    description: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    custom_credits: Optional[str] = Form(None),  # Changed to str to handle empty values
    is_featured: bool = Form(False),
    mvf_enabled: bool = Form(True),
    db: AsyncSession = Depends(get_db)
):
    """Update existing category"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse({"success": False, "error": "Not authenticated"}, status_code=401)
    
    try:
        # Handle custom_credits validation and conversion
        custom_credits_value = None
        if custom_credits and custom_credits.strip():
            try:
                custom_credits_value = int(custom_credits.strip())
                if custom_credits_value < 1 or custom_credits_value > 100:
                    return JSONResponse({"success": False, "error": "Custom credits must be between 1 and 100"}, status_code=400)
            except ValueError:
                return JSONResponse({"success": False, "error": "Custom credits must be a valid number"}, status_code=400)
        
        # Get existing category
        result = await db.execute(
            select(Category).where(Category.id == UUID(categoryId))
        )
        category = result.scalar_one_or_none()
        
        if not category:
            return JSONResponse({"success": False, "error": "Category not found"}, status_code=404)
        
        # If setting as featured, remove featured status from other categories
        if is_featured and not category.is_featured:
            await db.execute(
                text("UPDATE categories SET is_featured = FALSE WHERE is_featured = TRUE")
            )
        
        # Update category fields
        category.name = name
        category.slug = re.sub(r'[^a-zA-Z0-9]+', '-', name.lower()).strip('-')
        category.description = description
        category.image_url = image_url
        category.custom_credits = custom_credits_value  # Use the validated value
        category.is_featured = is_featured
        category.mvf_enabled = mvf_enabled
        
        await db.commit()
        
        logger.info(f"Category updated: {name} (ID: {categoryId})")
        return JSONResponse({"success": True})
        
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        await db.rollback()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@router.post("/categories/delete/{category_id}")
async def delete_category(
    request: Request,
    category_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete category (only if no myth facts associated)"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse({"success": False, "error": "Not authenticated"}, status_code=401)
    
    try:
        # Check if category has myth facts
        result = await db.execute(
            select(func.count(MythFact.id)).where(MythFact.category_id == UUID(category_id))
        )
        myth_fact_count = result.scalar()
        
        if myth_fact_count > 0:
            return JSONResponse({
                "success": False, 
                "error": f"Cannot delete category with {myth_fact_count} myth fact cards. Please move or delete the cards first."
            }, status_code=400)
        
        # Delete category
        result = await db.execute(
            select(Category).where(Category.id == UUID(category_id))
        )
        category = result.scalar_one_or_none()
        
        if not category:
            return JSONResponse({"success": False, "error": "Category not found"}, status_code=404)
        
        await db.delete(category)
        await db.commit()
        
        logger.info(f"Category deleted: {category.name} (ID: {category_id})")
        return JSONResponse({"success": True})
        
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        await db.rollback()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)