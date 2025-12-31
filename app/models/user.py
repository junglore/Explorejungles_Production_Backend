"""
User model for authentication and profile management
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Enum, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from uuid import uuid4
import enum

from app.db.database import Base


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class User(Base):
    __tablename__ = "users"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Authentication fields
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile fields
    full_name = Column(String(100), nullable=True)
    gender = Column(Enum(GenderEnum), nullable=True)
    country = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)
    
    # Community/Discussion fields
    organization = Column(String(200), nullable=True)          # Organization name for community display
    professional_title = Column(String(200), nullable=True)    # Professional title (e.g., "Wildlife Ecologist")
    discussion_count = Column(Integer, default=0, nullable=False)  # Total discussions created
    comment_count = Column(Integer, default=0, nullable=False)     # Total comments made
    reputation_score = Column(Integer, default=0, nullable=False)  # Based on likes, contributions
    
    # OAuth fields
    google_id = Column(String(255), nullable=True, unique=True)
    facebook_id = Column(String(255), nullable=True, unique=True)
    linkedin_id = Column(String(255), nullable=True, unique=True)
    
    # Email verification
    is_email_verified = Column(Boolean, default=False, nullable=False)
    email_verification_token = Column(String(100), nullable=True)
    email_verification_expires = Column(DateTime(timezone=True), nullable=True)
    
    # Password reset
    password_reset_token = Column(String(100), nullable=True)
    password_reset_expires = Column(DateTime(timezone=True), nullable=True)
    
    # System fields
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    
    # Currency System - Knowledge Engine Rewards
    points_balance = Column(Integer, default=0, nullable=False)
    credits_balance = Column(Integer, default=0, nullable=False)
    total_points_earned = Column(Integer, default=0, nullable=False)
    total_credits_earned = Column(Integer, default=0, nullable=False)
    
    # Preferences
    preferences = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships for leaderboard system (defined as strings to avoid circular imports)
    quiz_best_scores = relationship("UserQuizBestScore", back_populates="user", cascade="all, delete-orphan")
    weekly_leaderboard_entries = relationship("WeeklyLeaderboardCache", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, username={self.username})>"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def currency_summary(self):
        """Get user's currency summary for frontend display"""
        return {
            "points_balance": self.points_balance,
            "credits_balance": self.credits_balance,
            "total_points_earned": self.total_points_earned,
            "total_credits_earned": self.total_credits_earned
        }
        
    def can_afford(self, credits_cost: int) -> bool:
        """Check if user can afford a purchase"""
        return self.credits_balance >= credits_cost
