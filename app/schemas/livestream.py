"""
Livestream Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import datetime
from app.models.livestream import StreamStatusEnum

# User summary for livestream responses
class UserSummary(BaseModel):
    id: UUID
    full_name: str
    username: str
    
    class Config:
        from_attributes = True

# Category summary for livestream responses
class CategorySummary(BaseModel):
    id: UUID
    name: str
    slug: str
    
    class Config:
        from_attributes = True

class LivestreamBase(BaseModel):
    title: str = Field(..., max_length=500, description="Stream title")
    description: Optional[str] = Field(None, description="Stream description")
    category_id: UUID = Field(..., description="Stream category")
    stream_url: Optional[str] = Field(None, max_length=500, description="Stream URL")
    thumbnail_url: Optional[str] = Field(None, max_length=500, description="Thumbnail URL")
    status: Optional[StreamStatusEnum] = Field(StreamStatusEnum.SCHEDULED, description="Stream status")
    tags: Optional[List[str]] = Field(None, description="Stream tags")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled start time")

class LivestreamCreate(LivestreamBase):
    pass

class LivestreamUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500, description="Stream title")
    description: Optional[str] = Field(None, description="Stream description")
    category_id: Optional[UUID] = Field(None, description="Stream category")
    stream_url: Optional[str] = Field(None, max_length=500, description="Stream URL")
    thumbnail_url: Optional[str] = Field(None, max_length=500, description="Thumbnail URL")
    status: Optional[StreamStatusEnum] = Field(None, description="Stream status")
    tags: Optional[List[str]] = Field(None, description="Stream tags")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled start time")
    viewer_count: Optional[int] = Field(None, description="Current viewer count")

class LivestreamResponse(LivestreamBase):
    id: UUID
    host_id: UUID
    viewer_count: Optional[int] = 0
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    created_at: datetime
    host: UserSummary
    category: CategorySummary
    
    class Config:
        from_attributes = True
