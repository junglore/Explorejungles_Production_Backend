"""
Notification Model
Handles user notifications for approvals, rejections, and other system events
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class NotificationTypeEnum(str, enum.Enum):
    """Types of notifications"""
    DISCUSSION_APPROVED = "discussion_approved"
    DISCUSSION_REJECTED = "discussion_rejected"
    MEDIA_APPROVED = "media_approved"
    MEDIA_REJECTED = "media_rejected"
    VIDEO_APPROVED = "video_approved"
    VIDEO_REJECTED = "video_rejected"
    COMMENT_ON_DISCUSSION = "comment_on_discussion"
    REPLY_TO_COMMENT = "reply_to_comment"
    DISCUSSION_LIKED = "discussion_liked"
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class Notification(Base):
    """
    User notifications for various events
    """
    __tablename__ = "notifications"

    # Primary key and foreign keys
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Notification details
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    
    # Associated resource (optional)
    resource_type = Column(String(50), nullable=True, index=True)  # 'discussion', 'media', 'comment', etc.
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    resource_url = Column(String(1000), nullable=True)  # Link to the resource
    
    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data (renamed from metadata to avoid SQLAlchemy reserved word)
    extra_data = Column(JSON, default=dict, nullable=False)  # Flexible data storage
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", backref="notifications")
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_user_unread', 'user_id', 'is_read'),
        Index('idx_user_created', 'user_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Notification {self.type} for user {self.user_id}>"
    
    def to_dict(self):
        """Convert notification to dictionary"""
        return {
            "id": str(self.id),
            "type": self.type,
            "title": self.title,
            "message": self.message,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "resource_url": self.resource_url,
            "is_read": self.is_read,
            "read_at": self.read_at.isoformat() if self.read_at else None,
            "extra_data": self.extra_data,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
