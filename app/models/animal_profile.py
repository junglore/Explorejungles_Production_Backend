"""
Animal profile models for community features
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, Enum, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from uuid import uuid4
import enum

from app.db.database import Base


class ConservationStatusEnum(str, enum.Enum):
    LEAST_CONCERN = "least_concern"
    NEAR_THREATENED = "near_threatened"
    VULNERABLE = "vulnerable"
    ENDANGERED = "endangered"
    CRITICALLY_ENDANGERED = "critically_endangered"
    EXTINCT_IN_WILD = "extinct_in_wild"
    EXTINCT = "extinct"
    DATA_DEFICIENT = "data_deficient"


class HabitatTypeEnum(str, enum.Enum):
    FOREST = "forest"
    GRASSLAND = "grassland"
    DESERT = "desert"
    WETLAND = "wetland"
    MARINE = "marine"
    FRESHWATER = "freshwater"
    MOUNTAIN = "mountain"
    ARCTIC = "arctic"
    URBAN = "urban"


class AnimalProfile(Base):
    __tablename__ = "animal_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    
    # Basic Information
    common_name = Column(String(255), nullable=False, index=True)
    scientific_name = Column(String(255), nullable=False, index=True)
    other_names = Column(JSON, default=list)  # List of alternative names
    
    # Classification
    kingdom = Column(String(100), default="Animalia")
    phylum = Column(String(100), nullable=True)
    class_name = Column(String(100), nullable=True)  # 'class' is reserved keyword
    order = Column(String(100), nullable=True)
    family = Column(String(100), nullable=True)
    genus = Column(String(100), nullable=True)
    species = Column(String(100), nullable=True)
    
    # Physical Characteristics
    description = Column(Text, nullable=True)
    physical_description = Column(Text, nullable=True)
    average_weight_kg = Column(Float, nullable=True)  # in kg
    average_length_cm = Column(Float, nullable=True)  # in cm
    average_height_cm = Column(Float, nullable=True)  # in cm
    lifespan_years = Column(Integer, nullable=True)
    
    # Habitat and Distribution
    habitat_types = Column(JSON, default=list)  # List of HabitatTypeEnum values
    geographic_distribution = Column(JSON, default=list)  # List of countries/regions
    habitat_description = Column(Text, nullable=True)
    
    # Behavior and Diet
    diet_type = Column(String(100), nullable=True)  # carnivore, herbivore, omnivore
    diet_description = Column(Text, nullable=True)
    behavior_description = Column(Text, nullable=True)
    social_structure = Column(String(100), nullable=True)  # solitary, pack, herd, etc.
    
    # Conservation
    conservation_status = Column(Enum(ConservationStatusEnum), nullable=True)
    population_estimate = Column(String(255), nullable=True)
    conservation_threats = Column(JSON, default=list)  # List of threat descriptions
    conservation_efforts = Column(Text, nullable=True)
    
    # Media
    profile_image_url = Column(String(500), nullable=True)
    gallery_images = Column(JSON, default=list)  # List of image URLs
    featured_video_url = Column(String(500), nullable=True)
    
    # Interesting Facts
    fun_facts = Column(JSON, default=list)  # List of interesting facts
    cultural_significance = Column(Text, nullable=True)
    
    # Metadata
    profile_metadata = Column(JSON, default=dict)  # Additional flexible data
    view_count = Column(Integer, default=0)
    is_featured = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    category = relationship("Category", backref="animal_profiles")

    def __repr__(self):
        return f"<AnimalProfile(id={self.id}, common_name={self.common_name}, scientific_name={self.scientific_name})>"


class UserAnimalInteraction(Base):
    """Track user interactions with animal profiles"""
    __tablename__ = "user_animal_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    animal_profile_id = Column(UUID(as_uuid=True), ForeignKey("animal_profiles.id", ondelete="CASCADE"), nullable=False)
    
    # Interaction types
    is_favorite = Column(Boolean, default=False)
    has_viewed = Column(Boolean, default=True)
    view_count = Column(Integer, default=1)
    
    # Timestamps
    first_viewed_at = Column(DateTime(timezone=True), server_default=func.now())
    last_viewed_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    favorited_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", backref="animal_interactions")
    animal_profile = relationship("AnimalProfile", backref="user_interactions")

    def __repr__(self):
        return f"<UserAnimalInteraction(user_id={self.user_id}, animal_id={self.animal_profile_id}, favorite={self.is_favorite})>"


class AnimalSighting(Base):
    """User-submitted animal sightings"""
    __tablename__ = "animal_sightings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    animal_profile_id = Column(UUID(as_uuid=True), ForeignKey("animal_profiles.id", ondelete="SET NULL"), nullable=True)
    
    # Sighting details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Location
    location_name = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    country = Column(String(100), nullable=True)
    
    # Sighting metadata
    sighting_date = Column(DateTime(timezone=True), nullable=False)
    photo_urls = Column(JSON, default=list)  # List of photo URLs
    is_verified = Column(Boolean, default=False)
    verification_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="animal_sightings")
    animal_profile = relationship("AnimalProfile", backref="sightings")

    def __repr__(self):
        return f"<AnimalSighting(id={self.id}, title={self.title}, user_id={self.user_id})>"
