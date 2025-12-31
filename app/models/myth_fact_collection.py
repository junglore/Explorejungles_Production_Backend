"""
Myth Fact Collection Database Models

This module defines SQLAlchemy models for the collection-based myth vs facts system.
Collections allow grouping myth/fact cards into themed decks with custom rewards
and repeatability settings.

Database Schema:
- MythFactCollection: Themed collections/decks
- CollectionMythFact: Junction table for card assignments
- UserCollectionProgress: Daily progress tracking per collection

Author: Junglore Development Team
Version: 1.0.0
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Date, UniqueConstraint, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class MythFactCollection(Base):
    """
    SQLAlchemy model for myth fact collections (themed decks).
    
    Collections group myth/fact cards into themed experiences with:
    - Custom reward configurations
    - Repeatability settings (daily/weekly/unlimited)
    - Category-based organization
    - Progress tracking per user
    
    Attributes:
        id (UUID): Primary key
        category_id (UUID): Optional category for organization
        name (str): Collection display name
        description (str): Collection description
        is_active (bool): Whether collection is available for play
        cards_count (int): Cached count of cards in collection
        repeatability (str): Repeat frequency ('daily', 'weekly', 'unlimited')
        custom_points_enabled (bool): Whether to use custom point rewards
        custom_points_* (int): Custom point values per tier
        custom_credits_enabled (bool): Whether to use custom credit rewards
        custom_credits_* (int): Custom credit values per tier
        created_at (datetime): Creation timestamp
        updated_at (datetime): Last update timestamp
        created_by (UUID): Admin who created the collection
        
    Relationships:
        category: Many-to-one with Category
        cards: Many-to-many with MythFact through CollectionMythFact
        user_progress: One-to-many with UserCollectionProgress
    """
    __tablename__ = "myth_fact_collections"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Organization
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    cards_count = Column(Integer, default=0, nullable=False)
    
    # Repeatability settings
    repeatability = Column(String(20), default='daily', nullable=False)  # 'daily', 'weekly', 'unlimited'
    
    # Custom point rewards (override database defaults)
    custom_points_enabled = Column(Boolean, default=False, nullable=False)
    custom_points_bronze = Column(Integer, nullable=True)
    custom_points_silver = Column(Integer, nullable=True)
    custom_points_gold = Column(Integer, nullable=True)
    custom_points_platinum = Column(Integer, nullable=True)
    
    # Custom credit rewards (override database defaults)
    custom_credits_enabled = Column(Boolean, default=False, nullable=False)
    custom_credits_bronze = Column(Integer, nullable=True)
    custom_credits_silver = Column(Integer, nullable=True)
    custom_credits_gold = Column(Integer, nullable=True)
    custom_credits_platinum = Column(Integer, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    category = relationship("Category", backref="myth_fact_collections")
    creator = relationship("User", foreign_keys=[created_by])
    
    # Many-to-many with MythFact through CollectionMythFact
    collection_cards = relationship("CollectionMythFact", back_populates="collection", cascade="all, delete-orphan")
    
    # One-to-many with UserCollectionProgress
    user_progress = relationship("UserCollectionProgress", back_populates="collection", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MythFactCollection(id={self.id}, name='{self.name}')>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'category_id': str(self.category_id) if self.category_id else None,
            'name': self.name,
            'description': self.description,
            'is_active': self.is_active,
            'cards_count': self.cards_count,
            'repeatability': self.repeatability,
            'custom_points_enabled': self.custom_points_enabled,
            'custom_points': {
                'bronze': self.custom_points_bronze,
                'silver': self.custom_points_silver,
                'gold': self.custom_points_gold,
                'platinum': self.custom_points_platinum
            } if self.custom_points_enabled else None,
            'custom_credits_enabled': self.custom_credits_enabled,
            'custom_credits': {
                'bronze': self.custom_credits_bronze,
                'silver': self.custom_credits_silver,
                'gold': self.custom_credits_gold,
                'platinum': self.custom_credits_platinum
            } if self.custom_credits_enabled else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'category': self.category.name if self.category else None
        }


class CollectionMythFact(Base):
    """
    Junction table for many-to-many relationship between collections and myth facts.
    
    This table defines which cards belong to which collections and in what order.
    Supports ordered card presentation and ensures no duplicate cards per collection.
    
    Attributes:
        id (UUID): Primary key
        collection_id (UUID): Reference to MythFactCollection
        myth_fact_id (UUID): Reference to MythFact
        order_index (int): Order of card in collection (0-based)
        created_at (datetime): Assignment timestamp
        
    Constraints:
        - Unique(collection_id, myth_fact_id): No duplicate cards per collection
        - Unique(collection_id, order_index): No duplicate positions per collection
        
    Relationships:
        collection: Many-to-one with MythFactCollection
        myth_fact: Many-to-one with MythFact
    """
    __tablename__ = "collection_myth_facts"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    collection_id = Column(UUID(as_uuid=True), ForeignKey("myth_fact_collections.id", ondelete="CASCADE"), nullable=False)
    myth_fact_id = Column(UUID(as_uuid=True), ForeignKey("myths_facts.id", ondelete="CASCADE"), nullable=False)
    
    # Ordering
    order_index = Column(Integer, default=0, nullable=False)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Constraints
    __table_args__ = (
        UniqueConstraint('collection_id', 'myth_fact_id', name='uq_collection_myth_fact'),
        UniqueConstraint('collection_id', 'order_index', name='uq_collection_order'),
    )

    # Relationships
    collection = relationship("MythFactCollection", back_populates="collection_cards")
    myth_fact = relationship("MythFact", backref="collection_assignments")

    def __repr__(self):
        return f"<CollectionMythFact(collection_id={self.collection_id}, myth_fact_id={self.myth_fact_id}, order={self.order_index})>"


class UserCollectionProgress(Base):
    """
    Tracks user progress on myth fact collections.
    
    This model enforces daily repeatability limits and tracks detailed
    progress statistics for each user's interaction with collections.
    
    Attributes:
        id (UUID): Primary key
        user_id (UUID): Reference to User
        collection_id (UUID): Reference to MythFactCollection
        play_date (date): Date of play attempt
        completed (bool): Whether collection was completed
        score_percentage (int): Final score percentage (0-100)
        time_taken (int): Time taken in seconds
        answers_correct (int): Number of correct answers
        total_questions (int): Total number of questions attempted
        points_earned (int): Points earned this session
        credits_earned (int): Credits earned this session
        tier (str): Achievement tier (BRONZE, SILVER, GOLD, PLATINUM)
        bonus_applied (bool): Whether any bonuses were applied
        game_session_id (UUID): Optional game session reference
        created_at (datetime): Start timestamp
        completed_at (datetime): Completion timestamp
        
    Constraints:
        - Unique(user_id, collection_id, play_date): One attempt per collection per day
        - score_percentage: 0-100 range
        - answers_correct <= total_questions
        
    Relationships:
        user: Many-to-one with User
        collection: Many-to-one with MythFactCollection
    """
    __tablename__ = "user_collection_progress"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Foreign keys
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("myth_fact_collections.id", ondelete="CASCADE"), nullable=False)
    
    # Progress tracking
    play_date = Column(Date, nullable=False, server_default=func.current_date())
    completed = Column(Boolean, default=False, nullable=False)
    score_percentage = Column(Integer, default=0, nullable=False)
    time_taken = Column(Integer, nullable=True)  # seconds
    answers_correct = Column(Integer, default=0, nullable=False)
    total_questions = Column(Integer, default=0, nullable=False)
    
    # Rewards tracking
    points_earned = Column(Integer, default=0, nullable=False)
    credits_earned = Column(Integer, default=0, nullable=False)
    tier = Column(String(20), nullable=True)  # BRONZE, SILVER, GOLD, PLATINUM
    bonus_applied = Column(Boolean, default=False, nullable=False)
    
    # Session tracking
    game_session_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'collection_id', 'play_date', name='uq_user_collection_daily'),
        CheckConstraint('score_percentage >= 0 AND score_percentage <= 100', name='valid_score_percentage'),
        CheckConstraint('answers_correct >= 0 AND answers_correct <= total_questions', name='valid_answers'),
    )

    # Relationships
    user = relationship("User", backref="collection_progress")
    collection = relationship("MythFactCollection", back_populates="user_progress")

    def __repr__(self):
        return f"<UserCollectionProgress(user_id={self.user_id}, collection_id={self.collection_id}, date={self.play_date}, completed={self.completed})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'collection_id': str(self.collection_id),
            'play_date': self.play_date.isoformat() if self.play_date else None,
            'completed': self.completed,
            'score_percentage': self.score_percentage,
            'time_taken': self.time_taken,
            'answers_correct': self.answers_correct,
            'total_questions': self.total_questions,
            'points_earned': self.points_earned,
            'credits_earned': self.credits_earned,
            'tier': self.tier,
            'bonus_applied': self.bonus_applied,
            'game_session_id': str(self.game_session_id) if self.game_session_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }