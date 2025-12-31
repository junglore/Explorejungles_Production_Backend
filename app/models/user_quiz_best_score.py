"""
User Quiz Best Score Model
Tracks personal best scores for each user per quiz
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base


class UserQuizBestScore(Base):
    """Track personal best scores for each user per quiz"""
    __tablename__ = "user_quiz_best_scores"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    
    # Best score metrics
    best_score = Column(Integer, nullable=False)
    best_percentage = Column(Integer, nullable=False)
    best_time = Column(Integer, nullable=True)  # Time in seconds
    
    # Achievement details
    credits_earned = Column(Integer, default=0)
    points_earned = Column(Integer, default=0)
    reward_tier = Column(String(50), nullable=True)
    
    # Timestamps
    achieved_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="quiz_best_scores")
    quiz = relationship("Quiz", back_populates="user_best_scores")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'quiz_id', name='unique_user_quiz_best'),
        Index('idx_user_quiz_best_user_id', 'user_id'),
        Index('idx_user_quiz_best_quiz_id', 'quiz_id'),
        Index('idx_user_quiz_best_percentage', 'best_percentage'),
        Index('idx_user_quiz_best_achieved_at', 'achieved_at'),
    )
    
    def __repr__(self):
        return f"<UserQuizBestScore(user_id={self.user_id}, quiz_id={self.quiz_id}, best_percentage={self.best_percentage})>"
    
    @property
    def is_perfect_score(self) -> bool:
        """Check if this is a perfect score"""
        return self.best_percentage == 100
    
    @classmethod
    async def get_user_best_score(cls, db, user_id: uuid.UUID, quiz_id: uuid.UUID):
        """Get user's best score for a specific quiz"""
        from sqlalchemy import select
        result = await db.execute(
            select(cls).where(
                cls.user_id == user_id,
                cls.quiz_id == quiz_id
            )
        )
        return result.scalar_one_or_none()
    
    @classmethod
    async def update_or_create_best_score(cls, db, user_id: uuid.UUID, quiz_id: uuid.UUID, 
                                         score: int, percentage: int, time_taken: int = None,
                                         credits_earned: int = 0, points_earned: int = 0, 
                                         reward_tier: str = None):
        """Update existing best score or create new one if better"""
        existing = await cls.get_user_best_score(db, user_id, quiz_id)
        
        # Check if this is a new best score
        is_new_best = False
        if not existing or percentage > existing.best_percentage or \
           (percentage == existing.best_percentage and time_taken and 
            (not existing.best_time or time_taken < existing.best_time)):
            is_new_best = True
            
            if existing:
                # Update existing record
                existing.best_score = score
                existing.best_percentage = percentage
                existing.best_time = time_taken
                existing.credits_earned = credits_earned
                existing.points_earned = points_earned
                existing.reward_tier = reward_tier
                existing.achieved_at = datetime.utcnow()
                existing.updated_at = datetime.utcnow()
                best_score_record = existing
            else:
                # Create new record
                best_score_record = cls(
                    user_id=user_id,
                    quiz_id=quiz_id,
                    best_score=score,
                    best_percentage=percentage,
                    best_time=time_taken,
                    credits_earned=credits_earned,
                    points_earned=points_earned,
                    reward_tier=reward_tier
                )
                db.add(best_score_record)
        else:
            best_score_record = existing
            
        await db.flush()
        return best_score_record, is_new_best