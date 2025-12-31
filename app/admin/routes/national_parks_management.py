"""
Admin Routes for National Parks Management
Handles admin CRUD operations and media management for national parks
"""

from fastapi import APIRouter, Depends, Request, Form, HTTPException, status, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List
from uuid import UUID
from pathlib import Path
import shutil
from datetime import datetime

from app.db.database import get_db
from app.models.national_park import NationalPark
from app.models.user import User
from app.services.notification_service import NotificationService

router = APIRouter()
templates = Jinja2Templates(directory="app/admin/templates")


@router.get("/", response_class=HTMLResponse)
async def list_national_parks(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """List all national parks in admin panel"""
    
    # Check authentication via session
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    result = await db.execute(
        select(NationalPark).order_by(desc(NationalPark.created_at))
    )
    parks = result.scalars().all()
    
    return templates.TemplateResponse(
        "national_parks/list.html",
        {"request": request, "parks": parks}
    )


@router.get("/{park_id}/media", response_class=HTMLResponse)
async def manage_park_media(
    request: Request,
    park_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Manage media and videos for a specific park"""
    
    # Check authentication via session
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    result = await db.execute(
        select(NationalPark).where(NationalPark.id == park_id)
    )
    park = result.scalar_one_or_none()
    
    if not park:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="National park not found"
        )
    
    # Prepare media items with metadata
    media_items = []
    for idx, item in enumerate(park.media_urls or []):
        if isinstance(item, dict):
            # New format with approval tracking
            url = item.get('url', '')
            # Add /uploads/ prefix if not present
            display_url = f"/uploads/{url}" if url and not url.startswith('/uploads/') else url
            media_items.append({
                'index': idx,
                'url': display_url,
                'type': 'image',
                'approved': item.get('approved', False),
                'uploaded_at': item.get('uploaded_at', 'Unknown'),
                'uploaded_by': item.get('uploaded_by', 'Unknown')
            })
        else:
            # Old format (just URL string)
            # Add /uploads/ prefix if not present
            display_url = f"/uploads/{item}" if item and not item.startswith('/uploads/') else item
            media_items.append({
                'index': idx,
                'url': display_url,
                'type': 'image',
                'approved': True,  # Old items are considered approved
                'uploaded_at': 'Unknown',
                'uploaded_by': 'Unknown'
            })
    
    video_items = []
    for idx, item in enumerate(park.video_urls or []):
        if isinstance(item, dict):
            # New format with approval tracking
            url = item.get('url', '')
            # Add /uploads/ prefix if not present
            display_url = f"/uploads/{url}" if url and not url.startswith('/uploads/') else url
            video_items.append({
                'index': idx,
                'url': display_url,
                'type': 'video',
                'approved': item.get('approved', False),
                'uploaded_at': item.get('uploaded_at', 'Unknown'),
                'uploaded_by': item.get('uploaded_by', 'Unknown')
            })
        else:
            # Old format (just URL string)
            # Add /uploads/ prefix if not present
            display_url = f"/uploads/{item}" if item and not item.startswith('/uploads/') else item
            video_items.append({
                'index': idx,
                'url': display_url,
                'type': 'video',
                'approved': True,  # Old items are considered approved
                'uploaded_at': 'Unknown',
                'uploaded_by': 'Unknown'
            })
    
    return templates.TemplateResponse(
        "national_parks/media_management.html",
        {
            "request": request,
            "park": park,
            "media_items": media_items,
            "video_items": video_items
        }
    )


@router.post("/{park_id}/media/approve")
async def approve_media_admin(
    request: Request,
    park_id: UUID,
    media_type: str = Form(...),
    media_index: int = Form(...),
    approve: str = Form(...),  # Changed from bool to str to handle form data
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject media/video from park (Admin action)"""
    
    # Check authentication via session
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    if media_type not in ['media', 'videos']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid media type"
        )
    
    # Convert string to boolean
    approve_bool = approve.lower() in ('true', '1', 'yes')
    
    print(f"DEBUG: Approving media - park_id={park_id}, media_type={media_type}, index={media_index}, approve={approve}, approve_bool={approve_bool}")
    
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
        
        # Get the appropriate media list (create a mutable copy)
        media_list = list(park.media_urls) if media_type == 'media' else list(park.video_urls)
        
        print(f"DEBUG: Media list length: {len(media_list)}, index: {media_index}")
        
        if not media_list or media_index >= len(media_list) or media_index < 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found at specified index"
            )
        
        # Update approval status
        item = media_list[media_index]
        print(f"DEBUG: Current item: {item}")
        print(f"DEBUG: Item type: {type(item)}")
        
        if isinstance(item, dict):
            # Create a new dict to ensure SQLAlchemy detects the change
            updated_item = dict(item)
            updated_item['approved'] = approve_bool
            media_list[media_index] = updated_item
            print(f"DEBUG: Updated dict item: {media_list[media_index]}")
        else:
            # Convert old format to new format
            media_list[media_index] = {
                'url': item,
                'approved': approve_bool,
                'uploaded_at': datetime.now().isoformat(),
                'uploaded_by': 'Unknown'
            }
            print(f"DEBUG: Converted string to dict: {media_list[media_index]}")
        
        # Save changes - create NEW list to force SQLAlchemy to detect change
        new_list = list(media_list)
        if media_type == 'media':
            park.media_urls = new_list
            print(f"DEBUG: Set park.media_urls to new list")
        else:
            park.video_urls = new_list
            print(f"DEBUG: Set park.video_urls to new list")
        
        # Mark the attribute as modified explicitly
        from sqlalchemy.orm import attributes
        if media_type == 'media':
            attributes.flag_modified(park, 'media_urls')
        else:
            attributes.flag_modified(park, 'video_urls')
        
        print(f"DEBUG: Committing changes...")
        await db.commit()
        print(f"DEBUG: Commit successful!")
        
        # Create notification for the uploader if media was approved
        if approve_bool:
            try:
                # Get uploader identifier from the media item (could be email or username)
                uploader_identifier = media_list[media_index].get('uploaded_by')
                if uploader_identifier and uploader_identifier != 'Unknown':
                    # Look up user by email or username
                    user_result = await db.execute(
                        select(User).where(
                            (User.email == uploader_identifier) | (User.username == uploader_identifier)
                        )
                    )
                    user = user_result.scalar_one_or_none()
                    
                    if user:
                        await NotificationService.create_media_approved_notification(
                            db=db,
                            user_id=user.id,
                            park_name=park.name,
                            media_type=media_type
                        )
                        print(f"DEBUG: Notification created for user {user.email}")
                    else:
                        print(f"DEBUG: User not found for identifier: {uploader_identifier}")
            except Exception as e:
                print(f"Failed to create notification: {e}")
        
        # Redirect back to media management page
        return RedirectResponse(
            url=f"/admin/national-parks/{park_id}/media",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update approval status: {str(e)}"
        )


@router.post("/{park_id}/media/delete")
async def delete_media_admin(
    request: Request,
    park_id: UUID,
    media_type: str = Form(...),
    media_index: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Delete media/video from park (Admin action)"""
    
    # Check authentication via session
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    if media_type not in ['media', 'videos']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid media type"
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
        
        # Get the appropriate media list (create a mutable copy)
        media_list = list(park.media_urls) if media_type == 'media' else list(park.video_urls)
        
        if not media_list or media_index >= len(media_list) or media_index < 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Media not found at specified index"
            )
        
        # Get the item to extract URL for file deletion
        item = media_list[media_index]
        
        # Extract URL from either string or dict format
        if isinstance(item, dict):
            media_url = item.get('url', '')
        else:
            media_url = item
        
        # Try to delete the physical file
        try:
            if media_url:
                filename = media_url.split('/')[-1]
                file_path = Path("uploads/national_parks") / str(park.id) / media_type / filename
                if file_path.exists():
                    file_path.unlink()
        except Exception as e:
            print(f"Warning: Could not delete physical file: {str(e)}")
        
        # Remove from database list
        media_list.pop(media_index)
        
        if media_type == 'media':
            park.media_urls = media_list
        else:
            park.video_urls = media_list
        
        await db.commit()
        
        # Redirect back to media management page
        return RedirectResponse(
            url=f"/admin/national-parks/{park_id}/media",
            status_code=status.HTTP_303_SEE_OTHER
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete media: {str(e)}"
        )