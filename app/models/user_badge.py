"""
User badge system for community recognition
Supports badges like "Researcher", "Conservationist", "Wildlife Photographer", etc.
"""

from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4

from app.db.database import Base


class UserBadge(Base):
    """
    Defines available badges that can be assigned to users
    Examples: Researcher, Conservationist, Wildlife Photographer, etc.
    """
    __tablename__ = "user_badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Badge details
    name = Column(String(100), unique=True, nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Display properties
    color = Column(String(20), nullable=True)  # Hex color code for badge display
    icon = Column(String(100), nullable=True)   # Icon class or icon name
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    assignments = relationship(
        "UserBadgeAssignment",
        back_populates="badge",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<UserBadge(id={self.id}, name={self.name}, slug={self.slug})>"


class UserBadgeAssignment(Base):
    """
    Links users to their assigned badges
    Admins assign badges to recognize user expertise/contributions
    """
    __tablename__ = "user_badge_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    badge_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("user_badges.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Assignment metadata
    assigned_by = Column(
        UUID(as_uuid=True), 
        ForeignKey("users.id", ondelete="SET NULL"), 
        nullable=True  # Admin who assigned the badge
    )
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Optional assignment note
    note = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="badge_assignments")
    badge = relationship("UserBadge", back_populates="assignments")
    assigner = relationship("User", foreign_keys=[assigned_by])

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'badge_id', name='uq_user_badge'),
        Index('ix_badge_assignments_user', 'user_id', 'assigned_at'),
        Index('ix_badge_assignments_badge', 'badge_id', 'assigned_at'),
    )

    def __repr__(self):
        return f"<UserBadgeAssignment(user_id={self.user_id}, badge_id={self.badge_id})>"