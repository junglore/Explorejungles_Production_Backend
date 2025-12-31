"""
Category model for organizing content and livestreams
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.database import Base


class Category(Base):
    __tablename__ = "categories"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Core fields with proper constraints
    name = Column(String(255), unique=True, nullable=False, index=True)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # MVF System Enhancement Fields
    custom_credits = Column(Integer, nullable=True, 
                           doc="Custom credits awarded for completing this category in MVF")
    is_featured = Column(Boolean, default=False, nullable=False, 
                        doc="Featured category for MVF game default selection")
    mvf_enabled = Column(Boolean, default=True, nullable=False, 
                        doc="Enable this category for Myths vs Facts game")
    
    # Analytics and status with proper defaults
    viewer_count = Column(Integer, default=0, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes for performance optimization
    __table_args__ = (
        # Index for active categories
        Index('ix_categories_active_name', 'is_active', 'name'),
        # Index for MVF enabled categories
        Index('ix_categories_mvf_featured', 'mvf_enabled', 'is_featured'),
        # Index for active MVF categories
        Index('ix_categories_mvf_active', 'mvf_enabled', 'is_active'),
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name}, slug={self.slug})>"
