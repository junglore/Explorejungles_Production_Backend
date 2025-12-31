"""
Blog API Routes - Following junglore.com pattern
Dedicated blog endpoints with file upload functionality matching the reference implementation
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
from app.core.exceptions import (
    ContentNotFoundError,
    ContentValidationError,
    ContentPermissionError,
    FileUploadError,
    FileSizeError,
    FileTypeError,
    CategoryNotFoundError,
    ContentLimitError,
    create_http_exception
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
    """Save uploaded file and return the file path using enhanced upload service"""
    if not file:
        return None
        
    try:
        from app.services.file_upload import file_upload_service
        
        # Determine category based on file_type parameter
        category_mapping = {
            "image": "images",
            "video": "videos", 
            "document": "documents"
        }
        category = category_mapping.get(file_type, "images")
        
        # Upload file using enhanced service
        upload_result = await file_upload_service.upload_file(
            file=file,
            file_category=category,
            validate_content=True
        )
        
        return upload_result["file_url"]
        
    except (FileSizeError, FileTypeError, FileUploadError):
        raise
    except Exception as e:
        raise FileUploadError(f"Failed to save file: {str(e)}", file.filename)


# Blog endpoints following junglore.com pattern

@router.get("/", response_model=StandardAPIResponse)
async def fetch_all_blogs(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(9, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch all blogs with pagination - standardized response format"""
    try:
        skip = (page - 1) * limit
        
        # Build query
        query = select(Content).options(
            selectinload(Content.author),
            selectinload(Content.category)
        ).where(
            Content.type == ContentTypeEnum.BLOG,
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
            Content.type == ContentTypeEnum.BLOG,
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
        
        # Get blogs
        query = query.order_by(desc(Content.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        blogs = result.scalars().all()
        
        # Format response using standardized formatter
        pagination_data = format_content_list(blogs, page, limit, total_items)
        return create_success_response(pagination_data, "Blog Fetch Success")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/{blog_id}", response_model=StandardAPIResponse)
async def fetch_single_blog(
    blog_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Fetch single blog by ID - standardized response format"""
    try:
        result = await db.execute(
            select(Content)
            .options(selectinload(Content.author), selectinload(Content.category))
            .where(Content.id == blog_id, Content.type == ContentTypeEnum.BLOG)
        )
        blog = result.scalar_one_or_none()
        
        if not blog:
            raise ContentNotFoundError(str(blog_id), "blog")
        
        # Format response using standardized formatter
        formatted_blog = format_content_item(blog, include_full_content=True)
        return create_success_response(formatted_blog, "Blog Fetch Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.post("/", response_model=StandardAPIResponse)
async def create_blog(
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
    """Create new blog with file uploads - matching junglore.com pattern"""
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
                    raise CategoryNotFoundError(category_id)
            except ValueError:
                raise ContentValidationError("Invalid category ID format", "category_id", category_id)
        
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
        
        # Create blog
        blog = Content(
            title=title,
            content=content,
            type=ContentTypeEnum.BLOG,
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
        
        db.add(blog)
        await db.commit()
        await db.refresh(blog)
        
        # Format response using standardized formatter
        formatted_blog = format_content_item(blog)
        return create_success_response(formatted_blog, "Blog Created Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/{blog_id}", response_model=StandardAPIResponse)
async def update_blog(
    blog_id: UUID,
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
    """Update blog - matching junglore.com pattern"""
    try:
        # Get existing blog
        result = await db.execute(
            select(Content).where(Content.id == blog_id, Content.type == ContentTypeEnum.BLOG)
        )
        blog = result.scalar_one_or_none()
        
        if not blog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != blog.author_id:
            raise ContentPermissionError("update", "blog")
        
        # Handle file uploads
        if image:
            blog.featured_image = await save_uploaded_file(image, "image")
        
        if banner:
            blog.banner = await save_uploaded_file(banner, "image")
        
        if video:
            blog.video = await save_uploaded_file(video, "video")
        
        # Update fields
        if title:
            blog.title = title
            # Update slug if title changed
            base_slug = slugify(title)
            slug = base_slug
            counter = 1
            
            # Ensure slug uniqueness (excluding current blog)
            while True:
                result = await db.execute(
                    select(Content).where(and_(Content.slug == slug, Content.id != blog_id))
                )
                if not result.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            blog.slug = slug
        
        if content:
            blog.content = content
        
        if description:
            blog.excerpt = description
        
        if category_id:
            try:
                category_uuid = UUID(category_id)
                cat_result = await db.execute(select(Category).where(Category.id == category_uuid))
                if not cat_result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid category ID"
                    )
                blog.category_id = category_uuid
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid category ID format"
                )
        
        await db.commit()
        await db.refresh(blog)
        
        # Format response using standardized formatter
        formatted_blog = format_content_item(blog)
        return create_success_response(formatted_blog, "Blog Update Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/feature/{blog_id}", response_model=StandardAPIResponse)
async def feature_blog(
    blog_id: UUID,
    place: int = Form(..., ge=1, le=3, description="Featured placement (1-3)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Feature a blog - matching junglore.com pattern"""
    try:
        # Check if there are already 3 featured blogs
        featured_count_result = await db.execute(
            select(func.count(Content.id)).where(
                Content.type == ContentTypeEnum.BLOG,
                Content.featured == True
            )
        )
        featured_count = featured_count_result.scalar()
        
        if featured_count >= 3:
            raise ContentLimitError("featured blogs", featured_count, 3)
        
        # Get blog
        result = await db.execute(
            select(Content).where(Content.id == blog_id, Content.type == ContentTypeEnum.BLOG)
        )
        blog = result.scalar_one_or_none()
        
        if not blog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
        
        # Update featured status
        blog.featured = True
        blog.feature_place = place
        
        await db.commit()
        await db.refresh(blog)
        
        # Format response using standardized formatter
        formatted_blog = format_content_item(blog)
        return create_success_response(formatted_blog, "Blog Featured Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.delete("/{blog_id}", response_model=StandardAPIResponse)
async def delete_blog(
    blog_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete blog - matching junglore.com pattern"""
    try:
        # Get blog
        result = await db.execute(
            select(Content).where(Content.id == blog_id, Content.type == ContentTypeEnum.BLOG)
        )
        blog = result.scalar_one_or_none()
        
        if not blog:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Blog not found"
            )
        
        # Check permissions (admin or author)
        if not current_user.is_superuser and current_user.id != blog.author_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this blog"
            )
        
        await db.delete(blog)
        await db.commit()
        
        return create_success_response({"id": str(blog_id)}, "Blog Delete Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


# Blog Category endpoints following junglore.com pattern

@router.get("/category", response_model=StandardAPIResponse)
async def fetch_all_categories(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(9, ge=1, le=50, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in category name"),
    db: AsyncSession = Depends(get_db)
):
    """Fetch all blog categories - matching junglore.com pattern"""
    try:
        skip = (page - 1) * limit
        
        # Build query
        query = select(Category)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.where(Category.name.ilike(search_term))
        
        # Get total count
        count_query = select(func.count(Category.id))
        if search:
            search_term = f"%{search}%"
            count_query = count_query.where(Category.name.ilike(search_term))
        
        total_result = await db.execute(count_query)
        total_items = total_result.scalar()
        
        # Get categories
        query = query.order_by(desc(Category.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        categories = result.scalars().all()
        
        # Calculate total pages
        total_pages = (total_items + limit - 1) // limit
        
        # Format response to match junglore.com pattern
        formatted_categories = []
        for category in categories:
            formatted_categories.append({
                "id": str(category.id),
                "name": category.name,
                "slug": category.slug,
                "status": True,  # Assuming all categories are active
                "createdAt": category.created_at.isoformat(),
                "updatedAt": category.updated_at.isoformat()
            })
        
        response = {
            "result": formatted_categories,
            "totalPages": total_pages,
            "currentPage": page,
            "limit": len(formatted_categories)
        }
        
        return create_success_response(response, "Blog Categories Fetch Success")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.get("/category/{category_id}", response_model=StandardAPIResponse)
async def fetch_single_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Fetch single category - matching junglore.com pattern"""
    try:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Format response to match junglore.com pattern
        formatted_category = {
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "status": True,
            "createdAt": category.created_at.isoformat(),
            "updatedAt": category.updated_at.isoformat()
        }
        
        return create_success_response(formatted_category, "Category Fetch Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.post("/category", response_model=StandardAPIResponse)
async def create_category(
    name: str = Form(...),
    slug: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create blog category - matching junglore.com pattern"""
    try:
        # Generate slug if not provided
        if not slug:
            slug = slugify(name)
        
        # Ensure slug uniqueness
        base_slug = slug
        counter = 1
        while True:
            result = await db.execute(select(Category).where(Category.slug == slug))
            if not result.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Create category
        category = Category(
            name=name,
            slug=slug
        )
        
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        # Format response
        formatted_category = {
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "status": True,
            "createdAt": category.created_at.isoformat(),
            "updatedAt": category.updated_at.isoformat()
        }
        
        return create_success_response(formatted_category, "Category Created Success")
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.patch("/category/{category_id}", response_model=StandardAPIResponse)
async def update_category(
    category_id: UUID,
    name: Optional[str] = Form(None),
    slug: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update blog category - matching junglore.com pattern"""
    try:
        # Get category
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Update fields
        if name:
            category.name = name
        
        if slug:
            # Ensure slug uniqueness (excluding current category)
            base_slug = slug
            counter = 1
            while True:
                result = await db.execute(
                    select(Category).where(and_(Category.slug == slug, Category.id != category_id))
                )
                if not result.scalar_one_or_none():
                    break
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            category.slug = slug
        
        await db.commit()
        await db.refresh(category)
        
        # Format response
        formatted_category = {
            "id": str(category.id),
            "name": category.name,
            "slug": category.slug,
            "status": True,
            "createdAt": category.created_at.isoformat(),
            "updatedAt": category.updated_at.isoformat()
        }
        
        return create_success_response(formatted_category, "Category Update Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )


@router.delete("/category/{category_id}", response_model=StandardAPIResponse)
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete blog category - matching junglore.com pattern"""
    try:
        # Get category
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        await db.delete(category)
        await db.commit()
        
        return create_success_response({"id": str(category_id)}, "Category Delete Success")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {str(e)}"
        )
