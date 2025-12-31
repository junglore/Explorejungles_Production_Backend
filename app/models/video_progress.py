"""
Video watch progress tracking model
Stores user's watch progress for each video
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.database import Base


class VideoWatchProgress(Base):
    """Track user's watch progress for videos"""
    __tablename__ = "video_watch_progress"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # User who watched the video
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Video identifier (slug)
    video_slug = Column(String(255), nullable=False, index=True)
    
    # Video type (series or channel)
    video_type = Column(String(50), nullable=False)  # 'series' or 'channel'
    
    # Progress tracking
    current_time = Column(Float, default=0, nullable=False)  # Current playback position in seconds
    duration = Column(Float, nullable=True)  # Total video duration in seconds
    progress_percentage = Column(Float, default=0, nullable=False)  # 0-100
    
    # Status
    completed = Column(Integer, default=0, nullable=False)  # 0 = in progress, 1 = completed
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_watched_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes for faster queries
    __table_args__ = (
        Index('ix_video_progress_user_video', 'user_id', 'video_slug'),
        Index('ix_video_progress_user_type', 'user_id', 'video_type'),
    )

    def __repr__(self):
        return f"<VideoWatchProgress(user_id={self.user_id}, video_slug={self.video_slug}, progress={self.progress_percentage}%)>"
