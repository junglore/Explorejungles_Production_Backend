"""
Daily News API Routes - Following junglore.com pattern
Dedicated daily news endpoints with file upload functionality
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import aiofiles
import os
from pathlib import Path
from uuid import uuid4

try:
    from slugify import slugify
except ImportError:
    def slugify(text):
        import re
        return re.sub(r'[^a-zA-Z0-9]+', '-', text.lower()).strip('-')

from app.db.database import get_db
from app.models.content import Content, ContentTypeEnum, ContentStatusEnum
from app.models.category import Category
from app.models.user import User
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

# Upload settings
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/jpg", "image/avif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/mov", "video/wmv", "video/webm"}


def is_allowed_file_type(content_type: str) -> bool:
    """Check if the file type is allowed"""
    return content_type in ALLOWED_IMAGE_TYPES or content_type in ALLOWED_VIDEO_TYPES


async def save_uploaded_file(file: UploadFile, file_type: str) -> str:
    """Save uploaded file and return the file path"""
    if not file:
        return None
        
    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Validate file type
    if not is_allowed_file_type(file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {file.content_type} not allowed"
        )
    
    # Create appropriate directory
    type_dir = UPLOAD_DIR / f"{file_type}s"
    type_dir.mkdir(exist_ok=True)
    
    # Generate unique filename
    file_extension = Path(file.filename).suffix.lower()
    unique_filename = f"{uuid4()}{file_extension}"
    file_path = type_dir / unique_filename
    
    # Save file
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)
    
    return f"{file_type}s/{unique_filename}"


# Daily News endpoints following junglore.com pattern

@router.get("/", response_model=StandardAPIResponse)
async def fetch_all_daily_news(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(9, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch all daily news with pagination - standardized response format"""
    try:
        skip = (page - 1) * limit
        
        # Build query - includes both DAILY_UPDATE and NEWS types
        query = select(Content).options(
            selectinload(Content.author),
            selectinload(Content.category)
        ).where(
            Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS]),
            Content.status == ContentStatusEnum.PUBLISHED
        )
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Content.title.ilike(search_term),
                    Content.content.ilike(search_term)
                )
            )
        
        # Apply category filter
        if category_id:
            query = query.where(Content.category_id == category_id)
        
        # Get total count
        count_query = select(func.count(Content.id)).where(
            Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS]),
            Content.status == ContentStatusEnum.PUBLISHED
        )
        if search:
            search_term = f"%{search}%"
            count_query = count_query.where(
                or_(
                    Content.title.ilike(search_term),
                    Content.content.ilike(search_term)
                )
            )
        if category_id:
            count_query = count_query.where(Content.category_id == category_id)
        
        total_result = await db.execute(count_query)
        total_items = total_result.scalar()
        
        # Get daily news
        query = query.order_by(desc(Content.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        daily_news = result.scalars().all()
        
        # Calculate total pages
        total_pages = (total_items + limit - 1) // limit
        
        # Format response using standardized formatter
        pagination_data = format_content_list(daily_news, page, limit, total_items)
        return create_success_response(pagination_data, "Daily News Fetch Success")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/{news_id}", response_model=dict)
async def fetch_single_daily_news(
    news_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Fetch single daily news by ID - matching junglore.com pattern"""
    try:
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(
                Content.id == news_id, 
                Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS])
            )
        )
        news = result.scalar_one_or_none()
        
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily News not found"
            )
        
        # Format response to match junglore.com pattern
        formatted_news = {
            "id": str(news.id),
            "title": news.title,
            "slug": news.slug,
            "category_id": str(news.category_id) if news.category_id else None,
            "banner": news.banner,
            "image": news.featured_image,
            "video": news.video,
            "description": news.excerpt,
            "content": news.content,
            "featured": news.featured,
            "feature_place": news.feature_place,
            "status": news.status == ContentStatusEnum.PUBLISHED,
            "type": news.type.value,
            "createdAt": news.created_at.isoformat(),
            "updatedAt": news.updated_at.isoformat()
        }
        
        return {
            "message": "Daily News Fetch Success",
            "data": formatted_news,
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.post("/", response_model=dict)
async def create_daily_news(
    title: str = Form(...),
    content: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    news_type: str = Form("daily_update", description="Type: daily_update or news"),
    image: Optional[UploadFile] = File(None),
    banner: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new daily news with file uploads - matching junglore.com pattern"""
    try:
        # Validate news type
        if news_type not in ["daily_update", "news"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="news_type must be 'daily_update' or 'news'"
            )
        
        content_type = ContentTypeEnum.DAILY_UPDATE if news_type == "daily_update" else ContentTypeEnum.NEWS
        
        # Handle file uploads
        image_path = None
        banner_path = None
        video_path = None
        
        if image:
            image_path = await save_uploaded_file(image, "image")
        
        if banner:
            banner_path = await save_uploaded_file(banner, "image")
        
        if video:
            video_path = await save_uploaded_file(video, "video")
        
        # Validate category if provided
        category_uuid = None
        if category_id:
            try:
                category_uuid = UUID(category_id)
                cat_result = await db.execute(select(Category).where(Category.id == category_uuid))
                if not cat_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid category ID"
                    )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid category ID format"
                )
        
        # Generate slug from title
        base_slug = slugify(title)
        slug = base_slug
        counter = 1
        
        # Ensure slug uniqueness
        while True:
            result = await db.execute(select(Content).where(Content.slug == slug))
            if not result.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create daily news
        news = Content(
            title=title,
            content=content,
            type=content_type,
            category_id=category_uuid,
            featured_image=image_path,
            banner=banner_path,
            video=video_path,
            excerpt=description,
            slug=slug,
            author_id=current_user.id,
            status=ContentStatusEnum.PUBLISHED,
            published_at=datetime.utcnow()
        )
        
        db.add(news)
        await db.commit()
        await db.refresh(news)
        
        # Format response
        formatted_news = {
            "id": str(news.id),
            "title": news.title,
            "slug": news.slug,
            "category_id": str(news.category_id) if news.category_id else None,
            "banner": news.banner,
            "image": news.featured_image,
            "video": news.video,
            "description": news.excerpt,
            "featured": news.featured,
            "feature_place": news.feature_place,
            "status": news.status == ContentStatusEnum.PUBLISHED,
            "type": news.type.value,
            "createdAt": news.created_at.isoformat(),
            "updatedAt": news.updated_at.isoformat()
        }
        
        return {
            "message": "Daily News Created Success",
            "data": formatted_news,
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/{news_id}", response_model=dict)
async def update_daily_news(
    news_id: UUID,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    news_type: Optional[str] = Form(None, description="Type: daily_update or news"),
    image: Optional[UploadFile] = File(None),
    banner: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update daily news - matching junglore.com pattern"""
    try:
        # Get existing daily news
        result = await db.execute(
            select(Content).where(
                Content.id == news_id, 
                Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS])
            )
        )
        news = result.scalar_one_or_none()
        
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily News not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != news.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this daily news"
            )
        
        # Handle file uploads
        if image:
            news.featured_image = await save_uploaded_file(image, "image")
        
        if banner:
            news.banner = await save_uploaded_file(banner, "image")
        
        if video:
            news.video = await save_uploaded_file(video, "video")
        
        # Update fields
        if title:
            news.title = title
            # Update slug if title changed
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            
            # Ensure slug uniqueness (excluding current news)
            while True:
                result = await db.execute(
                    select(Content).where(and_(Content.slug == slug, Content.id != news_id))
                )
                if not result.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            news.slug = slug
        
        if content:
            news.content = content
        
        if description:
            news.excerpt = description
        
        if news_type:
            if news_type not in ["daily_update", "news"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="news_type must be 'daily_update' or 'news'"
                )
            news.type = ContentTypeEnum.DAILY_UPDATE if news_type == "daily_update" else ContentTypeEnum.NEWS
        
        if category_id:
            try:
                category_uuid = UUID(category_id)
                cat_result = await db.execute(select(Category).where(Category.id == category_uuid))
                if not cat_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid category ID"
                    )
                news.category_id = category_uuid
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid category ID format"
                )
        
        await db.commit()
        await db.refresh(news)
        
        # Format response
        formatted_news = {
            "id": str(news.id),
            "title": news.title,
            "slug": news.slug,
            "category_id": str(news.category_id) if news.category_id else None,
            "banner": news.banner,
            "image": news.featured_image,
            "video": news.video,
            "description": news.excerpt,
            "featured": news.featured,
            "feature_place": news.feature_place,
            "status": news.status == ContentStatusEnum.PUBLISHED,
            "type": news.type.value,
            "createdAt": news.created_at.isoformat(),
            "updatedAt": news.updated_at.isoformat()
        }
        
        return {
            "message": "Daily News Update Success",
            "data": formatted_news,
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/feature/{news_id}", response_model=dict)
async def feature_daily_news(
    news_id: UUID,
    place: int = Form(..., ge=1, le=3, description="Featured placement (1-3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Feature daily news - matching junglore.com pattern"""
    try:
        # Check if there are already 3 featured daily news
        featured_count_result = await db.execute(
            select(func.count(Content.id)).where(
                Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS]),
                Content.featured == True
            )
        )
        featured_count = featured_count_result.scalar()
        
        if featured_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already there are 3 featured daily news"
            )
        
        # Get daily news
        result = await db.execute(
            select(Content).where(
                Content.id == news_id, 
                Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS])
            )
        )
        news = result.scalar_one_or_none()
        
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily News not found"
            )
        
        # Update featured status
        news.featured = True
        news.feature_place = place
        
        await db.commit()
        await db.refresh(news)
        
        # Format response
        formatted_news = {
            "id": str(news.id),
            "title": news.title,
            "featured": news.featured,
            "feature_place": news.feature_place,
        }
        
        return {
            "message": "Daily News Featured Success",
            "data": formatted_news,
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.delete("/{news_id}", response_model=dict)
async def delete_daily_news(
    news_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete daily news - matching junglore.com pattern"""
    try:
        # Get daily news
        result = await db.execute(
            select(Content).where(
                Content.id == news_id, 
                Content.type.in_([ContentTypeEnum.DAILY_UPDATE, ContentTypeEnum.NEWS])
            )
        )
        news = result.scalar_one_or_none()
        
        if not news:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Daily News not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != news.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this daily news"
            )
        
        await db.delete(news)
        await db.commit()
        
        return {
            "message": "Daily News Delete Success",
            "data": {"id": str(news_id)},
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )
