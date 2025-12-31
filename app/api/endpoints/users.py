"""
User management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.models.user import User
from app.models.content import Content
from app.models import UserQuizResult
from app.models.animal_profile import UserAnimalInteraction
from app.schemas.user import UserResponse, UserUpdate, UserProfile
from app.core.security import get_current_user_optional
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserProfile)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's profile with statistics"""
    
    # Get user's content count
    content_count_result = await db.execute(
        select(func.count(Content.id)).where(Content.author_id == current_user.id)
    )
    content_count = content_count_result.scalar()
    
    # Get user's quiz results count
    quiz_count_result = await db.execute(
        select(func.count(UserQuizResult.id)).where(UserQuizResult.user_id == current_user.id)
    )
    quiz_results_count = quiz_count_result.scalar()
    
    # Get user's favorite animals count
    favorite_animals_result = await db.execute(
        select(func.count(UserAnimalInteraction.id)).where(
            UserAnimalInteraction.user_id == current_user.id,
            UserAnimalInteraction.is_favorite == True
        )
    )
    favorite_animals_count = favorite_animals_result.scalar()
    
    return UserProfile(
        id=str(current_user.id),
        email=current_user.email,
        username=current_user.username,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        followers_count=0,  # TODO: Implement follower system
        following_count=0,  # TODO: Implement following system
        content_count=content_count,
        quiz_results_count=quiz_results_count,
        # Include currency information
        points_balance=current_user.points_balance or 0,
        credits_balance=current_user.credits_balance or 0,
        total_points_earned=current_user.total_points_earned or 0,
        total_credits_earned=current_user.total_credits_earned or 0
    )


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update current user's profile"""
    
    try:
        # Get the current user ID to avoid session conflicts
        user_id = current_user.id
        
        # Fetch the user from the database to ensure it's attached to the current session
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update user fields
        for field, value in user_update.dict(exclude_unset=True).items():
            setattr(user, field, value)
        
        # Prepare response data before committing
        response_data = UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
        await db.commit()
        
        return response_data
    
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user profile"
        )


@router.get("/{user_id}", response_model=UserProfile)
async def get_user_profile(
    user_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get user profile by ID with statistics"""
    
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get user's content count
    content_count_result = await db.execute(
        select(func.count(Content.id)).where(Content.author_id == user.id)
    )
    content_count = content_count_result.scalar()
    
    # Get user's quiz results count
    quiz_count_result = await db.execute(
        select(func.count(UserQuizResult.id)).where(UserQuizResult.user_id == user.id)
    )
    quiz_results_count = quiz_count_result.scalar()
    
    return UserProfile(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        gender=user.gender,
        country=user.country,
        language=user.language,
        occupation=user.occupation,
        favorite_species=user.favorite_species,
        expertise=user.expertise,
        bio=user.bio,
        social_links=user.social_links or {},
        interests=user.interests or [],
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        followers_count=0,  # TODO: Implement follower system
        following_count=0,  # TODO: Implement following system
        content_count=content_count,
        quiz_results_count=quiz_results_count
    )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search in name, username, and bio"),
    country: Optional[str] = Query(None, description="Filter by country"),
    expertise: Optional[str] = Query(None, description="Filter by expertise"),
    db: AsyncSession = Depends(get_db)
):
    """List users with filtering and search"""
    
    query = select(User).where(User.is_active == True)
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        query = query.where(
            User.username.ilike(search_term)
        )
    
    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        ) for user in users
    ]


@router.get("/me/activity", response_model=dict)
async def get_user_activity(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's activity summary"""
    
    # Get recent content
    recent_content = await db.execute(
        select(Content)
        .where(Content.author_id == current_user.id)
        .order_by(desc(Content.created_at))
        .limit(5)
    )
    content_list = recent_content.scalars().all()
    
    # Get recent quiz results
    recent_quizzes = await db.execute(
        select(UserQuizResult)
        .where(UserQuizResult.user_id == current_user.id)
        .order_by(desc(UserQuizResult.completed_at))
        .limit(5)
    )
    quiz_list = recent_quizzes.scalars().all()
    
    # Get favorite animals
    favorite_animals = await db.execute(
        select(UserAnimalInteraction)
        .where(
            UserAnimalInteraction.user_id == current_user.id,
            UserAnimalInteraction.is_favorite == True
        )
        .order_by(desc(UserAnimalInteraction.favorited_at))
        .limit(10)
    )
    favorites_list = favorite_animals.scalars().all()
    
    return {
        "recent_content": [
            {
                "id": str(content.id),
                "title": content.title,
                "type": content.type,
                "created_at": content.created_at,
                "view_count": content.view_count
            } for content in content_list
        ],
        "recent_quiz_results": [
            {
                "id": str(quiz.id),
                "quiz_id": str(quiz.quiz_id),
                "score": quiz.score,
                "max_score": quiz.max_score,
                "percentage": quiz.percentage,
                "completed_at": quiz.completed_at
            } for quiz in quiz_list
        ],
        "favorite_animals": [
            {
                "id": str(fav.id),
                "animal_profile_id": str(fav.animal_profile_id),
                "favorited_at": fav.favorited_at,
                "view_count": fav.view_count
            } for fav in favorites_list
        ]
    }


@router.get("/search", response_model=List[UserResponse])
async def search_users(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Search users by name, username, or expertise"""
    
    search_term = f"%{q}%"
    result = await db.execute(
        select(User)
        .where(
            User.is_active == True,
            or_(
                User.full_name.ilike(search_term),
                User.username.ilike(search_term),
                User.expertise.ilike(search_term),
                User.bio.ilike(search_term)
            )
        )
        .limit(limit)
        .order_by(User.full_name)
    )
    users = result.scalars().all()
    
    return [
        UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            username=user.username,
            gender=user.gender,
            country=user.country,
            language=user.language,
            occupation=user.occupation,
            favorite_species=user.favorite_species,
            expertise=user.expertise,
            bio=user.bio,
            social_links=user.social_links or {},
            interests=user.interests or [],
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at
        ) for user in users
    ]
