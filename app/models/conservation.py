"""
Conservation effort model for tracking wildlife conservation projects
"""

from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from uuid import uuid4

from app.db.database import Base


class ConservationEffort(Base):
    __tablename__ = "conservation_efforts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=True)
    organization = Column(String(255), nullable=True)
    image_url = Column(String(500), nullable=True)
    
    # Impact metrics stored as JSON
    # Format: {"animals_saved": 150, "habitat_restored": "500 acres", "funding_raised": "$50000"}
    impact_metrics = Column(JSON, default=dict)
    
    # Project timeline
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ConservationEffort(id={self.id}, title={self.title}, organization={self.organization})>"
