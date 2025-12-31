"""
Pydantic Schemas for Myth Fact Collections

This module defines the request/response schemas for the collection-based
myth vs facts system API endpoints.

Schemas:
- Collection management (CRUD operations)
- User progress tracking
- Collection statistics and analytics

Author: Junglore Development Team
Version: 1.0.0
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, datetime
from enum import Enum


class RepeatabilityType(str, Enum):
    """Collection repeatability options"""
    DAILY = "daily"
    WEEKLY = "weekly"
    UNLIMITED = "unlimited"


class TierType(str, Enum):
    """Reward tier options"""
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"


# Collection Schemas
class CustomRewardsConfig(BaseModel):
    """Custom rewards configuration for a collection"""
    bronze: Optional[int] = Field(None, ge=0, le=1000)
    silver: Optional[int] = Field(None, ge=0, le=1000)
    gold: Optional[int] = Field(None, ge=0, le=1000)
    platinum: Optional[int] = Field(None, ge=0, le=1000)


class MythFactCollectionBase(BaseModel):
    """Base schema for myth fact collections"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: Optional[UUID] = None
    is_active: bool = True
    repeatability: RepeatabilityType = RepeatabilityType.DAILY
    
    # Custom rewards
    custom_points_enabled: bool = False
    custom_points: Optional[CustomRewardsConfig] = None
    custom_credits_enabled: bool = False
    custom_credits: Optional[CustomRewardsConfig] = None

    @validator('custom_points')
    def validate_custom_points(cls, v, values):
        if values.get('custom_points_enabled') and not v:
            raise ValueError('custom_points required when custom_points_enabled is True')
        return v
    
    @validator('custom_credits')
    def validate_custom_credits(cls, v, values):
        if values.get('custom_credits_enabled') and not v:
            raise ValueError('custom_credits required when custom_credits_enabled is True')
        return v


class MythFactCollectionCreate(MythFactCollectionBase):
    """Schema for creating a new collection"""
    myth_fact_ids: Optional[List[UUID]] = Field(default_factory=list, description="Initial cards to add to collection")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Wildlife Conservation Basics",
                "description": "Essential myths and facts about wildlife conservation",
                "category_id": "123e4567-e89b-12d3-a456-426614174000",
                "is_active": True,
                "repeatability": "daily",
                "custom_points_enabled": False,
                "custom_credits_enabled": False,
                "myth_fact_ids": []
            }
        }


class MythFactCollectionUpdate(BaseModel):
    """Schema for updating a collection"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    category_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    repeatability: Optional[RepeatabilityType] = None
    
    # Custom rewards
    custom_points_enabled: Optional[bool] = None
    custom_points: Optional[CustomRewardsConfig] = None
    custom_credits_enabled: Optional[bool] = None
    custom_credits: Optional[CustomRewardsConfig] = None


class MythFactCollectionResponse(MythFactCollectionBase):
    """Schema for collection responses"""
    id: UUID
    cards_count: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    category_name: Optional[str] = None

    class Config:
        from_attributes = True


class MythFactCollectionListResponse(BaseModel):
    """Schema for paginated collection list"""
    collections: List[MythFactCollectionResponse]
    total: int
    page: int
    limit: int
    total_pages: int


# Collection Card Assignment Schemas
class CollectionCardAssignment(BaseModel):
    """Schema for assigning cards to collections"""
    myth_fact_id: UUID
    order_index: int = Field(..., ge=0)


class CollectionCardsUpdate(BaseModel):
    """Schema for updating collection card assignments"""
    cards: List[CollectionCardAssignment] = Field(..., min_items=1)
    
    @validator('cards')
    def validate_unique_orders(cls, v):
        orders = [card.order_index for card in v]
        if len(orders) != len(set(orders)):
            raise ValueError('order_index values must be unique')
        return v
    
    @validator('cards')
    def validate_unique_cards(cls, v):
        card_ids = [card.myth_fact_id for card in v]
        if len(card_ids) != len(set(card_ids)):
            raise ValueError('myth_fact_id values must be unique')
        return v


class CollectionCardResponse(BaseModel):
    """Schema for collection card details"""
    id: UUID
    myth_fact_id: UUID
    order_index: int
    title: str
    myth_content: str
    fact_content: str
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


# User Progress Schemas
class UserCollectionProgressBase(BaseModel):
    """Base schema for user collection progress"""
    collection_id: UUID
    score_percentage: int = Field(..., ge=0, le=100)
    time_taken: Optional[int] = Field(None, ge=0, description="Time taken in seconds")
    answers_correct: int = Field(..., ge=0)
    total_questions: int = Field(..., ge=1)
    tier: Optional[TierType] = None
    bonus_applied: bool = False
    game_session_id: Optional[UUID] = None

    @validator('answers_correct')
    def validate_answers_correct(cls, v, values):
        total = values.get('total_questions', 0)
        if v > total:
            raise ValueError('answers_correct cannot exceed total_questions')
        return v


class UserCollectionProgressCreate(UserCollectionProgressBase):
    """Schema for creating user progress record"""
    completed: bool = True
    points_earned: int = Field(..., ge=0)
    credits_earned: int = Field(..., ge=0)


class UserCollectionProgressResponse(UserCollectionProgressBase):
    """Schema for user progress responses"""
    id: UUID
    user_id: UUID
    play_date: date
    completed: bool
    points_earned: int
    credits_earned: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    collection_name: Optional[str] = None

    class Config:
        from_attributes = True


class UserProgressSummary(BaseModel):
    """Schema for user progress summary"""
    user_id: UUID
    total_collections_played: int
    total_collections_completed: int
    total_points_earned: int
    total_credits_earned: int
    average_score: float
    favorite_category: Optional[str] = None
    current_streak: int
    last_play_date: Optional[date] = None


# Collection Statistics Schemas
class CollectionStats(BaseModel):
    """Schema for collection statistics"""
    id: UUID
    name: str
    description: Optional[str] = None
    is_active: bool
    repeatability: str
    category_name: Optional[str] = None
    total_cards: int
    unique_players: int
    total_plays: int
    completions: int
    avg_score: Optional[float] = None
    avg_time: Optional[float] = None
    completion_rate: Optional[float] = None

    class Config:
        from_attributes = True


# Game Play Schemas
class CollectionGameRequest(BaseModel):
    """Schema for starting a collection game"""
    collection_id: UUID


class CollectionGameResponse(BaseModel):
    """Schema for collection game data"""
    collection_id: UUID
    collection_name: str
    description: Optional[str] = None
    cards: List[CollectionCardResponse]
    total_cards: int
    repeatability: str
    custom_rewards: bool
    can_play_today: bool
    reason: Optional[str] = None  # Reason if can't play


class CollectionCompletionRequest(BaseModel):
    """Schema for submitting collection completion"""
    collection_id: UUID
    score_percentage: int = Field(..., ge=0, le=100)
    time_taken: int = Field(..., ge=1, description="Time taken in seconds")
    answers: List[Dict[str, Any]] = Field(..., description="User answers for each card")
    game_session_id: Optional[UUID] = None


class CollectionCompletionResponse(BaseModel):
    """Schema for collection completion response"""
    success: bool
    message: str
    progress_id: UUID
    points_earned: int
    credits_earned: int
    tier: str
    bonus_applied: bool
    can_play_again: bool
    next_play_time: Optional[datetime] = None
    breakdown: Dict[str, Any]


# Error and Success Schemas
class ErrorResponse(BaseModel):
    """Standard error response schema"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class SuccessResponse(BaseModel):
    """Standard success response schema"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None


# Pagination Schema
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = Field(1, ge=1, description="Page number")
    limit: int = Field(10, ge=1, le=100, description="Items per page")
    category_id: Optional[UUID] = Field(None, description="Filter by category")
    is_active: Optional[bool] = Field(None, description="Filter by active status")
    search: Optional[str] = Field(None, min_length=1, max_length=100, description="Search in name/description")