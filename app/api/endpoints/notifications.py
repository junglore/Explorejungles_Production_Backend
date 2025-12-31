"""
Notifications API Endpoints
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.notification_service import NotificationService


router = APIRouter()


# ============================================================================
# SCHEMAS
# ============================================================================

class NotificationResponse(BaseModel):
    """Notification response model"""
    id: str
    type: str
    title: str
    message: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_url: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    metadata: dict = {}
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationsListResponse(BaseModel):
    """List of notifications with pagination"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int


class UnreadCountResponse(BaseModel):
    """Unread notification count"""
    unread_count: int


class MarkAsReadRequest(BaseModel):
    """Request to mark notification(s) as read"""
    notification_ids: Optional[List[str]] = None
    mark_all: bool = False


class BulkActionResponse(BaseModel):
    """Response for bulk actions"""
    success: bool
    count: int
    message: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/", response_model=NotificationsListResponse)
async def get_notifications(
    unread_only: bool = Query(False, description="Get only unread notifications"),
    limit: int = Query(50, ge=1, le=100, description="Number of notifications to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get notifications for the current user
    
    - **unread_only**: If true, only return unread notifications
    - **limit**: Maximum number of notifications to return (1-100)
    - **offset**: Offset for pagination
    """
    notifications, total = await NotificationService.get_user_notifications(
        db=db,
        user_id=current_user.id,
        unread_only=unread_only,
        limit=limit,
        offset=offset
    )
    
    unread_count = await NotificationService.get_unread_count(db, current_user.id)
    
    return NotificationsListResponse(
        notifications=[
            NotificationResponse(
                id=str(n.id),
                type=n.type,
                title=n.title,
                message=n.message,
                resource_type=n.resource_type,
                resource_id=str(n.resource_id) if n.resource_id else None,
                resource_url=n.resource_url,
                is_read=n.is_read,
                read_at=n.read_at,
                metadata=n.extra_data or {},  # Map extra_data to metadata
                created_at=n.created_at
            )
            for n in notifications
        ],
        total=total,
        unread_count=unread_count
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get count of unread notifications for the current user
    """
    count = await NotificationService.get_unread_count(db, current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.post("/mark-as-read", response_model=BulkActionResponse)
async def mark_notifications_as_read(
    request: MarkAsReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark notification(s) as read
    
    - **notification_ids**: List of notification IDs to mark as read (optional)
    - **mark_all**: If true, mark all notifications as read
    """
    if request.mark_all:
        count = await NotificationService.mark_all_as_read(db, current_user.id)
        return BulkActionResponse(
            success=True,
            count=count,
            message=f"Marked {count} notifications as read"
        )
    elif request.notification_ids:
        count = 0
        for notification_id in request.notification_ids:
            try:
                notification = await NotificationService.mark_as_read(
                    db=db,
                    notification_id=UUID(notification_id),
                    user_id=current_user.id
                )
                if notification:
                    count += 1
            except ValueError:
                continue  # Invalid UUID
        
        return BulkActionResponse(
            success=True,
            count=count,
            message=f"Marked {count} notifications as read"
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either provide notification_ids or set mark_all to true"
        )


@router.delete("/{notification_id}", response_model=BulkActionResponse)
async def delete_notification(
    notification_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific notification
    """
    try:
        deleted = await NotificationService.delete_notification(
            db=db,
            notification_id=UUID(notification_id),
            user_id=current_user.id
        )
        
        if deleted:
            return BulkActionResponse(
                success=True,
                count=1,
                message="Notification deleted successfully"
            )
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid notification ID")


@router.delete("/", response_model=BulkActionResponse)
async def delete_all_read_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete all read notifications for the current user
    """
    count = await NotificationService.delete_all_read_notifications(db, current_user.id)
    return BulkActionResponse(
        success=True,
        count=count,
        message=f"Deleted {count} read notifications"
    )