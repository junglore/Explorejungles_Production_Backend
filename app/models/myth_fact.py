"""
Myth vs Fact Database Model

This module defines the SQLAlchemy model for storing educational myth vs fact content
used in the Junglore wildlife education game. The model supports categorization,
featured content marking, and proper relationship management.

Database Schema:
- Primary key: UUID for distributed system compatibility
- Foreign key: Optional category association with cascade handling
- Content fields: Title, myth statement, and factual explanation
- Media support: Optional image URL for visual content
- Metadata: Featured status and creation timestamp

Constraints:
- Title limited to 500 characters for UI compatibility
- Myth and fact content stored as unlimited text
- Image URL limited to 500 characters
- Category relationship with SET NULL on delete for data integrity

Author: Junglore Development Team
Version: 1.0.0
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class MythFact(Base):
    """
    SQLAlchemy model for myth vs fact educational content.
    
    This model represents individual myth vs fact entries used in the educational
    game interface. Each entry contains a myth statement paired with factual
    information to educate users about wildlife conservation topics.
    
    Attributes:
        id (UUID): Primary key, auto-generated UUID for unique identification
        category_id (UUID, optional): Foreign key to categories table for content organization
        title (str): Entry title, max 500 characters for display purposes
        myth_content (str): The myth or misconception statement (unlimited text)
        fact_content (str): The factual explanation that corrects the myth (unlimited text)
        image_url (str, optional): URL to supporting image, max 500 characters
        is_featured (bool): Flag indicating if content should be prominently displayed
        created_at (datetime): Auto-generated timestamp of record creation
        
    Relationships:
        category: Many-to-one relationship with Category model
        
    Database Constraints:
        - title: NOT NULL, max 500 characters
        - myth_content: NOT NULL, unlimited text
        - fact_content: NOT NULL, unlimited text
        - image_url: nullable, max 500 characters
        - category_id: nullable, SET NULL on category deletion
        
    Example:
        myth_fact = MythFact(
            title="Snake Behavior",
            myth_content="All snakes are dangerous to humans",
            fact_content="Most snakes are harmless and avoid human contact",
            is_featured=True
        )
    """
    __tablename__ = "myths_facts"

    # Primary key with UUID for distributed system compatibility
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, 
                doc="Unique identifier for the myth vs fact entry")
    
    # Foreign key relationship to categories (optional)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), 
                        nullable=True, doc="Optional category for content organization")
    
    # Content fields with appropriate constraints
    title = Column(String(500), nullable=False, 
                  doc="Entry title for display, max 500 characters")
    myth_content = Column(Text, nullable=False, 
                         doc="The myth or misconception statement")
    fact_content = Column(Text, nullable=False, 
                         doc="The factual explanation that corrects the myth")
    image_url = Column(String(500), nullable=True, 
                      doc="Optional URL to supporting image, max 500 characters")
    
    # MVF System Enhancement Fields
    custom_points = Column(Integer, nullable=True,
                          doc="Custom points awarded for this specific card (overrides base points)")
    
    # Card display type - controls which content shows to user during gameplay
    type = Column(String(10), nullable=False, default='myth',
                 doc="Card type: 'myth' shows myth_content, 'fact' shows fact_content during gameplay")
    
    # Metadata fields
    is_featured = Column(Boolean, default=False, 
                        doc="Flag indicating if content should be prominently displayed")
    
    # Timestamp fields with automatic population
    created_at = Column(DateTime(timezone=True), server_default=func.now(),
                       doc="Timestamp of record creation, auto-generated")

    # Relationship definitions
    category = relationship("Category", backref="myths_facts",
                          doc="Many-to-one relationship with Category model")

    def __repr__(self):
        """
        String representation for debugging and logging.
        
        Returns:
            str: Human-readable representation showing ID and title
        """
        return f"<MythFact(id={self.id}, title='{self.title[:50]}...')>"
    
    def to_dict(self):
        """
        Convert model instance to dictionary for JSON serialization.
        
        Returns:
            dict: Dictionary representation of the model with all fields
        """
        return {
            'id': str(self.id),
            'category_id': str(self.category_id) if self.category_id else None,
            'title': self.title,
            'myth_content': self.myth_content,
            'fact_content': self.fact_content,
            'image_url': self.image_url,
            'is_featured': self.is_featured,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'category': self.category.name if self.category else None
        }
