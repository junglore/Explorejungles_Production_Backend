"""
Myths & Facts API Routes

This module provides comprehensive REST API endpoints for managing wildlife myths and facts content.
It includes full CRUD operations, pagination, filtering, and specialized endpoints for frontend
game integration with robust error handling and validation.

Key Features:
- Full CRUD operations for myth/fact entries
- Pagination and filtering support
- Admin-only operations with proper authorization
- Frontend-optimized endpoints with fallback handling
- Comprehensive error handling and logging
- Database relationship management with categories

Endpoints:
- GET /: List myths/facts with pagination and filters
- POST /: Create new myth/fact (admin only)
- GET /{id}: Get specific myth/fact by ID
- PUT /{id}: Update myth/fact (admin only)
- DELETE /{id}: Delete myth/fact (admin only)
- GET /resources/myths: Frontend-optimized list endpoint
- GET /resources/random7: Get 7 random entries for game

Author: Junglore Development Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from app.models.rewards import CurrencyTypeEnum, ActivityTypeEnum
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from typing import List, Optional
from uuid import UUID
import structlog

from app.db.database import get_db, get_db_with_retry
from app.models.myth_fact import MythFact
from app.models.user import User
from app.models.category import Category
from app.core.security import get_current_user
from app.schemas.myth_fact import (
    MythFactCreate,
    MythFactUpdate,
    MythFactResponse,
    MythFactListResponse,
    MythFactGameResponse,
    PaginationParams,
    ErrorResponse,
    SuccessResponse
)
from app.services.rewards_service import rewards_service
from app.services.anti_gaming_service import anti_gaming_service

logger = structlog.get_logger()
router = APIRouter()


@router.get("/", response_model=MythFactListResponse)
async def get_myths_facts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    featured_only: bool = Query(False, description="Filter for featured items only"),
    category_id: Optional[UUID] = Query(None, description="Filter by category ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve a paginated list of myths and facts with optional filtering.
    
    This endpoint provides comprehensive listing functionality with support for:
    - Pagination to handle large datasets efficiently
    - Featured content filtering for promotional content
    - Category-based filtering for content organization
    - Eager loading of category relationships for performance
    
    Args:
        page (int): Page number starting from 1. Defaults to 1.
        limit (int): Number of items per page, maximum 50. Defaults to 10.
        featured_only (bool): If True, only returns featured content. Defaults to False.
        category_id (UUID, optional): Filter results by specific category ID.
        db (AsyncSession): Database session dependency.
    
    Returns:
        MythFactListResponse: Paginated response containing:
            - items: List of myth/fact entries with full details
            - pagination: Metadata including total count, pages, current page
    
    Raises:
        HTTPException: 500 for database errors or unexpected failures
        
    Example:
        GET /api/v1/myths-facts/?page=1&limit=20&featured_only=true
    """
    try:
        offset = (page - 1) * limit
        
        # Build query with filters
        query = select(MythFact).options(
            # Eager load category relationship
            selectinload(MythFact.category)
        )
        
        # Apply filters
        filters = []
        if featured_only:
            filters.append(MythFact.is_featured == True)
        if category_id:
            filters.append(MythFact.category_id == category_id)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Apply ordering and pagination
        query = query.order_by(desc(MythFact.created_at)).offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        items = result.scalars().all()
        
        # Get total count with same filters
        count_query = select(func.count(MythFact.id))
        if filters:
            count_query = count_query.where(and_(*filters))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Transform to response format
        response_items = []
        for item in items:
            response_items.append(MythFactResponse(
                id=item.id,
                title=item.title,
                myth_statement=item.myth_content,
                fact_explanation=item.fact_content,
                category=item.category.name if item.category else None,
                image_url=item.image_url,
                created_at=item.created_at,
                is_featured=item.is_featured,
                type=item.type  # ✅ Include card type
            ))
        
        return MythFactListResponse(
            items=response_items,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if total > 0 else 0,
            }
        )
        
    except SQLAlchemyError as e:
        logger.error("Database error in get_myths_facts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching myths and facts"
        )
    except Exception as e:
        logger.error("Unexpected error in get_myths_facts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_myth_fact(
    myth_fact_data: MythFactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a new myth vs fact entry with admin authorization.
    
    This endpoint allows administrators to create new educational content entries.
    It includes comprehensive validation for:
    - User authorization (admin only)
    - Category existence validation
    - Data integrity constraints
    - Proper database transaction handling
    
    Args:
        myth_fact_data (MythFactCreate): Validated input data containing:
            - title: Entry title (required, max 500 chars)
            - myth_content: The myth statement (required)
            - fact_content: The factual explanation (required)
            - category_id: Optional category association
            - custom_points: Optional custom points for this card (overrides base)
            - image_url: Optional supporting image URL
            - is_featured: Featured status flag
        db (AsyncSession): Database session dependency.
        current_user (User): Authenticated user from JWT token.
    
    Returns:
        SuccessResponse: Confirmation with created entry ID.
    
    Raises:
        HTTPException: 
            - 403 if user is not admin
            - 400 if category doesn't exist or data integrity error
            - 500 for database errors
            
    Example:
        POST /api/v1/myths-facts/
        {
            "title": "Snake Behavior Myth",
            "myth_content": "All snakes are dangerous",
            "fact_content": "Most snakes are harmless...",
            "is_featured": true
        }
    """
    try:
        # Check admin privileges
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can create myth vs fact entries"
            )
        
        # Validate category exists if provided
        if myth_fact_data.category_id:
            category_result = await db.execute(
                select(Category).where(Category.id == myth_fact_data.category_id)
            )
            if not category_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with ID {myth_fact_data.category_id} does not exist"
                )
        
        # Create new myth fact
        myth_fact = MythFact(
            title=myth_fact_data.title,
            myth_content=myth_fact_data.myth_content,
            fact_content=myth_fact_data.fact_content,
            image_url=myth_fact_data.image_url,
            category_id=myth_fact_data.category_id,
            custom_points=myth_fact_data.custom_points,
            is_featured=myth_fact_data.is_featured,
        )
        
        db.add(myth_fact)
        await db.commit()
        await db.refresh(myth_fact)
        
        logger.info("Created new myth fact", myth_fact_id=str(myth_fact.id), user_id=str(current_user.id))
        
        return SuccessResponse(
            message="Myth vs fact entry created successfully",
            data={"id": str(myth_fact.id)}
        )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error("Integrity error creating myth fact", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data integrity error - check for duplicate entries or invalid references"
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error creating myth fact", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while creating myth vs fact entry"
        )
    except Exception as e:
        await db.rollback()
        logger.error("Unexpected error creating myth fact", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/{myth_fact_id}", response_model=MythFactResponse)
async def get_myth_fact(
    myth_fact_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific myth vs fact entry by ID
    """
    try:
        result = await db.execute(
            select(MythFact).options(
                selectinload(MythFact.category)
            ).where(MythFact.id == myth_fact_id)
        )
        myth_fact = result.scalar_one_or_none()
        
        if not myth_fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Myth vs fact entry with ID {myth_fact_id} not found"
            )
        
        return MythFactResponse(
            id=myth_fact.id,
            title=myth_fact.title,
            myth_statement=myth_fact.myth_content,
            fact_explanation=myth_fact.fact_content,
            category=myth_fact.category.name if myth_fact.category else None,
            image_url=myth_fact.image_url,
            created_at=myth_fact.created_at,
            is_featured=myth_fact.is_featured
        )
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error("Database error getting myth fact", myth_fact_id=str(myth_fact_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while fetching myth vs fact entry"
        )
    except Exception as e:
        logger.error("Unexpected error getting myth fact", myth_fact_id=str(myth_fact_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.put("/{myth_fact_id}", response_model=SuccessResponse)
async def update_myth_fact(
    myth_fact_id: UUID,
    myth_fact_data: MythFactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a myth vs fact entry (Admin only)
    """
    try:
        # Check admin privileges
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can update myth vs fact entries"
            )
        
        # Get existing myth fact
        result = await db.execute(
            select(MythFact).where(MythFact.id == myth_fact_id)
        )
        myth_fact = result.scalar_one_or_none()
        
        if not myth_fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Myth vs fact entry with ID {myth_fact_id} not found"
            )
        
        # Validate category exists if provided
        if myth_fact_data.category_id:
            category_result = await db.execute(
                select(Category).where(Category.id == myth_fact_data.category_id)
            )
            if not category_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with ID {myth_fact_data.category_id} does not exist"
                )
        
        # Update fields that are provided
        update_data = myth_fact_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            if field == 'myth_content':
                setattr(myth_fact, 'myth_content', value)
            elif field == 'fact_content':
                setattr(myth_fact, 'fact_content', value)
            else:
                setattr(myth_fact, field, value)
        
        await db.commit()
        await db.refresh(myth_fact)
        
        logger.info("Updated myth fact", myth_fact_id=str(myth_fact_id), user_id=str(current_user.id))
        
        return SuccessResponse(
            message="Myth vs fact entry updated successfully",
            data={"id": str(myth_fact.id)}
        )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        logger.error("Integrity error updating myth fact", myth_fact_id=str(myth_fact_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data integrity error - check for invalid references"
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error updating myth fact", myth_fact_id=str(myth_fact_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while updating myth vs fact entry"
        )
    except Exception as e:
        await db.rollback()
        logger.error("Unexpected error updating myth fact", myth_fact_id=str(myth_fact_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.delete("/{myth_fact_id}", response_model=SuccessResponse)
async def delete_myth_fact(
    myth_fact_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a myth vs fact entry (Admin only)
    """
    try:
        # Check admin privileges
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only administrators can delete myth vs fact entries"
            )
        
        # Get existing myth fact
        result = await db.execute(
            select(MythFact).where(MythFact.id == myth_fact_id)
        )
        myth_fact = result.scalar_one_or_none()
        
        if not myth_fact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Myth vs fact entry with ID {myth_fact_id} not found"
            )
        
        await db.delete(myth_fact)
        await db.commit()
        
        logger.info("Deleted myth fact", myth_fact_id=str(myth_fact_id), user_id=str(current_user.id))
        
        return SuccessResponse(
            message="Myth vs fact entry deleted successfully",
            data={"id": str(myth_fact_id)}
        )
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error deleting myth fact", myth_fact_id=str(myth_fact_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while deleting myth vs fact entry"
        )
    except Exception as e:
        await db.rollback()
        logger.error("Unexpected error deleting myth fact", myth_fact_id=str(myth_fact_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )


@router.get("/resources/myths", response_model=MythFactListResponse)
async def get_myths_for_frontend(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=50, description="Items per page"),
    featured_only: bool = Query(False, description="Filter for featured items only"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get published myths vs facts for frontend with enhanced error handling
    
    This endpoint is optimized for frontend consumption with proper fallback handling.
    """
    try:
        offset = (page - 1) * limit
        
        # Build query
        query = select(MythFact).options(
            selectinload(MythFact.category)
        )
        
        if featured_only:
            query = query.where(MythFact.is_featured == True)
        
        query = query.order_by(desc(MythFact.created_at)).offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        myths = result.scalars().all()
        
        # Get total count
        count_query = select(func.count(MythFact.id))
        if featured_only:
            count_query = count_query.where(MythFact.is_featured == True)
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        # Transform response
        response_items = []
        for myth in myths:
            response_items.append(MythFactResponse(
                id=myth.id,
                title=myth.title,
                myth_statement=myth.myth_content,
                fact_explanation=myth.fact_content,
                category=myth.category.name if myth.category else None,
                image_url=myth.image_url,
                created_at=myth.created_at,
                is_featured=myth.is_featured,
                type=myth.type  # ✅ Include card type
            ))
        
        return MythFactListResponse(
            items=response_items,
            pagination={
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit if total > 0 else 0,
            }
        )
        
    except SQLAlchemyError as e:
        logger.error("Database error in get_myths_for_frontend", error=str(e))
        # Return empty result instead of error for frontend resilience
        return MythFactListResponse(
            items=[],
            pagination={
                "page": page,
                "limit": limit,
                "total": 0,
                "pages": 0,
            }
        )
    except Exception as e:
        logger.error("Unexpected error in get_myths_for_frontend", error=str(e))
        # Return empty result instead of error for frontend resilience
        return MythFactListResponse(
            items=[],
            pagination={
                "page": page,
                "limit": limit,
                "total": 0,
                "pages": 0,
            }
        )


@router.get("/resources/random7", response_model=List[MythFactGameResponse])
async def get_random_seven_myths(
    category_id: Optional[UUID] = Query(None, description="Category ID to get cards from"),
    db: AsyncSession = Depends(get_db)
):
    """
    Return 7 random myths/facts entries for game interface
    
    This endpoint is optimized for the game interface with fallback handling.
    Now supports category-based card selection.
    """
    try:
        # Build query
        query = select(MythFact)
        
        # Filter by category if provided
        if category_id:
            query = query.where(MythFact.category_id == category_id)
        
        # Using func.random() for PostgreSQL compatibility
        result = await db.execute(
            query.order_by(func.random()).limit(7)
        )
        myths = result.scalars().all()
        
        # If category filter was applied but no cards found, fall back to random from all categories
        if category_id and len(myths) == 0:
            result = await db.execute(
                select(MythFact).order_by(func.random()).limit(7)
            )
            myths = result.scalars().all()
        
        # Transform to game response format
        game_responses = []
        for myth in myths:
            game_responses.append(MythFactGameResponse(
                id=myth.id,
                title=myth.title,
                myth_statement=myth.myth_content,
                fact_explanation=myth.fact_content,
                image_url=myth.image_url,
                is_featured=myth.is_featured,
                type=myth.type  # ✅ NEW: Include card type to control frontend display
            ))
        
        return game_responses
        
    except SQLAlchemyError as e:
        logger.error("Database error in get_random_seven_myths", error=str(e))
        # Return empty list for graceful frontend handling
        return []
    except Exception as e:
        logger.error("Unexpected error in get_random_seven_myths", error=str(e))
        # Return empty list for graceful frontend handling
        return []


@router.post("/game/complete", response_model=SuccessResponse)
async def complete_myths_facts_game(
    game_data: dict,  # Will include score, time_taken, answers_correct, etc.
    db: AsyncSession = Depends(get_db_with_retry),  # Use retry for critical endpoint
    current_user: User = Depends(get_current_user)
):
    """
    Process myths vs facts game completion with rewards
    
    Args:
        game_data: Dictionary containing:
            - score_percentage: int (0-100)
            - time_taken: Optional[int] (seconds)
            - answers_correct: int
            - total_questions: int
            - category_id: Optional[UUID] for category-based games
            - card_ids: Optional[List[UUID]] for card-level point overrides
            - game_session_id: Optional[UUID] for tracking
    """
    try:
                # Validate input data
        score_percentage = game_data.get("score_percentage", 0)
        time_taken = game_data.get("time_taken")
        answers_correct = game_data.get("answers_correct", 0)
        total_questions = game_data.get("total_questions", 7)
        category_id = game_data.get("category_id")  # New: category for overrides
        card_ids = game_data.get("card_ids", [])  # New: specific cards played for custom points        # Generate a session ID if not provided
        import uuid
        game_session_id = game_data.get("game_session_id", str(uuid.uuid4()))
        
        # Validate score percentage
        if not (0 <= score_percentage <= 100):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score percentage must be between 0 and 100"
            )
        
        # Anti-gaming analysis (with fallback if service unavailable)
        try:
            gaming_analysis = await anti_gaming_service.analyze_myths_facts_completion(
                db=db,
                user_id=current_user.id,
                game_session_id=UUID(game_session_id),
                time_taken=time_taken,
                score_percentage=score_percentage
            )
        except Exception as e:
            logger.warning(
                "Anti-gaming service unavailable, proceeding with rewards",
                user_id=str(current_user.id),
                error=str(e)
            )
            gaming_analysis = {
                "allow_rewards": True,
                "risk_score": 0.0,
                "is_flagged": False
            }
        
        reward_result = None
        
        # Process rewards if not flagged for gaming
        if gaming_analysis.get("allow_rewards", True):
            try:
                # Simplified reward calculation for myths vs facts
                from app.services.currency_service import currency_service
                from app.services.settings_service import SettingsService
                
                # Check for pure scoring mode
                settings = SettingsService(db)
                pure_scoring_mode = await settings.get_bool('pure_scoring_mode', False)
                
                # Get base rewards from admin settings
                base_points_per_card = await settings.get_int('mvf_base_points_per_card', 50)
                base_credits_per_game = await settings.get_int('mvf_base_credits_per_game', 5)
                cards_per_game = await settings.get_int('mvf_cards_per_game', 7)
                
                # Check for category-based overrides
                category_credits_override = None
                if category_id:
                    from app.models.category import Category
                    category_result = await db.execute(
                        select(Category).where(Category.id == category_id)
                    )
                    category = category_result.scalar_one_or_none()
                    if category and category.custom_credits:
                        category_credits_override = category.custom_credits
                
                # Calculate rewards based on user's logic with hierarchy:
                # Credits: Category override → Base settings
                # Points: Card custom points → Base settings
                
                # Credits for completion (use category override if available)
                base_credits = category_credits_override if category_credits_override is not None else base_credits_per_game
                
                # Points calculation with card-level overrides
                if card_ids and len(card_ids) > 0:
                    # Calculate points based on individual card custom_points
                    from app.models.myth_fact import MythFact
                    from sqlalchemy import or_
                    card_query = select(MythFact).where(MythFact.id.in_(card_ids))
                    card_result = await db.execute(card_query)
                    cards = card_result.scalars().all()
                    
                    total_card_points = 0
                    for card in cards:
                        # Use card's custom_points if set, otherwise use base_points_per_card
                        card_points = card.custom_points if card.custom_points is not None else base_points_per_card
                        total_card_points += card_points
                    
                    # Apply accuracy multiplier to total card points
                    accuracy_percentage = answers_correct / total_questions if total_questions > 0 else 0
                    base_points = int(accuracy_percentage * total_card_points)
                else:
                    # Fallback to old calculation if no card IDs provided
                    accuracy_percentage = answers_correct / total_questions if total_questions > 0 else 0
                    base_points = int(accuracy_percentage * base_points_per_card * cards_per_game)
                
                # Determine tier based on accuracy for bonuses and categorization
                if score_percentage >= 95:
                    tier = "platinum"
                elif score_percentage >= 85:
                    tier = "gold"
                elif score_percentage >= 75:
                    tier = "silver"
                elif score_percentage >= 50:
                    tier = "bronze"
                else:
                    tier = "no_reward"
                
                # Apply bonuses only if pure scoring mode is disabled
                time_bonus_points = 0
                time_bonus_credits = 0
                perfect_bonus_points = 0
                perfect_bonus_credits = 0
                
                if not pure_scoring_mode:
                    # Apply time bonus (if completed in under 2 minutes) - bonus on accuracy-based points and completion credits
                    if time_taken and time_taken < 120:
                        time_bonus_points = int(base_points * 0.3)  # 30% bonus on accuracy points
                        time_bonus_credits = int(base_credits * 0.3)  # 30% bonus on completion credits
                    
                    # Apply perfect accuracy bonus - only if 100% correct
                    if score_percentage == 100:
                        perfect_bonus_points = int(base_points * 0.25)  # 25% bonus on accuracy points
                        perfect_bonus_credits = int(base_credits * 0.25)  # 25% bonus on completion credits
                
                total_points = base_points + time_bonus_points + perfect_bonus_points
                total_credits = base_credits + time_bonus_credits + perfect_bonus_credits
                
                # Award the rewards using currency service
                if total_credits > 0:
                    await currency_service.add_currency(
                        db=db,
                        user_id=current_user.id,
                        currency_type=CurrencyTypeEnum.CREDITS,
                        amount=total_credits,
                        activity_type=ActivityTypeEnum.MYTHS_FACTS_GAME,
                        transaction_metadata={
                            "tier": tier,
                            "score_percentage": score_percentage,
                            "time_taken": time_taken,
                            "category_id": str(category_id) if category_id else None
                        }
                    )
                
                reward_result = {
                    "points_earned": total_points,
                    "credits_earned": total_credits,
                    "reward_tier": tier,
                    "time_bonus_applied": time_bonus_points > 0,
                    "perfect_accuracy": score_percentage == 100,
                    "metadata": {
                        "base_points": base_points,
                        "base_credits": base_credits,
                        "category_credits_override": category_credits_override,
                        "card_ids_used": len(card_ids) if card_ids else 0,
                        "time_bonus_points": time_bonus_points,
                        "time_bonus_credits": time_bonus_credits,
                        "perfect_bonus_points": perfect_bonus_points,
                        "perfect_bonus_credits": perfect_bonus_credits,
                        "pure_scoring_mode": pure_scoring_mode
                    }
                }
                
            except Exception as e:
                logger.error(
                    "Error processing myths facts rewards",
                    user_id=str(current_user.id),
                    error=str(e)
                )
                # Continue without rewards rather than failing
                reward_result = None
            
            # CRITICAL FIX: Commit the reward transactions to database
            await db.commit()
            
        else:
            logger.warning(
                "Myths vs facts game rewards blocked due to gaming detection",
                user_id=str(current_user.id),
                game_session_id=game_session_id,
                risk_score=gaming_analysis.get("risk_score", 0)
            )
        
        # Prepare response
        response_data = {
            "game_session_id": game_session_id,
            "score_percentage": score_percentage,
            "answers_correct": answers_correct,
            "total_questions": total_questions,
            "category_id": str(category_id) if category_id else None,
            "card_ids": [str(cid) for cid in card_ids] if card_ids else None,
            "gaming_analysis": {
                "risk_score": gaming_analysis.get("risk_score", 0),
                "is_flagged": gaming_analysis.get("is_flagged", False)
            }
        }
        
        if reward_result:
            response_data["rewards"] = {
                "points_earned": reward_result.get("points_earned", 0),
                "credits_earned": reward_result.get("credits_earned", 0),
                "tier": reward_result.get("reward_tier"),
                "bonus_applied": reward_result.get("time_bonus_applied", False) or reward_result.get("perfect_accuracy", False),
                "breakdown": {
                    "base_points": reward_result.get("metadata", {}).get("base_points", 0),
                    "base_credits": reward_result.get("metadata", {}).get("base_credits", 0),
                    "category_credits_override": reward_result.get("metadata", {}).get("category_credits_override"),
                    "time_bonus_points": reward_result.get("metadata", {}).get("time_bonus_points", 0),
                    "time_bonus_credits": reward_result.get("metadata", {}).get("time_bonus_credits", 0),
                    "perfect_bonus_points": reward_result.get("metadata", {}).get("perfect_bonus_points", 0),
                    "perfect_bonus_credits": reward_result.get("metadata", {}).get("perfect_bonus_credits", 0),
                    "time_bonus_applied": reward_result.get("time_bonus_applied", False),
                    "perfect_accuracy": reward_result.get("perfect_accuracy", False),
                    "pure_scoring_mode": reward_result.get("metadata", {}).get("pure_scoring_mode", False)
                }
            }
        
        return SuccessResponse(
            message="Myths vs facts game completed successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error processing myths facts game completion", 
            user_id=str(current_user.id), 
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing game completion"
        )


# Collection Integration Endpoint
@router.get("/available-for-collections", response_model=List[MythFactResponse])
async def get_myths_facts_for_collections(
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Search in title or content"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get myths & facts available for collection assignment.
    
    This endpoint provides a clean list of all myths & facts that can be assigned
    to collections, with optional filtering by category and search terms.
    
    Args:
        category_id: Optional UUID to filter by category
        search: Optional search term to filter by title or content
        limit: Maximum number of results to return (1-200)
        db: Database session dependency
        current_user: Current authenticated user
    
    Returns:
        List[MythFactResponse]: List of available myths & facts
    
    Raises:
        HTTPException: If database error occurs
    """
    try:
        # Build the query
        query = select(MythFact).options(selectinload(MythFact.category))
        
        # Apply category filter if provided
        if category_id:
            query = query.where(MythFact.category_id == category_id)
        
        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (MythFact.title.ilike(search_term)) |
                (MythFact.myth_content.ilike(search_term)) |
                (MythFact.fact_content.ilike(search_term))
            )
        
        # Apply limit and ordering
        query = query.order_by(MythFact.created_at.desc()).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        myths_facts = result.scalars().all()
        
        # Convert to response format
        response_list = []
        for myth_fact in myths_facts:
            response_item = MythFactResponse(
                id=myth_fact.id,
                title=myth_fact.title,
                myth_content=myth_fact.myth_content,
                fact_content=myth_fact.fact_content,
                image_url=myth_fact.image_url,
                video_url=myth_fact.video_url,
                category_id=myth_fact.category_id,
                category_name=myth_fact.category.name if myth_fact.category else None,
                is_active=myth_fact.is_active,
                created_at=myth_fact.created_at,
                updated_at=myth_fact.updated_at
            )
            response_list.append(response_item)
        
        logger.info(
            f"Retrieved {len(response_list)} myths & facts for collection assignment",
            user_id=str(current_user.id),
            category_id=str(category_id) if category_id else None,
            search_term=search,
            results_count=len(response_list)
        )
        
        return response_list
        
    except SQLAlchemyError as e:
        logger.error(
            "Database error retrieving myths & facts for collections",
            user_id=str(current_user.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while retrieving myths & facts"
        )
    except Exception as e:
        logger.error(
            "Unexpected error retrieving myths & facts for collections",
            user_id=str(current_user.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving myths & facts"
        )


@router.post("/collection/complete", response_model=SuccessResponse)
async def complete_collection_myths_facts(
    completion_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete a collection-based myths vs facts game with enhanced tracking
    
    This endpoint handles completion of collection-based M&F games with:
    - Collection progress tracking
    - Daily repeatability enforcement
    - Custom reward calculations (if collection has custom rewards)
    - Integration with existing reward system
    """
    try:
        logger.info(
            "Processing collection-based myths facts game completion",
            user_id=str(current_user.id),
            collection_id=completion_data.get('collection_id'),
            score=completion_data.get('score_percentage', 0)
        )
        
        # Extract completion data
        collection_id = completion_data.get('collection_id')
        score_percentage = completion_data.get('score_percentage', 0)
        answers_correct = completion_data.get('answers_correct', 0)
        total_questions = completion_data.get('total_questions', 0)
        time_taken = completion_data.get('time_taken')
        
        if not collection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="collection_id is required for collection-based games"
            )
        
        # Import collection models
        from app.models.myth_fact_collection import MythFactCollection, UserCollectionProgress
        from datetime import date
        
        # Verify collection exists and is active
        collection_query = select(MythFactCollection).where(
            and_(
                MythFactCollection.id == collection_id,
                MythFactCollection.is_active == True
            )
        )
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collection not found or inactive"
            )
        
        # Check daily repeatability
        today = date.today()
        if collection.repeatability == "daily":
            existing_progress_query = select(UserCollectionProgress).where(
                and_(
                    UserCollectionProgress.user_id == current_user.id,
                    UserCollectionProgress.collection_id == collection_id,
                    UserCollectionProgress.play_date == today
                )
            )
            existing_result = await db.execute(existing_progress_query)
            existing_progress = existing_result.scalar_one_or_none()
            
            if existing_progress:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Collection already completed today. Daily limit reached."
                )
        
        # Calculate rewards (use collection custom rewards if enabled)
        from app.services.rewards_service import RewardsService
        rewards_service = RewardsService()
        
        if collection.custom_points_enabled and collection.custom_credits_enabled:
            # Use collection's custom rewards
            tier = rewards_service._calculate_myths_facts_reward_tier(score_percentage)
            
            # Get custom points/credits based on tier
            tier_mapping = {
                "bronze": (collection.custom_points_bronze, collection.custom_credits_bronze),
                "silver": (collection.custom_points_silver, collection.custom_credits_silver),
                "gold": (collection.custom_points_gold, collection.custom_credits_gold),
                "platinum": (collection.custom_points_platinum, collection.custom_credits_platinum)
            }
            
            points_earned, credits_earned = tier_mapping.get(tier.value, (0, 0))
            
        else:
            # Use standard reward calculation
            reward_result = await rewards_service.calculate_myths_facts_rewards(
                score_percentage=score_percentage,
                time_taken=time_taken,
                user_id=current_user.id,
                db=db
            )
            points_earned = reward_result["points"]
            credits_earned = reward_result["credits"] 
            tier = reward_result["tier"]
        
        # Create collection progress record
        progress = UserCollectionProgress(
            user_id=current_user.id,
            collection_id=collection_id,
            play_date=today,
            completed=True,
            score_percentage=score_percentage,
            time_taken=time_taken,
            answers_correct=answers_correct,
            total_questions=total_questions,
            points_earned=points_earned,
            credits_earned=credits_earned,
            tier=tier.value if hasattr(tier, 'value') else str(tier),
            completed_at=func.now()
        )
        
        db.add(progress)
        
        # Apply rewards to user account
        if credits_earned > 0:
            from app.services.currency_service import CurrencyService
            currency_service = CurrencyService()
            await currency_service.add_credits(
                user_id=current_user.id,
                amount=credits_earned,
                source="collection_myths_facts",
                description=f"Collection: {collection.name}",
                db=db
            )
        
        # Commit all changes
        await db.commit()
        await db.refresh(progress)
        
        logger.info(
            "Collection-based myths facts game completed successfully",
            user_id=str(current_user.id),
            collection_id=str(collection_id),
            collection_name=collection.name,
            score=score_percentage,
            tier=tier.value if hasattr(tier, 'value') else str(tier),
            points_earned=points_earned,
            credits_earned=credits_earned
        )
        
        return SuccessResponse(
            message="Collection myths vs facts game completed successfully",
            data={
                "progress_id": progress.id,
                "collection_name": collection.name,
                "score_percentage": score_percentage,
                "tier": tier.value if hasattr(tier, 'value') else str(tier),
                "points_earned": points_earned,
                "credits_earned": credits_earned,
                "completed_at": progress.completed_at,
                "can_play_again_today": collection.repeatability != "daily"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            "Error processing collection myths facts game completion", 
            user_id=str(current_user.id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing collection game completion"
        )