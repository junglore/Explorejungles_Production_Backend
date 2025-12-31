"""
Video Channel models for organizing general knowledge videos
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class VideoChannel(Base):
    """Video channels for organizing videos by topic/category"""
    __tablename__ = "video_channels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Channel information
    name = Column(String(255), nullable=False, unique=True)
    slug = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Channel branding
    thumbnail_url = Column(String(500), nullable=True)
    banner_url = Column(String(500), nullable=True)
    
    # Stats
    total_videos = Column(Integer, default=0, nullable=False)
    total_views = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Created by
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    videos = relationship("GeneralKnowledgeVideo", back_populates="channel", cascade="all, delete-orphan")
    creator = relationship("User", backref="video_channels")
    
    # Indexes
    __table_args__ = (
        Index('ix_video_channels_slug', 'slug'),
        Index('ix_video_channels_active', 'is_active', 'created_at'),
    )

    def __repr__(self):
        return f"<VideoChannel(id={self.id}, name={self.name}, videos={self.total_videos})>"


class GeneralKnowledgeVideo(Base):
    """Individual general knowledge video"""
    __tablename__ = "general_knowledge_videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Channel relationship
    channel_id = Column(UUID(as_uuid=True), ForeignKey("video_channels.id", ondelete="CASCADE"), nullable=False)
    
    # Video information
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500), nullable=True)
    slug = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Video file
    video_url = Column(String(500), nullable=False)
    thumbnail_url = Column(String(500), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    
    # Tags and hashtags (stored as comma-separated strings)
    tags = Column(Text, nullable=True)  # "wildlife,conservation,nature"
    hashtags = Column(String(500), nullable=True)  # "#wildlife #conservation"
    
    # Stats
    views = Column(Integer, default=0, nullable=False)
    likes = Column(Integer, default=0, nullable=False)
    
    # Status
    is_published = Column(Boolean, default=True, nullable=False)
    # Optional scheduled publish date for channel videos (applies per video)
    publish_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    channel = relationship("VideoChannel", back_populates="videos")
    
    # Indexes
    __table_args__ = (
        Index('ix_gk_videos_channel', 'channel_id', 'created_at'),
        Index('ix_gk_videos_slug', 'slug'),
        Index('ix_gk_videos_published', 'is_published', 'created_at'),
    )

    def __repr__(self):
        return f"<GeneralKnowledgeVideo(id={self.id}, title={self.title})>"