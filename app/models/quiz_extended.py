"""
Extended Quiz models with rewards system integration
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class RewardTierEnum(str, enum.Enum):
    """Reward tiers for quiz performance"""
    BRONZE = "bronze"      # Basic completion
    SILVER = "silver"      # Good performance (60-79%)
    GOLD = "gold"          # Excellent performance (80-94%)
    PLATINUM = "platinum"  # Perfect or near-perfect (95-100%)


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    cover_image = Column(String(500), nullable=True)  # URL to cover image
    
    # Quiz structure stored as JSON
    # Format: [{"question": "...", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "...", "points": 10}]
    questions = Column(JSON, nullable=False)
    
    difficulty_level = Column(Integer, default=1)  # 1=Easy, 2=Medium, 3=Hard
    time_limit = Column(Integer, nullable=True)    # in minutes
    is_active = Column(Boolean, default=True)
    
    # Rewards Configuration (can be overridden per quiz)
    base_points_reward = Column(Integer, default=10, nullable=False)  # Base points for completion
    credits_on_completion = Column(Integer, default=10, nullable=False)  # Credits awarded on completion (business-safe)
    time_bonus_threshold = Column(Integer, nullable=True)  # Seconds for time bonus
    perfect_score_bonus = Column(Integer, default=5, nullable=False)  # Extra points for perfect score
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    category = relationship("Category", backref="quizzes")
    user_best_scores = relationship("UserQuizBestScore", back_populates="quiz", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Quiz(id={self.id}, title={self.title}, difficulty={self.difficulty_level}, base_reward={self.base_points_reward})>"

    @property
    def total_possible_points(self):
        """Calculate total possible points for this quiz"""
        if not self.questions:
            return 0
        return sum(q.get('points', 1) for q in self.questions)


class UserQuizResult(Base):
    __tablename__ = "user_quiz_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    
    score = Column(Integer, nullable=False)  # Points scored
    max_score = Column(Integer, nullable=False)  # Maximum possible points
    percentage = Column(Integer, nullable=False)  # Percentage score
    
    # User answers stored as JSON
    # Format: [{"question_id": 0, "selected_answer": 2, "is_correct": true, "time_taken": 30, "points_earned": 1}]
    answers = Column(JSON, nullable=False)
    
    time_taken = Column(Integer, nullable=True)  # Total time in seconds
    
    # Rewards System Integration
    points_earned = Column(Integer, default=0, nullable=False)  # Knowledge Engine points earned
    credits_earned = Column(Integer, default=0, nullable=False)  # Knowledge Engine credits earned
    reward_tier = Column(Enum(RewardTierEnum), nullable=True)  # Performance tier achieved
    time_bonus_applied = Column(Boolean, default=False, nullable=False)  # Whether time bonus was awarded
    
    # Timestamps
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="quiz_results")
    quiz = relationship("Quiz", backref="user_results")

    def __repr__(self):
        return f"<UserQuizResult(id={self.id}, user_id={self.user_id}, score={self.score}/{self.max_score}, points_earned={self.points_earned}, tier={self.reward_tier})>"

    @property
    def performance_summary(self):
        """Get comprehensive performance summary"""
        return {
            "score": self.score,
            "max_score": self.max_score,
            "percentage": self.percentage,
            "time_taken": self.time_taken,
            "reward_tier": self.reward_tier.value if self.reward_tier else None,
            "points_earned": self.points_earned,
            "credits_earned": self.credits_earned,
            "time_bonus_applied": self.time_bonus_applied,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

    @classmethod
    def calculate_reward_tier(cls, percentage: int) -> RewardTierEnum:
        """Calculate reward tier based on percentage score"""
        if percentage >= 95:
            return RewardTierEnum.PLATINUM
        elif percentage >= 80:
            return RewardTierEnum.GOLD
        elif percentage >= 60:
            return RewardTierEnum.SILVER
        else:
            return RewardTierEnum.BRONZE

    def is_eligible_for_time_bonus(self, time_threshold: int = None) -> bool:
        """Check if this result qualifies for time bonus"""
        if not self.time_taken or not time_threshold:
            return False
        return self.time_taken <= time_threshold and self.percentage >= 80  # Must be good performance too