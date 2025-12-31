"""
Recommendation system models for personalized content
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, Enum, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class RecommendationTypeEnum(str, enum.Enum):
    CONTENT = "content"
    ANIMAL_PROFILE = "animal_profile"
    CATEGORY = "category"
    LIVESTREAM = "livestream"
    QUIZ = "quiz"
    MEDIA = "media"


class RecommendationSourceEnum(str, enum.Enum):
    COLLABORATIVE_FILTERING = "collaborative_filtering"  # Based on similar users
    CONTENT_BASED = "content_based"  # Based on user preferences
    POPULAR = "popular"  # Most popular items
    TRENDING = "trending"  # Trending items
    RECENT = "recent"  # Recently added items
    CATEGORY_BASED = "category_based"  # Based on user's favorite categories
    ADMIN_FEATURED = "admin_featured"  # Manually featured by admin


class UserRecommendation(Base):
    """Personalized recommendations for users"""
    __tablename__ = "user_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Recommendation details
    recommendation_type = Column(Enum(RecommendationTypeEnum), nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)  # ID of recommended item
    source = Column(Enum(RecommendationSourceEnum), nullable=False)
    
    # Scoring
    relevance_score = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    confidence_score = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    
    # Metadata
    recommendation_reason = Column(Text, nullable=True)  # Human-readable explanation
    recommendation_metadata = Column(JSON, default=dict)  # Additional context
    
    # Interaction tracking
    is_viewed = Column(Boolean, default=False)
    is_clicked = Column(Boolean, default=False)
    is_dismissed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)  # When recommendation expires
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="recommendations")

    def __repr__(self):
        return f"<UserRecommendation(id={self.id}, user_id={self.user_id}, type={self.recommendation_type}, score={self.relevance_score})>"


class UserPreference(Base):
    """User preferences for recommendation system"""
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    # Content preferences
    favorite_categories = Column(JSON, default=list)  # List of category IDs
    favorite_animals = Column(JSON, default=list)  # List of animal profile IDs
    preferred_content_types = Column(JSON, default=list)  # blog, case_study, news, etc.
    
    # Interaction patterns
    avg_session_duration = Column(Integer, nullable=True)  # in seconds
    preferred_time_of_day = Column(Integer, nullable=True)  # 0-23 hour
    most_active_day = Column(Integer, nullable=True)  # 0-6 (Monday=0)
    
    # Engagement metrics
    total_content_views = Column(Integer, default=0)
    total_quiz_attempts = Column(Integer, default=0)
    total_livestream_views = Column(Integer, default=0)
    
    # Preference scores (0.0 to 1.0)
    wildlife_interest_score = Column(Float, default=0.5)
    conservation_interest_score = Column(Float, default=0.5)
    education_interest_score = Column(Float, default=0.5)
    entertainment_interest_score = Column(Float, default=0.5)
    
    # Metadata
    preference_metadata = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="preference", uselist=False)

    def __repr__(self):
        return f"<UserPreference(id={self.id}, user_id={self.user_id})>"


class ViewingHistory(Base):
    """Track user viewing history for recommendations"""
    __tablename__ = "viewing_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Item details
    item_type = Column(String(50), nullable=False)  # content, animal_profile, livestream, etc.
    item_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Viewing details
    view_duration = Column(Integer, nullable=True)  # in seconds
    completion_percentage = Column(Float, nullable=True)  # 0.0 to 1.0
    interaction_score = Column(Float, default=0.0)  # engagement score
    
    # Context
    referrer_type = Column(String(50), nullable=True)  # recommendation, search, direct, etc.
    referrer_id = Column(UUID(as_uuid=True), nullable=True)  # ID of referring item
    device_type = Column(String(50), nullable=True)  # mobile, desktop, tablet
    
    # Timestamps
    viewed_at = Column(DateTime(timezone=True), server_default=func.now())
    session_start = Column(DateTime(timezone=True), nullable=True)
    session_end = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="viewing_history")

    def __repr__(self):
        return f"<ViewingHistory(id={self.id}, user_id={self.user_id}, item_type={self.item_type})>"


class TrendingItem(Base):
    """Track trending items across the platform"""
    __tablename__ = "trending_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Item details
    item_type = Column(String(50), nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Trending metrics
    view_count_24h = Column(Integer, default=0)
    view_count_7d = Column(Integer, default=0)
    view_count_30d = Column(Integer, default=0)
    
    unique_viewers_24h = Column(Integer, default=0)
    unique_viewers_7d = Column(Integer, default=0)
    unique_viewers_30d = Column(Integer, default=0)
    
    # Engagement metrics
    engagement_score_24h = Column(Float, default=0.0)
    engagement_score_7d = Column(Float, default=0.0)
    engagement_score_30d = Column(Float, default=0.0)
    
    # Trending score (calculated)
    trending_score = Column(Float, default=0.0)
    velocity_score = Column(Float, default=0.0)  # Rate of growth
    
    # Timestamps
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    trending_since = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<TrendingItem(id={self.id}, item_type={self.item_type}, trending_score={self.trending_score})>"
