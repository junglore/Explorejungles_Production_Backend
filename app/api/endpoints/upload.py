"""
File Upload API endpoints
Handles media file uploads for national parks
"""


from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os
import uuid
from pathlib import Path
import shutil
import structlog
import boto3
from botocore.exceptions import ClientError

# Import video duration utility
from app.utils.video_utils import get_video_duration
# Import file upload service for R2 presigned URLs
from app.services.file_upload import file_upload_service

from app.db.database import get_db
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.core.config import settings

router = APIRouter()

# Upload directory configuration
UPLOAD_DIR = Path("uploads")
MEDIA_DIR = UPLOAD_DIR / "media"
VIDEOS_DIR = UPLOAD_DIR / "videos"

# Create directories if they don't exist
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file extensions
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".avi"}

# Max file sizes (in bytes)
MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB


def get_file_extension(filename: str) -> str:
    """Get file extension from filename"""
    return Path(filename).suffix.lower()


def generate_unique_filename(original_filename: str) -> str:
    """Generate unique filename while preserving extension"""
    ext = get_file_extension(original_filename)
    unique_name = f"{uuid.uuid4()}{ext}"
    return unique_name


@router.post("/media", response_model=dict)
async def upload_media_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload a media file (image) for national parks
    Returns the file path that can be accessed via /uploads/media/{filename}
    """
    # Validate file extension
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_IMAGE_SIZE // (1024*1024)}MB"
        )
    
    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename)
    file_key = f"media/{unique_filename}"
    
    # Read file content
    file_content = await file.read()
    
    # Check if using R2
    use_r2 = settings.USE_R2_STORAGE.lower() == 'true'
    
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
        file_path = MEDIA_DIR / unique_filename
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    # Return relative path (frontend will add /uploads/ prefix)
    return {
        "filename": unique_filename,
        "url": file_key,  # Relative path: "media/{uuid}.jpg"
        "original_filename": file.filename
    }



@router.post("/videos", response_model=dict)
async def upload_video_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Upload a video file for national parks
    Returns the file path that can be accessed via /uploads/videos/{filename}
    Also extracts and returns the video duration (in seconds).
    """
    # Validate file extension
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_VIDEO_EXTENSIONS)}"
        )

    # Check file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_VIDEO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_VIDEO_SIZE // (1024*1024)}MB"
        )

    # Generate unique filename
    unique_filename = generate_unique_filename(file.filename)
    file_key = f"videos/{unique_filename}"
    
    # Read file content
    file_content = await file.read()
    
    # Check if using R2
    use_r2 = settings.USE_R2_STORAGE.lower() == 'true'
    
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
        
        # For R2, we can't extract duration easily, return None or 0
        duration = None
    else:
        # Save to local disk
        file_path = VIDEOS_DIR / unique_filename
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
        
        # Extract video duration (in seconds) - only for local files
        duration = get_video_duration(str(file_path))

    # Return relative path (frontend will add /uploads/ prefix)
    return {
        "filename": unique_filename,
        "url": file_key,  # Relative path: "videos/{uuid}.mp4"
        "original_filename": file.filename,
        "duration": duration
    }


@router.delete("/media/{filename}")
async def delete_media_file(
    filename: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a media file"""
    file_path = MEDIA_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        file_path.unlink()
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


@router.delete("/videos/{filename}")
async def delete_video_file(
    filename: str,
    current_user: User = Depends(get_current_admin_user)
):
    """Delete a video file"""
    file_path = VIDEOS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    try:
        file_path.unlink()
        return {"message": "File deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )


# ==================== R2 PRESIGNED URL ENDPOINTS ====================

@router.post("/request-presigned", response_model=dict)
async def request_presigned_upload_url(
    filename: str = Form(...),
    file_size: int = Form(...),
    mime_type: str = Form(...)
):
    """
    Request a presigned URL for direct R2 upload (for files >4MB)
    
    Frontend flow:
    1. Call this endpoint to get presigned URL
    2. Upload file directly to R2 using presigned URL (PUT request)
    3. Call /upload/confirm-presigned to record upload completion
    
    Args:
        filename: Original filename
        file_size: File size in bytes
        mime_type: File MIME type
        
    Returns:
        Dictionary with upload_url, file_key, and expires_in
    """
    logger = structlog.get_logger()
    
    try:
        # Check if R2 is enabled
        if not file_upload_service.use_r2:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="R2 storage is not enabled. Use regular upload endpoint."
            )
        
        # Generate presigned URL
        presigned_data = await file_upload_service.generate_presigned_upload_url(
            filename=filename,
            file_size=file_size,
            mime_type=mime_type
        )
        
        logger.info("Presigned URL requested", 
                   filename=filename, 
                   file_size=file_size, 
                   file_key=presigned_data["file_key"])
        
        return {
            "success": True,
            "upload_url": presigned_data["upload_url"],
            "file_key": presigned_data["file_key"],
            "expires_in": presigned_data["expires_in"],
            "mime_type": presigned_data["mime_type"],
            "category": presigned_data["category"]
        }
        
    except Exception as e:
        logger.error("Presigned URL generation failed", error=str(e), filename=filename)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )


@router.post("/confirm-presigned", response_model=dict)
async def confirm_presigned_upload(
    file_key: str = Form(...),
    file_size: int = Form(...),
    mime_type: str = Form(...),
    original_filename: str = Form(...)
):
    """
    Confirm that file was successfully uploaded to R2 via presigned URL
    
    Returns the same format as regular upload endpoint for consistency
    
    Args:
        file_key: R2 object key (e.g., "images/abc123.jpg")
        file_size: File size in bytes
        mime_type: File MIME type
        original_filename: Original filename
        
    Returns:
        Dictionary with file information
    """
    logger = structlog.get_logger()
    
    try:
        # Parse file info from file_key
        parts = file_key.split('/')
        if len(parts) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file_key format"
            )
        
        category = parts[0]
        filename = parts[-1]
        
        logger.info("Presigned upload confirmed", 
                   file_key=file_key, 
                   file_size=file_size,
                   category=category)
        
        # Return same format as upload_file() for consistency
        return {
            "success": True,
            "file_url": file_key,  # e.g., "images/abc123.jpg"
            "file_size": file_size,
            "mime_type": mime_type,
            "filename": filename,
            "original_filename": original_filename,
            "category": category,
            "upload_success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload confirmation failed", error=str(e), file_key=file_key)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to confirm upload: {str(e)}"
        )