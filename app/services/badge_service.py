"""
Badge service layer - Business logic for user badges
Handles badge creation, assignment, removal, etc.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.models.user_badge import UserBadge, UserBadgeAssignment
from app.models.user import User
from app.schemas.discussion import (
    BadgeCreate,
    BadgeUpdate,
    BadgeResponse,
    BadgeAssignmentCreate,
    BadgeAssignmentResponse
)


class BadgeService:
    """Service for badge operations"""
    
    @staticmethod
    async def create_badge(
        db: AsyncSession,
        badge_data: BadgeCreate
    ) -> UserBadge:
        """Create a new badge"""
        # Generate slug from name
        slug = badge_data.name.lower().replace(' ', '-')
        
        badge = UserBadge(
            name=badge_data.name,
            slug=slug,
            description=badge_data.description,
            icon=badge_data.icon,
            color=badge_data.color
        )
        
        db.add(badge)
        await db.commit()
        await db.refresh(badge)
        
        return badge
    
    @staticmethod
    async def get_badge_by_id(
        db: AsyncSession,
        badge_id: UUID
    ) -> Optional[UserBadge]:
        """Get badge by ID"""
        return await db.get(UserBadge, badge_id)
    
    @staticmethod
    async def get_badge_by_slug(
        db: AsyncSession,
        slug: str
    ) -> Optional[UserBadge]:
        """Get badge by slug"""
        result = await db.execute(
            select(UserBadge).where(UserBadge.slug == slug)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_badges(
        db: AsyncSession
    ) -> List[UserBadge]:
        """Get all badges"""
        result = await db.execute(
            select(UserBadge).order_by(UserBadge.name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_badge(
        db: AsyncSession,
        badge_id: UUID,
        update_data: BadgeUpdate
    ) -> Optional[UserBadge]:
        """Update badge"""
        badge = await db.get(UserBadge, badge_id)
        
        if not badge:
            return None
        
        if update_data.name is not None:
            badge.name = update_data.name
            badge.slug = update_data.name.lower().replace(' ', '-')
        
        if update_data.description is not None:
            badge.description = update_data.description
        
        if update_data.icon is not None:
            badge.icon = update_data.icon
        
        if update_data.color is not None:
            badge.color = update_data.color
        
        await db.commit()
        await db.refresh(badge)
        
        return badge
    
    @staticmethod
    async def delete_badge(
        db: AsyncSession,
        badge_id: UUID
    ) -> bool:
        """Delete badge"""
        badge = await db.get(UserBadge, badge_id)
        
        if not badge:
            return False
        
        await db.delete(badge)
        await db.commit()
        
        return True
    
    @staticmethod
    async def assign_badge_to_user(
        db: AsyncSession,
        user_id: UUID,
        badge_id: UUID,
        assigned_by: UUID,
        note: Optional[str] = None
    ) -> Optional[UserBadgeAssignment]:
        """Assign badge to user"""
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            return None
        
        # Check if badge exists
        badge = await db.get(UserBadge, badge_id)
        if not badge:
            return None
        
        # Check if already assigned
        existing = await db.execute(
            select(UserBadgeAssignment).where(
                and_(
                    UserBadgeAssignment.user_id == user_id,
                    UserBadgeAssignment.badge_id == badge_id
                )
            )
        )
        
        if existing.scalar_one_or_none():
            # Already assigned
            return None
        
        # Create assignment
        assignment = UserBadgeAssignment(
            user_id=user_id,
            badge_id=badge_id,
            assigned_by=assigned_by,
            note=note
        )
        
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        
        return assignment
    
    @staticmethod
    async def remove_badge_from_user(
        db: AsyncSession,
        user_id: UUID,
        badge_id: UUID
    ) -> bool:
        """Remove badge from user"""
        result = await db.execute(
            select(UserBadgeAssignment).where(
                and_(
                    UserBadgeAssignment.user_id == user_id,
                    UserBadgeAssignment.badge_id == badge_id
                )
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            return False
        
        await db.delete(assignment)
        await db.commit()
        
        return True
    
    @staticmethod
    async def get_user_badges(
        db: AsyncSession,
        user_id: UUID
    ) -> List[BadgeResponse]:
        """Get all badges for a user"""
        query = (
            select(UserBadge)
            .join(UserBadgeAssignment)
            .where(UserBadgeAssignment.user_id == user_id)
            .order_by(UserBadgeAssignment.assigned_at.desc())
        )
        
        result = await db.execute(query)
        badges = result.scalars().all()
        
        return [
            BadgeResponse(
                id=badge.id,
                name=badge.name,
                slug=badge.slug,
                description=badge.description,
                icon=badge.icon,
                color=badge.color,
                created_at=badge.created_at
            )
            for badge in badges
        ]
    
    @staticmethod
    async def get_badge_holders(
        db: AsyncSession,
        badge_id: UUID
    ) -> List[User]:
        """Get all users who have a specific badge"""
        query = (
            select(User)
            .join(UserBadgeAssignment)
            .where(UserBadgeAssignment.badge_id == badge_id)
            .order_by(UserBadgeAssignment.assigned_at.desc())
        )
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_badge_count_for_user(
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """Get count of badges for a user"""
        result = await db.execute(
            select(func.count())
            .select_from(UserBadgeAssignment)
            .where(UserBadgeAssignment.user_id == user_id)
        )
        return result.scalar()
    
    @staticmethod
    async def auto_assign_badges(
        db: AsyncSession,
        user_id: UUID
    ) -> List[UserBadge]:
        """
        Auto-assign badges based on user activity
        This can be called after certain milestones (e.g., 10 discussions, 50 comments)
        """
        user = await db.get(User, user_id)
        if not user:
            return []
        
        assigned_badges = []
        
        # Get system user ID for auto-assignments (or use a special admin ID)
        system_user_id = user_id  # For now, use same user; in production, use admin/system ID
        
        # Example: Assign "Active Contributor" badge if user has 10+ discussions
        if user.discussion_count >= 10:
            contributor_badge = await BadgeService.get_badge_by_slug(db, 'active-contributor')
            if contributor_badge:
                assignment = await BadgeService.assign_badge_to_user(
                    db, user_id, contributor_badge.id, system_user_id,
                    note="Auto-assigned for 10+ discussions"
                )
                if assignment:
                    assigned_badges.append(contributor_badge)
        
        # Example: Assign "Commenter" badge if user has 50+ comments
        if user.comment_count >= 50:
            commenter_badge = await BadgeService.get_badge_by_slug(db, 'commenter')
            if commenter_badge:
                assignment = await BadgeService.assign_badge_to_user(
                    db, user_id, commenter_badge.id, system_user_id,
                    note="Auto-assigned for 50+ comments"
                )
                if assignment:
                    assigned_badges.append(commenter_badge)
        
        return assigned_badges