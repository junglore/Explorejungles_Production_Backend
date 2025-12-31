"""
Pydantic schemas for discussion forum system
Request and response models for discussions, comments, votes, etc.
"""

from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from uuid import UUID


# ============================================================================
# DISCUSSION SCHEMAS
# ============================================================================

class DiscussionBase(BaseModel):
    """Base discussion schema with common fields"""
    title: str = Field(..., min_length=10, max_length=500, description="Discussion title")
    content: str = Field(..., min_length=50, max_length=10000, description="Discussion content (HTML allowed)")
    category_id: Optional[UUID] = Field(None, description="Category UUID")
    tags: List[str] = Field(default_factory=list, max_length=5, description="Tags (max 5)")
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 5:
            raise ValueError('Maximum 5 tags allowed')
        # Clean tags - remove # if present, strip whitespace
        cleaned = []
        for tag in v:
            tag = tag.strip().lstrip('#')
            if tag and len(tag) <= 50:
                cleaned.append(tag)
        return cleaned[:5]


class ThreadDiscussionCreate(DiscussionBase):
    """Schema for creating a general discussion thread"""
    type: str = Field(default="thread", description="Discussion type")
    media_url: Optional[str] = Field(None, max_length=500, description="Optional media attachment URL")


class NationalParkDiscussionCreate(BaseModel):
    """Schema for creating a national park discussion"""
    type: str = Field(default="national_park", description="Discussion type")
    park_name: str = Field(..., min_length=3, max_length=200, description="National park name")
    location: str = Field(..., min_length=3, max_length=200, description="Location (State, India)")
    banner_image: str = Field(..., max_length=500, description="Banner image URL (required)")
    content: str = Field(..., min_length=50, max_length=2000, description="Description (max 2000 chars)")
    tags: List[str] = Field(default_factory=list, max_length=5, description="Tags (max 5)")
    
    @validator('tags')
    def validate_tags(cls, v):
        if len(v) > 5:
            raise ValueError('Maximum 5 tags allowed')
        cleaned = []
        for tag in v:
            tag = tag.strip().lstrip('#')
            if tag and len(tag) <= 50:
                cleaned.append(tag)
        return cleaned[:5]


class DiscussionUpdate(BaseModel):
    """Schema for updating a discussion (only by author)"""
    title: Optional[str] = Field(None, min_length=10, max_length=500)
    content: Optional[str] = Field(None, min_length=50, max_length=10000)
    category_id: Optional[UUID] = None
    tags: Optional[List[str]] = Field(None, max_length=5)
    media_url: Optional[str] = Field(None, max_length=500)
    
    @validator('tags')
    def validate_tags(cls, v):
        if v is not None and len(v) > 5:
            raise ValueError('Maximum 5 tags allowed')
        if v:
            cleaned = []
            for tag in v:
                tag = tag.strip().lstrip('#')
                if tag and len(tag) <= 50:
                    cleaned.append(tag)
            return cleaned[:5]
        return v


# Author summary for display
class AuthorSummary(BaseModel):
    """Summary of discussion/comment author"""
    id: UUID
    full_name: Optional[str] = None
    username: str
    avatar_url: Optional[str] = None
    organization: Optional[str] = None
    professional_title: Optional[str] = None
    badges: List[str] = Field(default_factory=list, description="Badge names")
    
    model_config = ConfigDict(from_attributes=True)


# Category summary
class CategorySummary(BaseModel):
    """Summary of category"""
    id: UUID
    name: str
    slug: str
    
    model_config = ConfigDict(from_attributes=True)


# Discussion list response (minimal data)
class DiscussionListItem(BaseModel):
    """Minimal discussion data for listing"""
    id: UUID
    type: str
    title: str
    slug: str
    excerpt: Optional[str] = None
    author: AuthorSummary
    category: Optional[CategorySummary] = None
    tags: List[str] = Field(default_factory=list)
    status: str
    is_pinned: bool
    view_count: int
    like_count: int
    comment_count: int
    is_liked_by_user: bool = Field(default=False, description="Whether current user liked this")
    created_at: datetime
    last_activity_at: datetime
    
    # National park specific fields
    park_name: Optional[str] = None
    location: Optional[str] = None
    banner_image: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# Full discussion detail response
class DiscussionDetail(BaseModel):
    """Full discussion details"""
    id: UUID
    type: str
    title: str
    slug: str
    content: str
    excerpt: Optional[str] = None
    author: AuthorSummary
    category: Optional[CategorySummary] = None
    tags: List[str] = Field(default_factory=list)
    media_url: Optional[str] = None
    status: str
    is_pinned: bool
    is_locked: bool
    view_count: int
    like_count: int
    comment_count: int
    reply_count: int
    is_liked_by_user: bool = Field(default=False)
    is_saved_by_user: bool = Field(default=False)
    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime] = None
    last_activity_at: datetime
    
    # National park specific
    park_name: Optional[str] = None
    location: Optional[str] = None
    banner_image: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# COMMENT SCHEMAS
# ============================================================================

class CommentCreate(BaseModel):
    """Schema for creating a comment"""
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")


class CommentReply(BaseModel):
    """Schema for replying to a comment"""
    content: str = Field(..., min_length=1, max_length=1000, description="Reply content")


class CommentUpdate(BaseModel):
    """Schema for updating a comment"""
    content: str = Field(..., min_length=1, max_length=1000, description="Updated comment content")


class CommentVote(BaseModel):
    """Schema for voting on a comment"""
    vote_type: str = Field(..., description="Vote type: 'like' or 'dislike'")
    
    @validator('vote_type')
    def validate_vote_type(cls, v):
        if v not in ['like', 'dislike']:
            raise ValueError('vote_type must be "like" or "dislike"')
        return v


class CommentResponse(BaseModel):
    """Comment response with author and vote info"""
    id: UUID
    discussion_id: UUID
    author: AuthorSummary
    content: str
    depth_level: int
    like_count: int
    dislike_count: int
    reply_count: int
    user_vote: Optional[str] = Field(None, description="User's vote: 'like', 'dislike', or null")
    is_edited: bool
    edited_at: Optional[datetime] = None
    status: str
    created_at: datetime
    replies: List['CommentResponse'] = Field(default_factory=list, description="Nested replies")
    
    model_config = ConfigDict(from_attributes=True)


# Self-reference for nested comments
CommentResponse.model_rebuild()


# ============================================================================
# ENGAGEMENT SCHEMAS
# ============================================================================

class DiscussionLikeResponse(BaseModel):
    """Response after liking/unliking"""
    is_liked: bool
    like_count: int


class DiscussionSaveResponse(BaseModel):
    """Response after saving/unsaving"""
    is_saved: bool


# ============================================================================
# REPORT SCHEMAS
# ============================================================================

class ReportCreate(BaseModel):
    """Schema for reporting content"""
    report_type: str = Field(..., description="Type of report")
    reason: str = Field(..., min_length=10, max_length=1000, description="Reason for report")
    
    @validator('report_type')
    def validate_report_type(cls, v):
        allowed = ['spam', 'harassment', 'misinformation', 'inappropriate', 'other']
        if v not in allowed:
            raise ValueError(f'report_type must be one of: {", ".join(allowed)}')
        return v


class ReportResponse(BaseModel):
    """Report response"""
    id: UUID
    report_type: str
    reason: str
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# ADMIN SCHEMAS
# ============================================================================

class AdminApprovalRequest(BaseModel):
    """Schema for admin approval/rejection"""
    action: str = Field(..., description="'approve' or 'reject'")
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Reason for rejection")
    
    @validator('action')
    def validate_action(cls, v):
        if v not in ['approve', 'reject']:
            raise ValueError('action must be "approve" or "reject"')
        return v
    
    @validator('rejection_reason')
    def validate_rejection_reason(cls, v, values):
        if values.get('action') == 'reject' and not v:
            raise ValueError('rejection_reason is required when rejecting')
        return v


class AdminPinRequest(BaseModel):
    """Schema for pinning/unpinning discussion"""
    is_pinned: bool


class AdminLockRequest(BaseModel):
    """Schema for locking/unlocking discussion"""
    is_locked: bool


# ============================================================================
# BADGE SCHEMAS
# ============================================================================

class BadgeCreate(BaseModel):
    """Schema for creating a badge"""
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=20, description="Hex color code")
    icon: Optional[str] = Field(None, max_length=100, description="Icon class or name")


class BadgeResponse(BaseModel):
    """Badge response"""
    id: UUID
    name: str
    slug: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class BadgeUpdate(BaseModel):
    """Schema for updating a badge"""
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, max_length=20, description="Hex color code")
    icon: Optional[str] = Field(None, max_length=100, description="Icon class or name")


class BadgeAssignmentCreate(BaseModel):
    """Schema for assigning badge to user"""
    user_id: UUID
    badge_id: UUID
    note: Optional[str] = Field(None, max_length=500)


class BadgeAssignmentResponse(BaseModel):
    """Badge assignment response"""
    id: UUID
    user_id: UUID
    badge_id: UUID
    badge_name: str
    assigned_at: datetime
    note: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class BadgeAssignRequest(BaseModel):
    """Schema for assigning badge to user"""
    badge_id: UUID
    note: Optional[str] = Field(None, max_length=500)


# ============================================================================
# PAGINATION SCHEMAS
# ============================================================================

class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (starts at 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page (max 100)")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        return self.page_size


# TypeVar for generic pagination
T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    model_config = ConfigDict(arbitrary_types_allowed=True)


class PaginatedCommentsResponse(BaseModel):
    """Paginated comments response"""
    items: List[CommentResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool


# ============================================================================
# FILTER/SEARCH SCHEMAS
# ============================================================================

class DiscussionFilterParams(BaseModel):
    """Discussion filter parameters"""
    category_id: Optional[UUID] = None
    search: Optional[str] = Field(None, max_length=200, description="Search in title and content")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    type: Optional[str] = Field(None, description="Filter by type: 'thread' or 'national_park'")
    park_name: Optional[str] = Field(None, max_length=200, description="Filter by park name (for national_park type)")
    status: Optional[str] = Field(default="approved", description="Filter by status")
    sort_by: str = Field(default="recent", description="Sort by: recent, top, trending, most_discussed")
    is_pinned: Optional[bool] = None
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed = ['recent', 'top', 'trending', 'most_discussed', 'oldest']
        if v not in allowed:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed)}')
        return v


class CommentSortParams(BaseModel):
    """Comment sorting parameters"""
    sort_by: str = Field(default="top", description="Sort by: top, recent, oldest")
    
    @validator('sort_by')
    def validate_sort_by(cls, v):
        allowed = ['top', 'recent', 'oldest']
        if v not in allowed:
            raise ValueError(f'sort_by must be one of: {", ".join(allowed)}')
        return v


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class DiscussionStats(BaseModel):
    """Discussion statistics"""
    total_discussions: int
    pending_discussions: int
    approved_discussions: int
    total_comments: int
    total_likes: int
    total_views: int


class CategoryStats(BaseModel):
    """Category statistics"""
    category_id: UUID
    category_name: str
    discussion_count: int