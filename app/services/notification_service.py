"""
Notification Service
Handles creation and management of user notifications
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func

from app.models.notification import Notification, NotificationTypeEnum
from app.models.user import User


class NotificationService:
    """Service for managing user notifications"""
    
    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        resource_url: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        """
        Create a new notification for a user
        
        Args:
            db: Database session
            user_id: ID of the user to notify
            notification_type: Type of notification (from NotificationTypeEnum)
            title: Notification title
            message: Notification message
            resource_type: Type of associated resource (optional)
            resource_id: ID of associated resource (optional)
            resource_url: URL to the resource (optional)
            extra_data: Additional data (optional)
        
        Returns:
            Created notification
        """
        notification = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_url=resource_url,
            extra_data=extra_data or {},
            is_read=False
        )
        
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        
        return notification
    
    @staticmethod
    async def create_discussion_approved_notification(
        db: AsyncSession,
        user_id: UUID,
        discussion_id: UUID,
        discussion_title: str,
        discussion_slug: str
    ) -> Notification:
        """Create notification for discussion approval"""
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationTypeEnum.DISCUSSION_APPROVED.value,
            title="Discussion Approved! 🎉",
            message=f'Your discussion "{discussion_title}" has been approved and is now visible to the community.',
            resource_type="discussion",
            resource_id=discussion_id,
            resource_url=f"/community/discussions/{discussion_slug}",
            extra_data={"discussion_title": discussion_title, "discussion_slug": discussion_slug}
        )
    
    @staticmethod
    async def create_discussion_rejected_notification(
        db: AsyncSession,
        user_id: UUID,
        discussion_id: UUID,
        discussion_title: str,
        rejection_reason: Optional[str] = None
    ) -> Notification:
        """Create notification for discussion rejection"""
        message = f'Your discussion "{discussion_title}" was not approved.'
        if rejection_reason:
            message += f" Reason: {rejection_reason}"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationTypeEnum.DISCUSSION_REJECTED.value,
            title="Discussion Not Approved",
            message=message,
            resource_type="discussion",
            resource_id=discussion_id,
            extra_data={"discussion_title": discussion_title, "rejection_reason": rejection_reason}
        )
    
    @staticmethod
    async def create_media_approved_notification(
        db: AsyncSession,
        user_id: UUID,
        park_name: str,
        media_type: str = "media"  # "media" or "video"
    ) -> Notification:
        """Create notification for media/video approval in national park"""
        media_label = "photo" if media_type == "media" else "video"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationTypeEnum.MEDIA_APPROVED.value if media_type == "media" else NotificationTypeEnum.VIDEO_APPROVED.value,
            title=f"{media_label.capitalize()} Approved! 📸",
            message=f'Your {media_label} upload for "{park_name}" has been approved and is now visible.',
            resource_type="national_park_media",
            resource_url=f"/community/park/{park_name.lower().replace(' ', '-')}?tab=media",
            extra_data={"park_name": park_name, "media_type": media_type}
        )
    
    @staticmethod
    async def create_media_rejected_notification(
        db: AsyncSession,
        user_id: UUID,
        park_name: str,
        media_type: str = "media",
        rejection_reason: Optional[str] = None
    ) -> Notification:
        """Create notification for media/video rejection in national park"""
        media_label = "photo" if media_type == "media" else "video"
        message = f'Your {media_label} upload for "{park_name}" was not approved.'
        if rejection_reason:
            message += f" Reason: {rejection_reason}"
        
        return await NotificationService.create_notification(
            db=db,
            user_id=user_id,
            notification_type=NotificationTypeEnum.MEDIA_REJECTED.value if media_type == "media" else NotificationTypeEnum.VIDEO_REJECTED.value,
            title=f"{media_label.capitalize()} Not Approved",
            message=message,
            resource_type="national_park_media",
            extra_data={"park_name": park_name, "media_type": media_type, "rejection_reason": rejection_reason}
        )
    
    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[Notification], int]:
        """
        Get notifications for a user
        
        Args:
            db: Database session
            user_id: User ID
            unread_only: If True, only return unread notifications
            limit: Maximum number of notifications to return
            offset: Offset for pagination
        
        Returns:
            Tuple of (notifications list, total count)
        """
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get notifications
        query = query.order_by(desc(Notification.created_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        return list(notifications), total
    
    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: UUID) -> int:
        """Get count of unread notifications for a user"""
        query = select(func.count()).select_from(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        result = await db.execute(query)
        return result.scalar() or 0
    
    @staticmethod
    async def mark_as_read(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID
    ) -> Optional[Notification]:
        """Mark a notification as read"""
        query = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            await db.commit()
            await db.refresh(notification)
        
        return notification
    
    @staticmethod
    async def mark_all_as_read(db: AsyncSession, user_id: UUID) -> int:
        """Mark all notifications as read for a user"""
        query = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        )
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        count = 0
        for notification in notifications:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            count += 1
        
        if count > 0:
            await db.commit()
        
        return count
    
    @staticmethod
    async def delete_notification(
        db: AsyncSession,
        notification_id: UUID,
        user_id: UUID
    ) -> bool:
        """Delete a notification"""
        query = select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.user_id == user_id
            )
        )
        result = await db.execute(query)
        notification = result.scalar_one_or_none()
        
        if notification:
            await db.delete(notification)
            await db.commit()
            return True
        
        return False
    
    @staticmethod
    async def delete_all_read_notifications(db: AsyncSession, user_id: UUID) -> int:
        """Delete all read notifications for a user"""
        query = select(Notification).where(
            and_(
                Notification.user_id == user_id,
                Notification.is_read == True
            )
        )
        result = await db.execute(query)
        notifications = result.scalars().all()
        
        count = 0
        for notification in notifications:
            await db.delete(notification)
            count += 1
        
        if count > 0:
            await db.commit()
        
        return count