"""
National Park Schemas
Pydantic models for API request/response validation
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from uuid import UUID
from typing import Optional, List
import re


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


class NationalParkBase(BaseModel):
    """Base national park schema"""
    name: str = Field(..., min_length=3, max_length=255, description="Name of the national park")
    state: Optional[str] = Field(None, max_length=100, description="State where park is located")
    description: Optional[str] = Field(None, description="Description of the park")
    biodiversity: Optional[str] = Field(None, description="Biodiversity information")
    conservation: Optional[str] = Field(None, description="Conservation efforts information")
    media_urls: List[str] = Field(default_factory=list, description="List of photo URLs")
    video_urls: List[str] = Field(default_factory=list, description="List of video URLs")
    banner_media_url: Optional[str] = Field(None, description="Banner image or video URL")
    banner_media_type: Optional[str] = Field(None, description="Type of banner media: 'image' or 'video'")
    expedition_slugs: List[str] = Field(default_factory=list, description="List of expedition package slugs from junglore.com/explore/")
    is_active: bool = Field(default=True, description="Whether the park is active")
    
    @validator('state', 'description', 'biodiversity', 'conservation', pre=True)
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class NationalParkCreate(BaseModel):
    """Schema for creating a national park - only name required"""
    name: str = Field(..., min_length=3, max_length=255, description="Name of the national park")
    state: Optional[str] = Field(None, max_length=100, description="State where park is located")
    description: Optional[str] = Field(None, description="Description of the park")
    biodiversity: Optional[str] = Field(None, description="Biodiversity information")
    conservation: Optional[str] = Field(None, description="Conservation efforts information")
    media_urls: List[str] = Field(default_factory=list, description="List of photo URLs")
    video_urls: List[str] = Field(default_factory=list, description="List of video URLs")
    banner_media_url: Optional[str] = Field(None, description="Banner image or video URL")
    banner_media_type: Optional[str] = Field(None, description="Type of banner media: 'image' or 'video'")
    expedition_slugs: List[str] = Field(default_factory=list, description="List of expedition package slugs from junglore.com/explore/")
    is_active: bool = Field(default=True, description="Whether the park is active")
    
    @validator('state', 'biodiversity', 'conservation', pre=True)
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class NationalParkUpdate(BaseModel):
    """Schema for updating a national park"""
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    state: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    biodiversity: Optional[str] = None
    conservation: Optional[str] = None
    media_urls: Optional[List[str]] = None
    video_urls: Optional[List[str]] = None
    banner_media_url: Optional[str] = None
    banner_media_type: Optional[str] = None
    expedition_slugs: Optional[List[str]] = None
    is_active: Optional[bool] = None
    
    @validator('state', 'description', 'biodiversity', 'conservation', pre=True)
    def empty_str_to_none(cls, v):
        if v == '':
            return None
        return v


class NationalParkResponse(BaseModel):
    """Schema for national park response"""
    id: UUID
    name: str
    state: Optional[str] = None
    slug: str
    description: Optional[str] = None
    biodiversity: Optional[str] = None
    conservation: Optional[str] = None
    media_urls: List[str] = []
    video_urls: List[str] = []
    banner_media_url: Optional[str] = None
    banner_media_type: Optional[str] = None
    expedition_slugs: List[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NationalParkListItem(BaseModel):
    """Simplified schema for list views"""
    id: UUID
    name: str
    state: Optional[str] = None
    slug: str
    description: Optional[str] = None
    biodiversity: Optional[str] = None
    conservation: Optional[str] = None
    media_urls: List[str] = []
    video_urls: List[str] = []
    banner_media_url: Optional[str] = None
    banner_media_type: Optional[str] = None
    expedition_slugs: List[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True