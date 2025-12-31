"""
LiveStream model for managing live video content
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class StreamStatusEnum(str, enum.Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    ENDED = "ended"
    CANCELLED = "cancelled"


class LiveStream(Base):
    __tablename__ = "livestreams"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    host_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    stream_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    
    status = Column(Enum(StreamStatusEnum), default=StreamStatusEnum.SCHEDULED)
    is_live = Column(Boolean, default=False)
    viewer_count = Column(Integer, default=0)
    tags = Column(JSON, default=list)  # ["Wildlife", "Safari", "Conservation"]
    
    # Schedule and timing
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    host = relationship("User", backref="hosted_livestreams")
    category = relationship("Category", backref="livestreams")

    def __repr__(self):
        return f"<LiveStream(id={self.id}, title={self.title}, status={self.status})>"
