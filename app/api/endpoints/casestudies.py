"""
Case Studies API Routes - Following junglore.com pattern
Dedicated case study endpoints with file upload functionality
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


# Case Studies endpoints following junglore.com pattern

@router.get("/", response_model=StandardAPIResponse)
async def fetch_all_case_studies(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(9, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch all case studies with pagination - matching junglore.com pattern"""
    try:
        skip = (page - 1) * limit
        
        # Build query
        query = select(Content).options(
            selectinload(Content.author),
            selectinload(Content.category)
        ).where(
            Content.type == ContentTypeEnum.CASE_STUDY,
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
            Content.type == ContentTypeEnum.CASE_STUDY,
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
        
        # Get case studies
        query = query.order_by(desc(Content.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        case_studies = result.scalars().all()
        
        # Calculate total pages
        total_pages = (total_items + limit - 1) // limit
        
        # Format response using standardized formatter
        pagination_data = format_content_list(case_studies, page, limit, total_items)
        return create_success_response(pagination_data, "Case Studies Fetch Success")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/{case_study_id}", response_model=StandardAPIResponse)
async def fetch_single_case_study(
    case_study_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Fetch single case study by ID - matching junglore.com pattern"""
    try:
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(Content.id == case_study_id, Content.type == ContentTypeEnum.CASE_STUDY)
        )
        case_study = result.scalar_one_or_none()
        
        if not case_study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case Study not found"
            )
        
        # Format response using standardized formatter
        formatted_case_study = format_content_item(case_study, include_full_content=True)
        return create_success_response(formatted_case_study, "Case Study Fetch Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.post("/", response_model=StandardAPIResponse)
async def create_case_study(
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
    """Create new case study with file uploads - standardized response format"""
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
        
        # Create case study
        case_study = Content(
            title=title,
            content=content,
            type=ContentTypeEnum.CASE_STUDY,
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
        
        db.add(case_study)
        await db.commit()
        await db.refresh(case_study)
        
        # Format response using standardized formatter
        formatted_case_study = format_content_item(case_study)
        return create_success_response(formatted_case_study, "Case Study Created Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/{case_study_id}", response_model=StandardAPIResponse)
async def update_case_study(
    case_study_id: UUID,
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
    """Update case study - matching junglore.com pattern"""
    try:
        # Get existing case study
        result = await db.execute(
            select(Content).where(Content.id == case_study_id, Content.type == ContentTypeEnum.CASE_STUDY)
        )
        case_study = result.scalar_one_or_none()
        
        if not case_study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case Study not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != case_study.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this case study"
            )
        
        # Handle file uploads
        if image:
            case_study.featured_image = await save_uploaded_file(image, "image")
        
        if banner:
            case_study.banner = await save_uploaded_file(banner, "image")
        
        if video:
            case_study.video = await save_uploaded_file(video, "video")
        
        # Update fields
        if title:
            case_study.title = title
            # Update slug if title changed
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            
            # Ensure slug uniqueness (excluding current case study)
            while True:
                result = await db.execute(
                    select(Content).where(and_(Content.slug == slug, Content.id != case_study_id))
                )
                if not result.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            case_study.slug = slug
        
        if content:
            case_study.content = content
        
        if description:
            case_study.excerpt = description
        
        if category_id:
            try:
                category_uuid = UUID(category_id)
                cat_result = await db.execute(select(Category).where(Category.id == category_uuid))
                if not cat_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid category ID"
                    )
                case_study.category_id = category_uuid
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid category ID format"
                )
        
        await db.commit()
        await db.refresh(case_study)
        
        # Format response using standardized formatter
        formatted_case_study = format_content_item(case_study)
        return create_success_response(formatted_case_study, "Case Study Update Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/feature/{case_study_id}", response_model=StandardAPIResponse)
async def feature_case_study(
    case_study_id: UUID,
    place: int = Form(..., ge=1, le=3, description="Featured placement (1-3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Feature a case study - standardized response format"""
    try:
        # Check if there are already 3 featured case studies
        featured_count_result = await db.execute(
            select(func.count(Content.id)).where(
                Content.type == ContentTypeEnum.CASE_STUDY,
                Content.featured == True
            )
        )
        featured_count = featured_count_result.scalar()
        
        if featured_count >= 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Already there are 3 featured case studies"
            )
        
        # Get case study
        result = await db.execute(
            select(Content).where(Content.id == case_study_id, Content.type == ContentTypeEnum.CASE_STUDY)
        )
        case_study = result.scalar_one_or_none()
        
        if not case_study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case Study not found"
            )
        
        # Update featured status
        case_study.featured = True
        case_study.feature_place = place
        
        await db.commit()
        await db.refresh(case_study)
        
        # Format response using standardized formatter
        formatted_case_study = format_content_item(case_study)
        return create_success_response(formatted_case_study, "Case Study Featured Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.delete("/{case_study_id}", response_model=StandardAPIResponse)
async def delete_case_study(
    case_study_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete case study - standardized response format"""
    try:
        # Get case study
        result = await db.execute(
            select(Content).where(Content.id == case_study_id, Content.type == ContentTypeEnum.CASE_STUDY)
        )
        case_study = result.scalar_one_or_none()
        
        if not case_study:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case Study not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != case_study.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this case study"
            )
        
        await db.delete(case_study)
        await db.commit()
        
        return create_success_response({"id": str(case_study_id)}, "Case Study Delete Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )
