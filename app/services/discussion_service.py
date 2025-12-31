"""
Discussion service layer - Business logic for discussion operations
Handles CRUD, approval workflow, search, filtering, etc.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, desc, asc, update
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import re

from app.models.discussion import Discussion
from app.models.discussion_comment import DiscussionComment
from app.models.discussion_engagement import (
    DiscussionLike, DiscussionView, DiscussionSave, DiscussionReport
)
from app.models.user import User
from app.models.category import Category
from app.models.user_badge import UserBadge, UserBadgeAssignment
from app.schemas.discussion import (
    ThreadDiscussionCreate,
    NationalParkDiscussionCreate,
    DiscussionUpdate,
    DiscussionFilterParams,
    PaginationParams,
    DiscussionListItem,
    DiscussionDetail,
    AuthorSummary,
    CategorySummary,
    PaginatedResponse
)


class DiscussionService:
    """Service for discussion operations"""
    
    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate URL-friendly slug from title"""
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug[:600]
    
    @staticmethod
    def generate_excerpt(content: str, max_length: int = 500) -> str:
        """Generate excerpt from content (strip HTML, limit length)"""
        # Simple HTML strip (in production, use bleach or similar)
        text = re.sub(r'<[^>]+>', '', content)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > max_length:
            return text[:max_length] + '...'
        return text
    
    @staticmethod
    async def create_discussion(
        db: AsyncSession,
        discussion_data: ThreadDiscussionCreate | NationalParkDiscussionCreate,
        author_id: UUID,
        auto_approve: bool = False
    ) -> Discussion:
        """
        Create a new discussion
        Args:
            db: Database session
            discussion_data: Discussion creation data
            author_id: ID of the user creating the discussion
            auto_approve: If True, auto-approve (for admins)
        """
        # Generate slug
        slug = DiscussionService.generate_slug(discussion_data.title if hasattr(discussion_data, 'title') else discussion_data.park_name)
        
        # Make slug unique by appending timestamp if needed
        existing = await db.execute(select(Discussion).where(Discussion.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{int(datetime.utcnow().timestamp())}"
        
        # Create discussion
        discussion = Discussion(
            author_id=author_id,
            slug=slug,
            status='approved' if auto_approve else 'pending',
            published_at=datetime.utcnow() if auto_approve else None
        )
        
        # Set fields based on type
        if isinstance(discussion_data, ThreadDiscussionCreate):
            discussion.type = 'thread'
            discussion.title = discussion_data.title
            discussion.content = discussion_data.content
            discussion.excerpt = DiscussionService.generate_excerpt(discussion_data.content)
            discussion.category_id = discussion_data.category_id
            discussion.tags = discussion_data.tags
            discussion.media_url = discussion_data.media_url
        else:  # NationalParkDiscussionCreate
            discussion.type = 'national_park'
            discussion.title = discussion_data.park_name
            discussion.park_name = discussion_data.park_name
            discussion.location = discussion_data.location
            discussion.banner_image = discussion_data.banner_image
            discussion.content = discussion_data.content
            discussion.excerpt = DiscussionService.generate_excerpt(discussion_data.content)
            discussion.tags = discussion_data.tags
        
        db.add(discussion)
        await db.commit()
        await db.refresh(discussion)
        
        # Update user discussion count
        await db.execute(
            update(User)
            .where(User.id == author_id)
            .values(discussion_count=User.discussion_count + 1)
        )
        await db.commit()
        
        return discussion
    
    @staticmethod
    async def get_discussion_by_id(
        db: AsyncSession,
        discussion_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[Discussion]:
        """Get discussion by ID with author and category loaded"""
        query = (
            select(Discussion)
            .options(
                joinedload(Discussion.author),
                joinedload(Discussion.category)
            )
            .where(Discussion.id == discussion_id)
        )
        
        result = await db.execute(query)
        discussion = result.unique().scalar_one_or_none()
        
        if discussion and user_id:
            # Track view
            await DiscussionService.track_view(db, discussion_id, user_id)
        
        return discussion
    
    @staticmethod
    async def get_discussion_by_slug(
        db: AsyncSession,
        slug: str,
        user_id: Optional[UUID] = None
    ) -> Optional[Discussion]:
        """Get discussion by slug"""
        query = (
            select(Discussion)
            .options(
                joinedload(Discussion.author),
                joinedload(Discussion.category)
            )
            .where(Discussion.slug == slug)
        )
        
        result = await db.execute(query)
        discussion = result.unique().scalar_one_or_none()
        
        if discussion and user_id:
            await DiscussionService.track_view(db, discussion.id, user_id)
        
        return discussion
    
    @staticmethod
    async def list_discussions(
        db: AsyncSession,
        filters: DiscussionFilterParams,
        pagination: PaginationParams,
        user_id: Optional[UUID] = None
    ) -> Tuple[List[Discussion], int]:
        """
        List discussions with filters and pagination
        Returns: (discussions, total_count)
        """
        query = select(Discussion).options(
            joinedload(Discussion.author),
            joinedload(Discussion.category)
        )
        
        # Apply filters
        conditions = []
        
        if filters.status:
            conditions.append(Discussion.status == filters.status)
        
        if filters.category_id:
            conditions.append(Discussion.category_id == filters.category_id)
        
        if filters.type:
            conditions.append(Discussion.type == filters.type)
        
        if filters.park_name:
            # Exact match for park name (case-insensitive, trimmed)
            park_name_clean = filters.park_name.strip()
            conditions.append(Discussion.park_name.ilike(park_name_clean))
        
        if filters.is_pinned is not None:
            conditions.append(Discussion.is_pinned == filters.is_pinned)
        
        if filters.tags:
            # Search for any of the provided tags
            conditions.append(Discussion.tags.overlap(filters.tags))
        
        if filters.search:
            search_term = f"%{filters.search}%"
            conditions.append(
                or_(
                    Discussion.title.ilike(search_term),
                    Discussion.content.ilike(search_term),
                    Discussion.excerpt.ilike(search_term)
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Apply sorting
        if filters.sort_by == 'recent':
            query = query.order_by(desc(Discussion.created_at))
        elif filters.sort_by == 'oldest':
            query = query.order_by(asc(Discussion.created_at))
        elif filters.sort_by == 'top':
            query = query.order_by(desc(Discussion.like_count))
        elif filters.sort_by == 'trending':
            query = query.order_by(desc(Discussion.last_activity_at))
        elif filters.sort_by == 'most_discussed':
            query = query.order_by(desc(Discussion.comment_count))
        
        # Pinned discussions always on top
        query = query.order_by(desc(Discussion.is_pinned))
        
        # Get total count
        count_query = select(func.count()).select_from(Discussion)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await db.execute(query)
        discussions = result.unique().scalars().all()
        
        return list(discussions), total
    
    @staticmethod
    async def update_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        update_data: DiscussionUpdate,
        user_id: UUID
    ) -> Optional[Discussion]:
        """Update discussion (only by author or admin)"""
        discussion = await db.get(Discussion, discussion_id)
        
        if not discussion or discussion.author_id != user_id:
            return None
        
        # Update fields
        if update_data.title is not None:
            discussion.title = update_data.title
            discussion.slug = DiscussionService.generate_slug(update_data.title)
        
        if update_data.content is not None:
            discussion.content = update_data.content
            discussion.excerpt = DiscussionService.generate_excerpt(update_data.content)
        
        if update_data.category_id is not None:
            discussion.category_id = update_data.category_id
        
        if update_data.tags is not None:
            discussion.tags = update_data.tags
        
        if update_data.media_url is not None:
            discussion.media_url = update_data.media_url
        
        discussion.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(discussion)
        
        return discussion
    
    @staticmethod
    async def delete_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        user_id: UUID,
        is_admin: bool = False
    ) -> bool:
        """Delete discussion (by author or admin)"""
        discussion = await db.get(Discussion, discussion_id)
        
        if not discussion:
            return False
        
        if not is_admin and discussion.author_id != user_id:
            return False
        
        # Update user discussion count
        await db.execute(
            update(User)
            .where(User.id == discussion.author_id)
            .values(discussion_count=User.discussion_count - 1)
        )
        
        await db.delete(discussion)
        await db.commit()
        
        return True
    
    @staticmethod
    async def like_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        user_id: UUID
    ) -> Tuple[bool, int]:
        """
        Like/unlike a discussion
        Returns: (is_liked, new_like_count)
        """
        # Check if already liked
        existing = await db.execute(
            select(DiscussionLike).where(
                and_(
                    DiscussionLike.discussion_id == discussion_id,
                    DiscussionLike.user_id == user_id
                )
            )
        )
        like = existing.scalar_one_or_none()
        
        if like:
            # Unlike
            await db.delete(like)
            await db.execute(
                update(Discussion)
                .where(Discussion.id == discussion_id)
                .values(like_count=Discussion.like_count - 1)
            )
            is_liked = False
        else:
            # Like
            new_like = DiscussionLike(
                discussion_id=discussion_id,
                user_id=user_id
            )
            db.add(new_like)
            await db.execute(
                update(Discussion)
                .where(Discussion.id == discussion_id)
                .values(like_count=Discussion.like_count + 1)
            )
            is_liked = True
        
        await db.commit()
        
        # Get updated like count
        discussion = await db.get(Discussion, discussion_id)
        
        return is_liked, discussion.like_count if discussion else 0
    
    @staticmethod
    async def save_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Save/unsave a discussion
        Returns: is_saved
        """
        # Check if already saved
        existing = await db.execute(
            select(DiscussionSave).where(
                and_(
                    DiscussionSave.discussion_id == discussion_id,
                    DiscussionSave.user_id == user_id
                )
            )
        )
        save = existing.scalar_one_or_none()
        
        if save:
            # Unsave
            await db.delete(save)
            is_saved = False
        else:
            # Save
            new_save = DiscussionSave(
                discussion_id=discussion_id,
                user_id=user_id
            )
            db.add(new_save)
            is_saved = True
        
        await db.commit()
        
        return is_saved
    
    @staticmethod
    async def track_view(
        db: AsyncSession,
        discussion_id: UUID,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None
    ) -> None:
        """Track a discussion view (unique per user/IP per day)"""
        # Check if already viewed today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        query = select(DiscussionView).where(
            and_(
                DiscussionView.discussion_id == discussion_id,
                DiscussionView.viewed_at >= today_start
            )
        )
        
        if user_id:
            query = query.where(DiscussionView.user_id == user_id)
        elif ip_address:
            query = query.where(DiscussionView.ip_address == ip_address)
        else:
            return  # No tracking without user or IP
        
        result = await db.execute(query)
        existing_view = result.scalar_one_or_none()
        
        if not existing_view:
            # New view
            new_view = DiscussionView(
                discussion_id=discussion_id,
                user_id=user_id,
                ip_address=ip_address
            )
            db.add(new_view)
            
            # Increment view count
            await db.execute(
                update(Discussion)
                .where(Discussion.id == discussion_id)
                .values(view_count=Discussion.view_count + 1)
            )
            
            # Don't commit here - let the caller handle transaction
            # await db.commit()
    
    @staticmethod
    async def get_user_engagement(
        db: AsyncSession,
        discussion_id: UUID,
        user_id: Optional[UUID] = None
    ) -> dict:
        """
        Get user's engagement with a discussion
        Returns: {is_liked, is_saved}
        """
        if not user_id:
            return {'is_liked': False, 'is_saved': False}
        
        # Check like
        like_result = await db.execute(
            select(DiscussionLike).where(
                and_(
                    DiscussionLike.discussion_id == discussion_id,
                    DiscussionLike.user_id == user_id
                )
            )
        )
        is_liked = like_result.scalar_one_or_none() is not None
        
        # Check save
        save_result = await db.execute(
            select(DiscussionSave).where(
                and_(
                    DiscussionSave.discussion_id == discussion_id,
                    DiscussionSave.user_id == user_id
                )
            )
        )
        is_saved = save_result.scalar_one_or_none() is not None
        
        return {'is_liked': is_liked, 'is_saved': is_saved}
    
    @staticmethod
    async def get_author_summary(
        db: AsyncSession,
        user: User
    ) -> AuthorSummary:
        """Get author summary with badges"""
        # Get user's badges
        badge_query = (
            select(UserBadge.name)
            .join(UserBadgeAssignment)
            .where(UserBadgeAssignment.user_id == user.id)
        )
        badge_result = await db.execute(badge_query)
        badges = [badge for badge in badge_result.scalars().all()]
        
        return AuthorSummary(
            id=user.id,
            full_name=user.full_name,
            username=user.username,
            avatar_url=user.avatar_url,
            organization=user.organization,
            professional_title=user.professional_title,
            badges=badges
        )
    
    @staticmethod
    async def update_activity_timestamp(
        db: AsyncSession,
        discussion_id: UUID
    ) -> None:
        """Update last_activity_at when there's new activity (comment, etc.)"""
        await db.execute(
            update(Discussion)
            .where(Discussion.id == discussion_id)
            .values(last_activity_at=datetime.utcnow())
        )
        await db.commit()