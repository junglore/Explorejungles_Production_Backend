"""
Quiz schemas for request/response models
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class QuizQuestionSchema(BaseModel):
    """Schema for a single quiz question"""
    question: str = Field(..., min_length=3, max_length=1000, description="The question text")
    options: List[str] = Field(..., min_items=2, max_items=6, description="Answer options")
    correct_answer: int = Field(..., ge=0, description="Index of correct answer (0-based)")
    explanation: Optional[str] = Field(None, max_length=500, description="Explanation of the answer")
    points: int = Field(default=1, ge=1, le=10, description="Points for correct answer")
    time_limit: Optional[int] = Field(None, ge=10, le=300, description="Time limit for this question in seconds")

    @field_validator('correct_answer')
    @classmethod
    def validate_correct_answer(cls, v, info):
        if hasattr(info, 'data') and info.data and 'options' in info.data:
            options = info.data['options']
            if v >= len(options):
                raise ValueError('correct_answer index must be within options range')
        return v


class QuizCreateSchema(BaseModel):
    """Schema for creating a quiz"""
    title: str = Field(..., min_length=5, max_length=500, description="Quiz title")
    description: Optional[str] = Field(None, max_length=2000, description="Quiz description")
    category_id: Optional[UUID] = Field(None, description="Category ID")
    questions: List[QuizQuestionSchema] = Field(..., min_items=1, max_items=50, description="Quiz questions")
    difficulty_level: int = Field(default=1, ge=1, le=3, description="1=Easy, 2=Medium, 3=Hard")
    time_limit: Optional[int] = Field(None, ge=60, le=7200, description="Total quiz time limit in seconds")
    is_active: bool = Field(default=True, description="Whether quiz is active")


class QuizUpdateSchema(BaseModel):
    """Schema for updating a quiz"""
    title: Optional[str] = Field(None, min_length=5, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    category_id: Optional[UUID] = None
    questions: Optional[List[QuizQuestionSchema]] = Field(None, min_items=1, max_items=50)
    difficulty_level: Optional[int] = Field(None, ge=1, le=3)
    time_limit: Optional[int] = Field(None, ge=60, le=7200)
    is_active: Optional[bool] = None


class QuizResponseSchema(BaseModel):
    """Schema for quiz response"""
    id: UUID
    title: str
    description: Optional[str]
    cover_image: Optional[str]
    category_id: Optional[UUID]
    questions: List[QuizQuestionSchema]
    difficulty_level: int
    time_limit: Optional[int]
    is_active: bool
    created_at: datetime
    
    # Additional computed fields
    total_questions: int
    total_points: int
    
    # Reward fields for frontend display
    credits_on_completion: Optional[int] = Field(default=10, description="Credits awarded on completion")
    base_points_reward: Optional[int] = Field(default=10, description="Base points reward")

    class Config:
        from_attributes = True

    @field_validator('total_questions', mode='before')
    @classmethod
    def calculate_total_questions(cls, v, info):
        if hasattr(info, 'data') and info.data and 'questions' in info.data:
            return len(info.data['questions'])
        return 0

    @field_validator('total_points', mode='before')
    @classmethod
    def calculate_total_points(cls, v, info):
        if hasattr(info, 'data') and info.data and 'questions' in info.data:
            return sum(q.points for q in info.data['questions'])
        return 0


class QuizListResponseSchema(BaseModel):
    """Schema for quiz list response (without questions for performance)"""
    id: UUID
    title: str
    description: Optional[str]
    cover_image: Optional[str]
    category_id: Optional[UUID]
    difficulty_level: int
    time_limit: Optional[int]
    is_active: bool
    created_at: datetime
    total_questions: int
    total_points: int
    
    # Reward fields for frontend display
    credits_on_completion: Optional[int] = Field(default=10, description="Credits awarded on completion")
    base_points_reward: Optional[int] = Field(default=10, description="Base points reward")

    class Config:
        from_attributes = True


class UserAnswerSchema(BaseModel):
    """Schema for user's answer to a question"""
    question_index: int = Field(..., ge=0, description="Index of the question (0-based)")
    selected_answer: int = Field(..., ge=0, description="Index of selected answer (0-based)")
    time_taken: Optional[int] = Field(None, ge=0, le=300, description="Time taken in seconds")


class QuizSubmissionSchema(BaseModel):
    """Schema for quiz submission"""
    answers: List[UserAnswerSchema] = Field(..., min_items=1, description="User's answers")
    total_time_taken: Optional[int] = Field(None, ge=0, description="Total time taken in seconds")

    @field_validator('answers')
    @classmethod
    def validate_unique_questions(cls, v):
        question_indices = [answer.question_index for answer in v]
        if len(question_indices) != len(set(question_indices)):
            raise ValueError('Duplicate answers for the same question are not allowed')
        return v


class QuizResultSchema(BaseModel):
    """Schema for quiz result"""
    id: UUID
    user_id: UUID
    quiz_id: UUID
    score: int
    max_score: int
    percentage: int
    answers: List[Dict[str, Any]]  # Detailed answer results
    time_taken: Optional[int]
    completed_at: datetime
    
    # Reward fields
    points_earned: Optional[int] = Field(default=0, description="Knowledge Engine Points earned")
    credits_earned: Optional[int] = Field(default=0, description="Knowledge Engine Credits earned")
    reward_tier: Optional[str] = Field(default=None, description="Reward tier achieved (Bronze/Silver/Gold/Platinum)")

    class Config:
        from_attributes = True


class QuizStatsSchema(BaseModel):
    """Schema for quiz statistics"""
    quiz_id: UUID
    total_attempts: int
    average_score: float
    average_percentage: float
    average_time: Optional[float]
    difficulty_rating: float  # Based on success rate
    popular_wrong_answers: List[Dict[str, Any]]  # Most common wrong answers

    class Config:
        from_attributes = True


class UserQuizHistorySchema(BaseModel):
    """Schema for user's quiz history"""
    results: List[QuizResultSchema]
    total_quizzes_taken: int
    average_score: float
    best_score: int
    favorite_categories: List[str]
    total_time_spent: int  # in seconds

    class Config:
        from_attributes = True