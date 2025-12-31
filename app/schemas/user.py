"""
User schemas for request/response models
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime

from app.models.user import GenderEnum


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str


class UserCreate(UserBase):
    """Schema for creating a user"""
    password: str


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    username: Optional[str] = None


class UserResponse(UserBase):
    """Schema for user response"""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    """Extended user profile with additional stats"""
    followers_count: int = 0
    following_count: int = 0
    content_count: int = 0
    quiz_results_count: int = 0
    # Currency System - Knowledge Engine Rewards
    points_balance: int = 0
    credits_balance: int = 0
    total_points_earned: int = 0
    total_credits_earned: int = 0
