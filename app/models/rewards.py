"""
Rewards system models for the dual-currency Knowledge Engine
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Date, JSON, Float, Enum, Index, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum
from datetime import datetime, date

from app.db.database import Base


# Enums for rewards system
class TransactionTypeEnum(str, enum.Enum):
    POINTS_EARNED = "points_earned"
    CREDITS_EARNED = "credits_earned"
    CREDITS_SPENT = "credits_spent"
    POINTS_PENALTY = "points_penalty"
    CREDITS_PENALTY = "credits_penalty"
    ADMIN_ADJUSTMENT = "admin_adjustment"


class CurrencyTypeEnum(str, enum.Enum):
    POINTS = "points"
    CREDITS = "credits"


class ActivityTypeEnum(str, enum.Enum):
    QUIZ_COMPLETION = "quiz_completion"
    MYTHS_FACTS_GAME = "myths_facts_game"
    DAILY_LOGIN = "daily_login"
    STREAK_BONUS = "streak_bonus"
    ACHIEVEMENT_UNLOCK = "achievement_unlock"
    ADMIN_GRANT = "admin_grant"
    PURCHASE = "purchase"
    REFUND = "refund"


class RewardTierEnum(str, enum.Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class AchievementTypeEnum(str, enum.Enum):
    QUIZ_MASTER = "quiz_master"          # Complete X quizzes
    MYTH_BUSTER = "myth_buster"          # Complete X myths vs facts games
    SPEED_DEMON = "speed_demon"          # Complete quiz/game within time limit
    PERFECT_SCORE = "perfect_score"      # Get 100% on quiz/game
    DAILY_WARRIOR = "daily_warrior"      # Login daily for X days
    WEEK_STREAK = "week_streak"          # 7-day streak
    MONTH_STREAK = "month_streak"        # 30-day streak
    QUIZ_CHAMPION = "quiz_champion"      # Top leaderboard position


class LeaderboardTypeEnum(str, enum.Enum):
    GLOBAL_POINTS = "global_points"
    GLOBAL_QUIZ = "global_quiz"
    GLOBAL_MYTHS = "global_myths"
    WEEKLY_POINTS = "weekly_points"
    MONTHLY_POINTS = "monthly_points"
    CATEGORY_SPECIFIC = "category_specific"


# Main models
class UserCurrencyTransaction(Base):
    """Track all currency transactions for complete audit trail"""
    __tablename__ = "user_currency_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    transaction_type = Column(Enum(TransactionTypeEnum), nullable=False)
    currency_type = Column(Enum(CurrencyTypeEnum), nullable=False)
    amount = Column(Integer, nullable=False)  # Positive for credits, negative for debits
    balance_after = Column(Integer, nullable=False)  # Balance after this transaction
    
    # Activity context
    activity_type = Column(Enum(ActivityTypeEnum), nullable=False)
    activity_reference_id = Column(UUID(as_uuid=True), nullable=True)  # Reference to quiz result, etc.
    transaction_metadata = Column(JSON, default=dict)  # Additional context (score, time, etc.)
    
    # Processing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    is_processed = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", backref="currency_transactions")

    # Indexes for performance
    __table_args__ = (
        Index('idx_user_currency_transactions_user_id', 'user_id'),
        Index('idx_user_currency_transactions_activity', 'activity_type', 'activity_reference_id'),
        Index('idx_user_currency_transactions_created', 'created_at'),
    )

    def __repr__(self):
        return f"<Transaction(user={self.user_id}, type={self.transaction_type}, amount={self.amount})>"


class RewardsConfiguration(Base):
    """Configure rewards for different activities and performance tiers"""
    __tablename__ = "rewards_configuration"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    activity_type = Column(Enum(ActivityTypeEnum), nullable=False)
    reward_tier = Column(Enum(RewardTierEnum), nullable=False)
    
    # Reward amounts
    points_reward = Column(Integer, default=0, nullable=False)
    credits_reward = Column(Integer, default=0, nullable=False)
    
    # Qualification criteria
    minimum_score_percentage = Column(Integer, nullable=True)  # 0-100 for quiz rewards
    time_bonus_threshold = Column(Integer, nullable=True)  # Seconds for time bonus
    daily_cap = Column(Integer, nullable=True)  # Maximum rewards per day
    
    # System
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Constraints
    __table_args__ = (
        UniqueConstraint('activity_type', 'reward_tier', name='uq_rewards_config_activity_tier'),
        Index('idx_rewards_config_activity', 'activity_type', 'is_active'),
    )

    def __repr__(self):
        return f"<RewardsConfig(activity={self.activity_type}, tier={self.reward_tier}, points={self.points_reward})>"


class UserDailyActivity(Base):
    """Track daily user activity for caps and streak calculations"""
    __tablename__ = "user_daily_activity"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    activity_date = Column(Date, nullable=False)
    
    # Activity counters
    quiz_attempts = Column(Integer, default=0, nullable=False)
    quiz_completions = Column(Integer, default=0, nullable=False)
    myths_facts_games = Column(Integer, default=0, nullable=False)
    
    # Currency earned today
    points_earned_today = Column(Integer, default=0, nullable=False)
    credits_earned_today = Column(Integer, default=0, nullable=False)
    
    # Streak tracking
    login_streak = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    last_activity_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="daily_activities")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'activity_date', name='uq_user_daily_activity'),
        Index('idx_user_daily_activity_user_date', 'user_id', 'activity_date'),
        Index('idx_user_daily_activity_date', 'activity_date'),
    )

    def __repr__(self):
        return f"<DailyActivity(user={self.user_id}, date={self.activity_date}, streak={self.login_streak})>"


class UserAchievement(Base):
    """Track user achievements and associated rewards"""
    __tablename__ = "user_achievements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    achievement_type = Column(Enum(AchievementTypeEnum), nullable=False)
    achievement_level = Column(Integer, default=1, nullable=False)  # For progressive achievements
    
    # Rewards granted
    points_rewarded = Column(Integer, default=0, nullable=False)
    credits_rewarded = Column(Integer, default=0, nullable=False)
    
    # Achievement data
    achievement_metadata = Column(JSON, default=dict)  # Achievement-specific context
    unlocked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="achievements")

    # Indexes
    __table_args__ = (
        Index('idx_user_achievements_user_id', 'user_id'),
        Index('idx_user_achievements_type', 'achievement_type'),
    )

    def __repr__(self):
        return f"<Achievement(user={self.user_id}, type={self.achievement_type}, level={self.achievement_level})>"


class LeaderboardEntry(Base):
    """Enhanced leaderboard system for multiple ranking types"""
    __tablename__ = "leaderboard_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    leaderboard_type = Column(Enum(LeaderboardTypeEnum), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    
    # Ranking data
    score = Column(Integer, nullable=False)
    rank_position = Column(Integer, nullable=False)
    additional_metrics = Column(JSON, default=dict)  # accuracy, speed, streaks, etc.
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="leaderboard_entries")
    category = relationship("Category", backref="leaderboard_entries")

    # Indexes for performance
    __table_args__ = (
        Index('idx_leaderboard_entries_type_period', 'leaderboard_type', 'period_start', 'period_end'),
        Index('idx_leaderboard_entries_user_type', 'user_id', 'leaderboard_type'),
        Index('idx_leaderboard_entries_category', 'category_id'),
        Index('idx_leaderboard_entries_rank', 'leaderboard_type', 'rank_position'),
    )

    def __repr__(self):
        return f"<LeaderboardEntry(user={self.user_id}, type={self.leaderboard_type}, rank={self.rank_position})>"


class AntiGamingTracking(Base):
    """Track patterns to prevent gaming the rewards system"""
    __tablename__ = "anti_gaming_tracking"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    activity_type = Column(Enum(ActivityTypeEnum), nullable=False)
    activity_reference_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Performance metrics
    completion_time_seconds = Column(Integer, nullable=True)
    score_percentage = Column(Integer, nullable=True)
    
    # Risk assessment
    suspicious_patterns = Column(JSON, default=dict)  # Fast completion, perfect scores, repeated patterns
    risk_score = Column(Float, default=0.0, nullable=False)  # 0.0 to 1.0
    
    # Review status
    is_flagged = Column(Boolean, default=False, nullable=False)
    admin_reviewed = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", backref="anti_gaming_records")

    # Indexes
    __table_args__ = (
        Index('idx_anti_gaming_user_activity', 'user_id', 'activity_type'),
        Index('idx_anti_gaming_flagged', 'is_flagged', 'admin_reviewed'),
        Index('idx_anti_gaming_risk_score', 'risk_score'),
    )

    def __repr__(self):
        return f"<AntiGaming(user={self.user_id}, activity={self.activity_type}, risk={self.risk_score})>"