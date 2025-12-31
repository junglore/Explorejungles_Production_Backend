"""
Pydantic schemas for Myth vs Fact models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class MythFactBase(BaseModel):
    """Base schema for MythFact"""
    title: str = Field(..., min_length=1, max_length=500, description="Title of the myth vs fact entry")
    myth_content: str = Field(..., min_length=1, description="The myth statement")
    fact_content: str = Field(..., min_length=1, description="The fact explanation")
    image_url: Optional[str] = Field(None, max_length=500, description="URL to associated image")
    category_id: Optional[UUID] = Field(None, description="Category ID if associated with a category")
    custom_points: Optional[int] = Field(None, ge=0, description="Custom points awarded for this card (overrides base points)")
    is_featured: bool = Field(False, description="Whether this entry is featured")

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

    @validator('myth_content')
    def validate_myth_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Myth content cannot be empty')
        return v.strip()

    @validator('fact_content')
    def validate_fact_content(cls, v):
        if not v or not v.strip():
            raise ValueError('Fact content cannot be empty')
        return v.strip()

    @validator('image_url')
    def validate_image_url(cls, v):
        if v is not None and v.strip():
            # Basic URL validation
            if not (v.startswith('http://') or v.startswith('https://') or v.startswith('/')):
                raise ValueError('Image URL must be a valid URL or path')
            return v.strip()
        return None


class MythFactCreate(MythFactBase):
    """Schema for creating a new MythFact"""
    pass


class MythFactUpdate(BaseModel):
    """Schema for updating a MythFact"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    myth_content: Optional[str] = Field(None, min_length=1)
    fact_content: Optional[str] = Field(None, min_length=1)
    image_url: Optional[str] = Field(None, max_length=500)
    category_id: Optional[UUID] = None
    custom_points: Optional[int] = Field(None, ge=0, description="Custom points awarded for this card")
    is_featured: Optional[bool] = None

    @validator('title')
    def validate_title(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Title cannot be empty')
        return v.strip() if v else None

    @validator('myth_content')
    def validate_myth_content(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Myth content cannot be empty')
        return v.strip() if v else None

    @validator('fact_content')
    def validate_fact_content(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Fact content cannot be empty')
        return v.strip() if v else None

    @validator('image_url')
    def validate_image_url(cls, v):
        if v is not None and v.strip():
            if not (v.startswith('http://') or v.startswith('https://') or v.startswith('/')):
                raise ValueError('Image URL must be a valid URL or path')
            return v.strip()
        return None


class MythFactResponse(BaseModel):
    """Schema for MythFact response"""
    id: UUID
    title: str
    myth_statement: str
    fact_explanation: str
    category: Optional[str] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None
    is_featured: bool
    type: Optional[str] = Field("myth", description="Card type: 'myth' or 'fact' - controls which content displays to user")

    class Config:
        from_attributes = True


class MythFactListResponse(BaseModel):
    """Schema for paginated MythFact list response"""
    items: List[MythFactResponse]
    pagination: dict


class PaginationParams(BaseModel):
    """Schema for pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=50, description="Items per page")


class MythFactGameResponse(BaseModel):
    """Schema for game-specific MythFact response"""
    id: UUID
    title: str
    myth_statement: str
    fact_explanation: str
    image_url: Optional[str] = None
    is_featured: bool
    type: Optional[str] = Field("myth", description="Card type: 'myth' or 'fact' - controls which content displays to user")

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    """Schema for error responses"""
    detail: str
    error_code: Optional[str] = None
    field_errors: Optional[dict] = None


class SuccessResponse(BaseModel):
    """Schema for success responses"""
    message: str
    data: Optional[dict] = None