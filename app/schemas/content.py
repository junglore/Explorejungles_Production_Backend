"""
Content Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from app.models.content import ContentTypeEnum, ContentStatusEnum

# User summary for content responses
class UserSummary(BaseModel):
    id: UUID
    username: str
    
    class Config:
        from_attributes = True

# Category summary for content responses
class CategorySummary(BaseModel):
    id: UUID
    name: str
    slug: str
    
    class Config:
        from_attributes = True

class ContentBase(BaseModel):
    title: str = Field(..., max_length=500, description="Content title")
    content: str = Field(..., description="Main content body")
    type: ContentTypeEnum = Field(..., description="Type of content")
    category_id: Optional[UUID] = Field(None, description="Associated category")
    
    # Author display name (can be different from user account name)
    author_name: Optional[str] = Field(None, max_length=200, description="Custom author name for display")
    
    # Media fields (matching junglore.com Blog model)
    featured_image: Optional[str] = Field(None, max_length=500, description="Featured image URL")
    banner: Optional[str] = Field(None, max_length=500, description="Banner image URL")
    video: Optional[str] = Field(None, max_length=500, description="Video URL")
    
    # Featured blog system (matching junglore.com)
    featured: Optional[bool] = Field(False, description="Whether content is featured")
    feature_place: Optional[int] = Field(0, description="Featured placement position (1-3)")
    
    excerpt: Optional[str] = Field(None, description="Content excerpt")
    meta_description: Optional[str] = Field(None, max_length=255, description="SEO meta description")
    content_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    status: Optional[ContentStatusEnum] = Field(ContentStatusEnum.DRAFT, description="Content status")

class ContentCreate(ContentBase):
    pass

class ContentUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=500, description="Content title")
    content: Optional[str] = Field(None, description="Main content body")
    type: Optional[ContentTypeEnum] = Field(None, description="Type of content")
    category_id: Optional[UUID] = Field(None, description="Associated category")
    
    # Author display name (can be different from user account name)
    author_name: Optional[str] = Field(None, max_length=200, description="Custom author name for display")
    
    # Media fields (matching junglore.com Blog model)
    featured_image: Optional[str] = Field(None, max_length=500, description="Featured image URL")
    banner: Optional[str] = Field(None, max_length=500, description="Banner image URL")
    video: Optional[str] = Field(None, max_length=500, description="Video URL")
    
    # Featured blog system (matching junglore.com)
    featured: Optional[bool] = Field(None, description="Whether content is featured")
    feature_place: Optional[int] = Field(None, description="Featured placement position (1-3)")
    
    excerpt: Optional[str] = Field(None, description="Content excerpt")
    meta_description: Optional[str] = Field(None, max_length=255, description="SEO meta description")
    content_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    status: Optional[ContentStatusEnum] = Field(None, description="Content status")

class ContentListResponse(BaseModel):
    id: UUID
    title: str
    excerpt: Optional[str]
    featured_image: Optional[str]
    banner: Optional[str]
    video: Optional[str]
    featured: Optional[bool] = False
    feature_place: Optional[int] = 0
    slug: str
    type: ContentTypeEnum
    status: ContentStatusEnum
    view_count: Optional[int] = 0
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    author: UserSummary
    category: Optional[CategorySummary]
    
    # Author display name (can be different from user account name)
    author_name: Optional[str] = None
    
    class Config:
        from_attributes = True

class ContentResponse(ContentListResponse):
    content: str
    meta_description: Optional[str]
    content_metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True

# Standardized API Response Schemas (matching junglore.com pattern)
class StandardContentItem(BaseModel):
    """Standardized content item format for all content types"""
    id: str
    title: str
    slug: Optional[str]
    category_id: Optional[str]
    banner: Optional[str]
    image: Optional[str]  # Maps to featured_image
    video: Optional[str]
    description: Optional[str]  # Maps to excerpt
    content: Optional[str] = None  # Only included in single item responses
    featured: bool = False
    feature_place: int = 0
    status: bool = True  # Maps to published status
    type: Optional[str] = None  # Content type for mixed responses
    author_name: Optional[str] = None  # Author display name
    createdAt: str
    updatedAt: str

class StandardPaginationResponse(BaseModel):
    """Standardized pagination response"""
    result: List[StandardContentItem]
    totalPages: int
    currentPage: int
    limit: int

class StandardAPIResponse(BaseModel):
    """Standardized API response wrapper"""
    message: str
    data: StandardPaginationResponse | StandardContentItem | Dict[str, Any]
    status: bool = True
