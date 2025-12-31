"""
National Park API Routes
Handles CRUD operations for national parks
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
import os
import shutil
from pathlib import Path
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from app.db.database import get_db
from app.models.national_park import NationalPark
from app.schemas.national_park import (
    NationalParkCreate, 
    NationalParkUpdate, 
    NationalParkResponse,
    NationalParkListItem,
    slugify
)
from app.core.security import get_current_user
from app.models.user import User
from app.core.config import settings

router = APIRouter()


@router.get("/", response_model=List[NationalParkListItem])
async def get_national_parks(
    skip: int = Query(0, ge=0, description="Number of parks to skip"),
    limit: int = Query(100, ge=1, le=200, description="Number of parks to return"),
    search: Optional[str] = Query(None, description="Search parks by name or state"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    include_unapproved: bool = Query(False, description="Include unapproved media (admin only)"),
    db: AsyncSession = Depends(get_db)
):
    """Get all national parks with optional filtering (Public access)"""
    try:
        query = select(NationalPark)
        
        # Apply filters
        if is_active is not None:
            query = query.where(NationalPark.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                NationalPark.name.ilike(search_term) | 
                NationalPark.state.ilike(search_term)
            )
        
        # Apply pagination and ordering
        query = query.offset(skip).limit(limit).order_by(NationalPark.name)
        
        result = await db.execute(query)
        parks = result.scalars().all()
        
        # Filter media based on include_unapproved flag
        filtered_parks = []
        for park in parks:
            if include_unapproved:
                # Admin view - show all media regardless of approval status
                all_media = [item["url"] if isinstance(item, dict) else item for item in (park.media_urls or [])]
                all_videos = [item["url"] if isinstance(item, dict) else item for item in (park.video_urls or [])]
            else:
                # Public view - only show approved media
                all_media = [item["url"] if isinstance(item, dict) else item for item in (park.media_urls or []) if (isinstance(item, dict) and item.get("approved", False)) or isinstance(item, str)]
                all_videos = [item["url"] if isinstance(item, dict) else item for item in (park.video_urls or []) if (isinstance(item, dict) and item.get("approved", False)) or isinstance(item, str)]
            
            # Add /uploads/ prefix for presigned URL generation
            media_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in all_media]
            videos_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in all_videos]
            
            park_dict = {
                "id": park.id,
                "name": park.name,
                "state": park.state,
                "slug": park.slug,
                "description": park.description,
                "biodiversity": park.biodiversity,
                "conservation": park.conservation,
                "media_urls": media_with_prefix,
                "video_urls": videos_with_prefix,
                "banner_media_url": f"/uploads/{park.banner_media_url}" if park.banner_media_url and not park.banner_media_url.startswith('/uploads/') else park.banner_media_url,
                "expedition_slugs": park.expedition_slugs or [],
                "banner_media_type": park.banner_media_type,
                "is_active": park.is_active,
                "created_at": park.created_at,
                "updated_at": park.updated_at
            }
            filtered_parks.append(park_dict)
        
        return filtered_parks
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch national parks: {str(e)}"
        )


@router.get("/{park_id}", response_model=NationalParkResponse)
async def get_national_park_by_id(
    park_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific national park by ID (Public access)"""
    try:
        result = await db.execute(
            select(NationalPark).where(NationalPark.id == park_id)
        )
        park = result.scalar_one_or_none()
        
        if not park:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="National park not found"
            )
        
        # Filter to only show approved media for public access
        approved_media = [item["url"] if isinstance(item, dict) else item for item in (park.media_urls or []) if (isinstance(item, dict) and item.get("approved", False)) or isinstance(item, str)]
        approved_videos = [item["url"] if isinstance(item, dict) else item for item in (park.video_urls or []) if (isinstance(item, dict) and item.get("approved", False)) or isinstance(item, str)]
        
        # Add /uploads/ prefix for presigned URL generation
        media_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in approved_media]
        videos_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in approved_videos]
        
        park_dict = {
            "id": park.id,
            "name": park.name,
            "state": park.state,
            "slug": park.slug,
            "description": park.description,
            "biodiversity": park.biodiversity,
            "conservation": park.conservation,
            "media_urls": media_with_prefix,
            "video_urls": videos_with_prefix,
            "banner_media_url": f"/uploads/{park.banner_media_url}" if park.banner_media_url and not park.banner_media_url.startswith('/uploads/') else park.banner_media_url,
            "expedition_slugs": park.expedition_slugs or [],
            "banner_media_type": park.banner_media_type,
            "is_active": park.is_active,
            "created_at": park.created_at,
            "updated_at": park.updated_at
        }
        
        return park_dict
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch national park: {str(e)}"
        )


@router.post("/", response_model=NationalParkResponse, status_code=status.HTTP_201_CREATED)
async def create_national_park(
    park_data: NationalParkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new national park (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create national parks"
        )
    
    try:
        # Check if park with same name exists
        existing_result = await db.execute(
            select(NationalPark).where(NationalPark.name == park_data.name)
        )
        existing_park = existing_result.scalar_one_or_none()
        
        if existing_park:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"National park '{park_data.name}' already exists"
            )
        
        # Create slug from name
        slug = slugify(park_data.name)
        
        # Check if slug exists
        slug_result = await db.execute(
            select(NationalPark).where(NationalPark.slug == slug)
        )
        if slug_result.scalar_one_or_none():
            # Add a number to make it unique
            count_result = await db.execute(
                select(func.count()).select_from(NationalPark).where(
                    NationalPark.slug.like(f"{slug}%")
                )
            )
            count = count_result.scalar()
            slug = f"{slug}-{count + 1}"
        
        # Create new park
        new_park = NationalPark(
            name=park_data.name,
            slug=slug,
            state=park_data.state,
            description=park_data.description,
            biodiversity=park_data.biodiversity,
            conservation=park_data.conservation,
            media_urls=park_data.media_urls,
            video_urls=park_data.video_urls,
            banner_media_url=park_data.banner_media_url,
            banner_media_type=park_data.banner_media_type,
            expedition_slugs=park_data.expedition_slugs,
            is_active=park_data.is_active
        )
        
        db.add(new_park)
        await db.commit()
        await db.refresh(new_park)
        
        # Don't filter by approval for CREATE response - admin should see what they just created
        all_media = new_park.media_urls or []
        all_videos = new_park.video_urls or []
        
        media_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in all_media]
        videos_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in all_videos]
        
        return {
            "id": new_park.id,
            "name": new_park.name,
            "state": new_park.state,
            "slug": new_park.slug,
            "description": new_park.description,
            "biodiversity": new_park.biodiversity,
            "conservation": new_park.conservation,
            "media_urls": media_with_prefix,
            "video_urls": videos_with_prefix,
            "banner_media_url": f"/uploads/{new_park.banner_media_url}" if new_park.banner_media_url and not new_park.banner_media_url.startswith('/uploads/') else new_park.banner_media_url,
            "expedition_slugs": new_park.expedition_slugs or [],
            "banner_media_type": new_park.banner_media_type,
            "is_active": new_park.is_active,
            "created_at": new_park.created_at,
            "updated_at": new_park.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create national park: {str(e)}"
        )


@router.put("/{park_id}", response_model=NationalParkResponse)
async def update_national_park(
    park_id: UUID,
    park_data: NationalParkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update national park (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update national parks"
        )
    
    try:
        # Get existing park
        result = await db.execute(
            select(NationalPark).where(NationalPark.id == park_id)
        )
        park = result.scalar_one_or_none()
        
        if not park:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="National park not found"
            )
        
        # Update fields if provided
        update_data = park_data.model_dump(exclude_unset=True)
        
        # If name is being updated, check for duplicates and update slug
        if 'name' in update_data and update_data['name'] != park.name:
            existing_result = await db.execute(
                select(NationalPark).where(
                    NationalPark.name == update_data['name'],
                    NationalPark.id != park_id
                )
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"National park '{update_data['name']}' already exists"
                )
            
            # Update slug
            update_data['slug'] = slugify(update_data['name'])
        
        # Apply updates
        for field, value in update_data.items():
            setattr(park, field, value)
        
        await db.commit()
        await db.refresh(park)
        
        # Don't filter by approval for UPDATE response - admin should see what they just updated
        all_media = park.media_urls or []
        all_videos = park.video_urls or []
        
        media_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in all_media]
        videos_with_prefix = [f"/uploads/{url}" if not url.startswith('/uploads/') else url for url in all_videos]
        
        return {
            "id": park.id,
            "name": park.name,
            "state": park.state,
            "slug": park.slug,
            "description": park.description,
            "biodiversity": park.biodiversity,
            "conservation": park.conservation,
            "media_urls": media_with_prefix,
            "video_urls": videos_with_prefix,
            "banner_media_url": f"/uploads/{park.banner_media_url}" if park.banner_media_url and not park.banner_media_url.startswith('/uploads/') else park.banner_media_url,
            "expedition_slugs": park.expedition_slugs or [],
            "banner_media_type": park.banner_media_type,
            "is_active": park.is_active,
            "created_at": park.created_at,
            "updated_at": park.updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update national park: {str(e)}"
        )


@router.delete("/{park_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_national_park(
    park_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete national park (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete national parks"
        )
    
    try:
        result = await db.execute(
            select(NationalPark).where(NationalPark.id == park_id)
        )
        park = result.scalar_one_or_none()
        
        if not park:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="National park not found"
            )
        
        await db.delete(park)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete national park: {str(e)}"
        )


@router.patch("/{park_id}/toggle-active", response_model=NationalParkResponse)
async def toggle_park_active_status(
    park_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle national park active status (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can toggle park status"
        )
    
    try:
        result = await db.execute(
            select(NationalPark).where(NationalPark.id == park_id)
        )
        park = result.scalar_one_or_none()
        
        if not park:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="National park not found"
            )
        
        park.is_active = not park.is_active
        await db.commit()
        await db.refresh(park)
        
        return park
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle park status: {str(e)}"
        )


@router.post("/upload-media", status_code=status.HTTP_201_CREATED)
async def upload_park_media(
    park_id: str = Form(...),
    upload_type: str = Form(...),  # 'media' or 'videos'
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload media (images/videos) to national park (Authenticated users)"""
    
    # Validate upload type
    if upload_type not in ['media', 'videos']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="upload_type must be 'media' or 'videos'"
        )
    
    try:
        # Get park by slug (park_id is actually the slug from URL)
        result = await db.execute(
            select(NationalPark).where(NationalPark.slug == park_id)
        )
        park = result.scalar_one_or_none()
        
        if not park:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="National park not found"
            )
        
        # Check if using R2 storage
        use_r2 = settings.USE_R2_STORAGE.lower() == 'true'
        
        uploaded_urls = []
        
        # Process each file
        for file in files:
            # Validate file type
            if upload_type == 'media':
                allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
                if file.content_type not in allowed_types:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid image type: {file.content_type}"
                    )
            else:  # videos
                allowed_types = ['video/mp4', 'video/webm', 'video/quicktime', 'video/x-msvideo']
                if file.content_type not in allowed_types:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid video type: {file.content_type}"
                    )
            
            # Generate unique filename (same as before)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = file.filename.split('.')[-1]
            filename = f"{timestamp}_{file.filename}"
            
            # Create relative path for storage
            file_key = f"national_parks/{park.id}/{upload_type}/{filename}"
            
            # Read file content
            file_content = await file.read()
            
            if use_r2:
                # Upload to R2
                try:
                    r2_client = boto3.client(
                        's3',
                        endpoint_url=settings.R2_ENDPOINT_URL,
                        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                        region_name='auto'
                    )
                    r2_client.put_object(
                        Bucket=settings.R2_BUCKET_NAME,
                        Key=file_key,
                        Body=file_content,
                        ContentType=file.content_type
                    )
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to upload to R2: {str(e)}"
                    )
            else:
                # Save to local disk
                upload_dir = Path("uploads") / "national_parks" / str(park.id) / upload_type
                upload_dir.mkdir(parents=True, exist_ok=True)
                file_path = upload_dir / filename
                with open(file_path, "wb") as buffer:
                    buffer.write(file_content)
            
            # Create media object with approval tracking (store relative path)
            media_object = {
                "url": file_key,  # Relative path: "national_parks/{park.id}/{upload_type}/{timestamp}_{filename}"
                "approved": False,  # Requires admin approval
                "uploaded_at": datetime.now().isoformat(),
                "uploaded_by": current_user.email if current_user.email else current_user.username
            }
            uploaded_urls.append(media_object)
        
        # Update park's media/video URLs
        if upload_type == 'media':
            current_urls = park.media_urls or []
            park.media_urls = current_urls + uploaded_urls
        else:
            current_urls = park.video_urls or []
            park.video_urls = current_urls + uploaded_urls
        
        await db.commit()
        await db.refresh(park)
        
        return {
            "message": f"Successfully uploaded {len(uploaded_urls)} file(s)",
            "uploaded_urls": uploaded_urls,
            "park_id": str(park.id),
            "upload_type": upload_type,
            "requires_approval": True,
            "approval_message": "Your upload is pending admin approval. It will be visible once an admin approves it."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload media: {str(e)}"
        )


@router.delete("/{park_id}/media/{media_type}/{media_index}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_park_media(
    park_id: UUID,
    media_type: str,
    media_index: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete specific media/video from park (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete park media"
        )
    
    if media_type not in ['media', 'videos']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="media_type must be 'media' or 'videos'"
        )
    
    try:
        result = await db.execute(
            select(NationalPark).where(NationalPark.id == park_id)
        )
        park = result.scalar_one_or_none()
        
        if not park:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="National park not found"
            )
        
        # Get the appropriate media list
        media_list = park.media_urls if media_type == 'media' else park.video_urls
        
        if not media_list or media_index >= len(media_list) or media_index < 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found at specified index"
            )
        
        # Get the media object to delete
        media_obj = media_list[media_index]
        media_url = media_obj if isinstance(media_obj, str) else media_obj.get('url', '')
        
        # Try to delete the file
        try:
            use_r2 = settings.USE_R2_STORAGE.lower() == 'true'
            
            if use_r2:
                # Delete from R2
                r2_client = boto3.client(
                    's3',
                    endpoint_url=settings.R2_ENDPOINT_URL,
                    aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                    region_name='auto'
                )
                r2_client.delete_object(
                    Bucket=settings.R2_BUCKET_NAME,
                    Key=media_url
                )
            else:
                # Delete from local disk
                file_path = Path("uploads") / media_url
                if file_path.exists():
                    file_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete file: {str(e)}")
        
        # Remove from database
        media_list.pop(media_index)
        
        if media_type == 'media':
            park.media_urls = media_list
        else:
            park.video_urls = media_list
        
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete media: {str(e)}"
        )