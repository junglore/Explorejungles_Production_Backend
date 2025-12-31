# 

"""
Main admin router that combines all admin routes
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.admin.templates.base import create_html_page
from app.admin.routes.blog import router as blog_router
from app.admin.routes.case_study import router as case_study_router
from app.admin.routes.conservation import router as conservation_router
from app.admin.routes.daily_update import router as daily_update_router
from app.admin.routes.manage import router as manage_router
from app.admin.routes.uploads import router as upload_router
from app.admin.routes.media import router as media_router
from app.admin.routes.myths_facts import router as myths_facts_router
from app.admin.routes.podcasts import router as podcasts_router
from app.admin.routes.quizzes import router as quizzes_router
from app.admin.routes.settings import router as settings_router
from app.admin.routes.leaderboard_admin import router as leaderboard_admin_router
from app.admin.routes.analytics_admin import router as analytics_admin_router
from app.admin.routes.category_management import router as category_management_router
from app.admin.routes.quiz_mvf_config import router as quiz_mvf_config_router
from app.admin.routes.data_reset import router as data_reset_router
from app.admin.routes.discussion_moderation import router as discussion_moderation_router
from app.admin.routes.national_parks_management import router as national_parks_router
from app.admin.routes.video_stats import router as video_stats_router
from app.admin.routes.videos import router as videos_router
from app.admin.routes.channels import router as channels_router
from app.admin.routes.analytics import router as video_analytics_router
router = APIRouter()

# Include sub-routers
router.include_router(blog_router)
router.include_router(case_study_router)
router.include_router(conservation_router)
router.include_router(daily_update_router)
router.include_router(manage_router)
router.include_router(upload_router)
router.include_router(media_router, prefix="/media")
router.include_router(myths_facts_router)
router.include_router(podcasts_router, prefix="/podcasts")
router.include_router(quizzes_router)
router.include_router(settings_router)
router.include_router(leaderboard_admin_router)
router.include_router(analytics_admin_router)
router.include_router(category_management_router)
router.include_router(quiz_mvf_config_router)
router.include_router(data_reset_router, prefix="/data-reset")
router.include_router(discussion_moderation_router, prefix="/discussions", tags=["Admin - Discussions"])
router.include_router(national_parks_router, prefix="/national-parks", tags=["Admin - National Parks"])
router.include_router(video_stats_router, tags=["Admin - Video Stats"])  # Individual video stats
router.include_router(channels_router, tags=["Admin - Channels"])  # Must come before videos_router
router.include_router(videos_router, tags=["Admin - Videos"])
router.include_router(video_analytics_router, tags=["Admin - Video Analytics"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Admin login page"""
    login_form = """
    <div style="display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f8fafc;">
        <div style="background: white; padding: 2rem; border-radius: 12px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); width: 100%; max-width: 400px;">
            <h2 style="text-align: center; margin-bottom: 2rem; color: #1e293b;">Junglore Admin Login</h2>
            <form method="post" action="/admin/login">
                <div style="margin-bottom: 1rem;">
                    <label style="display: block; font-weight: 600; margin-bottom: 0.5rem;">Email</label>
                    <input name="username" type="email" required 
                           style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px;" />
                </div>
                <div style="margin-bottom: 1.5rem;">
                    <label style="display: block; font-weight: 600; margin-bottom: 0.5rem;">Password</label>
                    <input name="password" type="password" required 
                           style="width: 100%; padding: 0.75rem; border: 1px solid #d1d5db; border-radius: 8px;" />
                </div>
                <button type="submit" 
                        style="width: 100%; padding: 0.75rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer;">
                    Login
                </button>
            </form>
        </div>
    </div>
    """
    return HTMLResponse(content=login_form)

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
    """Handle admin login"""
    try:
        # Authenticate against database using proper password hashing
        from sqlalchemy import select
        from app.models.user import User
        from app.core.security import verify_password
        
        # Get user by email
        result = await db.execute(
            select(User).where(User.email == username, User.is_active == True, User.is_superuser == True)
        )
        user = result.scalar_one_or_none()
        
        if user and verify_password(password, user.hashed_password):
            request.session["authenticated"] = True
            request.session["user_id"] = str(user.id)
            request.session["user_email"] = user.email
            request.session["username"] = username
            return RedirectResponse(url="/admin/", status_code=302)
        else:
            return RedirectResponse(url="/admin/login?error=1", status_code=302)
            
    except Exception as e:
        # Log error and redirect to login with error
        import logging
        logging.error(f"Admin login error: {e}")
        return RedirectResponse(url="/admin/login?error=1", status_code=302)

@router.get("/token")
async def get_admin_token(request: Request):
    """Get JWT token for admin session - allows admin dashboard HTML to call API endpoints"""
    from fastapi import HTTPException
    from app.core.security import create_access_token
    from app.db.database import get_db_session
    from app.models.user import User
    from sqlalchemy import select
    
    # Check if admin is authenticated via session
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get username from session or use default admin
    username = request.session.get("username", "admin@junglore.com")
    
    # Fetch the actual user from database to ensure they exist and are superuser
    async with get_db_session() as session:
        result = await session.execute(
            select(User).where(User.email == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not user.is_superuser:
            raise HTTPException(status_code=403, detail="Not authorized - user is not superuser")
    
    # Create JWT token with the user's ID (UUID) as the 'sub' claim
    access_token = create_access_token(
        data={"sub": str(user.id)}
    )
    
    return {"access_token": access_token, "token_type": "bearer"}



@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Modern admin dashboard"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    dashboard_content = """
        <div class="page-header">
            <h1 class="page-title">Dashboard</h1>
            <p class="page-subtitle">Welcome to Junglore Wildlife Conservation Admin Panel</p>
            <button id="refresh-components-btn" class="btn btn-secondary" style="margin-left: auto; display: none;">
                <i class="fas fa-sync-alt"></i> Refresh Components
            </button>
        </div>
        
        <div class="dashboard-grid">
            <div class="dashboard-card">
                <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 12px; margin-right: 1rem;">
                        <i class="fas fa-plus" style="color: white; font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <h3 style="color: #2d3748; margin-bottom: 0.25rem; font-size: 1.25rem; font-weight: 700;">Quick Create</h3>
                        <p style="color: #718096; font-size: 0.95rem;">Add new content to your platform</p>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <a href="/admin/create/blog" class="btn btn-primary" style="justify-content: flex-start; text-decoration: none;">
                        <i class="fas fa-blog"></i> Blog Post
                    </a>
                    <a href="/admin/create/case-study" class="btn btn-secondary" style="justify-content: flex-start; text-decoration: none;">
                        <i class="fas fa-microscope"></i> Case Study
                    </a>
                    <a href="/admin/create/conservation" class="btn btn-success" style="justify-content: flex-start; text-decoration: none;">
                        <i class="fas fa-leaf"></i> Conservation Effort
                    </a>
                    <a href="/admin/create/daily-update" class="btn btn-primary" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                        <i class="fas fa-newspaper"></i> Daily Update
                    </a>
                    <a href="/admin/myths-facts/create" class="btn btn-primary" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        <i class="fas fa-question-circle"></i> Myth vs Fact
                    </a>
                    <a href="/admin/podcasts/create" class="btn btn-primary" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);">
                        <i class="fas fa-podcast"></i> Podcast
                    </a>
                    <a href="/admin/quizzes/create" class="btn btn-primary" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
                        <i class="fas fa-question-circle"></i> Quiz
                    </a>
                    <a href="/admin/videos" class="btn btn-primary" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                        <i class="fas fa-video"></i> Video
                    </a>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                    <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1rem; border-radius: 12px; margin-right: 1rem;">
                        <i class="fas fa-cog" style="color: white; font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <h3 style="color: #2d3748; margin-bottom: 0.25rem; font-size: 1.25rem; font-weight: 700;">Management</h3>
                        <p style="color: #718096; font-size: 0.95rem;">Organize and manage your content</p>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                    <a href="/admin/manage/content" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white;">
                        <i class="fas fa-list-alt"></i> All Content
                    </a>
                    <a href="/admin/manage/categories" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white;">
                        <i class="fas fa-tags"></i> Category Management (MVF)</a>
                    <a href="/admin/media/library" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                        <i class="fas fa-images"></i> Media Library
                    </a>
                    <a href="/admin/media/featured" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">
                        <i class="fas fa-star"></i> Featured Images
                    </a>
                    <a href="/admin/myths-facts" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                        <i class="fas fa-question-circle"></i> Myths vs Facts
                    </a>
                    <a href="/admin/podcasts" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); color: white;">
                        <i class="fas fa-podcast"></i> Podcasts
                    </a>
                    <a href="/admin/quizzes" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white;">
                        <i class="fas fa-question-circle"></i> Quizzes
                    </a>
                    <a href="/admin/quizzes/analytics" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); color: white;">
                        <i class="fas fa-chart-bar"></i> Quiz Analytics
                    </a>
                    <a href="/admin/videos" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">
                        <i class="fas fa-video"></i> Videos
                    </a>
                    <a href="/admin/quiz-mvf-config" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #ff9a56 0%, #ff6b35 100%); color: white;">
                        <i class="fas fa-cogs"></i> Quiz/MVF Config Panel
                    </a>
                    <a href="/admin/analytics" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                        <i class="fas fa-chart-line"></i> Advanced Analytics
                    </a>
                    <a href="/admin/leaderboard" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white;">
                        <i class="fas fa-trophy"></i> Leaderboard Admin
                    </a>
                    <a href="/admin/data-reset" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white;">
                        <i class="fas fa-exclamation-triangle"></i> Production Data Reset
                    </a>
                    <a href="/admin/discussions/dashboard" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                        <i class="fas fa-comments"></i> Discussions & Categories
                    </a>
                    <a href="/admin/national-parks" class="btn" style="justify-content: flex-start; text-decoration: none; background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); color: white;">
                        <i class="fas fa-tree"></i> National Parks
                    </a>
                </div>
            </div>
            
            <div class="dashboard-card">
                <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
                    <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1rem; border-radius: 12px; margin-right: 1rem;">
                        <i class="fas fa-chart-line" style="color: white; font-size: 1.5rem;"></i>
                    </div>
                    <div>
                        <h3 style="color: #2d3748; margin-bottom: 0.25rem; font-size: 1.25rem; font-weight: 700;">Statistics</h3>
                        <p style="color: #718096; font-size: 0.95rem;">Platform overview and metrics</p>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                    <div style="text-align: center; padding: 1rem; background: #f7fafc; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: #667eea;">0</div>
                        <div style="font-size: 0.875rem; color: #718096;">Total Posts</div>
                    </div>
                    <div style="text-align: center; padding: 1rem; background: #f7fafc; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: #48bb78;">0</div>
                        <div style="font-size: 0.875rem; color: #718096;">Published</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="dashboard-card">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
                <div>
                    <h3 style="color: #2d3748; margin-bottom: 0.25rem; font-size: 1.25rem; font-weight: 700;">Recent Activity</h3>
                    <p style="color: #718096; font-size: 0.95rem;">Latest content and system updates</p>
                </div>
                <i class="fas fa-history" style="color: #cbd5e0; font-size: 1.5rem;"></i>
            </div>
            <div style="text-align: center; padding: 2rem; color: #a0aec0;">
                <i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                <p style="font-size: 1.125rem; font-weight: 500;">No recent activity</p>
                <p style="font-size: 0.95rem;">Start creating content to see activity here</p>
            </div>
        </div>
    """
    
    return HTMLResponse(content=create_html_page("Dashboard", dashboard_content, "dashboard"))

@router.get("/discussions/dashboard", response_class=HTMLResponse)
async def discussions_dashboard(request: Request):
    """Discussion moderation dashboard"""
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Read and return the HTML file
    import os
    template_path = os.path.join(os.path.dirname(__file__), "../templates/discussions/dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)

@router.get("/categories", response_class=HTMLResponse)
async def categories_management(request: Request):
    """Categories management dashboard"""
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Read and return the HTML file
    import os
    from app.core.config import settings
    template_path = os.path.join(os.path.dirname(__file__), "../templates/categories/list.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Replace hardcoded localhost:8000 with actual backend URL
    html_content = html_content.replace(
        "const API_BASE = 'http://localhost:8000/api/v1';",
        f"const API_BASE = '{settings.BACKEND_URL}/api/v1';"
    )
    
    return HTMLResponse(content=html_content)

@router.get("/national-parks", response_class=HTMLResponse)
async def national_parks_management(request: Request):
    """National parks management dashboard"""
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    # Read and return the HTML file
    import os
    from app.core.config import settings
    template_path = os.path.join(os.path.dirname(__file__), "../templates/national_parks/list.html")
    with open(template_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # Replace hardcoded localhost:8000 with actual backend URL
    html_content = html_content.replace(
        "const API_BASE = 'http://localhost:8000/api/v1';",
        f"const API_BASE = '{settings.BACKEND_URL}/api/v1';"
    )
    
    return HTMLResponse(content=html_content)

@router.patch("/categories/{category_id}")
async def toggle_category_status(
    request: Request,
    category_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Toggle category active status (Admin only - uses session auth)"""
    # Check authentication
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        from uuid import UUID
        from sqlalchemy import select
        from app.models.category import Category
        
        # Parse category ID
        try:
            cat_uuid = UUID(category_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid category ID")
        
        # Get request body
        body = await request.json()
        is_active = body.get('is_active')
        
        if is_active is None:
            raise HTTPException(status_code=400, detail="is_active field is required")
        
        # Fetch category
        result = await db.execute(
            select(Category).where(Category.id == cat_uuid)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Update status
        category.is_active = is_active
        await db.commit()
        await db.refresh(category)
        
        return {
            "message": "Category status updated successfully",
            "category": {
                "id": str(category.id),
                "name": category.name,
                "slug": category.slug,
                "is_active": category.is_active
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update category: {str(e)}"
        )

@router.get("/logout")
async def logout(request: Request):
    """Admin logout"""
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=302)