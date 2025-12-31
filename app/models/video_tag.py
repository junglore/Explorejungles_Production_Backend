"""
Video Tags model for managing predefined tags
"""

from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.database import Base


class VideoTag(Base):
    """Predefined tags for videos"""
    __tablename__ = "video_tags"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    usage_count = Column(Integer, default=0, nullable=False)  # Track how many times used
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<VideoTag(name={self.name}, usage={self.usage_count})>"
