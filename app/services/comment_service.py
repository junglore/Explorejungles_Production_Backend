"""
Comment service layer - Business logic for comments and nested replies
Handles comment CRUD, voting, nested structure, etc.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, asc, update
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime

from app.models.discussion import Discussion
from app.models.discussion_comment import DiscussionComment
from app.models.discussion_engagement import CommentVote
from app.models.user import User
from app.schemas.discussion import (
    CommentCreate,
    CommentUpdate,
    CommentResponse
)


class CommentService:
    """Service for comment operations"""
    
    MAX_DEPTH = 5  # Maximum nesting level
    
    @staticmethod
    async def create_comment(
        db: AsyncSession,
        discussion_id: UUID,
        comment_data: CommentCreate,
        author_id: UUID
    ) -> Optional[DiscussionComment]:
        """
        Create a new top-level comment
        """
        # Verify discussion exists and is not locked
        discussion = await db.get(Discussion, discussion_id)
        if not discussion or discussion.is_locked:
            return None
        
        # Create comment
        comment = DiscussionComment(
            discussion_id=discussion_id,
            author_id=author_id,
            content=comment_data.content,
            depth_level=0,
            path=None  # Will be set after flush
        )
        
        db.add(comment)
        await db.flush()  # Get the ID
        
        # Set path to "comment_id" (materialized path as string)
        comment.path = str(comment.id)
        
        # Update discussion comment count and activity
        await db.execute(
            update(Discussion)
            .where(Discussion.id == discussion_id)
            .values(
                comment_count=Discussion.comment_count + 1,
                last_activity_at=datetime.utcnow()
            )
        )
        
        # Update user comment count
        await db.execute(
            update(User)
            .where(User.id == author_id)
            .values(comment_count=User.comment_count + 1)
        )
        
        await db.commit()
        await db.refresh(comment)
        
        return comment
    
    @staticmethod
    async def create_reply(
        db: AsyncSession,
        parent_comment_id: UUID,
        comment_data: CommentCreate,
        author_id: UUID
    ) -> Optional[DiscussionComment]:
        """
        Create a nested reply to a comment
        """
        # Get parent comment
        parent = await db.execute(
            select(DiscussionComment)
            .options(joinedload(DiscussionComment.discussion))
            .where(DiscussionComment.id == parent_comment_id)
        )
        parent_comment = parent.unique().scalar_one_or_none()
        
        if not parent_comment:
            return None
        
        # Check depth limit
        if parent_comment.depth_level >= CommentService.MAX_DEPTH:
            return None
        
        # Check if discussion is locked
        if parent_comment.discussion.is_locked:
            return None
        
        # Create reply
        reply = DiscussionComment(
            discussion_id=parent_comment.discussion_id,
            author_id=author_id,
            parent_comment_id=parent_comment_id,
            content=comment_data.content,
            depth_level=parent_comment.depth_level + 1,
            path=None  # Will be set after flush
        )
        
        db.add(reply)
        await db.flush()
        
        # Set path: "parent_path.reply_id" (materialized path as string)
        reply.path = f"{parent_comment.path}.{reply.id}"
        
        # Update discussion comment count and activity
        await db.execute(
            update(Discussion)
            .where(Discussion.id == parent_comment.discussion_id)
            .values(
                comment_count=Discussion.comment_count + 1,
                last_activity_at=datetime.utcnow()
            )
        )
        
        # Update user comment count
        await db.execute(
            update(User)
            .where(User.id == author_id)
            .values(comment_count=User.comment_count + 1)
        )
        
        await db.commit()
        await db.refresh(reply)
        
        return reply
    
    @staticmethod
    async def get_comment_by_id(
        db: AsyncSession,
        comment_id: UUID
    ) -> Optional[DiscussionComment]:
        """Get comment by ID with author loaded"""
        query = (
            select(DiscussionComment)
            .options(joinedload(DiscussionComment.author))
            .where(DiscussionComment.id == comment_id)
        )
        
        result = await db.execute(query)
        return result.unique().scalar_one_or_none()
    
    @staticmethod
    async def get_comments_for_discussion(
        db: AsyncSession,
        discussion_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[DiscussionComment], int]:
        """
        Get top-level comments for a discussion with their nested replies
        Returns: (comments, total_count)
        """
        # Get top-level comments only (depth_level = 0)
        query = (
            select(DiscussionComment)
            .options(joinedload(DiscussionComment.author))
            .where(
                and_(
                    DiscussionComment.discussion_id == discussion_id,
                    DiscussionComment.depth_level == 0,
                    DiscussionComment.status == 'active'
                )
            )
            .order_by(desc(DiscussionComment.like_count), desc(DiscussionComment.created_at))
            .offset(offset)
            .limit(limit)
        )
        
        result = await db.execute(query)
        comments = result.unique().scalars().all()
        
        # Get total count
        count_query = select(func.count()).select_from(DiscussionComment).where(
            and_(
                DiscussionComment.discussion_id == discussion_id,
                DiscussionComment.depth_level == 0,
                DiscussionComment.status == 'active'
            )
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        return list(comments), total
    
    @staticmethod
    async def get_replies_for_comment(
        db: AsyncSession,
        parent_comment_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[DiscussionComment]:
        """Get direct replies to a comment"""
        query = (
            select(DiscussionComment)
            .options(joinedload(DiscussionComment.author))
            .where(
                and_(
                    DiscussionComment.parent_comment_id == parent_comment_id,
                    DiscussionComment.status == 'active'
                )
            )
            .order_by(asc(DiscussionComment.created_at))
            .offset(offset)
            .limit(limit)
        )
        
        result = await db.execute(query)
        return list(result.unique().scalars().all())
    
    @staticmethod
    async def update_comment(
        db: AsyncSession,
        comment_id: UUID,
        update_data: CommentUpdate,
        user_id: UUID
    ) -> Optional[DiscussionComment]:
        """Update comment (only by author)"""
        comment = await db.get(DiscussionComment, comment_id)
        
        if not comment or comment.author_id != user_id:
            return None
        
        if update_data.content is not None:
            comment.content = update_data.content
            comment.is_edited = True
            comment.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(comment)
        
        return comment
    
    @staticmethod
    async def delete_comment(
        db: AsyncSession,
        comment_id: UUID,
        user_id: UUID,
        is_admin: bool = False
    ) -> bool:
        """
        Delete comment (soft delete - mark as deleted)
        Only by author or admin
        """
        comment = await db.execute(
            select(DiscussionComment)
            .options(joinedload(DiscussionComment.discussion))
            .where(DiscussionComment.id == comment_id)
        )
        comment_obj = comment.unique().scalar_one_or_none()
        
        if not comment_obj:
            return False
        
        if not is_admin and comment_obj.author_id != user_id:
            return False
        
        # Soft delete
        comment_obj.status = 'deleted'
        comment_obj.content = '[This comment has been deleted]'
        
        # Update discussion comment count
        await db.execute(
            update(Discussion)
            .where(Discussion.id == comment_obj.discussion_id)
            .values(comment_count=Discussion.comment_count - 1)
        )
        
        # Update user comment count
        await db.execute(
            update(User)
            .where(User.id == comment_obj.author_id)
            .values(comment_count=User.comment_count - 1)
        )
        
        await db.commit()
        
        return True
    
    @staticmethod
    async def vote_comment(
        db: AsyncSession,
        comment_id: UUID,
        user_id: UUID,
        vote_type: str  # 'like' or 'dislike'
    ) -> Tuple[Optional[str], int, int]:
        """
        Vote on a comment (like/dislike)
        Returns: (current_vote_type, like_count, dislike_count)
        """
        # Check existing vote
        existing = await db.execute(
            select(CommentVote).where(
                and_(
                    CommentVote.comment_id == comment_id,
                    CommentVote.user_id == user_id
                )
            )
        )
        existing_vote = existing.scalar_one_or_none()
        
        comment = await db.get(DiscussionComment, comment_id)
        if not comment:
            return None, 0, 0
        
        if existing_vote:
            if existing_vote.vote_type == vote_type:
                # Remove vote (toggle off)
                if vote_type == 'like':
                    comment.like_count = max(0, comment.like_count - 1)
                else:
                    comment.dislike_count = max(0, comment.dislike_count - 1)
                
                await db.delete(existing_vote)
                current_vote = None
            else:
                # Change vote
                if existing_vote.vote_type == 'like':
                    comment.like_count = max(0, comment.like_count - 1)
                    comment.dislike_count += 1
                else:
                    comment.dislike_count = max(0, comment.dislike_count - 1)
                    comment.like_count += 1
                
                existing_vote.vote_type = vote_type
                current_vote = vote_type
        else:
            # New vote
            new_vote = CommentVote(
                comment_id=comment_id,
                user_id=user_id,
                vote_type=vote_type
            )
            db.add(new_vote)
            
            if vote_type == 'like':
                comment.like_count += 1
            else:
                comment.dislike_count += 1
            
            current_vote = vote_type
        
        await db.commit()
        await db.refresh(comment)
        
        return current_vote, comment.like_count, comment.dislike_count
    
    @staticmethod
    async def get_user_vote(
        db: AsyncSession,
        comment_id: UUID,
        user_id: Optional[UUID] = None
    ) -> Optional[str]:
        """Get user's vote on a comment"""
        if not user_id:
            return None
        
        result = await db.execute(
            select(CommentVote.vote_type).where(
                and_(
                    CommentVote.comment_id == comment_id,
                    CommentVote.user_id == user_id
                )
            )
        )
        vote = result.scalar_one_or_none()
        
        return vote
    
    @staticmethod
    async def build_comment_tree(
        db: AsyncSession,
        comments: List[DiscussionComment],
        user_id: Optional[UUID] = None
    ) -> List[CommentResponse]:
        """
        Build nested comment tree structure
        Recursively loads replies for each comment
        """
        result = []
        
        for comment in comments:
            # Get user's vote on this comment
            user_vote = await CommentService.get_user_vote(db, comment.id, user_id)
            
            # Get direct replies
            replies = await CommentService.get_replies_for_comment(db, comment.id)
            
            # Recursively build reply tree
            reply_responses = await CommentService.build_comment_tree(db, replies, user_id) if replies else []
            
            # Build response
            from app.services.discussion_service import DiscussionService
            author_summary = await DiscussionService.get_author_summary(db, comment.author)
            
            comment_response = CommentResponse(
                id=comment.id,
                discussion_id=comment.discussion_id,
                author=author_summary,
                content=comment.content,
                depth_level=comment.depth_level,
                like_count=comment.like_count,
                dislike_count=comment.dislike_count,
                reply_count=len(reply_responses),  # Count of direct replies
                is_edited=comment.is_edited,
                is_flagged=comment.is_flagged,
                status=comment.status,
                user_vote=user_vote,
                replies=reply_responses,
                created_at=comment.created_at,
                updated_at=comment.updated_at
            )
            
            result.append(comment_response)
        
        return result
    
    @staticmethod
    async def get_comment_count_by_discussion(
        db: AsyncSession,
        discussion_id: UUID
    ) -> int:
        """Get total comment count for a discussion"""
        result = await db.execute(
            select(func.count())
            .select_from(DiscussionComment)
            .where(
                and_(
                    DiscussionComment.discussion_id == discussion_id,
                    DiscussionComment.status == 'active'
                )
            )
        )
        return result.scalar()