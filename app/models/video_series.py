"""
Video Series models for managing episodic video content
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class VideoSeries(Base):
    """Video series containing multiple related videos"""
    __tablename__ = "video_series"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Series information
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500), nullable=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    
    # Metadata
    thumbnail_url = Column(String(500), nullable=True)
    total_videos = Column(Integer, default=0, nullable=False)
    total_views = Column(Integer, default=0, nullable=False)
    
    # Status
    is_published = Column(Integer, default=1, nullable=False)  # 0 = draft, 1 = published
    
    # Featured status (only one series can be featured at a time)
    is_featured = Column(Integer, default=0, nullable=False)  # 0 = not featured, 1 = featured
    featured_at = Column(DateTime(timezone=True), nullable=True)
    
    # Created by
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    videos = relationship("SeriesVideo", back_populates="series", cascade="all, delete-orphan", order_by="SeriesVideo.position")
    creator = relationship("User", backref="video_series")
    
    # Indexes
    __table_args__ = (
        Index('ix_video_series_slug', 'slug'),
        Index('ix_video_series_published', 'is_published', 'created_at'),
        Index('ix_video_series_featured', 'is_featured', 'featured_at'),
    )

    def __repr__(self):
        return f"<VideoSeries(id={self.id}, title={self.title}, videos={self.total_videos})>"


class SeriesVideo(Base):
    """Individual video within a series"""
    __tablename__ = "series_videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Series relationship
    series_id = Column(UUID(as_uuid=True), ForeignKey("video_series.id", ondelete="CASCADE"), nullable=False)
    
    # Video information
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500), nullable=True)
    slug = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Video file
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    
    # Position in series
    position = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    # Optional scheduled publish date for the episode
    publish_date = Column(DateTime(timezone=True), nullable=True)
    
    # Tags and hashtags (stored as JSON arrays)
    tags = Column(JSON, default=list, nullable=False)
    hashtags = Column(String(500), nullable=True)  # Space-separated hashtags
    
    # Stats
    views = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    series = relationship("VideoSeries", back_populates="videos")
    
    # Indexes
    __table_args__ = (
        Index('ix_series_videos_series_position', 'series_id', 'position'),
        Index('ix_series_videos_slug', 'slug'),
        Index('ix_series_videos_publish_date', 'publish_date'),
    )

    def __repr__(self):
        return f"<SeriesVideo(id={self.id}, title={self.title}, position={self.position})>"