"""
Public API endpoints for discussions
Handles discussion CRUD, comments, likes, saves, reports
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
import os
import shutil
from datetime import datetime
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

from app.db.database import get_db, get_db_with_retry
from app.core.config import settings
from app.core.deps import get_current_user, get_optional_user
from app.models.user import User
from app.services import DiscussionService, CommentService, ModerationService
from app.schemas.discussion import (
    ThreadDiscussionCreate,
    NationalParkDiscussionCreate,
    DiscussionUpdate,
    DiscussionListItem,
    DiscussionDetail,
    DiscussionFilterParams,
    PaginationParams,
    PaginatedResponse,
    CommentCreate,
    CommentUpdate,
    CommentResponse,
    CommentVote,
    ReportCreate,
    AuthorSummary,
    CategorySummary
)

router = APIRouter()


# ============================================================================
# DISCUSSION ENDPOINTS
# ============================================================================

@router.get("/", response_model=PaginatedResponse[DiscussionListItem])
async def list_discussions(
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected, archived"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    type: Optional[str] = Query(None, description="Filter by type: thread, national_park"),
    park_name: Optional[str] = Query(None, description="Filter by park name (for national_park type)"),
    is_pinned: Optional[bool] = Query(None, description="Filter pinned discussions"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    search: Optional[str] = Query(None, description="Search in title, content, excerpt"),
    sort_by: str = Query("recent", description="Sort by: recent, oldest, top, trending, most_discussed"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    List discussions with filtering and pagination
    
    - **status**: Filter by approval status (default: approved for public)
    - **category_id**: Filter by category
    - **type**: thread or national_park
    - **is_pinned**: Show only pinned discussions
    - **tags**: Filter by tags (multiple allowed)
    - **search**: Full-text search
    - **sort_by**: recent, oldest, top, trending, most_discussed
    - **page**: Page number (starts at 1)
    - **page_size**: Items per page (max 100)
    """
    # Public users only see approved discussions
    if not current_user or not current_user.is_superuser:
        status = "approved"
    
    filters = DiscussionFilterParams(
        status=status or "approved",
        category_id=category_id,
        type=type,
        park_name=park_name,
        is_pinned=is_pinned,
        tags=tags,
        search=search,
        sort_by=sort_by
    )
    
    pagination = PaginationParams(page=page, page_size=page_size)
    
    discussions, total = await DiscussionService.list_discussions(
        db, filters, pagination, current_user.id if current_user else None
    )
    
    # Build response items
    items = []
    for discussion in discussions:
        # Handle case where author might be None (deleted user or data issue)
        if discussion.author:
            author_summary = await DiscussionService.get_author_summary(db, discussion.author)
        else:
            # Fallback author for orphaned discussions
            author_summary = AuthorSummary(
                id=UUID('00000000-0000-0000-0000-000000000000'),
                username="[Deleted User]",
                full_name="Deleted User",
                avatar_url=None,
                organization=None,
                professional_title=None,
                badges=[]
            )
        
        category_summary = None
        if discussion.category:
            category_summary = CategorySummary(
                id=discussion.category.id,
                name=discussion.category.name,
                slug=discussion.category.slug
            )
        
        # Get user engagement if logged in
        engagement = await DiscussionService.get_user_engagement(
            db, discussion.id, current_user.id if current_user else None
        )
        
        item = DiscussionListItem(
            id=discussion.id,
            type=discussion.type,
            title=discussion.title,
            slug=discussion.slug,
            excerpt=discussion.excerpt,
            author=author_summary,
            category=category_summary,
            tags=discussion.tags or [],
            status=discussion.status,
            is_pinned=discussion.is_pinned,
            is_locked=discussion.is_locked,
            view_count=discussion.view_count,
            like_count=discussion.like_count,
            comment_count=discussion.comment_count,
            is_liked=engagement['is_liked'],
            is_saved=engagement['is_saved'],
            created_at=discussion.created_at,
            last_activity_at=discussion.last_activity_at
        )
        items.append(item)
    
    total_pages = (total + page_size - 1) // page_size
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1
    )


@router.get("/{discussion_id}", response_model=DiscussionDetail)
async def get_discussion(
    discussion_id: str,  # Accept string to handle both UUID and slug
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get discussion detail by ID or slug
    
    Tracks view if user is logged in or has IP address
    Supports both UUID and slug for SEO-friendly URLs
    """
    # Try to parse as UUID first, if fails, treat as slug
    try:
        uuid_id = UUID(discussion_id)
        discussion = await DiscussionService.get_discussion_by_id(
            db, uuid_id, current_user.id if current_user else None
        )
    except ValueError:
        # Not a valid UUID, treat as slug
        from sqlalchemy import select
        from app.models.discussion import Discussion
        
        result = await db.execute(
            select(Discussion).where(Discussion.slug == discussion_id)
        )
        discussion_model = result.scalar_one_or_none()
        
        if discussion_model:
            discussion = await DiscussionService.get_discussion_by_id(
                db, discussion_model.id, current_user.id if current_user else None
            )
        else:
            discussion = None
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    # Check access rights
    if discussion.status != "approved":
        if not current_user or (not current_user.is_superuser and discussion.author_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this discussion"
            )
    
    # Build response
    # Handle case where author might be None (deleted user or data issue)
    if discussion.author:
        author_summary = await DiscussionService.get_author_summary(db, discussion.author)
    else:
        # Fallback author for orphaned discussions
        author_summary = AuthorSummary(
            id=UUID('00000000-0000-0000-0000-000000000000'),
            username="[Deleted User]",
            full_name="Deleted User",
            avatar_url=None,
            organization=None,
            professional_title=None,
            badges=[]
        )
    
    category_summary = None
    if discussion.category:
        category_summary = CategorySummary(
            id=discussion.category.id,
            name=discussion.category.name,
            slug=discussion.category.slug
        )
    
    engagement = await DiscussionService.get_user_engagement(
        db, discussion.id, current_user.id if current_user else None
    )
    
    return DiscussionDetail(
        id=discussion.id,
        type=discussion.type,
        title=discussion.title,
        slug=discussion.slug,
        content=discussion.content,
        excerpt=discussion.excerpt,
        author=author_summary,
        category=category_summary,
        tags=discussion.tags or [],
        media_url=discussion.media_url,
        park_name=discussion.park_name,
        location=discussion.location,
        banner_image=discussion.banner_image,
        status=discussion.status,
        is_pinned=discussion.is_pinned,
        is_locked=discussion.is_locked,
        view_count=discussion.view_count,
        like_count=discussion.like_count,
        comment_count=discussion.comment_count,
        reply_count=discussion.reply_count,
        is_liked_by_user=engagement['is_liked'],
        is_saved_by_user=engagement['is_saved'],
        published_at=discussion.published_at,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        last_activity_at=discussion.last_activity_at
    )


@router.get("/slug/{slug}", response_model=DiscussionDetail)
async def get_discussion_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get discussion by slug (SEO-friendly URL)"""
    discussion = await DiscussionService.get_discussion_by_slug(
        db, slug, current_user.id if current_user else None
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    # Check access rights
    if discussion.status != "approved":
        if not current_user or (not current_user.is_superuser and discussion.author_id != current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this discussion"
            )
    
    # Build response (same as get_discussion)
    # Handle case where author might be None (deleted user or data issue)
    if discussion.author:
        author_summary = await DiscussionService.get_author_summary(db, discussion.author)
    else:
        # Fallback author for orphaned discussions
        author_summary = AuthorSummary(
            id=UUID('00000000-0000-0000-0000-000000000000'),
            username="[Deleted User]",
            full_name="Deleted User",
            avatar_url=None,
            organization=None,
            professional_title=None,
            badges=[]
        )
    
    category_summary = None
    if discussion.category:
        category_summary = CategorySummary(
            id=discussion.category.id,
            name=discussion.category.name,
            slug=discussion.category.slug
        )
    
    engagement = await DiscussionService.get_user_engagement(
        db, discussion.id, current_user.id if current_user else None
    )
    
    return DiscussionDetail(
        id=discussion.id,
        type=discussion.type,
        title=discussion.title,
        slug=discussion.slug,
        content=discussion.content,
        excerpt=discussion.excerpt,
        author=author_summary,
        category=category_summary,
        tags=discussion.tags or [],
        media_url=discussion.media_url,
        park_name=discussion.park_name,
        location=discussion.location,
        banner_image=discussion.banner_image,
        status=discussion.status,
        is_pinned=discussion.is_pinned,
        is_locked=discussion.is_locked,
        view_count=discussion.view_count,
        like_count=discussion.like_count,
        comment_count=discussion.comment_count,
        reply_count=discussion.reply_count,
        is_liked_by_user=engagement['is_liked'],
        is_saved_by_user=engagement['is_saved'],
        published_at=discussion.published_at,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        last_activity_at=discussion.last_activity_at
    )


@router.post("/", response_model=DiscussionDetail, status_code=status.HTTP_201_CREATED)
async def create_discussion(
    discussion_data: ThreadDiscussionCreate | NationalParkDiscussionCreate,
    db: AsyncSession = Depends(get_db_with_retry),  # Use retry for critical user content
    current_user: User = Depends(get_current_user)
):
    """
    Create a new discussion
    
    Requires authentication. Auto-approved for admins, pending for regular users.
    """
    # Auto-approve for admins
    # auto_approve = current_user.is_superuser if hasattr(current_user, 'is_admin') else False
    auto_approve = current_user.is_superuser if hasattr(current_user, 'is_superuser') else False
    
    discussion = await DiscussionService.create_discussion(
        db, discussion_data, current_user.id, auto_approve=auto_approve
    )
    
    # Build response
    author_summary = await DiscussionService.get_author_summary(db, current_user)
    
    category_summary = None
    if hasattr(discussion_data, 'category_id') and discussion_data.category_id:
        discussion = await DiscussionService.get_discussion_by_id(db, discussion.id)
        if discussion.category:
            category_summary = CategorySummary(
                id=discussion.category.id,
                name=discussion.category.name,
                slug=discussion.category.slug
            )
    
    return DiscussionDetail(
        id=discussion.id,
        type=discussion.type,
        title=discussion.title,
        slug=discussion.slug,
        content=discussion.content,
        excerpt=discussion.excerpt,
        author=author_summary,
        category=category_summary,
        tags=discussion.tags or [],
        media_url=discussion.media_url,
        park_name=discussion.park_name,
        location=discussion.location,
        banner_image=discussion.banner_image,
        status=discussion.status,
        is_pinned=discussion.is_pinned,
        is_locked=discussion.is_locked,
        view_count=discussion.view_count,
        like_count=discussion.like_count,
        comment_count=discussion.comment_count,
        reply_count=discussion.reply_count,
        is_liked_by_user=False,
        is_saved_by_user=False,
        published_at=discussion.published_at,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        last_activity_at=discussion.last_activity_at
    )


@router.put("/{discussion_id}", response_model=DiscussionDetail)
async def update_discussion(
    discussion_id: UUID,
    update_data: DiscussionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update discussion
    
    Only author or admin can update. Editing resets approval status to pending.
    """
    discussion = await DiscussionService.update_discussion(
        db, discussion_id, update_data, current_user.id
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found or you don't have permission to edit"
        )
    
    # Build response
    discussion = await DiscussionService.get_discussion_by_id(db, discussion_id)
    author_summary = await DiscussionService.get_author_summary(db, discussion.author)
    
    category_summary = None
    if discussion.category:
        category_summary = CategorySummary(
            id=discussion.category.id,
            name=discussion.category.name,
            slug=discussion.category.slug
        )
    
    engagement = await DiscussionService.get_user_engagement(db, discussion.id, current_user.id)
    
    return DiscussionDetail(
        id=discussion.id,
        type=discussion.type,
        title=discussion.title,
        slug=discussion.slug,
        content=discussion.content,
        excerpt=discussion.excerpt,
        author=author_summary,
        category=category_summary,
        tags=discussion.tags or [],
        media_url=discussion.media_url,
        park_name=discussion.park_name,
        location=discussion.location,
        banner_image=discussion.banner_image,
        status=discussion.status,
        is_pinned=discussion.is_pinned,
        is_locked=discussion.is_locked,
        view_count=discussion.view_count,
        like_count=discussion.like_count,
        comment_count=discussion.comment_count,
        reply_count=discussion.reply_count,
        is_liked_by_user=engagement['is_liked'],
        is_saved_by_user=engagement['is_saved'],
        published_at=discussion.published_at,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        last_activity_at=discussion.last_activity_at
    )


@router.delete("/{discussion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discussion(
    discussion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete discussion
    
    Only author or admin can delete
    """
    # is_admin = current_user.is_superuser if hasattr(current_user, 'is_admin') else False

    is_admin = current_user.is_superuser if hasattr(current_user, 'is_superuser') else False
    
    deleted = await DiscussionService.delete_discussion(
        db, discussion_id, current_user.id, is_admin=is_admin
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found or you don't have permission to delete"
        )
    
    return None


# ============================================================================
# ENGAGEMENT ENDPOINTS (Like, Save, Report)
# ============================================================================

@router.post("/{discussion_id}/like")
async def like_discussion(
    discussion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Like/unlike a discussion (toggle)
    
    Returns updated like status and count
    """
    is_liked, like_count = await DiscussionService.like_discussion(
        db, discussion_id, current_user.id
    )
    
    return {
        "is_liked": is_liked,
        "like_count": like_count,
        "message": "Liked" if is_liked else "Unliked"
    }


@router.post("/{discussion_id}/save")
async def save_discussion(
    discussion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Save/unsave a discussion (toggle)
    
    Returns updated save status
    """
    is_saved = await DiscussionService.save_discussion(
        db, discussion_id, current_user.id
    )
    
    return {
        "is_saved": is_saved,
        "message": "Saved" if is_saved else "Unsaved"
    }


@router.post("/{discussion_id}/report")
async def report_discussion(
    discussion_id: UUID,
    report_data: ReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Report a discussion
    
    Types: spam, harassment, misinformation, inappropriate, other
    """
    report = await ModerationService.create_report(
        db, discussion_id, current_user.id, report_data
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discussion not found or already reported by you"
        )
    
    return {
        "message": "Report submitted successfully",
        "report_id": report.id
    }


# ============================================================================
# COMMENT ENDPOINTS
# ============================================================================

@router.get("/{discussion_id}/comments", response_model=List[CommentResponse])
async def get_comments(
    discussion_id: str,  # Accept string to handle both UUID and slug
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get comments for a discussion (accepts UUID or slug)
    
    Returns top-level comments with nested replies
    """
    # Try to parse as UUID first, if fails, treat as slug
    try:
        uuid_id = UUID(discussion_id)
    except ValueError:
        # Not a valid UUID, treat as slug
        from sqlalchemy import select
        from app.models.discussion import Discussion
        
        result = await db.execute(
            select(Discussion).where(Discussion.slug == discussion_id)
        )
        discussion_model = result.scalar_one_or_none()
        
        if not discussion_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found"
            )
        uuid_id = discussion_model.id
    
    comments, total = await CommentService.get_comments_for_discussion(
        db, uuid_id, limit, offset
    )
    
    # Build comment tree
    comment_tree = await CommentService.build_comment_tree(
        db, comments, current_user.id if current_user else None
    )
    
    return comment_tree


@router.post("/{discussion_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    discussion_id: str,  # Accept string to handle both UUID and slug
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a top-level comment on a discussion (accepts UUID or slug)
    """
    # Try to parse as UUID first, if fails, treat as slug
    try:
        uuid_id = UUID(discussion_id)
    except ValueError:
        # Not a valid UUID, treat as slug
        from sqlalchemy import select
        from app.models.discussion import Discussion
        
        result = await db.execute(
            select(Discussion).where(Discussion.slug == discussion_id)
        )
        discussion_model = result.scalar_one_or_none()
        
        if not discussion_model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Discussion not found"
            )
        uuid_id = discussion_model.id
    
    comment = await CommentService.create_comment(
        db, uuid_id, comment_data, current_user.id
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Discussion not found or is locked"
        )
    
    # Build response
    author_summary = await DiscussionService.get_author_summary(db, current_user)
    user_vote = await CommentService.get_user_vote(db, comment.id, current_user.id)
    
    return CommentResponse(
        id=comment.id,
        discussion_id=comment.discussion_id,
        author=author_summary,
        content=comment.content,
        depth_level=comment.depth_level,
        like_count=comment.like_count,
        dislike_count=comment.dislike_count,
        reply_count=0,
        user_vote=user_vote,
        is_edited=comment.is_edited,
        is_flagged=comment.is_flagged,
        status=comment.status,
        replies=[],
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


@router.post("/comments/{comment_id}/reply", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def reply_to_comment(
    comment_id: UUID,
    comment_data: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reply to a comment
    
    Supports nested replies up to 5 levels deep
    """
    reply = await CommentService.create_reply(
        db, comment_id, comment_data, current_user.id
    )
    
    if not reply:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Comment not found, discussion is locked, or max nesting depth reached"
        )
    
    # Build response
    author_summary = await DiscussionService.get_author_summary(db, current_user)
    user_vote = await CommentService.get_user_vote(db, reply.id, current_user.id)
    
    return CommentResponse(
        id=reply.id,
        discussion_id=reply.discussion_id,
        author=author_summary,
        content=reply.content,
        depth_level=reply.depth_level,
        like_count=reply.like_count,
        dislike_count=reply.dislike_count,
        reply_count=0,
        user_vote=user_vote,
        is_edited=reply.is_edited,
        is_flagged=reply.is_flagged,
        status=reply.status,
        replies=[],
        created_at=reply.created_at,
        updated_at=reply.updated_at
    )


@router.put("/comments/{comment_id}", response_model=CommentResponse)
async def update_comment(
    comment_id: UUID,
    update_data: CommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a comment
    
    Only author can update their own comments
    """
    comment = await CommentService.update_comment(
        db, comment_id, update_data, current_user.id
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to edit"
        )
    
    # Build response
    comment = await CommentService.get_comment_by_id(db, comment_id)
    author_summary = await DiscussionService.get_author_summary(db, comment.author)
    user_vote = await CommentService.get_user_vote(db, comment.id, current_user.id)
    
    # Get reply count
    replies = await CommentService.get_replies_for_comment(db, comment.id)
    
    return CommentResponse(
        id=comment.id,
        discussion_id=comment.discussion_id,
        author=author_summary,
        content=comment.content,
        depth_level=comment.depth_level,
        like_count=comment.like_count,
        dislike_count=comment.dislike_count,
        reply_count=len(replies),
        user_vote=user_vote,
        is_edited=comment.is_edited,
        is_flagged=comment.is_flagged,
        status=comment.status,
        replies=[],
        created_at=comment.created_at,
        updated_at=comment.updated_at
    )


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a comment (soft delete)
    
    Only author or admin can delete
    """
    # is_admin = current_user.is_superuser if hasattr(current_user, 'is_admin') else False

    is_admin = current_user.is_superuser if hasattr(current_user, 'is_superuser') else False
    
    deleted = await CommentService.delete_comment(
        db, comment_id, current_user.id, is_admin=is_admin
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found or you don't have permission to delete"
        )
    
    return None


@router.post("/comments/{comment_id}/vote")
async def vote_on_comment(
    comment_id: UUID,
    vote_data: CommentVote,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Vote on a comment (like/dislike)
    
    Toggle vote: voting again removes vote, voting opposite changes vote
    """
    current_vote, like_count, dislike_count = await CommentService.vote_comment(
        db, comment_id, current_user.id, vote_data.vote_type
    )
    
    return {
        "current_vote": current_vote,
        "like_count": like_count,
        "dislike_count": dislike_count,
        "message": f"Vote recorded: {current_vote}" if current_vote else "Vote removed"
    }


@router.post("/comments/{comment_id}/flag")
async def flag_comment(
    comment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Flag a comment for moderation review
    """
    comment = await ModerationService.flag_comment(
        db, comment_id, current_user.id
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return {
        "message": "Comment flagged for review",
        "comment_id": comment.id
    }


# ============================================================================
# BANNER UPLOAD ENDPOINT
# ============================================================================

@router.post("/upload")
async def upload_discussion_banner(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Upload a banner image for a discussion.
    
    This endpoint handles simple banner uploads for discussions.
    - No approval workflow (discussion itself requires approval)
    - Validates file type (images only) and size (max 10MB)
    - Saves to uploads/discussions/banners/ directory
    - Returns file URL for use in discussion creation
    """
    
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 10MB)
    max_size = 10 * 1024 * 1024  # 10MB in bytes
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 10MB limit"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = Path(file.filename).suffix
    filename = f"banner_{timestamp}{file_extension}"
    file_key = f"discussions/banners/{filename}"
    
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
        upload_dir = Path("uploads/discussions/banners")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    # Return file URL (relative path)
    file_url = f"/uploads/{file_key}"
    
    return {
        "file_url": file_url,
        "filename": filename,
        "message": "Banner uploaded successfully"
    }


@router.post("/upload-media")
async def upload_discussion_media(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Upload media (images/videos) for thread discussions.
    
    This endpoint handles simple media uploads for thread discussions.
    - No approval workflow (discussion itself requires approval)
    - Validates file type (images and videos) and size (max 50MB)
    - Saves to uploads/discussions/media/ directory
    - Returns file URL for use in discussion creation
    """
    
    # Validate file type
    allowed_types = [
        "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp",
        "video/mp4", "video/webm", "video/avi", "video/mov", "video/mkv"
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 50MB)
    max_size = 50 * 1024 * 1024  # 50MB in bytes
    file_content = await file.read()
    if len(file_content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 50MB limit"
        )
    
    # Reset file pointer
    await file.seek(0)
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_extension = Path(file.filename).suffix
    filename = f"media_{timestamp}{file_extension}"
    file_key = f"discussions/media/{filename}"
    
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
        upload_dir = Path("uploads/discussions/media")
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / filename
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(file_content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file: {str(e)}"
            )
    
    # Return file URL (relative path)
    file_url = f"/uploads/{file_key}"
    
    return {
        "file_url": file_url,
        "filename": filename,
        "message": "Media uploaded successfully"
    }