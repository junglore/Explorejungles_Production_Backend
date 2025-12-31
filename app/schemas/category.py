"""
Category Pydantic Schemas
"""

from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

class CategoryBase(BaseModel):
    name: str = Field(..., max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    image_url: Optional[str] = Field(None, max_length=500, description="Category image URL")
    is_active: bool = Field(True, description="Whether category is active")

class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    image_url: Optional[str] = Field(None, max_length=500, description="Category image URL")
    is_active: bool = Field(default=True, description="Whether category is active")
    slug: Optional[str] = Field(None, description="URL slug (auto-generated if not provided)")


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="Category name")
    description: Optional[str] = Field(None, description="Category description")
    image_url: Optional[str] = Field(None, max_length=500, description="Category image URL")
    is_active: Optional[bool] = Field(None, description="Whether category is active")
    
class CategoryResponse(CategoryBase):
    id: UUID
    slug: str
    viewer_count: Optional[int] = 0
    created_at: datetime
    
    # MVF System Fields
    custom_credits: Optional[int] = Field(None, description="Custom credits for this category in MVF")
    is_featured: bool = Field(False, description="Whether this is a featured category")
    mvf_enabled: bool = Field(True, description="Whether this category is enabled for MVF")
    
    class Config:
        from_attributes = True
