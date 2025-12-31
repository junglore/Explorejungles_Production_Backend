"""
Content API Routes
Handles blogs, case studies, news articles, and other content
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import re
from slugify import slugify

from app.db.database import get_db
from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
from app.models.user import User
from app.models.category import Category
from app.core.security import get_current_user, get_current_user_optional
from app.schemas.content import (
    ContentCreate,
    ContentUpdate,
    ContentResponse,
    ContentListResponse,
    UserSummary,
    CategorySummary,
    StandardAPIResponse
)
from app.utils.content_formatter import (
    format_content_list,
    format_content_item,
    create_success_response
)

router = APIRouter()


@router.get("/", response_model=StandardAPIResponse)
async def get_content(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Number of items to return"),
    type: Optional[str] = Query(None, description="Filter by content type"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    status: Optional[ContentStatusEnum] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title and content"),
    sort: Optional[str] = Query("created_at", description="Sort field"),
    published_only: bool = Query(True, description="Show only published content"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get content with filtering and pagination - standardized response format"""
    try:
        skip = (page - 1) * limit
        
        query = select(Content).options(
            selectinload(Content.author),
            selectinload(Content.category)
        )
        
        # Apply filters
        if published_only and (not current_user or not current_user.is_superuser):
            query = query.where(Content.status == ContentStatusEnum.PUBLISHED)
        
        # Convert type string to enum if provided
        if type:
            try:
                content_type_enum = ContentTypeEnum(type.lower())
                query = query.where(Content.type == content_type_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid content type: {type}"
                )
            
        if category_id:
            query = query.where(Content.category_id == category_id)
            
        if status and current_user and current_user.is_superuser:
            query = query.where(Content.status == status)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Content.title.ilike(search_term),
                    Content.content.ilike(search_term),
                    Content.excerpt.ilike(search_term)
                )
            )
        
        # Get total count for pagination
        count_query = select(func.count(Content.id))
        # Apply same filters to count query
        if published_only and (not current_user or not current_user.is_superuser):
            count_query = count_query.where(Content.status == ContentStatusEnum.PUBLISHED)
        if type:
            try:
                content_type_enum = ContentTypeEnum(type.lower())
                count_query = count_query.where(Content.type == content_type_enum)
            except ValueError:
                pass
        if category_id:
            count_query = count_query.where(Content.category_id == category_id)
        if status and current_user and current_user.is_superuser:
            count_query = count_query.where(Content.status == status)
        if search:
            search_term = f"%{search}%"
            count_query = count_query.where(
                or_(
                    Content.title.ilike(search_term),
                    Content.content.ilike(search_term),
                    Content.excerpt.ilike(search_term)
                )
            )
        
        total_result = await db.execute(count_query)
        total_items = total_result.scalar()
        
        # Apply pagination and ordering
        if sort == "created_at":
            query = query.order_by(desc(Content.created_at))
        else:
            query = query.order_by(desc(Content.published_at), desc(Content.created_at))
            
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        content_items = result.scalars().all()
        
        # Format response using standardized formatter
        pagination_data = format_content_list(content_items, page, limit, total_items)
        return create_success_response(pagination_data, "Content Fetch Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content_by_id(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    response: Response = None,
    request: Request = None,
):
    """Get specific content by ID"""
    
    result = await db.execute(
        select(Content)
        .options(selectinload(Content.author), selectinload(Content.category))
        .where(Content.id == content_id)
    )
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check if user can view unpublished content
    if content.status != ContentStatusEnum.PUBLISHED:
        if not current_user or (not current_user.is_superuser and current_user.id != content.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Content not available"
            )
    
    # Enforce 3-free-blogs rule for unauthenticated users using a cookie counter
    try:
        if (
            not current_user
            and content.type in [ContentTypeEnum.BLOG, ContentTypeEnum.ARTICLE]
        ):
            current_views = 0
            if request is not None:
                cookie_val = request.cookies.get("free_blog_views")
                try:
                    current_views = int(cookie_val) if cookie_val is not None else 0
                except ValueError:
                    current_views = 0

            if current_views >= 3:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Login required to continue reading more blogs"
                )

            # Increment cookie counter
            new_count = current_views + 1
            if response is not None:
                response.set_cookie(
                    key="free_blog_views",
                    value=str(new_count),
                    max_age=30 * 24 * 60 * 60,  # 30 days
                    httponly=False,
                    samesite="lax"
                )
    except HTTPException:
        # re-raise auth gating HTTP errors
        raise
    except Exception:
        # Do not block content on unexpected cookie errors
        pass

    # Increment view count
    content.view_count = (content.view_count or 0) + 1
    await db.commit()
    
    # Prepare response
    author_summary = UserSummary(
        id=content.author.id,
        username=content.author.username
    ) if content.author else None
    
    category_summary = CategorySummary(
        id=content.category.id,
        name=content.category.name,
        slug=content.category.slug
    ) if content.category else None
    
    return ContentResponse(
        id=content.id,
        title=content.title,
        content=content.content,
        excerpt=content.excerpt,
        featured_image=content.featured_image,
        banner=content.banner,
        video=content.video,
        featured=content.featured,
        feature_place=content.feature_place,
        slug=content.slug,
        type=content.type,
        status=content.status,
        view_count=content.view_count,
        meta_description=content.meta_description,
        content_metadata=content.content_metadata,
        published_at=content.published_at,
        created_at=content.created_at,
        updated_at=content.updated_at,
        author=author_summary,
        category=category_summary
    )


@router.get("/slug/{slug}", response_model=ContentResponse)
async def get_content_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
    response: Response = None,
    request: Request = None,
):
    """Get specific content by slug"""
    
    result = await db.execute(
        select(Content)
        .options(selectinload(Content.author), selectinload(Content.category))
        .where(Content.slug == slug)
    )
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check if user can view unpublished content
    if content.status != ContentStatusEnum.PUBLISHED:
        if not current_user or (not current_user.is_superuser and current_user.id != content.author_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Content not available"
            )
    
    # Enforce 3-free-blogs rule for unauthenticated users using a cookie counter
    try:
        if (
            not current_user
            and content.type in [ContentTypeEnum.BLOG, ContentTypeEnum.ARTICLE]
        ):
            current_views = 0
            if request is not None:
                cookie_val = request.cookies.get("free_blog_views")
                try:
                    current_views = int(cookie_val) if cookie_val is not None else 0
                except ValueError:
                    current_views = 0

            if current_views >= 3:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Login required to continue reading more blogs"
                )

            # Increment cookie counter
            new_count = current_views + 1
            if response is not None:
                response.set_cookie(
                    key="free_blog_views",
                    value=str(new_count),
                    max_age=30 * 24 * 60 * 60,  # 30 days
                    httponly=False,
                    samesite="lax"
                )
    except HTTPException:
        # re-raise auth gating HTTP errors
        raise
    except Exception:
        # Do not block content on unexpected cookie errors
        pass

    # Increment view count
    content.view_count = (content.view_count or 0) + 1
    await db.commit()
    
    # Prepare response (same as above)
    author_summary = UserSummary(
        id=content.author.id,
        username=content.author.username
    ) if content.author else None
    
    category_summary = CategorySummary(
        id=content.category.id,
        name=content.category.name,
        slug=content.category.slug
    ) if content.category else None
    
    return ContentResponse(
        id=content.id,
        title=content.title,
        content=content.content,
        excerpt=content.excerpt,
        featured_image=content.featured_image,
        banner=content.banner,
        video=content.video,
        featured=content.featured,
        feature_place=content.feature_place,
        slug=content.slug,
        type=content.type,
        status=content.status,
        view_count=content.view_count,
        meta_description=content.meta_description,
        content_metadata=content.content_metadata,
        published_at=content.published_at,
        created_at=content.created_at,
        updated_at=content.updated_at,
        author=author_summary,
        category=category_summary
    )


@router.post("/", response_model=ContentResponse)
async def create_content(
    content_data: ContentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new content"""
    
    # Validate category if provided
    if content_data.category_id:
        result = await db.execute(select(Category).where(Category.id == content_data.category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    # Generate slug from title
    base_slug = slugify(content_data.title)
    slug = base_slug
    counter = 1
    
    # Ensure slug uniqueness
    while True:
        result = await db.execute(select(Content).where(Content.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Create content
    content = Content(
        title=content_data.title,
        content=content_data.content,
        type=content_data.type,
        category_id=content_data.category_id,
        featured_image=content_data.featured_image,
        banner=content_data.banner,
        video=content_data.video,
        featured=content_data.featured,
        feature_place=content_data.feature_place,
        excerpt=content_data.excerpt,
        meta_description=content_data.meta_description,
        content_metadata=content_data.content_metadata or {},
        status=content_data.status,
        slug=slug,
        author_id=current_user.id,
        published_at=datetime.utcnow() if content_data.status == ContentStatusEnum.PUBLISHED else None
    )
    
    db.add(content)
    await db.commit()
    await db.refresh(content, ["author", "category"])
    
    # Prepare response
    author_summary = UserSummary(
        id=content.author.id,
        username=content.author.username
    )
    
    category_summary = CategorySummary(
        id=content.category.id,
        name=content.category.name,
        slug=content.category.slug
    ) if content.category else None
    
    return ContentResponse(
        id=content.id,
        title=content.title,
        content=content.content,
        excerpt=content.excerpt,
        featured_image=content.featured_image,
        banner=content.banner,
        video=content.video,
        featured=content.featured,
        feature_place=content.feature_place,
        slug=content.slug,
        type=content.type,
        status=content.status,
        view_count=content.view_count,
        meta_description=content.meta_description,
        content_metadata=content.content_metadata,
        published_at=content.published_at,
        created_at=content.created_at,
        updated_at=content.updated_at,
        author=author_summary,
        category=category_summary
    )


@router.put("/{content_id}", response_model=ContentResponse)
async def update_content(
    content_id: UUID,
    content_data: ContentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update content"""
    
    result = await db.execute(
        select(Content)
        .options(selectinload(Content.author), selectinload(Content.category))
        .where(Content.id == content_id)
    )
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check permissions
    if not current_user.is_superuser and current_user.id != content.author_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this content"
        )
    
    # Update fields
    update_data = content_data.dict(exclude_unset=True)
    
    # Validate category if being updated
    if 'category_id' in update_data and update_data['category_id']:
        result = await db.execute(select(Category).where(Category.id == update_data['category_id']))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    # Update slug if title changed
    if 'title' in update_data and update_data['title'] != content.title:
        base_slug = slugify(update_data['title'])
        slug = base_slug
        counter = 1
        
        # Ensure slug uniqueness (excluding current content)
        while True:
            result = await db.execute(
                select(Content).where(and_(Content.slug == slug, Content.id != content_id))
            )
            if not result.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        update_data['slug'] = slug
    
    # Set published_at if status changed to published
    if 'status' in update_data and update_data['status'] == ContentStatusEnum.PUBLISHED and not content.published_at:
        update_data['published_at'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(content, field, value)
    
    await db.commit()
    await db.refresh(content)
    
    # Prepare response
    author_summary = UserSummary(
        id=content.author.id,
        username=content.author.username
    )
    
    category_summary = CategorySummary(
        id=content.category.id,
        name=content.category.name,
        slug=content.category.slug
    ) if content.category else None
    
    return ContentResponse(
        id=content.id,
        title=content.title,
        content=content.content,
        excerpt=content.excerpt,
        featured_image=content.featured_image,
        banner=content.banner,
        video=content.video,
        featured=content.featured,
        feature_place=content.feature_place,
        slug=content.slug,
        type=content.type,
        status=content.status,
        view_count=content.view_count,
        meta_description=content.meta_description,
        content_metadata=content.content_metadata,
        published_at=content.published_at,
        created_at=content.created_at,
        updated_at=content.updated_at,
        author=author_summary,
        category=category_summary
    )


@router.delete("/{content_id}")
async def delete_content(
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete content"""
    
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content not found"
        )
    
    # Check permissions
    if not current_user.is_superuser and current_user.id != content.author_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this content"
        )
    
    await db.delete(content)
    await db.commit()
    
    return {"message": "Content deleted successfully"}


# Specific endpoints for different content types
@router.get("/blogs/", response_model=List[ContentListResponse])
async def get_blogs(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get blog posts"""
    return await get_content(
        skip=skip, limit=limit, content_type=ContentTypeEnum.BLOG,
        category_id=category_id, db=db, current_user=current_user
    )


@router.get("/case-studies/", response_model=List[ContentListResponse])
async def get_case_studies(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get case studies"""
    return await get_content(
        skip=skip, limit=limit, content_type=ContentTypeEnum.CASE_STUDY,
        category_id=category_id, db=db, current_user=current_user
    )


@router.get("/daily-updates/", response_model=List[ContentListResponse])
async def get_daily_updates(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get daily updates"""
    return await get_content(
        skip=skip, limit=limit, content_type=ContentTypeEnum.DAILY_UPDATE,
        category_id=category_id, db=db, current_user=current_user
    )


@router.get("/news/", response_model=List[ContentListResponse])
async def get_news(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get news articles"""
    return await get_content(
        skip=skip, limit=limit, content_type=ContentTypeEnum.NEWS,
        category_id=category_id, db=db, current_user=current_user
    )


# Frontend API endpoints for resources
@router.get("/resources/blogs")
async def get_blogs_for_frontend(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get published blogs and articles for frontend"""
    try:
        offset = (page - 1) * limit
        
        # Get published blogs and articles
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(
                Content.type.in_([ContentTypeEnum.BLOG, ContentTypeEnum.ARTICLE]),
                Content.status == ContentStatusEnum.PUBLISHED
            )
            .order_by(Content.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        blogs = result.scalars().all()
        
        # Get total count
        count_result = await db.execute(
            select(func.count(Content.id))
            .where(
                Content.type.in_([ContentTypeEnum.BLOG, ContentTypeEnum.ARTICLE]),
                Content.status == ContentStatusEnum.PUBLISHED
            )
        )
        total = count_result.scalar()
        
        return {
            "blogs": [
                {
                    "id": str(blog.id),
                    "title": blog.title,
                    "excerpt": blog.excerpt,
                    "content": blog.content,
                    "author": {
                        "id": str(blog.author.id),
                        "username": blog.author.username,
                        "full_name": blog.author.full_name
                    } if blog.author else None,
                    "category": {
                        "id": str(blog.category.id),
                        "name": blog.category.name,
                        "slug": blog.category.slug
                    } if blog.category else None,
                    "published_at": blog.published_at.isoformat() if blog.published_at else None,
                    "reading_time": blog.content_metadata.get('reading_time') if blog.content_metadata else None,
                    "tags": blog.content_metadata.get('tags', []) if blog.content_metadata else [],
                    "type": blog.type.value
                }
                for blog in blogs
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/casestudies")
async def get_casestudies_for_frontend(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get published case studies for frontend"""
    try:
        offset = (page - 1) * limit
        
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(
                Content.type == ContentTypeEnum.CASE_STUDY,
                Content.status == ContentStatusEnum.PUBLISHED
            )
            .order_by(Content.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        casestudies = result.scalars().all()
        
        count_result = await db.execute(
            select(func.count(Content.id))
            .where(
                Content.type == ContentTypeEnum.CASE_STUDY,
                Content.status == ContentStatusEnum.PUBLISHED
            )
        )
        total = count_result.scalar()
        
        return {
            "casestudies": [
                {
                    "id": str(study.id),
                    "title": study.title,
                    "excerpt": study.excerpt,
                    "content": study.content,
                    "featured_image": study.featured_image,
                    "banner": study.banner,
                    "author_name": study.author_name,
                    "author": {
                        "id": str(study.author.id),
                        "username": study.author.username,
                        "full_name": study.author.full_name
                    } if study.author else None,
                    "category": {
                        "id": str(study.category.id),
                        "name": study.category.name,
                        "slug": study.category.slug
                    } if study.category else None,
                    "published_at": study.published_at.isoformat() if study.published_at else None,
                    "created_at": study.created_at.isoformat() if study.created_at else None,
                    "reading_time": study.content_metadata.get('reading_time') if study.content_metadata else None,
                    "tags": study.content_metadata.get('tags', []) if study.content_metadata else []
                }
                for study in casestudies
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/conservation")
async def get_conservation_for_frontend(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get published conservation efforts for frontend"""
    try:
        offset = (page - 1) * limit
        
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(
                Content.type == ContentTypeEnum.CONSERVATION_EFFORT,
                Content.status == ContentStatusEnum.PUBLISHED
            )
            .order_by(Content.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        conservation = result.scalars().all()
        
        count_result = await db.execute(
            select(func.count(Content.id))
            .where(
                Content.type == ContentTypeEnum.CONSERVATION_EFFORT,
                Content.status == ContentStatusEnum.PUBLISHED
            )
        )
        total = count_result.scalar()
        
        return {
            "conservation": [
                {
                    "id": str(item.id),
                    "title": item.title,
                    "excerpt": item.excerpt,
                    "content": item.content,
                    "featured_image": item.featured_image,
                    "banner": item.banner,
                    "author_name": item.author_name,
                    "author": {
                        "id": str(item.author.id),
                        "username": item.author.username,
                        "full_name": item.author.full_name
                    } if item.author else None,
                    "category": {
                        "id": str(item.category.id),
                        "name": item.category.name,
                        "slug": item.category.slug
                    } if item.category else None,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "reading_time": item.content_metadata.get('reading_time') if item.content_metadata else None,
                    "tags": item.content_metadata.get('tags', []) if item.content_metadata else []
                }
                for item in conservation
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/resources/dailyupdates")
async def get_dailyupdates_for_frontend(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get published daily updates and news for frontend"""
    try:
        offset = (page - 1) * limit
        
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(
                Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS]),
                Content.status == ContentStatusEnum.PUBLISHED
            )
            .order_by(Content.published_at.desc())
            .offset(offset)
            .limit(limit)
        )
        updates = result.scalars().all()
        
        count_result = await db.execute(
            select(func.count(Content.id))
            .where(
                Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS]),
                Content.status == ContentStatusEnum.PUBLISHED
            )
        )
        total = count_result.scalar()
        
        return {
            "updates": [
                {
                    "id": str(update.id),
                    "title": update.title,
                    "excerpt": update.excerpt,
                    "content": update.content,
                    "featured_image": update.featured_image,
                    "banner": update.banner,
                    "author_name": update.author_name,
                    "author": {
                        "id": str(update.author.id),
                        "username": update.author.username,
                        "full_name": update.author.full_name
                    } if update.author else None,
                    "category": {
                        "id": str(update.category.id),
                        "name": update.category.name,
                        "slug": update.category.slug
                    } if update.category else None,
                    "published_at": update.published_at.isoformat() if update.published_at else None,
                    "created_at": update.created_at.isoformat() if update.created_at else None,
                    "reading_time": update.content_metadata.get('reading_time') if update.content_metadata else None,
                    "tags": update.content_metadata.get('tags', []) if update.content_metadata else [],
                    "type": update.type.value
                }
                for update in updates
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
