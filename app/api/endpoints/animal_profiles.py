"""
Animal Profile API Routes
Handles animal profiles, sightings, and user interactions
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.db.database import get_db
from app.models.animal_profile import (
    AnimalProfile, 
    UserAnimalInteraction, 
    AnimalSighting,
    ConservationStatusEnum,
    HabitatTypeEnum
)
from app.models.user import User
from app.models.category import Category
from app.core.security import get_current_user, get_current_user_optional
from app.schemas.animal_profile import (
    AnimalProfileCreate,
    AnimalProfileUpdate,
    AnimalProfileResponse,
    AnimalProfileListResponse,
    AnimalSightingCreate,
    AnimalSightingResponse,
    UserAnimalInteractionResponse,
    AnimalStatsResponse,
    CategorySummary
)

router = APIRouter()


@router.get("/", response_model=List[AnimalProfileListResponse])
async def get_animal_profiles(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    conservation_status: Optional[ConservationStatusEnum] = Query(None, description="Filter by conservation status"),
    habitat_type: Optional[HabitatTypeEnum] = Query(None, description="Filter by habitat type"),
    search: Optional[str] = Query(None, description="Search in names and description"),
    featured_only: bool = Query(False, description="Show only featured animals"),
    active_only: bool = Query(True, description="Show only active animals"),
    db: AsyncSession = Depends(get_db)
):
    """Get animal profiles with filtering and pagination"""
    
    query = select(AnimalProfile)
    
    # Apply filters
    if active_only:
        query = query.where(AnimalProfile.is_active == True)
    
    if featured_only:
        query = query.where(AnimalProfile.is_featured == True)
        
    if category_id:
        query = query.where(AnimalProfile.category_id == category_id)
        
    if conservation_status:
        query = query.where(AnimalProfile.conservation_status == conservation_status)
    
    if habitat_type:
        query = query.where(AnimalProfile.habitat_types.contains([habitat_type]))
    
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                AnimalProfile.common_name.ilike(search_term),
                AnimalProfile.scientific_name.ilike(search_term),
                AnimalProfile.description.ilike(search_term)
            )
        )
    
    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(
        desc(AnimalProfile.is_featured),
        desc(AnimalProfile.view_count),
        AnimalProfile.common_name
    )
    
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    return [AnimalProfileListResponse(
        id=profile.id,
        common_name=profile.common_name,
        scientific_name=profile.scientific_name,
        profile_image_url=profile.profile_image_url,
        conservation_status=profile.conservation_status,
        habitat_types=profile.habitat_types,
        view_count=profile.view_count,
        is_featured=profile.is_featured,
        created_at=profile.created_at
    ) for profile in profiles]


@router.get("/featured", response_model=List[AnimalProfileListResponse])
async def get_featured_animals(
    limit: int = Query(10, ge=1, le=50, description="Number of featured animals to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get featured animal profiles"""
    
    result = await db.execute(
        select(AnimalProfile)
        .where(and_(AnimalProfile.is_featured == True, AnimalProfile.is_active == True))
        .order_by(desc(AnimalProfile.view_count))
        .limit(limit)
    )
    profiles = result.scalars().all()
    
    return [AnimalProfileListResponse(
        id=profile.id,
        common_name=profile.common_name,
        scientific_name=profile.scientific_name,
        profile_image_url=profile.profile_image_url,
        conservation_status=profile.conservation_status,
        habitat_types=profile.habitat_types,
        view_count=profile.view_count,
        is_featured=profile.is_featured,
        created_at=profile.created_at
    ) for profile in profiles]


@router.get("/recommendations/{user_id}", response_model=List[AnimalProfileListResponse])
async def get_animal_recommendations(
    user_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get personalized animal recommendations for user"""
    
    # For now, implement simple recommendation based on user's favorite categories
    # and previously viewed animals (can be enhanced with ML later)
    
    # Get user's interactions to understand preferences
    user_interactions = await db.execute(
        select(UserAnimalInteraction)
        .options(selectinload(UserAnimalInteraction.animal_profile))
        .where(UserAnimalInteraction.user_id == user_id)
        .order_by(desc(UserAnimalInteraction.last_viewed_at))
        .limit(20)
    )
    interactions = user_interactions.scalars().all()
    
    # Get categories from viewed animals
    viewed_categories = []
    for interaction in interactions:
        if interaction.animal_profile.category_id:
            viewed_categories.append(interaction.animal_profile.category_id)
    
    # Get animals from similar categories that user hasn't viewed
    viewed_animal_ids = [i.animal_profile_id for i in interactions]
    
    query = select(AnimalProfile).where(
        and_(
            AnimalProfile.is_active == True,
            ~AnimalProfile.id.in_(viewed_animal_ids)  # Exclude already viewed
        )
    )
    
    if viewed_categories:
        query = query.where(AnimalProfile.category_id.in_(viewed_categories))
    
    # Prioritize featured and popular animals
    query = query.order_by(
        desc(AnimalProfile.is_featured),
        desc(AnimalProfile.view_count)
    ).limit(limit)
    
    result = await db.execute(query)
    recommendations = result.scalars().all()
    
    return [AnimalProfileListResponse(
        id=profile.id,
        common_name=profile.common_name,
        scientific_name=profile.scientific_name,
        profile_image_url=profile.profile_image_url,
        conservation_status=profile.conservation_status,
        habitat_types=profile.habitat_types,
        view_count=profile.view_count,
        is_featured=profile.is_featured,
        created_at=profile.created_at
    ) for profile in recommendations]


@router.get("/{profile_id}", response_model=AnimalProfileResponse)
async def get_animal_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get specific animal profile by ID"""
    
    result = await db.execute(
        select(AnimalProfile)
        .options(selectinload(AnimalProfile.category))
        .where(AnimalProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal profile not found"
        )
    
    if not profile.is_active and (not current_user or not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Animal profile not available"
        )
    
    # Increment view count
    profile.view_count = (profile.view_count or 0) + 1
    
    # Track user interaction if logged in
    if current_user:
        # Check if interaction exists
        interaction_result = await db.execute(
            select(UserAnimalInteraction).where(
                and_(
                    UserAnimalInteraction.user_id == current_user.id,
                    UserAnimalInteraction.animal_profile_id == profile_id
                )
            )
        )
        interaction = interaction_result.scalar_one_or_none()
        
        if interaction:
            # Update existing interaction
            interaction.view_count += 1
            interaction.last_viewed_at = datetime.utcnow()
        else:
            # Create new interaction
            interaction = UserAnimalInteraction(
                user_id=current_user.id,
                animal_profile_id=profile_id,
                view_count=1
            )
            db.add(interaction)
    
    await db.commit()
    await db.refresh(profile)
    
    # Prepare category summary
    category_summary = None
    if profile.category:
        category_summary = CategorySummary(
            id=profile.category.id,
            name=profile.category.name,
            slug=profile.category.slug
        )
    
    return AnimalProfileResponse(
        id=profile.id,
        common_name=profile.common_name,
        scientific_name=profile.scientific_name,
        other_names=profile.other_names,
        category_id=profile.category_id,
        category=category_summary,
        kingdom=profile.kingdom,
        phylum=profile.phylum,
        class_name=profile.class_name,
        order=profile.order,
        family=profile.family,
        genus=profile.genus,
        species=profile.species,
        description=profile.description,
        physical_description=profile.physical_description,
        average_weight_kg=profile.average_weight_kg,
        average_length_cm=profile.average_length_cm,
        average_height_cm=profile.average_height_cm,
        lifespan_years=profile.lifespan_years,
        habitat_types=profile.habitat_types,
        geographic_distribution=profile.geographic_distribution,
        habitat_description=profile.habitat_description,
        diet_type=profile.diet_type,
        diet_description=profile.diet_description,
        behavior_description=profile.behavior_description,
        social_structure=profile.social_structure,
        conservation_status=profile.conservation_status,
        population_estimate=profile.population_estimate,
        conservation_threats=profile.conservation_threats,
        conservation_efforts=profile.conservation_efforts,
        profile_image_url=profile.profile_image_url,
        gallery_images=profile.gallery_images,
        featured_video_url=profile.featured_video_url,
        fun_facts=profile.fun_facts,
        cultural_significance=profile.cultural_significance,
        profile_metadata=profile.profile_metadata,
        view_count=profile.view_count,
        is_featured=profile.is_featured,
        is_active=profile.is_active,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.post("/", response_model=AnimalProfileResponse)
async def create_animal_profile(
    profile_data: AnimalProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new animal profile (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create animal profiles"
        )
    
    # Validate category if provided
    if profile_data.category_id:
        result = await db.execute(select(Category).where(Category.id == profile_data.category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    # Check for duplicate scientific name
    existing_result = await db.execute(
        select(AnimalProfile).where(AnimalProfile.scientific_name == profile_data.scientific_name)
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Animal profile with this scientific name already exists"
        )
    
    # Create profile
    profile = AnimalProfile(
        common_name=profile_data.common_name,
        scientific_name=profile_data.scientific_name,
        other_names=profile_data.other_names or [],
        category_id=profile_data.category_id,
        kingdom=profile_data.kingdom,
        phylum=profile_data.phylum,
        class_name=profile_data.class_name,
        order=profile_data.order,
        family=profile_data.family,
        genus=profile_data.genus,
        species=profile_data.species,
        description=profile_data.description,
        physical_description=profile_data.physical_description,
        average_weight_kg=profile_data.average_weight_kg,
        average_length_cm=profile_data.average_length_cm,
        average_height_cm=profile_data.average_height_cm,
        lifespan_years=profile_data.lifespan_years,
        habitat_types=profile_data.habitat_types or [],
        geographic_distribution=profile_data.geographic_distribution or [],
        habitat_description=profile_data.habitat_description,
        diet_type=profile_data.diet_type,
        diet_description=profile_data.diet_description,
        behavior_description=profile_data.behavior_description,
        social_structure=profile_data.social_structure,
        conservation_status=profile_data.conservation_status,
        population_estimate=profile_data.population_estimate,
        conservation_threats=profile_data.conservation_threats or [],
        conservation_efforts=profile_data.conservation_efforts,
        profile_image_url=profile_data.profile_image_url,
        gallery_images=profile_data.gallery_images or [],
        featured_video_url=profile_data.featured_video_url,
        fun_facts=profile_data.fun_facts or [],
        cultural_significance=profile_data.cultural_significance,
        profile_metadata=profile_data.profile_metadata or {},
        is_featured=profile_data.is_featured,
        is_active=profile_data.is_active
    )
    
    db.add(profile)
    await db.commit()
    await db.refresh(profile, ["category"])
    
    # Prepare response with category
    category_summary = None
    if profile.category:
        category_summary = CategorySummary(
            id=profile.category.id,
            name=profile.category.name,
            slug=profile.category.slug
        )
    
    return AnimalProfileResponse(
        id=profile.id,
        common_name=profile.common_name,
        scientific_name=profile.scientific_name,
        other_names=profile.other_names,
        category_id=profile.category_id,
        category=category_summary,
        kingdom=profile.kingdom,
        phylum=profile.phylum,
        class_name=profile.class_name,
        order=profile.order,
        family=profile.family,
        genus=profile.genus,
        species=profile.species,
        description=profile.description,
        physical_description=profile.physical_description,
        average_weight_kg=profile.average_weight_kg,
        average_length_cm=profile.average_length_cm,
        average_height_cm=profile.average_height_cm,
        lifespan_years=profile.lifespan_years,
        habitat_types=profile.habitat_types,
        geographic_distribution=profile.geographic_distribution,
        habitat_description=profile.habitat_description,
        diet_type=profile.diet_type,
        diet_description=profile.diet_description,
        behavior_description=profile.behavior_description,
        social_structure=profile.social_structure,
        conservation_status=profile.conservation_status,
        population_estimate=profile.population_estimate,
        conservation_threats=profile.conservation_threats,
        conservation_efforts=profile.conservation_efforts,
        profile_image_url=profile.profile_image_url,
        gallery_images=profile.gallery_images,
        featured_video_url=profile.featured_video_url,
        fun_facts=profile.fun_facts,
        cultural_significance=profile.cultural_significance,
        profile_metadata=profile.profile_metadata,
        view_count=profile.view_count,
        is_featured=profile.is_featured,
        is_active=profile.is_active,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.put("/{profile_id}", response_model=AnimalProfileResponse)
async def update_animal_profile(
    profile_id: UUID,
    profile_data: AnimalProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update animal profile (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update animal profiles"
        )
    
    result = await db.execute(
        select(AnimalProfile)
        .options(selectinload(AnimalProfile.category))
        .where(AnimalProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal profile not found"
        )
    
    # Update fields
    update_data = profile_data.dict(exclude_unset=True)
    
    # Validate category if being updated
    if 'category_id' in update_data and update_data['category_id']:
        result = await db.execute(select(Category).where(Category.id == update_data['category_id']))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    # Check for duplicate scientific name if being updated
    if 'scientific_name' in update_data and update_data['scientific_name'] != profile.scientific_name:
        existing_result = await db.execute(
            select(AnimalProfile).where(
                and_(
                    AnimalProfile.scientific_name == update_data['scientific_name'],
                    AnimalProfile.id != profile_id
                )
            )
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Animal profile with this scientific name already exists"
            )
    
    for field, value in update_data.items():
        setattr(profile, field, value)
    
    await db.commit()
    await db.refresh(profile)
    
    # Prepare response with category
    category_summary = None
    if profile.category:
        category_summary = CategorySummary(
            id=profile.category.id,
            name=profile.category.name,
            slug=profile.category.slug
        )
    
    return AnimalProfileResponse(
        id=profile.id,
        common_name=profile.common_name,
        scientific_name=profile.scientific_name,
        other_names=profile.other_names,
        category_id=profile.category_id,
        category=category_summary,
        kingdom=profile.kingdom,
        phylum=profile.phylum,
        class_name=profile.class_name,
        order=profile.order,
        family=profile.family,
        genus=profile.genus,
        species=profile.species,
        description=profile.description,
        physical_description=profile.physical_description,
        average_weight_kg=profile.average_weight_kg,
        average_length_cm=profile.average_length_cm,
        average_height_cm=profile.average_height_cm,
        lifespan_years=profile.lifespan_years,
        habitat_types=profile.habitat_types,
        geographic_distribution=profile.geographic_distribution,
        habitat_description=profile.habitat_description,
        diet_type=profile.diet_type,
        diet_description=profile.diet_description,
        behavior_description=profile.behavior_description,
        social_structure=profile.social_structure,
        conservation_status=profile.conservation_status,
        population_estimate=profile.population_estimate,
        conservation_threats=profile.conservation_threats,
        conservation_efforts=profile.conservation_efforts,
        profile_image_url=profile.profile_image_url,
        gallery_images=profile.gallery_images,
        featured_video_url=profile.featured_video_url,
        fun_facts=profile.fun_facts,
        cultural_significance=profile.cultural_significance,
        profile_metadata=profile.profile_metadata,
        view_count=profile.view_count,
        is_featured=profile.is_featured,
        is_active=profile.is_active,
        created_at=profile.created_at,
        updated_at=profile.updated_at
    )


@router.delete("/{profile_id}")
async def delete_animal_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete animal profile (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete animal profiles"
        )
    
    result = await db.execute(select(AnimalProfile).where(AnimalProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal profile not found"
        )
    
    await db.delete(profile)
    await db.commit()
    
    return {"message": "Animal profile deleted successfully"}


@router.post("/{profile_id}/favorite")
async def toggle_favorite_animal(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Toggle favorite status for an animal profile"""
    
    # Check if profile exists
    profile_result = await db.execute(select(AnimalProfile).where(AnimalProfile.id == profile_id))
    profile = profile_result.scalar_one_or_none()
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Animal profile not found"
        )
    
    # Check if interaction exists
    interaction_result = await db.execute(
        select(UserAnimalInteraction).where(
            and_(
                UserAnimalInteraction.user_id == current_user.id,
                UserAnimalInteraction.animal_profile_id == profile_id
            )
        )
    )
    interaction = interaction_result.scalar_one_or_none()
    
    if interaction:
        # Toggle favorite status
        interaction.is_favorite = not interaction.is_favorite
        interaction.favorited_at = datetime.utcnow() if interaction.is_favorite else None
        action = "added to" if interaction.is_favorite else "removed from"
    else:
        # Create new interaction with favorite status
        interaction = UserAnimalInteraction(
            user_id=current_user.id,
            animal_profile_id=profile_id,
            is_favorite=True,
            favorited_at=datetime.utcnow()
        )
        db.add(interaction)
        action = "added to"
    
    await db.commit()
    
    return {
        "message": f"Animal {action} favorites",
        "is_favorite": interaction.is_favorite
    }


@router.get("/user/favorites", response_model=List[AnimalProfileListResponse])
async def get_user_favorite_animals(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's favorite animal profiles"""
    
    result = await db.execute(
        select(AnimalProfile)
        .join(UserAnimalInteraction)
        .where(
            and_(
                UserAnimalInteraction.user_id == current_user.id,
                UserAnimalInteraction.is_favorite == True,
                AnimalProfile.is_active == True
            )
        )
        .order_by(desc(UserAnimalInteraction.favorited_at))
        .offset(skip)
        .limit(limit)
    )
    profiles = result.scalars().all()
    
    return [AnimalProfileListResponse(
        id=profile.id,
        common_name=profile.common_name,
        scientific_name=profile.scientific_name,
        profile_image_url=profile.profile_image_url,
        conservation_status=profile.conservation_status,
        habitat_types=profile.habitat_types,
        view_count=profile.view_count,
        is_featured=profile.is_featured,
        created_at=profile.created_at
    ) for profile in profiles]


@router.get("/stats/overview", response_model=AnimalStatsResponse)
async def get_animal_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get animal statistics (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view animal statistics"
        )
    
    # Get total counts
    total_result = await db.execute(select(func.count(AnimalProfile.id)))
    total_profiles = total_result.scalar()
    
    featured_result = await db.execute(
        select(func.count(AnimalProfile.id)).where(AnimalProfile.is_featured == True)
    )
    featured_profiles = featured_result.scalar()
    
    # Get sightings count
    sightings_result = await db.execute(select(func.count(AnimalSighting.id)))
    total_sightings = sightings_result.scalar()
    
    # Get most viewed animals
    most_viewed_result = await db.execute(
        select(AnimalProfile)
        .where(AnimalProfile.is_active == True)
        .order_by(desc(AnimalProfile.view_count))
        .limit(5)
    )
    most_viewed = most_viewed_result.scalars().all()
    
    # Get recently added
    recent_result = await db.execute(
        select(AnimalProfile)
        .where(AnimalProfile.is_active == True)
        .order_by(desc(AnimalProfile.created_at))
        .limit(5)
    )
    recently_added = recent_result.scalars().all()
    
    return AnimalStatsResponse(
        total_profiles=total_profiles,
        featured_profiles=featured_profiles,
        by_conservation_status={},  # TODO: Implement detailed stats
        by_habitat_type={},  # TODO: Implement detailed stats
        most_viewed=[AnimalProfileListResponse(
            id=profile.id,
            common_name=profile.common_name,
            scientific_name=profile.scientific_name,
            profile_image_url=profile.profile_image_url,
            conservation_status=profile.conservation_status,
            habitat_types=profile.habitat_types,
            view_count=profile.view_count,
            is_featured=profile.is_featured,
            created_at=profile.created_at
        ) for profile in most_viewed],
        recently_added=[AnimalProfileListResponse(
            id=profile.id,
            common_name=profile.common_name,
            scientific_name=profile.scientific_name,
            profile_image_url=profile.profile_image_url,
            conservation_status=profile.conservation_status,
            habitat_types=profile.habitat_types,
            view_count=profile.view_count,
            is_featured=profile.is_featured,
            created_at=profile.created_at
        ) for profile in recently_added],
        total_sightings=total_sightings
    )


# Animal Sighting endpoints
@router.post("/sightings", response_model=AnimalSightingResponse)
async def create_animal_sighting(
    sighting_data: AnimalSightingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new animal sighting"""
    
    # Validate animal profile if provided
    if sighting_data.animal_profile_id:
        profile_result = await db.execute(
            select(AnimalProfile).where(AnimalProfile.id == sighting_data.animal_profile_id)
        )
        if not profile_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid animal profile ID"
            )
    
    sighting = AnimalSighting(
        user_id=current_user.id,
        animal_profile_id=sighting_data.animal_profile_id,
        title=sighting_data.title,
        description=sighting_data.description,
        location_name=sighting_data.location_name,
        latitude=sighting_data.latitude,
        longitude=sighting_data.longitude,
        country=sighting_data.country,
        sighting_date=sighting_data.sighting_date,
        photo_urls=sighting_data.photo_urls or []
    )
    
    db.add(sighting)
    await db.commit()
    await db.refresh(sighting)
    
    return AnimalSightingResponse(
        id=sighting.id,
        user_id=sighting.user_id,
        animal_profile_id=sighting.animal_profile_id,
        title=sighting.title,
        description=sighting.description,
        location_name=sighting.location_name,
        latitude=sighting.latitude,
        longitude=sighting.longitude,
        country=sighting.country,
        sighting_date=sighting.sighting_date,
        photo_urls=sighting.photo_urls,
        is_verified=sighting.is_verified,
        verification_notes=sighting.verification_notes,
        created_at=sighting.created_at,
        updated_at=sighting.updated_at
    )


@router.get("/sightings", response_model=List[AnimalSightingResponse])
async def get_animal_sightings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    animal_profile_id: Optional[UUID] = Query(None, description="Filter by animal profile"),
    verified_only: bool = Query(False, description="Show only verified sightings"),
    db: AsyncSession = Depends(get_db)
):
    """Get animal sightings with filtering"""
    
    query = select(AnimalSighting)
    
    if animal_profile_id:
        query = query.where(AnimalSighting.animal_profile_id == animal_profile_id)
    
    if verified_only:
        query = query.where(AnimalSighting.is_verified == True)
    
    query = query.offset(skip).limit(limit).order_by(desc(AnimalSighting.sighting_date))
    
    result = await db.execute(query)
    sightings = result.scalars().all()
    
    return [AnimalSightingResponse(
        id=sighting.id,
        user_id=sighting.user_id,
        animal_profile_id=sighting.animal_profile_id,
        title=sighting.title,
        description=sighting.description,
        location_name=sighting.location_name,
        latitude=sighting.latitude,
        longitude=sighting.longitude,
        country=sighting.country,
        sighting_date=sighting.sighting_date,
        photo_urls=sighting.photo_urls,
        is_verified=sighting.is_verified,
        verification_notes=sighting.verification_notes,
        created_at=sighting.created_at,
        updated_at=sighting.updated_at
    ) for sighting in sightings]
