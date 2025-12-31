"""
Collection Management Schemas

Pydantic schemas for collection-based Myths vs Facts system.
Handles validation for collection creation, updates, and progress tracking.

Author: Junglore Development Team
Version: 1.0.0
"""

from datetime import date, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, validator


class CollectionBase(BaseModel):
    """Base schema for collection data"""
    name: str = Field(..., min_length=1, max_length=255, description="Collection name")
    description: Optional[str] = Field(None, description="Collection description")
    category_id: Optional[UUID] = Field(None, description="Category UUID")
    is_active: bool = Field(True, description="Whether collection is active")
    repeatability: str = Field("daily", description="Repeatability setting")
    cards_count: int = Field(0, ge=0, description="Number of cards in collection")
    
    @validator('repeatability')
    def validate_repeatability(cls, v):
        allowed = ['daily', 'weekly', 'unlimited']
        if v not in allowed:
            raise ValueError(f'Repeatability must be one of: {allowed}')
        return v


class CollectionCreate(CollectionBase):
    """Schema for creating a new collection"""
    custom_points_enabled: bool = Field(False, description="Enable custom points")
    custom_points_bronze: Optional[int] = Field(None, ge=0, description="Bronze tier points")
    custom_points_silver: Optional[int] = Field(None, ge=0, description="Silver tier points")
    custom_points_gold: Optional[int] = Field(None, ge=0, description="Gold tier points")
    custom_points_platinum: Optional[int] = Field(None, ge=0, description="Platinum tier points")
    
    custom_credits_enabled: bool = Field(False, description="Enable custom credits")
    custom_credits_bronze: Optional[int] = Field(None, ge=0, description="Bronze tier credits")
    custom_credits_silver: Optional[int] = Field(None, ge=0, description="Silver tier credits")
    custom_credits_gold: Optional[int] = Field(None, ge=0, description="Gold tier credits")
    custom_credits_platinum: Optional[int] = Field(None, ge=0, description="Platinum tier credits")


class CollectionUpdate(BaseModel):
    """Schema for updating collection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    repeatability: Optional[str] = None
    
    @validator('repeatability')
    def validate_repeatability(cls, v):
        if v is not None:
            allowed = ['daily', 'weekly', 'unlimited']
            if v not in allowed:
                raise ValueError(f'Repeatability must be one of: {allowed}')
        return v


class CollectionResponse(CollectionBase):
    """Schema for collection response"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    
    class Config:
        from_attributes = True


class CollectionMythFactCreate(BaseModel):
    """Schema for adding myth/fact to collection"""
    collection_id: UUID
    myth_fact_id: UUID
    order_index: int = Field(0, ge=0, description="Order in collection")


class CollectionMythFactResponse(BaseModel):
    """Schema for collection myth/fact relationship"""
    id: UUID
    collection_id: UUID
    myth_fact_id: UUID
    order_index: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserCollectionProgressCreate(BaseModel):
    """Schema for creating user progress record"""
    user_id: UUID
    collection_id: UUID
    play_date: Optional[date] = Field(default_factory=date.today)
    completed: bool = Field(False)
    score_percentage: int = Field(0, ge=0, le=100)
    time_taken: Optional[int] = Field(None, ge=0, description="Time in seconds")
    answers_correct: int = Field(0, ge=0)
    total_questions: int = Field(0, ge=0)
    points_earned: int = Field(0, ge=0)
    credits_earned: int = Field(0, ge=0)
    tier: Optional[str] = None
    bonus_applied: bool = Field(False)
    game_session_id: Optional[UUID] = None


class MythFactInCollection(BaseModel):
    """Schema for myth/fact card within a collection"""
    id: UUID
    title: str
    myth_content: str
    fact_content: str
    image_url: Optional[str] = None
    is_featured: bool = False
    order_index: int = 0
    
    class Config:
        from_attributes = True


class CollectionWithCards(BaseModel):
    """Schema for collection with its assigned cards"""
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool = True
    cards_count: int = 0
    repeatability: str = "daily"
    category_id: Optional[UUID] = None
    custom_points_enabled: bool = False
    custom_credits_enabled: bool = False
    custom_points_bronze: Optional[int] = None
    custom_points_silver: Optional[int] = None
    custom_points_gold: Optional[int] = None
    custom_points_platinum: Optional[int] = None
    custom_credits_bronze: Optional[int] = None
    custom_credits_silver: Optional[int] = None
    custom_credits_gold: Optional[int] = None
    custom_credits_platinum: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    cards: List[MythFactInCollection] = []
    
    class Config:
        from_attributes = True


class UserCollectionProgressResponse(BaseModel):
    """Schema for user progress response"""
    id: UUID
    user_id: UUID
    collection_id: UUID
    play_date: date
    completed: bool
    score_percentage: int
    time_taken: Optional[int]
    answers_correct: int
    total_questions: int
    points_earned: int
    credits_earned: int
    tier: Optional[str]
    bonus_applied: bool
    game_session_id: Optional[UUID]
    created_at: datetime
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CollectionStatsResponse(BaseModel):
    """Schema for collection statistics view"""
    id: UUID
    name: str
    description: Optional[str]
    is_active: bool
    repeatability: str
    category_name: Optional[str]
    total_cards: int
    unique_players: int
    total_plays: int
    completions: int
    avg_score: Optional[float]
    avg_time: Optional[float]
    
    class Config:
        from_attributes = True


class UserDailySummaryResponse(BaseModel):
    """Schema for user daily collection summary"""
    user_id: UUID
    play_date: date
    collections_attempted: int
    collections_completed: int
    total_points_earned: int
    total_credits_earned: int
    avg_score_percentage: Optional[float]
    
    class Config:
        from_attributes = True


class CollectionGameRequest(BaseModel):
    """Schema for starting a collection-based game"""
    collection_id: UUID
    user_id: UUID


class CollectionGameResponse(BaseModel):
    """Schema for collection game data"""
    collection_id: UUID
    collection_name: str
    cards: List[dict]  # Will contain the actual myth/fact data
    total_cards: int
    repeatability: str
    can_play_today: bool
    
    class Config:
        from_attributes = True


# Error response schemas
class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    details: Optional[dict] = None


class ValidationErrorResponse(BaseModel):
    """Validation error response"""
    error: str = "validation_error"
    message: str
    field_errors: List[dict]