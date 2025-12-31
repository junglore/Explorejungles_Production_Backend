"""
Discussion engagement models: likes, votes, views, saves, and reports
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class VoteTypeEnum(str, enum.Enum):
    """Vote type for comments"""
    LIKE = "like"
    DISLIKE = "dislike"


class ReportTypeEnum(str, enum.Enum):
    """Type of content report"""
    SPAM = "spam"
    HARASSMENT = "harassment"
    MISINFORMATION = "misinformation"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class ReportStatusEnum(str, enum.Enum):
    """Status of report review"""
    PENDING = "pending"
    REVIEWED = "reviewed"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class DiscussionLike(Base):
    """
    Tracks user likes on discussions
    Binary like system (like/unlike)
    """
    __tablename__ = "discussion_likes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    discussion_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussions.id", ondelete="CASCADE"), 
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    discussion = relationship("Discussion", back_populates="likes")
    user = relationship("User", backref="discussion_likes")

    # Constraints
    __table_args__ = (
        UniqueConstraint('discussion_id', 'user_id', name='uq_discussion_like_user'),
        Index('ix_discussion_likes_user', 'user_id', 'created_at'),
        Index('ix_discussion_likes_discussion', 'discussion_id', 'created_at'),
    )

    def __repr__(self):
        return f"<DiscussionLike(discussion_id={self.discussion_id}, user_id={self.user_id})>"


class CommentVote(Base):
    """
    Tracks user votes (like/dislike) on comments
    Upvote/downvote system for comments
    """
    __tablename__ = "comment_votes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    comment_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussion_comments.id", ondelete="CASCADE"), 
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    vote_type = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    comment = relationship("DiscussionComment", back_populates="votes")
    user = relationship("User", backref="comment_votes")

    # Constraints
    __table_args__ = (
        UniqueConstraint('comment_id', 'user_id', name='uq_comment_vote_user'),
        Index('ix_comment_votes_user', 'user_id', 'vote_type', 'created_at'),
        Index('ix_comment_votes_comment', 'comment_id', 'vote_type'),
    )

    def __repr__(self):
        return f"<CommentVote(comment_id={self.comment_id}, user_id={self.user_id}, type={self.vote_type})>"


class DiscussionView(Base):
    """
    Tracks unique views per user/session for analytics
    Helps calculate view counts
    """
    __tablename__ = "discussion_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    discussion_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussions.id", ondelete="CASCADE"), 
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True  # Nullable for anonymous users
    )
    ip_address = Column(String(45), nullable=True)  # For anonymous tracking (IPv4/IPv6)
    viewed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    discussion = relationship("Discussion", back_populates="views")
    user = relationship("User", backref="discussion_views")

    # Indexes
    __table_args__ = (
        Index('ix_discussion_views_unique', 'discussion_id', 'user_id'),
        Index('ix_discussion_views_ip', 'discussion_id', 'ip_address', 'viewed_at'),
    )

    def __repr__(self):
        return f"<DiscussionView(discussion_id={self.discussion_id}, user_id={self.user_id})>"


class DiscussionSave(Base):
    """
    Tracks saved/bookmarked discussions per user
    """
    __tablename__ = "discussion_saves"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    discussion_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussions.id", ondelete="CASCADE"), 
        nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    discussion = relationship("Discussion", back_populates="saves")
    user = relationship("User", backref="discussion_saves")

    # Constraints
    __table_args__ = (
        UniqueConstraint('discussion_id', 'user_id', name='uq_discussion_save_user'),
        Index('ix_discussion_saves_user', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<DiscussionSave(discussion_id={self.discussion_id}, user_id={self.user_id})>"


class DiscussionReport(Base):
    """
    User reports for content moderation
    Can report both discussions and comments
    """
    __tablename__ = "discussion_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    discussion_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussions.id", ondelete="CASCADE"), 
        nullable=True  # Either discussion or comment
    )
    comment_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("discussion_comments.id", ondelete="CASCADE"), 
        nullable=True  # Either discussion or comment
    )
    reporter_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Report details
    report_type = Column(String(50), nullable=False)
    reason = Column(Text, nullable=False)
    
    # Review status
    status = Column(
        String(50),
        default=ReportStatusEnum.PENDING.value,
        nullable=False,
        index=True
    )
    reviewed_by = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True
    )
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    discussion = relationship("Discussion", back_populates="reports")
    comment = relationship("DiscussionComment", back_populates="reports")
    reporter = relationship("User", foreign_keys=[reporter_id], backref="reports_made")
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    # Indexes
    __table_args__ = (
        Index('ix_reports_status_created', 'status', 'created_at'),
        Index('ix_reports_discussion', 'discussion_id', 'status'),
        Index('ix_reports_comment', 'comment_id', 'status'),
        Index('ix_reports_reporter', 'reporter_id', 'created_at'),
    )

    def __repr__(self):
        content_type = "discussion" if self.discussion_id else "comment"
        return f"<DiscussionReport(id={self.id}, type={content_type}, status={self.status})>"