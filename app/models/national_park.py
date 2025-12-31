"""
National Park Model
Stores information about Indian National Parks for community discussions
"""

from sqlalchemy import Column, String, Boolean, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
import uuid

from app.db.database import Base


class NationalPark(Base):
    """National Park model for managing park information"""
    
    __tablename__ = "national_parks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    state = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    
    # About section fields
    biodiversity = Column(Text, nullable=True)
    conservation = Column(Text, nullable=True)
    
    # Media fields (stored as JSON arrays of media objects)
    # Each item: {"url": str, "approved": bool, "uploaded_at": str, "uploaded_by": str}
    media_urls = Column(JSONB, default=list, nullable=False)  # Photo objects with approval
    video_urls = Column(JSONB, default=list, nullable=False)  # Video objects with approval
    
    # Banner media (single image or video for banner/hero section)
    banner_media_url = Column(String(500), nullable=True)  # URL to banner image or video
    banner_media_type = Column(String(20), nullable=True)  # 'image' or 'video'
    
    # Expedition packages (array of slugs for junglore.com/explore/{slug})
    expedition_slugs = Column(JSONB, default=list, nullable=False)  # List of expedition package slugs

    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<NationalPark {self.name}>"
