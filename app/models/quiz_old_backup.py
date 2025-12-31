"""
Quiz models for interactive wildlife quizzes
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    cover_image = Column(String(500), nullable=True)  # URL to cover image
    
    # Quiz structure stored as JSON
    # Format: [{"question": "...", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "..."}]
    questions = Column(JSON, nullable=False)
    
    difficulty_level = Column(Integer, default=1)  # 1=Easy, 2=Medium, 3=Hard
    time_limit = Column(Integer, nullable=True)    # in minutes
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    category = relationship("Category", backref="quizzes")

    def __repr__(self):
        return f"<Quiz(id={self.id}, title={self.title}, difficulty={self.difficulty_level})>"


class UserQuizResult(Base):
    __tablename__ = "user_quiz_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quiz_id = Column(UUID(as_uuid=True), ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    
    score = Column(Integer, nullable=False)  # Points scored
    max_score = Column(Integer, nullable=False)  # Maximum possible points
    percentage = Column(Integer, nullable=False)  # Percentage score
    
    # User answers stored as JSON
    # Format: [{"question_id": 0, "selected_answer": 2, "is_correct": true, "time_taken": 30}]
    answers = Column(JSON, nullable=False)
    
    time_taken = Column(Integer, nullable=True)  # Total time in seconds
    
    # Timestamps
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="quiz_results")
    quiz = relationship("Quiz", backref="user_results")

    def __repr__(self):
        return f"<UserQuizResult(id={self.id}, user_id={self.user_id}, score={self.score}/{self.max_score})>"