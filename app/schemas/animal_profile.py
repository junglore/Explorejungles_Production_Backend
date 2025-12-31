"""
Animal profile schemas for request/response models
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from app.models.animal_profile import ConservationStatusEnum, HabitatTypeEnum


class AnimalProfileBase(BaseModel):
    """Base schema for animal profile"""
    common_name: str = Field(..., min_length=1, max_length=255, description="Common name of the animal")
    scientific_name: str = Field(..., min_length=1, max_length=255, description="Scientific name")
    other_names: Optional[List[str]] = Field(None, description="Alternative names")
    category_id: Optional[UUID] = Field(None, description="Category ID")
    
    # Classification
    kingdom: str = Field(default="Animalia", max_length=100)
    phylum: Optional[str] = Field(None, max_length=100)
    class_name: Optional[str] = Field(None, max_length=100, description="Taxonomic class")
    order: Optional[str] = Field(None, max_length=100)
    family: Optional[str] = Field(None, max_length=100)
    genus: Optional[str] = Field(None, max_length=100)
    species: Optional[str] = Field(None, max_length=100)
    
    # Physical Characteristics
    description: Optional[str] = Field(None, description="General description")
    physical_description: Optional[str] = Field(None, description="Physical characteristics")
    average_weight_kg: Optional[float] = Field(None, ge=0, description="Average weight in kg")
    average_length_cm: Optional[float] = Field(None, ge=0, description="Average length in cm")
    average_height_cm: Optional[float] = Field(None, ge=0, description="Average height in cm")
    lifespan_years: Optional[int] = Field(None, ge=0, le=500, description="Lifespan in years")
    
    # Habitat and Distribution
    habitat_types: Optional[List[HabitatTypeEnum]] = Field(None, description="Habitat types")
    geographic_distribution: Optional[List[str]] = Field(None, description="Geographic distribution")
    habitat_description: Optional[str] = Field(None, description="Habitat description")
    
    # Behavior and Diet
    diet_type: Optional[str] = Field(None, max_length=100, description="Diet type")
    diet_description: Optional[str] = Field(None, description="Diet description")
    behavior_description: Optional[str] = Field(None, description="Behavior description")
    social_structure: Optional[str] = Field(None, max_length=100, description="Social structure")
    
    # Conservation
    conservation_status: Optional[ConservationStatusEnum] = Field(None, description="Conservation status")
    population_estimate: Optional[str] = Field(None, max_length=255, description="Population estimate")
    conservation_threats: Optional[List[str]] = Field(None, description="Conservation threats")
    conservation_efforts: Optional[str] = Field(None, description="Conservation efforts")
    
    # Media
    profile_image_url: Optional[str] = Field(None, max_length=500, description="Profile image URL")
    gallery_images: Optional[List[str]] = Field(None, description="Gallery image URLs")
    featured_video_url: Optional[str] = Field(None, max_length=500, description="Featured video URL")
    
    # Interesting Facts
    fun_facts: Optional[List[str]] = Field(None, description="Fun facts")
    cultural_significance: Optional[str] = Field(None, description="Cultural significance")
    
    # Metadata
    profile_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    is_featured: bool = Field(default=False, description="Is featured animal")
    is_active: bool = Field(default=True, description="Is active")


class AnimalProfileCreate(AnimalProfileBase):
    """Schema for creating animal profile"""
    pass


class AnimalProfileUpdate(BaseModel):
    """Schema for updating animal profile"""
    common_name: Optional[str] = Field(None, min_length=1, max_length=255)
    scientific_name: Optional[str] = Field(None, min_length=1, max_length=255)
    other_names: Optional[List[str]] = None
    category_id: Optional[UUID] = None
    
    # Classification
    kingdom: Optional[str] = Field(None, max_length=100)
    phylum: Optional[str] = Field(None, max_length=100)
    class_name: Optional[str] = Field(None, max_length=100)
    order: Optional[str] = Field(None, max_length=100)
    family: Optional[str] = Field(None, max_length=100)
    genus: Optional[str] = Field(None, max_length=100)
    species: Optional[str] = Field(None, max_length=100)
    
    # Physical Characteristics
    description: Optional[str] = None
    physical_description: Optional[str] = None
    average_weight_kg: Optional[float] = Field(None, ge=0)
    average_length_cm: Optional[float] = Field(None, ge=0)
    average_height_cm: Optional[float] = Field(None, ge=0)
    lifespan_years: Optional[int] = Field(None, ge=0, le=500)
    
    # Habitat and Distribution
    habitat_types: Optional[List[HabitatTypeEnum]] = None
    geographic_distribution: Optional[List[str]] = None
    habitat_description: Optional[str] = None
    
    # Behavior and Diet
    diet_type: Optional[str] = Field(None, max_length=100)
    diet_description: Optional[str] = None
    behavior_description: Optional[str] = None
    social_structure: Optional[str] = Field(None, max_length=100)
    
    # Conservation
    conservation_status: Optional[ConservationStatusEnum] = None
    population_estimate: Optional[str] = Field(None, max_length=255)
    conservation_threats: Optional[List[str]] = None
    conservation_efforts: Optional[str] = None
    
    # Media
    profile_image_url: Optional[str] = Field(None, max_length=500)
    gallery_images: Optional[List[str]] = None
    featured_video_url: Optional[str] = Field(None, max_length=500)
    
    # Interesting Facts
    fun_facts: Optional[List[str]] = None
    cultural_significance: Optional[str] = None
    
    # Metadata
    profile_metadata: Optional[Dict[str, Any]] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None


class CategorySummary(BaseModel):
    """Summary of category for animal profile"""
    id: UUID
    name: str
    slug: str

    class Config:
        from_attributes = True


class AnimalProfileResponse(BaseModel):
    """Schema for animal profile response"""
    id: UUID
    common_name: str
    scientific_name: str
    other_names: Optional[List[str]]
    category_id: Optional[UUID]
    category: Optional[CategorySummary]
    
    # Classification
    kingdom: str
    phylum: Optional[str]
    class_name: Optional[str]
    order: Optional[str]
    family: Optional[str]
    genus: Optional[str]
    species: Optional[str]
    
    # Physical Characteristics
    description: Optional[str]
    physical_description: Optional[str]
    average_weight_kg: Optional[float]
    average_length_cm: Optional[float]
    average_height_cm: Optional[float]
    lifespan_years: Optional[int]
    
    # Habitat and Distribution
    habitat_types: Optional[List[HabitatTypeEnum]]
    geographic_distribution: Optional[List[str]]
    habitat_description: Optional[str]
    
    # Behavior and Diet
    diet_type: Optional[str]
    diet_description: Optional[str]
    behavior_description: Optional[str]
    social_structure: Optional[str]
    
    # Conservation
    conservation_status: Optional[ConservationStatusEnum]
    population_estimate: Optional[str]
    conservation_threats: Optional[List[str]]
    conservation_efforts: Optional[str]
    
    # Media
    profile_image_url: Optional[str]
    gallery_images: Optional[List[str]]
    featured_video_url: Optional[str]
    
    # Interesting Facts
    fun_facts: Optional[List[str]]
    cultural_significance: Optional[str]
    
    # Metadata
    profile_metadata: Optional[Dict[str, Any]]
    view_count: int
    is_featured: bool
    is_active: bool
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnimalProfileListResponse(BaseModel):
    """Schema for animal profile list response (minimal info for performance)"""
    id: UUID
    common_name: str
    scientific_name: str
    profile_image_url: Optional[str]
    conservation_status: Optional[ConservationStatusEnum]
    habitat_types: Optional[List[HabitatTypeEnum]]
    view_count: int
    is_featured: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AnimalSightingCreate(BaseModel):
    """Schema for creating animal sighting"""
    animal_profile_id: Optional[UUID] = Field(None, description="Animal profile ID if known")
    title: str = Field(..., min_length=1, max_length=255, description="Sighting title")
    description: Optional[str] = Field(None, description="Sighting description")
    
    # Location
    location_name: Optional[str] = Field(None, max_length=255, description="Location name")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Longitude")
    country: Optional[str] = Field(None, max_length=100, description="Country")
    
    # Sighting metadata
    sighting_date: datetime = Field(..., description="Date and time of sighting")
    photo_urls: Optional[List[str]] = Field(None, description="Photo URLs")


class AnimalSightingResponse(BaseModel):
    """Schema for animal sighting response"""
    id: UUID
    user_id: UUID
    animal_profile_id: Optional[UUID]
    title: str
    description: Optional[str]
    
    # Location
    location_name: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    country: Optional[str]
    
    # Sighting metadata
    sighting_date: datetime
    photo_urls: Optional[List[str]]
    is_verified: bool
    verification_notes: Optional[str]
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserAnimalInteractionResponse(BaseModel):
    """Schema for user animal interaction response"""
    id: UUID
    user_id: UUID
    animal_profile_id: UUID
    is_favorite: bool
    view_count: int
    first_viewed_at: datetime
    last_viewed_at: datetime
    favorited_at: Optional[datetime]

    class Config:
        from_attributes = True


class AnimalStatsResponse(BaseModel):
    """Schema for animal statistics"""
    total_profiles: int
    featured_profiles: int
    by_conservation_status: Dict[str, int]
    by_habitat_type: Dict[str, int]
    most_viewed: List[AnimalProfileListResponse]
    recently_added: List[AnimalProfileListResponse]
    total_sightings: int

    class Config:
        from_attributes = True
