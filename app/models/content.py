"""
Content model for blogs, case studies, daily updates, etc.
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, Enum, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class ContentTypeEnum(str, enum.Enum):
    BLOG = "blog"
    CASE_STUDY = "case_study"
    DAILY_UPDATE = "daily_update"
    CONSERVATION_EFFORT = "conservation_effort"
    NEWS = "news"
    ARTICLE = "article"


class ContentStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Content(Base):
    __tablename__ = "content"

    # Primary key and foreign keys
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    # Core content fields with proper constraints
    type = Column(Enum(ContentTypeEnum), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    
    # Author display name (can be different from user account name)
    author_name = Column(String(200), nullable=True)  # Custom author name for display
    
    # Media fields (matching junglore.com Blog model)
    featured_image = Column(String(500), nullable=True)  # image field from junglore.com
    banner = Column(String(500), nullable=True)          # banner field from junglore.com  
    video = Column(String(500), nullable=True)           # video field from junglore.com
    
    # Featured blog system (matching junglore.com)
    featured = Column(Boolean, default=False, nullable=False, index=True)  # featured field from junglore.com
    feature_place = Column(Integer, default=0, nullable=False)             # feature_place field from junglore.com
    
    # SEO and metadata with proper constraints
    slug = Column(String(500), unique=True, index=True, nullable=True)
    excerpt = Column(Text, nullable=True)
    meta_description = Column(String(255), nullable=True)
    content_metadata = Column(JSON, default=dict, nullable=False)  # Flexible metadata storage
    
    # Analytics with proper defaults and constraints
    view_count = Column(Integer, default=0, nullable=False)
    status = Column(Enum(ContentStatusEnum), default=ContentStatusEnum.DRAFT, nullable=False, index=True)
    
    # Timestamps with proper constraints
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships with proper cascade behavior
    author = relationship("User", backref="content")
    category = relationship("Category", backref="content")

    # Composite indexes for performance optimization
    __table_args__ = (
        # Index for filtering published content by type and date
        Index('ix_content_published_type_date', 'status', 'type', 'published_at'),
        # Index for featured content queries
        Index('ix_content_featured_place', 'featured', 'feature_place'),
        # Index for author's content queries
        Index('ix_content_author_status', 'author_id', 'status'),
        # Index for category content queries
        Index('ix_content_category_status', 'category_id', 'status'),
        # Index for content search and ordering
        Index('ix_content_type_created', 'type', 'created_at'),
    )

    def __repr__(self):
        return f"<Content(id={self.id}, title={self.title}, type={self.type})>"
