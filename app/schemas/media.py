"""
Media schemas for request/response models
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from enum import Enum


class MediaTypeEnum(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    PODCAST = "PODCAST"
    DOCUMENT = "DOCUMENT"


class MediaBase(BaseModel):
    """Base schema for media"""
    media_type: MediaTypeEnum = Field(..., description="Type of media file")
    file_url: str = Field(..., max_length=500, description="URL of the media file")
    thumbnail_url: Optional[str] = Field(None, max_length=500, description="URL of thumbnail")
    title: Optional[str] = Field(None, max_length=500, description="Media title")
    description: Optional[str] = Field(None, description="Media description")
    content_id: Optional[UUID] = Field(None, description="Associated content ID")
    
    # Photographer and location information
    photographer: Optional[str] = Field(None, max_length=255, description="Photographer/Captured by")
    national_park: Optional[str] = Field(None, max_length=255, description="National park name")
    
    # File metadata
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    duration: Optional[int] = Field(None, ge=0, description="Duration in seconds (for audio/video)")
    width: Optional[int] = Field(None, ge=1, description="Width in pixels (for images/videos)")
    height: Optional[int] = Field(None, ge=1, description="Height in pixels (for images/videos)")
    file_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional file metadata")


class MediaCreate(MediaBase):
    """Schema for creating media"""
    pass


class MediaUpdate(BaseModel):
    """Schema for updating media"""
    media_type: Optional[MediaTypeEnum] = Field(None, description="Type of media file")
    file_url: Optional[str] = Field(None, max_length=500, description="URL of the media file")
    thumbnail_url: Optional[str] = Field(None, max_length=500, description="URL of thumbnail")
    title: Optional[str] = Field(None, max_length=500, description="Media title")
    description: Optional[str] = Field(None, description="Media description")
    content_id: Optional[UUID] = Field(None, description="Associated content ID")
    
    # Photographer and location information
    photographer: Optional[str] = Field(None, max_length=255, description="Photographer/Captured by")
    national_park: Optional[str] = Field(None, max_length=255, description="National park name")
    
    # File metadata
    file_size: Optional[int] = Field(None, ge=0, description="File size in bytes")
    duration: Optional[int] = Field(None, ge=0, description="Duration in seconds (for audio/video)")
    width: Optional[int] = Field(None, ge=1, description="Width in pixels (for images/videos)")
    height: Optional[int] = Field(None, ge=1, description="Height in pixels (for images/videos)")
    file_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional file metadata")


class MediaResponse(BaseModel):
    """Schema for media response"""
    id: UUID
    media_type: MediaTypeEnum
    file_url: str
    thumbnail_url: Optional[str]
    title: Optional[str]
    description: Optional[str]
    content_id: Optional[UUID]
    
    # Photographer and location information
    photographer: Optional[str]
    national_park: Optional[str]
    
    # File metadata
    file_size: Optional[int]
    duration: Optional[int]
    width: Optional[int]
    height: Optional[int]
    file_metadata: Optional[Dict[str, Any]]
    
    # Timestamps
    created_at: datetime

    class Config:
        from_attributes = True


class MediaListResponse(BaseModel):
    """Schema for media list response (minimal info for performance)"""
    id: UUID
    media_type: MediaTypeEnum
    file_url: str
    thumbnail_url: Optional[str]
    title: Optional[str]
    
    # Photographer and location information
    photographer: Optional[str]
    national_park: Optional[str]
    
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class PodcastResponse(MediaResponse):
    """Extended schema for podcast responses"""
    episode_number: Optional[int] = Field(None, description="Episode number")
    season_number: Optional[int] = Field(None, description="Season number")
    show_name: Optional[str] = Field(None, description="Podcast show name")
    guest_names: Optional[List[str]] = Field(None, description="Guest names")
    transcript_url: Optional[str] = Field(None, description="Transcript URL")

    @field_validator('episode_number', 'season_number', mode='before')
    @classmethod
    def extract_from_metadata(cls, v, info):
        if v is None and hasattr(info, 'data') and info.data and 'file_metadata' in info.data:
            metadata = info.data['file_metadata']
            if metadata and info.field_name in metadata:
                return metadata.get(info.field_name)
        return v

    @field_validator('show_name', 'transcript_url', mode='before')
    @classmethod
    def extract_string_from_metadata(cls, v, info):
        if v is None and hasattr(info, 'data') and info.data and 'file_metadata' in info.data:
            metadata = info.data['file_metadata']
            if metadata and info.field_name in metadata:
                return metadata.get(info.field_name)
        return v

    @field_validator('guest_names', mode='before')
    @classmethod
    def extract_guests_from_metadata(cls, v, info):
        if v is None and hasattr(info, 'data') and info.data and 'file_metadata' in info.data:
            metadata = info.data['file_metadata']
            if metadata:
                guests = metadata.get('guest_names')
                if isinstance(guests, str):
                    return [name.strip() for name in guests.split(',')]
                return guests
        return v


class MediaCollageResponse(BaseModel):
    """Schema for media collage response"""
    images: List[MediaListResponse]
    videos: List[MediaListResponse]
    total_count: int
    page: int
    page_size: int
    has_next: bool

    class Config:
        from_attributes = True


class MediaUploadResponse(BaseModel):
    """Schema for media upload response"""
    id: UUID
    file_url: str
    thumbnail_url: Optional[str]
    media_type: MediaTypeEnum
    file_size: int
    message: str

    class Config:
        from_attributes = True


class MediaStatsResponse(BaseModel):
    """Schema for media statistics"""
    total_media: int
    images_count: int
    videos_count: int
    podcasts_count: int
    total_file_size: int  # in bytes
    most_viewed_media: List[MediaListResponse]
    recent_uploads: List[MediaListResponse]

    class Config:
        from_attributes = True