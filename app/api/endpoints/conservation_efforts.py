"""
Conservation Efforts API Routes - Following junglore.com pattern
Dedicated conservation efforts endpoints with file upload functionality
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


# Conservation Efforts endpoints following junglore.com pattern

@router.get("/", response_model=StandardAPIResponse)
async def fetch_all_conservation_efforts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(9, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch all conservation efforts with pagination - standardized response format"""
    try:
        skip = (page - 1) * limit
        
        # Build query
        query = select(Content).options(
            selectinload(Content.author),
            selectinload(Content.category)
        ).where(
            Content.type == ContentTypeEnum.CONSERVATION_EFFORT,
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
            Content.type == ContentTypeEnum.CONSERVATION_EFFORT,
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
        
        # Get conservation efforts
        query = query.order_by(desc(Content.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        conservation_efforts = result.scalars().all()
        
        # Calculate total pages
        total_pages = (total_items + limit - 1) // limit
        
        # Format response using standardized formatter
        pagination_data = format_content_list(conservation_efforts, page, limit, total_items)
        return create_success_response(pagination_data, "Conservation Efforts Fetch Success")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/{effort_id}", response_model=dict)
async def fetch_single_conservation_effort(
    effort_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Fetch single conservation effort by ID - matching junglore.com pattern"""
    try:
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(Content.id == effort_id, Content.type == ContentTypeEnum.CONSERVATION_EFFORT)
        )
        effort = result.scalar_one_or_none()
        
        if not effort:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conservation Effort not found"
            )
        
        # Format response to match junglore.com pattern
        formatted_effort = {
            "id": str(effort.id),
            "title": effort.title,
            "slug": effort.slug,
            "category_id": str(effort.category_id) if effort.category_id else None,
            "banner": effort.banner,
            "image": effort.featured_image,
            "video": effort.video,
            "description": effort.excerpt,
            "content": effort.content,
            "featured": effort.featured,
            "feature_place": effort.feature_place,
            "status": effort.status == ContentStatusEnum.PUBLISHED,
            "createdAt": effort.created_at.isoformat(),
            "updatedAt": effort.updated_at.isoformat()
        }
        
        return {
            "message": "Conservation Effort Fetch Success",
            "data": formatted_effort,
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
async def create_conservation_effort(
    title: str = Form(...),
    content: str = Form(...),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    banner: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new conservation effort with file uploads - matching junglore.com pattern"""
    try:
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
        
        # Create conservation effort
        effort = Content(
            title=title,
            content=content,
            type=ContentTypeEnum.CONSERVATION_EFFORT,
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
        
        db.add(effort)
        await db.commit()
        await db.refresh(effort)
        
        # Format response
        formatted_effort = {
            "id": str(effort.id),
            "title": effort.title,
            "slug": effort.slug,
            "category_id": str(effort.category_id) if effort.category_id else None,
            "banner": effort.banner,
            "image": effort.featured_image,
            "video": effort.video,
            "description": effort.excerpt,
            "featured": effort.featured,
            "feature_place": effort.feature_place,
            "status": effort.status == ContentStatusEnum.PUBLISHED,
            "createdAt": effort.created_at.isoformat(),
            "updatedAt": effort.updated_at.isoformat()
        }
        
        return {
            "message": "Conservation Effort Created Success",
            "data": formatted_effort,
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/{effort_id}", response_model=dict)
async def update_conservation_effort(
    effort_id: UUID,
    title: Optional[str] = Form(None),
    content: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    category_id: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    banner: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update conservation effort - matching junglore.com pattern"""
    try:
        # Get existing conservation effort
        result = await db.execute(
            select(Content).where(Content.id == effort_id, Content.type == ContentTypeEnum.CONSERVATION_EFFORT)
        )
        effort = result.scalar_one_or_none()
        
        if not effort:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conservation Effort not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != effort.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this conservation effort"
            )
        
        # Handle file uploads
        if image:
            effort.featured_image = await save_uploaded_file(image, "image")
        
        if banner:
            effort.banner = await save_uploaded_file(banner, "image")
        
        if video:
            effort.video = await save_uploaded_file(video, "video")
        
        # Update fields
        if title:
            effort.title = title
            # Update slug if title changed
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            
            # Ensure slug uniqueness (excluding current effort)
            while True:
                result = await db.execute(
                    select(Content).where(and_(Content.slug == slug, Content.id != effort_id))
                )
                if not result.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            effort.slug = slug
        
        if content:
            effort.content = content
        
        if description:
            effort.excerpt = description
        
        if category_id:
            try:
                category_uuid = UUID(category_id)
                cat_result = await db.execute(select(Category).where(Category.id == category_uuid))
                if not cat_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid category ID"
                    )
                effort.category_id = category_uuid
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid category ID format"
                )
        
        await db.commit()
        await db.refresh(effort)
        
        # Format response
        formatted_effort = {
            "id": str(effort.id),
            "title": effort.title,
            "slug": effort.slug,
            "category_id": str(effort.category_id) if effort.category_id else None,
            "banner": effort.banner,
            "image": effort.featured_image,
            "video": effort.video,
            "description": effort.excerpt,
            "featured": effort.featured,
            "feature_place": effort.feature_place,
            "status": effort.status == ContentStatusEnum.PUBLISHED,
            "createdAt": effort.created_at.isoformat(),
            "updatedAt": effort.updated_at.isoformat()
        }
        
        return {
            "message": "Conservation Effort Update Success",
            "data": formatted_effort,
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/feature/{effort_id}", response_model=dict)
async def feature_conservation_effort(
    effort_id: UUID,
    place: int = Form(..., ge=1, le=3, description="Featured placement (1-3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Feature a conservation effort - matching junglore.com pattern"""
    try:
        # Check if there are already 3 featured conservation efforts
        featured_count_result = await db.execute(
            select(func.count(Content.id)).where(
                Content.type == ContentTypeEnum.CONSERVATION_EFFORT,
                Content.featured == True
            )
        )
        featured_count = featured_count_result.scalar()
        
        if featured_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already there are 3 featured conservation efforts"
            )
        
        # Get conservation effort
        result = await db.execute(
            select(Content).where(Content.id == effort_id, Content.type == ContentTypeEnum.CONSERVATION_EFFORT)
        )
        effort = result.scalar_one_or_none()
        
        if not effort:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conservation Effort not found"
            )
        
        # Update featured status
        effort.featured = True
        effort.feature_place = place
        
        await db.commit()
        await db.refresh(effort)
        
        # Format response
        formatted_effort = {
            "id": str(effort.id),
            "title": effort.title,
            "featured": effort.featured,
            "feature_place": effort.feature_place,
        }
        
        return {
            "message": "Conservation Effort Featured Success",
            "data": formatted_effort,
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.delete("/{effort_id}", response_model=dict)
async def delete_conservation_effort(
    effort_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete conservation effort - matching junglore.com pattern"""
    try:
        # Get conservation effort
        result = await db.execute(
            select(Content).where(Content.id == effort_id, Content.type == ContentTypeEnum.CONSERVATION_EFFORT)
        )
        effort = result.scalar_one_or_none()
        
        if not effort:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conservation Effort not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != effort.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this conservation effort"
            )
        
        await db.delete(effort)
        await db.commit()
        
        return {
            "message": "Conservation Effort Delete Success",
            "data": {"id": str(effort_id)},
            "status": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )
