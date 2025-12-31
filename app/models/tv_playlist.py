"""
TV Playlist model - stores ordered list of video slugs selected for the TV carousel
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class TVPlaylist(Base):
    __tablename__ = "tv_playlist"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    position = Column(Integer, nullable=False, unique=True, index=True)
    video_slug = Column(String(200), nullable=False, index=True)
    title = Column(String(300), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TVPlaylist(position={self.position}, video_slug={self.video_slug})>"