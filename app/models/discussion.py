"""
Discussion model for community forum/threads system
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class DiscussionStatusEnum(str, enum.Enum):
    """Status of discussion for moderation workflow"""
    PENDING = "pending"      # Awaiting admin approval
    APPROVED = "approved"    # Approved and visible
    REJECTED = "rejected"    # Rejected by admin
    ARCHIVED = "archived"    # Archived/hidden


class DiscussionTypeEnum(str, enum.Enum):
    """Type of discussion post"""
    THREAD = "thread"                # General discussion thread
    NATIONAL_PARK = "national_park"  # National park specific post


class Discussion(Base):
    """
    Main discussion/thread entity for community forum
    Supports both general discussions and national park posts
    """
    __tablename__ = "discussions"

    # Primary key and foreign keys
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Core fields
    type = Column(String(50), default=DiscussionTypeEnum.THREAD.value, nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    slug = Column(String(600), unique=True, nullable=False, index=True)
    content = Column(Text, nullable=False)  # Rich HTML content
    excerpt = Column(Text, nullable=True)   # Auto-generated from content (first 500 chars)
    
    # National Park specific fields
    park_name = Column(String(200), nullable=True, index=True)  # For national_park type
    location = Column(String(200), nullable=True)                # State, India
    banner_image = Column(String(500), nullable=True)            # Banner for park posts
    
    # Media and tags
    media_url = Column(String(500), nullable=True)  # Optional attached media
    tags = Column(ARRAY(String), default=list, nullable=False)  # Array of hashtags
    
    # Status and moderation
    status = Column(
        String(50),
        default=DiscussionStatusEnum.PENDING.value,
        nullable=False, 
        index=True
    )
    is_pinned = Column(Boolean, default=False, nullable=False, index=True)  # Featured/sticky
    is_locked = Column(Boolean, default=False, nullable=False)              # Prevent new comments
    
    # Admin moderation fields
    rejection_reason = Column(Text, nullable=True)  # Admin feedback for rejected discussions
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Analytics and engagement
    view_count = Column(Integer, default=0, nullable=False, index=True)
    like_count = Column(Integer, default=0, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False, index=True)  # Includes nested replies
    reply_count = Column(Integer, default=0, nullable=False)                # Total nested replies only
    
    # Activity tracking
    last_activity_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    
    # Timestamps
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)  # When approved
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Flexible metadata storage (using different name to avoid SQLAlchemy reserved word)
    content_metadata = Column(JSON, default=dict, nullable=False)

    # Relationships
    author = relationship("User", foreign_keys=[author_id], backref="discussions")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    category = relationship("Category", backref="discussions")
    comments = relationship(
        "DiscussionComment", 
        back_populates="discussion",
        cascade="all, delete-orphan",
        order_by="DiscussionComment.created_at"
    )
    likes = relationship(
        "DiscussionLike",
        back_populates="discussion",
        cascade="all, delete-orphan"
    )
    views = relationship(
        "DiscussionView",
        back_populates="discussion",
        cascade="all, delete-orphan"
    )
    saves = relationship(
        "DiscussionSave",
        back_populates="discussion",
        cascade="all, delete-orphan"
    )
    reports = relationship(
        "DiscussionReport",
        back_populates="discussion",
        cascade="all, delete-orphan"
    )

    # Composite indexes for performance
    __table_args__ = (
        # For listing approved discussions by activity
        Index('ix_discussions_status_activity', 'status', 'last_activity_at'),
        # For filtering by category and status
        Index('ix_discussions_category_status', 'category_id', 'status', 'created_at'),
        # For filtering by type and status
        Index('ix_discussions_type_status', 'type', 'status', 'created_at'),
        # For pinned discussions
        Index('ix_discussions_pinned_status', 'is_pinned', 'status', 'created_at'),
        # For national park posts
        Index('ix_discussions_park_status', 'park_name', 'status', 'created_at'),
        # For trending discussions (high engagement)
        Index('ix_discussions_engagement', 'status', 'like_count', 'comment_count'),
    )

    def __repr__(self):
        return f"<Discussion(id={self.id}, title={self.title}, status={self.status})>"