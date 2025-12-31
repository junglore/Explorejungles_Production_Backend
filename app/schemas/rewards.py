"""
Pydantic schemas for rewards system API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class CurrencyBalanceResponse(BaseModel):
    """Response schema for user currency balance"""
    points_balance: int = Field(..., description="Current points balance")
    credits_balance: int = Field(..., description="Current credits balance")
    total_points_earned: int = Field(..., description="Total points earned all time")
    total_credits_earned: int = Field(..., description="Total credits earned all time")

    class Config:
        from_attributes = True


class TransactionItem(BaseModel):
    """Individual transaction item"""
    id: str
    transaction_type: str
    currency_type: str
    amount: int
    balance_after: int
    activity_type: str
    activity_reference_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TransactionHistoryResponse(BaseModel):
    """Response schema for transaction history"""
    transactions: List[TransactionItem]
    total_count: int
    has_more: bool

    class Config:
        from_attributes = True


class RewardTierInfo(BaseModel):
    """Information about a reward tier"""
    tier: str
    points_reward: int
    credits_reward: int
    minimum_score_percentage: Optional[int] = None
    time_bonus_threshold: Optional[int] = None


class ActivityRewardsInfo(BaseModel):
    """Information about rewards for an activity"""
    tiers: List[RewardTierInfo]
    daily_cap: Optional[int] = None


class DailyProgress(BaseModel):
    """Daily progress information"""
    points_earned_today: int
    credits_earned_today: int
    quiz_completions: int
    myths_facts_games: int
    login_streak: int


class DailyLimits(BaseModel):
    """Daily limits information"""
    max_points_remaining: int
    max_credits_remaining: int
    quiz_attempts_remaining: int
    myths_games_remaining: int


class RewardsConfigResponse(BaseModel):
    """Response schema for rewards configuration"""
    rewards_structure: Dict[str, ActivityRewardsInfo]
    daily_progress: DailyProgress

    class Config:
        from_attributes = True


class DailySummaryResponse(BaseModel):
    """Response schema for daily summary"""
    points_earned_today: int
    credits_earned_today: int
    quiz_attempts: int
    quiz_completions: int
    myths_facts_games: int
    login_streak: int
    daily_limits: DailyLimits

    class Config:
        from_attributes = True


class LeaderboardEntry(BaseModel):
    """Individual leaderboard entry"""
    rank: int
    user_id: str
    username: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    # Dynamic fields based on leaderboard type
    total_points_earned: Optional[int] = None
    current_balance: Optional[int] = None
    weekly_points: Optional[int] = None
    monthly_points: Optional[int] = None
    total_quizzes: Optional[int] = None
    average_percentage: Optional[float] = None
    total_points_from_quizzes: Optional[int] = None
    best_score: Optional[int] = None
    category_quizzes: Optional[int] = None
    category_points: Optional[int] = None

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """Response schema for leaderboards"""
    leaderboard_type: str
    entries: List[LeaderboardEntry]
    user_rank: Optional[int] = None
    total_entries: int
    last_updated: str
    # Optional fields for specific leaderboard types
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    week_start: Optional[str] = None
    week_end: Optional[str] = None
    month_start: Optional[str] = None
    month_end: Optional[str] = None

    class Config:
        from_attributes = True


class RewardProcessingRequest(BaseModel):
    """Request schema for processing rewards"""
    score_percentage: int = Field(..., ge=0, le=100, description="Performance percentage")
    time_taken: Optional[int] = Field(None, ge=0, description="Time taken in seconds")


class QuizRewardRequest(RewardProcessingRequest):
    """Request schema for quiz reward processing"""
    quiz_result_id: UUID
    quiz_id: UUID


class MythsFactsRewardRequest(RewardProcessingRequest):
    """Request schema for myths vs facts reward processing"""
    game_session_id: UUID


class RewardProcessingResponse(BaseModel):
    """Response schema for reward processing"""
    success: bool
    message: str
    points_earned: int
    credits_earned: int
    reward_tier: str
    time_bonus_applied: bool = False
    perfect_score_bonus: Optional[bool] = False
    perfect_accuracy: Optional[bool] = False
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class UserLeaderboardPositions(BaseModel):
    """User's positions across all leaderboards"""
    global_points: Optional[int] = None
    weekly_points: Optional[int] = None
    monthly_points: Optional[int] = None
    quiz_performance: Optional[int] = None

    class Config:
        from_attributes = True


class UserPositionsResponse(BaseModel):
    """Response schema for user's leaderboard positions"""
    user_id: str
    positions: UserLeaderboardPositions
    last_updated: str

    class Config:
        from_attributes = True


# Achievement schemas
class AchievementInfo(BaseModel):
    """Achievement information"""
    type: str
    name: str
    description: str
    level: int
    points_rewarded: int
    credits_rewarded: int
    unlocked_at: datetime
    metadata: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class AchievementsResponse(BaseModel):
    """Response schema for user achievements"""
    achievements: List[AchievementInfo]
    total_achievements: int
    total_points_from_achievements: int
    total_credits_from_achievements: int

    class Config:
        from_attributes = True


# Admin schemas
class AdminRewardsConfigItem(BaseModel):
    """Admin rewards configuration item"""
    id: str
    activity_type: str
    reward_tier: str
    points_reward: int
    credits_reward: int
    minimum_score_percentage: Optional[int] = None
    time_bonus_threshold: Optional[int] = None
    daily_cap: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminRewardsConfigResponse(BaseModel):
    """Admin response for rewards configuration"""
    configurations: List[AdminRewardsConfigItem]
    total_count: int

    class Config:
        from_attributes = True


class UpdateRewardsConfigRequest(BaseModel):
    """Request to update rewards configuration"""
    points_reward: Optional[int] = Field(None, ge=0)
    credits_reward: Optional[int] = Field(None, ge=0)
    minimum_score_percentage: Optional[int] = Field(None, ge=0, le=100)
    time_bonus_threshold: Optional[int] = Field(None, ge=0)
    daily_cap: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None


class CreateRewardsConfigRequest(BaseModel):
    """Request to create rewards configuration"""
    activity_type: str
    reward_tier: str
    points_reward: int = Field(..., ge=0)
    credits_reward: int = Field(..., ge=0)
    minimum_score_percentage: Optional[int] = Field(None, ge=0, le=100)
    time_bonus_threshold: Optional[int] = Field(None, ge=0)
    daily_cap: Optional[int] = Field(None, ge=0)
    is_active: bool = True


class AdminCurrencyAdjustmentRequest(BaseModel):
    """Request to adjust user currency (admin only)"""
    user_id: UUID
    currency_type: str  # "points" or "credits"
    amount: int
    reason: str = Field(..., max_length=500)
    adjustment_type: str = "admin_adjustment"  # "admin_adjustment", "penalty", "bonus"


class AdminCurrencyAdjustmentResponse(BaseModel):
    """Response for currency adjustment"""
    success: bool
    message: str
    transaction_id: str
    user_id: str
    currency_type: str
    amount: int
    new_balance: int
    reason: str

    class Config:
        from_attributes = True