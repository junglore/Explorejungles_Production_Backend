"""
Pydantic schemas for leaderboard-related data structures
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class LeaderboardParticipantResponse(BaseModel):
    """Schema for individual leaderboard participant"""
    user_id: UUID
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    rank: int
    score: int
    quizzes_completed: int
    average_score: float
    is_current_user: bool = False

    class Config:
        from_attributes = True

class LeaderboardRankingResponse(BaseModel):
    """Schema for leaderboard rankings response"""
    type: str  # "weekly", "monthly", "alltime"
    period_start: Optional[datetime] = None
    participants: List[LeaderboardParticipantResponse]
    total_participants: int
    current_user_rank: Optional[int] = None

    class Config:
        from_attributes = True

class LeaderboardStatsResponse(BaseModel):
    """Schema for user leaderboard statistics"""
    user_id: UUID
    weekly_rank: Optional[int] = None
    monthly_rank: Optional[int] = None
    alltime_rank: Optional[int] = None
    total_quizzes_completed: int
    total_credits_earned: int
    average_score: float
    best_score: float

    class Config:
        from_attributes = True

class GeneralLeaderboardStatsResponse(BaseModel):
    """Schema for general leaderboard statistics"""
    total_participants: int
    total_quizzes_completed: int
    last_updated: datetime

    class Config:
        from_attributes = True

class UserRankingResponse(BaseModel):
    """Schema for specific user ranking information"""
    user_id: UUID
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    period: str  # "weekly", "monthly", "alltime"
    rank: Optional[int] = None
    total_score: int

    class Config:
        from_attributes = True

class WeeklyLeaderboardEntry(BaseModel):
    """Schema for weekly leaderboard entry"""
    user_id: UUID
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    total_credits: int
    quizzes_completed: int
    average_score: float
    rank: int
    week_start: datetime

    class Config:
        from_attributes = True

class MonthlyLeaderboardEntry(BaseModel):
    """Schema for monthly leaderboard entry"""
    user_id: UUID
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    total_credits: int
    quizzes_completed: int
    average_score: float
    rank: int
    month_start: datetime

    class Config:
        from_attributes = True