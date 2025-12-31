"""
Media API Routes
Handles images, videos, podcasts, and other media files
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_, update, cast, String
from typing import List, Optional
from uuid import UUID, uuid4
import os
import aiofiles
from pathlib import Path
import mimetypes
from PIL import Image
import io

from app.db.database import get_db, get_db_with_retry
from app.models.media import Media, MediaTypeEnum as ModelMediaTypeEnum
from app.models.content import Content
from app.models.user import User
from app.core.security import get_current_user, get_current_user_optional
from app.schemas.media import (
    MediaCreate,
    MediaUpdate,
    MediaResponse,
    MediaListResponse,
    PodcastResponse,
    MediaUploadResponse,
    MediaStatsResponse,
    MediaTypeEnum
)

router = APIRouter()

# Configuration for file uploads
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/avif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/avi", "video/mov", "video/mkv"}
ALLOWED_AUDIO_TYPES = {"audio/mp3", "audio/wav", "audio/ogg", "audio/m4a"}


def get_media_type_from_mimetype(mimetype: str) -> MediaTypeEnum:
    """Determine media type from MIME type"""
    if mimetype.startswith("image/"):
        return MediaTypeEnum.IMAGE
    elif mimetype.startswith("video/"):
        return MediaTypeEnum.VIDEO
    elif mimetype.startswith("audio/"):
        if "podcast" in mimetype.lower():
            return MediaTypeEnum.PODCAST
        return MediaTypeEnum.AUDIO
    else:
        return MediaTypeEnum.DOCUMENT


def is_allowed_file_type(mimetype: str) -> bool:
    """Check if file type is allowed"""
    return (
        mimetype in ALLOWED_IMAGE_TYPES or
        mimetype in ALLOWED_VIDEO_TYPES or
        mimetype in ALLOWED_AUDIO_TYPES
    )


async def create_thumbnail(file_path: Path, media_type: MediaTypeEnum) -> Optional[str]:
    """Create thumbnail for media file"""
    if media_type != MediaTypeEnum.IMAGE:
        return None
    
    try:
        thumbnail_dir = UPLOAD_DIR / "thumbnails"
        thumbnail_dir.mkdir(exist_ok=True)
        
        # Generate thumbnail filename
        thumbnail_name = f"thumb_{file_path.stem}.jpg"
        thumbnail_path = thumbnail_dir / thumbnail_name
        
        # Create thumbnail using Pillow
        with Image.open(file_path) as img:
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            img.save(thumbnail_path, "JPEG", quality=85)
        
        return f"/uploads/thumbnails/{thumbnail_name}"
    except Exception as e:
        print(f"Failed to create thumbnail: {e}")
        return None


@router.get("/", response_model=List[MediaListResponse])
async def get_media(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    media_type: Optional[MediaTypeEnum] = Query(None, description="Filter by media type"),
    search: Optional[str] = Query(None, description="Search in title, description, photographer, and national park"),
    content_id: Optional[UUID] = Query(None, description="Filter by content ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get media files with filtering and pagination"""
    
    query = select(Media)
    
    # Apply filters
    if media_type:
        query = query.where(Media.media_type == media_type)
        
    if content_id:
        query = query.where(Media.content_id == content_id)
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Media.title.ilike(search_term),
                Media.description.ilike(search_term),
                Media.photographer.ilike(search_term),
                Media.national_park.ilike(search_term)
            )
        )
    
    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(desc(Media.created_at))
    
    result = await db.execute(query)
    media_items = result.scalars().all()
    
    return [MediaListResponse(
        id=media.id,
        media_type=media.media_type,
        file_url=media.file_url,
        thumbnail_url=media.thumbnail_url,
        title=media.title,
        photographer=media.photographer,
        national_park=media.national_park,
        width=media.width,
        height=media.height,
        duration=media.duration,
        created_at=media.created_at
    ) for media in media_items]



@router.get("/podcasts", response_model=List[MediaResponse])
async def get_podcasts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = Query(None, description="Search in title and description"),
    db: AsyncSession = Depends(get_db)
):
    """Get podcast episodes"""
    
    query = select(Media).where(Media.media_type == 'PODCAST')
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                Media.title.ilike(search_term),
                Media.description.ilike(search_term)
            )
        )
    
    query = query.offset(skip).limit(limit).order_by(desc(Media.created_at))
    
    result = await db.execute(query)
    podcasts = result.scalars().all()
    
    return [MediaResponse(
        id=podcast.id,
        media_type=podcast.media_type,
        file_url=podcast.file_url,
        thumbnail_url=podcast.thumbnail_url,
        title=podcast.title,
        description=podcast.description,
        content_id=podcast.content_id,
        photographer=podcast.photographer,
        national_park=podcast.national_park,
        file_size=podcast.file_size,
        duration=podcast.duration,
        width=podcast.width,
        height=podcast.height,
        file_metadata=podcast.file_metadata,
        created_at=podcast.created_at
    ) for podcast in podcasts]





@router.get("/featured", response_model=List[MediaListResponse])
async def get_featured_images(
    db: AsyncSession = Depends(get_db)
):
    """Get featured images for the platform"""
    
    # Get featured images ordered by their featured position
    featured_result = await db.execute(
        select(Media)
        .where(and_(Media.is_featured > 0, Media.media_type == 'IMAGE'))
        .order_by(Media.is_featured)
        .limit(6)
    )
    featured_images = featured_result.scalars().all()
    
    # If no featured images, return recent images instead
    if not featured_images:
        recent_result = await db.execute(
            select(Media)
            .where(Media.media_type == 'IMAGE')
            .order_by(desc(Media.created_at))
            .limit(6)
        )
        featured_images = recent_result.scalars().all()
    
    return [MediaListResponse(
        id=media.id,
        media_type=media.media_type,
        file_url=media.file_url,
        thumbnail_url=media.thumbnail_url,
        title=media.title,
        photographer=media.photographer,
        national_park=media.national_park,
        width=media.width,
        height=media.height,
        duration=media.duration,
        created_at=media.created_at
    ) for media in featured_images]


@router.post("/featured")
async def set_featured_images(
    featured_images: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Set featured images (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can set featured images"
        )
    
    try:
        # Clear all existing featured images
        await db.execute(
            update(Media).where(Media.is_featured > 0).values(is_featured=0)
        )
        
        # Set new featured images
        for position, image_id in enumerate(featured_images.get("featured_images", []), 1):
            if position > 6:  # Maximum 6 featured images
                break
                
            # Update media item with featured position
            await db.execute(
                update(Media)
                .where(Media.id == image_id)
                .values(is_featured=position)
            )
        
        await db.commit()
        
        return {"message": "Featured images updated successfully"}
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update featured images: {str(e)}"
        )


@router.get("/{media_id}", response_model=MediaResponse)
async def get_media_by_id(
    media_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific media by ID"""
    
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    return MediaResponse(
        id=media.id,
        media_type=media.media_type,
        file_url=media.file_url,
        thumbnail_url=media.thumbnail_url,
        title=media.title,
        description=media.description,
        content_id=media.content_id,
        photographer=media.photographer,
        national_park=media.national_park,
        file_size=media.file_size,
        duration=media.duration,
        width=media.width,
        height=media.height,
        file_metadata=media.file_metadata,
        created_at=media.created_at
    )


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_media_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    photographer: Optional[str] = Form(None),
    national_park: Optional[str] = Form(None),
    content_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_with_retry),  # Use retry for critical uploads
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Upload a media file using enhanced upload service (authentication optional)"""
    
    try:
        from app.services.file_upload import file_upload_service
        from app.core.exceptions import (
            FileUploadError, FileSizeError, FileTypeError, 
            CategoryNotFoundError, create_http_exception
        )
        
        # Validate content_id if provided
        content_uuid = None
        if content_id:
            try:
                content_uuid = UUID(content_id)
                result = await db.execute(select(Content).where(Content.id == content_uuid))
                if not result.scalar_one_or_none():
                    raise CategoryNotFoundError(content_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid content ID format"
                )
        
        # Upload file using enhanced service
        upload_result = await file_upload_service.upload_file(
            file=file,
            validate_content=False,
        )
        
        # Determine media type from MIME type
        media_type = get_media_type_from_mimetype(upload_result["mime_type"])
        
        # Get image dimensions if it's an image
        width = height = None
        if media_type == MediaTypeEnum.IMAGE and upload_result["category"] == "images":
            try:
                file_path = Path(upload_result["file_path"])
                with Image.open(file_path) as img:
                    width, height = img.size
            except Exception:
                pass
        
        # Create thumbnail for images
        thumbnail_url = None
        if media_type == MediaTypeEnum.IMAGE:
            thumbnail_url = await create_thumbnail(Path(upload_result["file_path"]), media_type)
        
        # Create media record
        media = Media(
            media_type=media_type,
            file_url=f"/uploads/{upload_result['file_url']}",
            thumbnail_url=thumbnail_url,
            title=title or upload_result["original_filename"],
            description=description,
            photographer=photographer,
            national_park=national_park,
            content_id=content_uuid,
            file_size=upload_result["file_size"],
            width=width,
            height=height,
            file_metadata={
                "original_filename": upload_result["original_filename"],
                "mimetype": upload_result["mime_type"],
                "uploaded_by": str(current_user.id) if current_user else "anonymous",
                "file_hash": upload_result["file_hash"],
                "secure_filename": upload_result["filename"]
            }
        )
        
        db.add(media)
        await db.commit()
        await db.refresh(media)
        
        return MediaUploadResponse(
            id=media.id,
            file_url=media.file_url,
            thumbnail_url=media.thumbnail_url,
            media_type=media.media_type,
            file_size=media.file_size,
            message="File uploaded successfully"
        )
        
    except (FileUploadError, FileSizeError, FileTypeError) as e:
        raise create_http_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@router.post("/", response_model=MediaResponse)
async def create_media(
    media_data: MediaCreate,
    db: AsyncSession = Depends(get_db_with_retry),  # Use retry for critical content creation
    current_user: User = Depends(get_current_user)
):
    """Create media record (for external URLs)"""
    
    # Validate content_id if provided
    if media_data.content_id:
        result = await db.execute(select(Content).where(Content.id == media_data.content_id))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content ID"
            )
    
    media = Media(
        media_type=media_data.media_type,
        file_url=media_data.file_url,
        thumbnail_url=media_data.thumbnail_url,
        title=media_data.title,
        description=media_data.description,
        content_id=media_data.content_id,
        photographer=media_data.photographer,
        national_park=media_data.national_park,
        file_size=media_data.file_size,
        duration=media_data.duration,
        width=media_data.width,
        height=media_data.height,
        file_metadata=media_data.file_metadata or {}
    )
    
    db.add(media)
    await db.commit()
    await db.refresh(media)
    
    return MediaResponse(
        id=media.id,
        media_type=media.media_type,
        file_url=media.file_url,
        thumbnail_url=media.thumbnail_url,
        title=media.title,
        description=media.description,
        content_id=media.content_id,
        photographer=media.photographer,
        national_park=media.national_park,
        file_size=media.file_size,
        duration=media.duration,
        width=media.width,
        height=media.height,
        file_metadata=media.file_metadata,
        created_at=media.created_at
    )


@router.put("/{media_id}", response_model=MediaResponse)
async def update_media(
    media_id: UUID,
    media_data: MediaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update media record"""
    
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Check if user can update (admin or uploader)
    if not current_user.is_superuser:
        uploader_id = media.file_metadata.get("uploaded_by") if media.file_metadata else None
        if uploader_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this media"
            )
    
    # Update fields
    update_data = media_data.dict(exclude_unset=True)
    
    # Validate content_id if being updated
    if 'content_id' in update_data and update_data['content_id']:
        result = await db.execute(select(Content).where(Content.id == update_data['content_id']))
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content ID"
            )
    
    for field, value in update_data.items():
        setattr(media, field, value)
    
    await db.commit()
    await db.refresh(media)
    
    return MediaResponse(
        id=media.id,
        media_type=media.media_type,
        file_url=media.file_url,
        thumbnail_url=media.thumbnail_url,
        title=media.title,
        description=media.description,
        content_id=media.content_id,
        photographer=media.photographer,
        national_park=media.national_park,
        file_size=media.file_size,
        duration=media.duration,
        width=media.width,
        height=media.height,
        file_metadata=media.file_metadata,
        created_at=media.created_at
    )


@router.delete("/{media_id}")
async def delete_media(
    media_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete media record and file"""
    
    result = await db.execute(select(Media).where(Media.id == media_id))
    media = result.scalar_one_or_none()
    
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media not found"
        )
    
    # Check permissions
    if not current_user.is_superuser:
        uploader_id = media.file_metadata.get("uploaded_by") if media.file_metadata else None
        if uploader_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this media"
            )
    
    # Delete physical file if it's a local upload
    if media.file_url.startswith("/uploads/"):
        file_path = Path(media.file_url[1:])  # Remove leading slash
        if file_path.exists():
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        # Delete thumbnail if exists
        if media.thumbnail_url and media.thumbnail_url.startswith("/uploads/"):
            thumb_path = Path(media.thumbnail_url[1:])
            if thumb_path.exists():
                try:
                    os.remove(thumb_path)
                except OSError:
                    pass
    
    await db.delete(media)
    await db.commit()
    
    return {"message": "Media deleted successfully"}


@router.get("/stats/overview", response_model=MediaStatsResponse)
async def get_media_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get media statistics (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view media statistics"
        )
    
    # Get counts by type
    total_result = await db.execute(select(func.count(Media.id)))
    total_media = total_result.scalar()
    
    images_result = await db.execute(
        select(func.count(Media.id)).where(Media.media_type == 'IMAGE')
    )
    images_count = images_result.scalar()
    
    videos_result = await db.execute(
        select(func.count(Media.id)).where(Media.media_type == 'VIDEO')
    )
    videos_count = videos_result.scalar()
    
    podcasts_result = await db.execute(
        select(func.count(Media.id)).where(Media.media_type == 'PODCAST')
    )
    podcasts_count = podcasts_result.scalar()
    
    # Get total file size
    size_result = await db.execute(select(func.sum(Media.file_size)))
    total_file_size = size_result.scalar() or 0
    
    # Get recent uploads
    recent_result = await db.execute(
        select(Media).order_by(desc(Media.created_at)).limit(5)
    )
    recent_uploads = recent_result.scalars().all()
    
    return MediaStatsResponse(
        total_media=total_media,
        images_count=images_count,
        videos_count=videos_count,
        podcasts_count=podcasts_count,
        total_file_size=total_file_size,
        most_viewed_media=[],  # TODO: Implement view tracking
        recent_uploads=[MediaListResponse(
            id=media.id,
            media_type=media.media_type,
            file_url=media.file_url,
            thumbnail_url=media.thumbnail_url,
            title=media.title,
            photographer=media.photographer,
            national_park=media.national_park,
            width=media.width,
            height=media.height,
            duration=media.duration,
            created_at=media.created_at
        ) for media in recent_uploads]
    )
