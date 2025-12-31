"""
Video engagement models: likes, dislikes, and comments
Tracks user interactions with videos
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class VideoLike(Base):
    """Track user likes/dislikes on videos"""
    __tablename__ = "video_likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User who liked/disliked
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Video identifier
    video_slug = Column(String(255), nullable=False, index=True)
    video_type = Column(String(50), nullable=False)  # 'series' or 'channel'
    
    # Like/Dislike (1 = like, -1 = dislike)
    vote = Column(Integer, nullable=False)  # 1 or -1
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes and constraints
    __table_args__ = (
        Index('ix_video_likes_user_video', 'user_id', 'video_slug'),
        UniqueConstraint('user_id', 'video_slug', name='uq_user_video_like'),  # One vote per user per video
    )

    def __repr__(self):
        return f"<VideoLike(user_id={self.user_id}, video_slug={self.video_slug}, vote={self.vote})>"


class VideoComment(Base):
    """User comments on videos"""
    __tablename__ = "video_comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User who commented
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Video identifier
    video_slug = Column(String(255), nullable=False, index=True)
    video_type = Column(String(50), nullable=False)  # 'series' or 'channel'
    
    # Comment content
    content = Column(Text, nullable=False)
    
    # Reply support (optional)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("video_comments.id", ondelete="CASCADE"), nullable=True)
    
    # Stats
    likes_count = Column(Integer, default=0, nullable=False)
    replies_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_edited = Column(Integer, default=0, nullable=False)  # 0 = original, 1 = edited
    is_deleted = Column(Integer, default=0, nullable=False)  # 0 = active, 1 = deleted
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="video_comments")
    replies = relationship("VideoComment", backref="parent", remote_side=[id], cascade="all, delete")
    
    # Indexes
    __table_args__ = (
        Index('ix_video_comments_video', 'video_slug', 'created_at'),
        Index('ix_video_comments_user', 'user_id', 'created_at'),
        Index('ix_video_comments_parent', 'parent_id'),
    )

    def __repr__(self):
        return f"<VideoComment(id={self.id}, user_id={self.user_id}, video_slug={self.video_slug})>"


class VideoCommentLike(Base):
    """Track user likes on video comments"""
    __tablename__ = "video_comment_likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User who liked
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Comment being liked
    comment_id = Column(UUID(as_uuid=True), ForeignKey("video_comments.id", ondelete="CASCADE"), nullable=False)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Indexes and constraints
    __table_args__ = (
        Index('ix_video_comment_likes_user_comment', 'user_id', 'comment_id'),
        UniqueConstraint('user_id', 'comment_id', name='uq_user_comment_like'),  # One like per user per comment
    )

    def __repr__(self):
        return f"<VideoCommentLike(user_id={self.user_id}, comment_id={self.comment_id})>"