"""
Discussion comment model for threaded comments/replies
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class CommentStatusEnum(str, enum.Enum):
    """Status of comment"""
    ACTIVE = "active"              # Normal visible comment
    DELETED = "deleted"            # Soft deleted by user
    HIDDEN_BY_ADMIN = "hidden"     # Hidden by admin moderation


class DiscussionComment(Base):
    """
    Comments and nested replies for discussions
    Supports threaded/nested comment structure
    """
    __tablename__ = "discussion_comments"

    # Primary key and foreign keys
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    discussion_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussions.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    author_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    parent_comment_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussion_comments.id", ondelete="CASCADE"), 
        nullable=True,
        index=True
    )
    
    # Content
    content = Column(Text, nullable=False)
    
    # Nested structure metadata
    depth_level = Column(Integer, default=0, nullable=False)  # 0 = top-level, 1+ = nested
    path = Column(String(500), nullable=True, index=True)     # Materialized path (e.g., "1.5.12")
    
    # Vote counts
    like_count = Column(Integer, default=0, nullable=False)
    dislike_count = Column(Integer, default=0, nullable=False)
    reply_count = Column(Integer, default=0, nullable=False)  # Direct replies count
    
    # Edit tracking
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    # Moderation
    is_flagged = Column(Boolean, default=False, nullable=False, index=True)
    status = Column(
        String(50),
        default=CommentStatusEnum.ACTIVE.value,
        nullable=False,
        index=True
    )
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    discussion = relationship("Discussion", back_populates="comments")
    author = relationship("User", backref="discussion_comments")
    
    # Self-referential relationship for nested comments
    parent_comment = relationship(
        "DiscussionComment",
        remote_side=[id],
        backref="replies"
    )
    
    votes = relationship(
        "CommentVote",
        back_populates="comment",
        cascade="all, delete-orphan"
    )
    
    reports = relationship(
        "DiscussionReport",
        back_populates="comment",
        cascade="all, delete-orphan"
    )

    # Composite indexes
    __table_args__ = (
        # For fetching discussion comments
        Index('ix_comments_discussion_created', 'discussion_id', 'status', 'created_at'),
        # For nested replies
        Index('ix_comments_parent_created', 'parent_comment_id', 'status', 'created_at'),
        # For user's comments
        Index('ix_comments_author_status', 'author_id', 'status', 'created_at'),
        # For flagged comments (admin moderation)
        Index('ix_comments_flagged', 'is_flagged', 'status', 'created_at'),
    )

    def __repr__(self):
        return f"<DiscussionComment(id={self.id}, discussion_id={self.discussion_id}, depth={self.depth_level})>"