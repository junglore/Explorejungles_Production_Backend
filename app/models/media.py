"""
Media model for managing files, images, videos, podcasts
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Enum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class MediaTypeEnum(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    PODCAST = "podcast"
    DOCUMENT = "document"


class Media(Base):
    __tablename__ = "media"

    # Primary key and foreign keys with proper cascade behavior
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content.id", ondelete="CASCADE"), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    # Core media fields with proper constraints
    media_type = Column(String(50), nullable=False, index=True)
    file_url = Column(String(500), nullable=False, unique=True)
    thumbnail_url = Column(String(500), nullable=True)
    
    # File identification
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    
    # Metadata fields
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    
    # Photographer and location information
    photographer = Column(String(255), nullable=True, index=True)  # Captured by
    national_park = Column(String(255), nullable=True, index=True)  # National park name
    
    # File metadata with proper constraints
    file_size = Column(Integer, nullable=True)  # in bytes
    duration = Column(Integer, nullable=True)   # in seconds for audio/video
    width = Column(Integer, nullable=True)      # for images/videos
    height = Column(Integer, nullable=True)     # for images/videos
    
    # Additional metadata
    file_metadata = Column(JSON, default=dict, nullable=False)  # EXIF data, codec info, etc.
    
    # Featured status
    is_featured = Column(Integer, default=0, nullable=False)  # 0 = not featured, 1-6 = featured position
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships with proper cascade behavior
    content = relationship("Content", backref="media")
    uploader = relationship("User", backref="uploaded_media")

    # Indexes for performance optimization
    __table_args__ = (
        # Index for content media queries
        Index('ix_media_content_type', 'content_id', 'media_type'),
        # Index for user uploaded media
        Index('ix_media_uploader_created', 'uploaded_by', 'created_at'),
        # Index for media type and creation date
        Index('ix_media_type_created', 'media_type', 'created_at'),
        # Index for photographer and national park searches
        Index('ix_media_photographer_park', 'photographer', 'national_park'),
        # Index for featured media
        Index('ix_media_featured', 'is_featured'),
    )

    def __repr__(self):
        return f"<Media(id={self.id}, type={self.media_type}, filename={self.filename})>"
