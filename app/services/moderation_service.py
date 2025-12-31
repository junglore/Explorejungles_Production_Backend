"""
Moderation service layer - Business logic for admin moderation operations
Handles approval workflow, reports, pin/lock, etc.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, update
from sqlalchemy.orm import joinedload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from app.models.discussion import Discussion
from app.models.discussion_comment import DiscussionComment
from app.models.discussion_engagement import DiscussionReport
from app.models.user import User
from app.services.notification_service import NotificationService
from app.schemas.discussion import (
    AdminApprovalRequest,
    ReportCreate,
    ReportResponse,
    PaginationParams
)


class ModerationService:
    """Service for moderation and admin operations"""
    
    @staticmethod
    async def approve_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        admin_id: UUID
    ) -> Optional[Discussion]:
        """Approve a pending discussion"""
        discussion = await db.get(Discussion, discussion_id)
        
        if not discussion or discussion.status != 'pending':
            return None
        
        discussion.status = 'approved'
        discussion.reviewed_by = admin_id
        discussion.reviewed_at = datetime.utcnow()
        discussion.published_at = datetime.utcnow()
        discussion.rejection_reason = None
        
        await db.commit()
        await db.refresh(discussion)
        
        # Create notification for the author
        try:
            await NotificationService.create_discussion_approved_notification(
                db=db,
                user_id=discussion.author_id,
                discussion_id=discussion.id,
                discussion_title=discussion.title,
                discussion_slug=discussion.slug
            )
        except Exception as e:
            # Don't fail the approval if notification fails
            print(f"Failed to create notification: {e}")
        
        return discussion
    
    @staticmethod
    async def reject_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        admin_id: UUID,
        rejection_data: AdminApprovalRequest
    ) -> Optional[Discussion]:
        """Reject a pending discussion"""
        discussion = await db.get(Discussion, discussion_id)
        
        if not discussion or discussion.status != 'pending':
            return None
        
        discussion.status = 'rejected'
        discussion.reviewed_by = admin_id
        discussion.reviewed_at = datetime.utcnow()
        discussion.rejection_reason = rejection_data.rejection_reason
        
        await db.commit()
        await db.refresh(discussion)
        
        # Create notification for the author
        try:
            await NotificationService.create_discussion_rejected_notification(
                db=db,
                user_id=discussion.author_id,
                discussion_id=discussion.id,
                discussion_title=discussion.title,
                rejection_reason=rejection_data.rejection_reason
            )
        except Exception as e:
            # Don't fail the rejection if notification fails
            print(f"Failed to create notification: {e}")
        
        return discussion
    
    @staticmethod
    async def pin_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        admin_id: UUID,
        pin: bool = True
    ) -> Optional[Discussion]:
        """Pin/unpin a discussion"""
        discussion = await db.get(Discussion, discussion_id)
        
        if not discussion:
            return None
        
        discussion.is_pinned = pin
        
        await db.commit()
        await db.refresh(discussion)
        
        return discussion
    
    @staticmethod
    async def lock_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        admin_id: UUID,
        lock: bool = True
    ) -> Optional[Discussion]:
        """Lock/unlock a discussion (prevents new comments)"""
        discussion = await db.get(Discussion, discussion_id)
        
        if not discussion:
            return None
        
        discussion.is_locked = lock
        
        await db.commit()
        await db.refresh(discussion)
        
        return discussion
    
    @staticmethod
    async def archive_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        admin_id: UUID
    ) -> Optional[Discussion]:
        """Archive a discussion"""
        discussion = await db.get(Discussion, discussion_id)
        
        if not discussion:
            return None
        
        discussion.status = 'archived'
        discussion.reviewed_by = admin_id
        discussion.reviewed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(discussion)
        
        return discussion
    
    @staticmethod
    async def get_pending_discussions(
        db: AsyncSession,
        pagination: PaginationParams
    ) -> Tuple[List[Discussion], int]:
        """Get all pending discussions for review"""
        query = (
            select(Discussion)
            .options(
                joinedload(Discussion.author),
                joinedload(Discussion.category)
            )
            .where(Discussion.status == 'pending')
            .order_by(desc(Discussion.created_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        
        result = await db.execute(query)
        discussions = result.unique().scalars().all()
        
        # Get total count
        count_query = select(func.count()).select_from(Discussion).where(
            Discussion.status == 'pending'
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return list(discussions), total
    
    @staticmethod
    async def create_report(
        db: AsyncSession,
        discussion_id: UUID,
        reporter_id: UUID,
        report_data: ReportCreate
    ) -> Optional[DiscussionReport]:
        """Report a discussion"""
        # Check if discussion exists
        discussion = await db.get(Discussion, discussion_id)
        if not discussion:
            return None
        
        # Check if user already reported this discussion
        existing = await db.execute(
            select(DiscussionReport).where(
                and_(
                    DiscussionReport.discussion_id == discussion_id,
                    DiscussionReport.reporter_id == reporter_id
                )
            )
        )
        
        if existing.scalar_one_or_none():
            # Already reported
            return None
        
        # Create report
        report = DiscussionReport(
            discussion_id=discussion_id,
            reporter_id=reporter_id,
            report_type=report_data.report_type,
            reason=report_data.reason,
            status='pending'
        )
        
        db.add(report)
        await db.commit()
        await db.refresh(report)
        
        return report
    
    @staticmethod
    async def get_reports(
        db: AsyncSession,
        status: Optional[str] = None,
        pagination: Optional[PaginationParams] = None
    ) -> Tuple[List[DiscussionReport], int]:
        """Get all reports (optionally filtered by status)"""
        query = (
            select(DiscussionReport)
            .options(
                joinedload(DiscussionReport.discussion),
                joinedload(DiscussionReport.reporter)
            )
            .order_by(desc(DiscussionReport.created_at))
        )
        
        if status:
            query = query.where(DiscussionReport.status == status)
        
        # Get total count
        count_query = select(func.count()).select_from(DiscussionReport)
        if status:
            count_query = count_query.where(DiscussionReport.status == status)
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        if pagination:
            query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await db.execute(query)
        reports = result.unique().scalars().all()
        
        return list(reports), total
    
    @staticmethod
    async def resolve_report(
        db: AsyncSession,
        report_id: UUID,
        admin_id: UUID,
        resolution: str,  # 'resolved', 'dismissed'
        admin_notes: Optional[str] = None
    ) -> Optional[DiscussionReport]:
        """Resolve a report"""
        report = await db.get(DiscussionReport, report_id)
        
        if not report or report.status != 'pending':
            return None
        
        report.status = resolution
        report.reviewed_by = admin_id
        report.reviewed_at = datetime.utcnow()
        report.admin_notes = admin_notes
        
        await db.commit()
        await db.refresh(report)
        
        return report
    
    @staticmethod
    async def hide_comment(
        db: AsyncSession,
        comment_id: UUID,
        admin_id: UUID,
        hide: bool = True
    ) -> Optional[DiscussionComment]:
        """Hide/unhide a comment (admin moderation)"""
        comment = await db.get(DiscussionComment, comment_id)
        
        if not comment:
            return None
        
        comment.status = 'hidden' if hide else 'active'
        
        await db.commit()
        await db.refresh(comment)
        
        return comment
    
    @staticmethod
    async def flag_comment(
        db: AsyncSession,
        comment_id: UUID,
        user_id: UUID
    ) -> Optional[DiscussionComment]:
        """Flag a comment for review"""
        comment = await db.get(DiscussionComment, comment_id)
        
        if not comment:
            return None
        
        comment.is_flagged = True
        
        await db.commit()
        await db.refresh(comment)
        
        return comment
    
    @staticmethod
    async def get_flagged_comments(
        db: AsyncSession,
        pagination: PaginationParams
    ) -> Tuple[List[DiscussionComment], int]:
        """Get all flagged comments for review"""
        query = (
            select(DiscussionComment)
            .options(
                joinedload(DiscussionComment.author),
                joinedload(DiscussionComment.discussion)
            )
            .where(DiscussionComment.is_flagged == True)
            .order_by(desc(DiscussionComment.created_at))
            .offset(pagination.offset)
            .limit(pagination.limit)
        )
        
        result = await db.execute(query)
        comments = result.unique().scalars().all()
        
        # Get total count
        count_query = select(func.count()).select_from(DiscussionComment).where(
            DiscussionComment.is_flagged == True
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return list(comments), total
    
    @staticmethod
    async def get_moderation_stats(
        db: AsyncSession
    ) -> dict:
        """Get moderation statistics for admin dashboard"""
        # Pending discussions count
        pending_discussions = await db.execute(
            select(func.count()).select_from(Discussion).where(
                Discussion.status == 'pending'
            )
        )
        
        # Pending reports count
        pending_reports = await db.execute(
            select(func.count()).select_from(DiscussionReport).where(
                DiscussionReport.status == 'pending'
            )
        )
        
        # Flagged comments count
        flagged_comments = await db.execute(
            select(func.count()).select_from(DiscussionComment).where(
                DiscussionComment.is_flagged == True
            )
        )
        
        # Total approved discussions
        approved_discussions = await db.execute(
            select(func.count()).select_from(Discussion).where(
                Discussion.status == 'approved'
            )
        )
        
        # Total rejected discussions
        rejected_discussions = await db.execute(
            select(func.count()).select_from(Discussion).where(
                Discussion.status == 'rejected'
            )
        )
        
        return {
            'pending_discussions': pending_discussions.scalar(),
            'pending_reports': pending_reports.scalar(),
            'flagged_comments': flagged_comments.scalar(),
            'approved_discussions': approved_discussions.scalar(),
            'rejected_discussions': rejected_discussions.scalar()
        }
    
    @staticmethod
    async def bulk_approve_discussions(
        db: AsyncSession,
        discussion_ids: List[UUID],
        admin_id: UUID
    ) -> int:
        """Bulk approve multiple discussions"""
        count = 0
        
        for discussion_id in discussion_ids:
            discussion = await ModerationService.approve_discussion(
                db, discussion_id, admin_id
            )
            if discussion:
                count += 1
        
        return count
    
    @staticmethod
    async def bulk_reject_discussions(
        db: AsyncSession,
        discussion_ids: List[UUID],
        admin_id: UUID,
        rejection_data: AdminApprovalRequest
    ) -> int:
        """Bulk reject multiple discussions"""
        count = 0
        
        for discussion_id in discussion_ids:
            discussion = await ModerationService.reject_discussion(
                db, discussion_id, admin_id, rejection_data
            )
            if discussion:
                count += 1
        
        return count