"""
Collection Management API Endpoints

This module provides comprehensive API endpoints for the collection-based
myth vs facts system, including CRUD operations, user progress tracking,
and game completion handling.

Endpoints:
- Collection CRUD operations
- Card assignment to collections
- User progress tracking
- Game play and completion
- Analytics and statistics

Author: Junglore Development Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import date, datetime, timedelta
import logging

from app.db.database import get_db
from app.services.auth_service import get_current_user
from app.models.myth_fact_collection import (
    MythFactCollection,
    CollectionMythFact,
    UserCollectionProgress
)
from app.models.user import User
from app.models.myths_facts import MythsFacts
from app.models.categories import Category
from app.schemas.myth_fact_collection import (
    MythFactCollectionCreate,
    MythFactCollectionUpdate,
    MythFactCollectionResponse,
    MythFactCollectionListResponse,
    CollectionCardsUpdate,
    CollectionCardResponse,
    UserCollectionProgressCreate,
    UserCollectionProgressResponse,
    UserProgressSummary,
    CollectionStats,
    CollectionGameRequest,
    CollectionGameResponse,
    CollectionCompletionRequest,
    CollectionCompletionResponse,
    PaginationParams,
    RepeatabilityType,
    TierType,
    ErrorResponse,
    SuccessResponse
)
from app.services.rewards_service import get_rewards_for_tier, calculate_tier
from app.services.achievement_service import check_achievements

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/collections", tags=["Collection Management"])


# Collection CRUD Operations
@router.post("/", response_model=MythFactCollectionResponse)
async def create_collection(
    collection_data: MythFactCollectionCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Create a new myth fact collection.
    
    - **Admin only endpoint**
    - Creates collection with optional initial cards
    - Validates custom rewards configuration
    """
    try:
        # Create the collection
        collection = MythFactCollection(
            id=uuid4(),
            name=collection_data.name,
            description=collection_data.description,
            category_id=collection_data.category_id,
            is_active=collection_data.is_active,
            repeatability=collection_data.repeatability.value,
            custom_points_enabled=collection_data.custom_points_enabled,
            custom_points=collection_data.custom_points.dict() if collection_data.custom_points else None,
            custom_credits_enabled=collection_data.custom_credits_enabled,
            custom_credits=collection_data.custom_credits.dict() if collection_data.custom_credits else None,
            created_by=admin_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(collection)
        db.flush()  # Get the ID
        
        # Add initial cards if provided
        if collection_data.myth_fact_ids:
            for idx, myth_fact_id in enumerate(collection_data.myth_fact_ids):
                # Verify the myth fact exists
                myth_fact = db.query(MythsFacts).filter(
                    MythsFacts.id == myth_fact_id
                ).first()
                
                if not myth_fact:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Myth fact with ID {myth_fact_id} not found"
                    )
                
                # Add to collection
                collection_card = CollectionMythFact(
                    id=uuid4(),
                    collection_id=collection.id,
                    myth_fact_id=myth_fact_id,
                    order_index=idx,
                    added_at=datetime.utcnow()
                )
                db.add(collection_card)
        
        db.commit()
        
        # Load the complete collection with category name
        collection_response = db.query(MythFactCollection).options(
            joinedload(MythFactCollection.category)
        ).filter(MythFactCollection.id == collection.id).first()
        
        # Get cards count
        cards_count = db.query(CollectionMythFact).filter(
            CollectionMythFact.collection_id == collection.id
        ).count()
        
        response_data = MythFactCollectionResponse(
            id=collection_response.id,
            name=collection_response.name,
            description=collection_response.description,
            category_id=collection_response.category_id,
            is_active=collection_response.is_active,
            repeatability=collection_response.repeatability,
            custom_points_enabled=collection_response.custom_points_enabled,
            custom_points=collection_response.custom_points,
            custom_credits_enabled=collection_response.custom_credits_enabled,
            custom_credits=collection_response.custom_credits,
            cards_count=cards_count,
            created_at=collection_response.created_at,
            updated_at=collection_response.updated_at,
            created_by=collection_response.created_by,
            category_name=collection_response.category.name if collection_response.category else None
        )
        
        logger.info(f"Collection created: {collection.name} by admin {admin_user.id}")
        return response_data
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating collection: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")


@router.get("/", response_model=MythFactCollectionListResponse)
async def list_collections(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category_id: Optional[UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List collections with pagination and filtering.
    
    - **Supports pagination, search, and filtering**
    - **Returns category names and card counts**
    - **Available to all authenticated users**
    """
    try:
        # Build query
        query = db.query(MythFactCollection).options(
            joinedload(MythFactCollection.category)
        )
        
        # Apply filters
        if category_id:
            query = query.filter(MythFactCollection.category_id == category_id)
        
        if is_active is not None:
            query = query.filter(MythFactCollection.is_active == is_active)
        
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    MythFactCollection.name.ilike(search_term),
                    MythFactCollection.description.ilike(search_term)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        collections = query.order_by(
            MythFactCollection.created_at.desc()
        ).offset(offset).limit(limit).all()
        
        # Build response with card counts
        collection_responses = []
        for collection in collections:
            cards_count = db.query(CollectionMythFact).filter(
                CollectionMythFact.collection_id == collection.id
            ).count()
            
            response_data = MythFactCollectionResponse(
                id=collection.id,
                name=collection.name,
                description=collection.description,
                category_id=collection.category_id,
                is_active=collection.is_active,
                repeatability=collection.repeatability,
                custom_points_enabled=collection.custom_points_enabled,
                custom_points=collection.custom_points,
                custom_credits_enabled=collection.custom_credits_enabled,
                custom_credits=collection.custom_credits,
                cards_count=cards_count,
                created_at=collection.created_at,
                updated_at=collection.updated_at,
                created_by=collection.created_by,
                category_name=collection.category.name if collection.category else None
            )
            collection_responses.append(response_data)
        
        total_pages = (total + limit - 1) // limit
        
        return MythFactCollectionListResponse(
            collections=collection_responses,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )
        
    except Exception as e:
        logger.error(f"Error listing collections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@router.get("/{collection_id}", response_model=MythFactCollectionResponse)
async def get_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific collection by ID.
    
    - **Returns full collection details with category name**
    - **Includes card count**
    """
    try:
        collection = db.query(MythFactCollection).options(
            joinedload(MythFactCollection.category)
        ).filter(MythFactCollection.id == collection_id).first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Get cards count
        cards_count = db.query(CollectionMythFact).filter(
            CollectionMythFact.collection_id == collection.id
        ).count()
        
        response_data = MythFactCollectionResponse(
            id=collection.id,
            name=collection.name,
            description=collection.description,
            category_id=collection.category_id,
            is_active=collection.is_active,
            repeatability=collection.repeatability,
            custom_points_enabled=collection.custom_points_enabled,
            custom_points=collection.custom_points,
            custom_credits_enabled=collection.custom_credits_enabled,
            custom_credits=collection.custom_credits,
            cards_count=cards_count,
            created_at=collection.created_at,
            updated_at=collection.updated_at,
            created_by=collection.created_by,
            category_name=collection.category.name if collection.category else None
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection: {str(e)}")


@router.put("/{collection_id}", response_model=MythFactCollectionResponse)
async def update_collection(
    collection_id: UUID,
    update_data: MythFactCollectionUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Update a collection.
    
    - **Admin only endpoint**
    - **Partial updates supported**
    """
    try:
        collection = db.query(MythFactCollection).filter(
            MythFactCollection.id == collection_id
        ).first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Update fields if provided
        update_dict = update_data.dict(exclude_unset=True)
        
        for field, value in update_dict.items():
            if field == "repeatability" and value:
                setattr(collection, field, value.value)
            elif field in ["custom_points", "custom_credits"] and value:
                setattr(collection, field, value.dict())
            else:
                setattr(collection, field, value)
        
        collection.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(collection)
        
        # Load with category for response
        collection_with_category = db.query(MythFactCollection).options(
            joinedload(MythFactCollection.category)
        ).filter(MythFactCollection.id == collection.id).first()
        
        # Get cards count
        cards_count = db.query(CollectionMythFact).filter(
            CollectionMythFact.collection_id == collection.id
        ).count()
        
        response_data = MythFactCollectionResponse(
            id=collection_with_category.id,
            name=collection_with_category.name,
            description=collection_with_category.description,
            category_id=collection_with_category.category_id,
            is_active=collection_with_category.is_active,
            repeatability=collection_with_category.repeatability,
            custom_points_enabled=collection_with_category.custom_points_enabled,
            custom_points=collection_with_category.custom_points,
            custom_credits_enabled=collection_with_category.custom_credits_enabled,
            custom_credits=collection_with_category.custom_credits,
            cards_count=cards_count,
            created_at=collection_with_category.created_at,
            updated_at=collection_with_category.updated_at,
            created_by=collection_with_category.created_by,
            category_name=collection_with_category.category.name if collection_with_category.category else None
        )
        
        logger.info(f"Collection updated: {collection.name} by admin {admin_user.id}")
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating collection {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update collection: {str(e)}")


@router.delete("/{collection_id}", response_model=SuccessResponse)
async def delete_collection(
    collection_id: UUID,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Delete a collection and all associated data.
    
    - **Admin only endpoint**
    - **Cascade deletes progress records and card assignments**
    """
    try:
        collection = db.query(MythFactCollection).filter(
            MythFactCollection.id == collection_id
        ).first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        collection_name = collection.name
        
        # Delete related records (cascade)
        db.query(UserCollectionProgress).filter(
            UserCollectionProgress.collection_id == collection_id
        ).delete()
        
        db.query(CollectionMythFact).filter(
            CollectionMythFact.collection_id == collection_id
        ).delete()
        
        # Delete the collection
        db.delete(collection)
        db.commit()
        
        logger.info(f"Collection deleted: {collection_name} by admin {admin_user.id}")
        return SuccessResponse(
            message=f"Collection '{collection_name}' deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting collection {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete collection: {str(e)}")


# Collection Card Management
@router.get("/{collection_id}/cards", response_model=List[CollectionCardResponse])
async def get_collection_cards(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all cards in a collection ordered by order_index.
    """
    try:
        collection = db.query(MythFactCollection).filter(
            MythFactCollection.id == collection_id
        ).first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Get cards with myth fact details
        cards = db.query(
            CollectionMythFact, MythsFacts
        ).join(
            MythsFacts, CollectionMythFact.myth_fact_id == MythsFacts.id
        ).filter(
            CollectionMythFact.collection_id == collection_id
        ).order_by(CollectionMythFact.order_index).all()
        
        card_responses = []
        for collection_card, myth_fact in cards:
            response = CollectionCardResponse(
                id=collection_card.id,
                myth_fact_id=myth_fact.id,
                order_index=collection_card.order_index,
                title=myth_fact.title,
                myth_content=myth_fact.myth_content,
                fact_content=myth_fact.fact_content,
                image_url=myth_fact.image_url
            )
            card_responses.append(response)
        
        return card_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting collection cards {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection cards: {str(e)}")


@router.put("/{collection_id}/cards", response_model=SuccessResponse)
async def update_collection_cards(
    collection_id: UUID,
    cards_data: CollectionCardsUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Update the cards in a collection.
    
    - **Admin only endpoint**
    - **Replaces all existing cards with new assignments**
    - **Validates card existence and order uniqueness**
    """
    try:
        collection = db.query(MythFactCollection).filter(
            MythFactCollection.id == collection_id
        ).first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Validate all myth facts exist
        myth_fact_ids = [card.myth_fact_id for card in cards_data.cards]
        existing_facts = db.query(MythsFacts.id).filter(
            MythsFacts.id.in_(myth_fact_ids)
        ).all()
        existing_fact_ids = [fact.id for fact in existing_facts]
        
        missing_ids = set(myth_fact_ids) - set(existing_fact_ids)
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Myth facts not found: {list(missing_ids)}"
            )
        
        # Delete existing cards
        db.query(CollectionMythFact).filter(
            CollectionMythFact.collection_id == collection_id
        ).delete()
        
        # Add new cards
        for card_data in cards_data.cards:
            collection_card = CollectionMythFact(
                id=uuid4(),
                collection_id=collection_id,
                myth_fact_id=card_data.myth_fact_id,
                order_index=card_data.order_index,
                added_at=datetime.utcnow()
            )
            db.add(collection_card)
        
        # Update collection timestamp
        collection.updated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Collection cards updated: {collection.name} ({len(cards_data.cards)} cards) by admin {admin_user.id}")
        return SuccessResponse(
            message=f"Collection '{collection.name}' cards updated successfully",
            data={"cards_count": len(cards_data.cards)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating collection cards {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update collection cards: {str(e)}")


# Game Play Endpoints
@router.get("/{collection_id}/play", response_model=CollectionGameResponse)
async def start_collection_game(
    collection_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start a collection game session.
    
    - **Checks repeatability rules**
    - **Returns game data if allowed to play**
    """
    try:
        # Get collection with cards
        collection = db.query(MythFactCollection).filter(
            and_(
                MythFactCollection.id == collection_id,
                MythFactCollection.is_active == True
            )
        ).first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found or inactive")
        
        # Check repeatability
        can_play, reason = await _check_repeatability(
            db, current_user.id, collection_id, collection.repeatability
        )
        
        if not can_play:
            return CollectionGameResponse(
                collection_id=collection_id,
                collection_name=collection.name,
                description=collection.description,
                cards=[],
                total_cards=0,
                repeatability=collection.repeatability,
                custom_rewards=collection.custom_points_enabled or collection.custom_credits_enabled,
                can_play_today=False,
                reason=reason
            )
        
        # Get cards
        cards_query = db.query(
            CollectionMythFact, MythsFacts
        ).join(
            MythsFacts, CollectionMythFact.myth_fact_id == MythsFacts.id
        ).filter(
            CollectionMythFact.collection_id == collection_id
        ).order_by(CollectionMythFact.order_index).all()
        
        if not cards_query:
            raise HTTPException(status_code=400, detail="Collection has no cards")
        
        card_responses = []
        for collection_card, myth_fact in cards_query:
            response = CollectionCardResponse(
                id=collection_card.id,
                myth_fact_id=myth_fact.id,
                order_index=collection_card.order_index,
                title=myth_fact.title,
                myth_content=myth_fact.myth_content,
                fact_content=myth_fact.fact_content,
                image_url=myth_fact.image_url
            )
            card_responses.append(response)
        
        return CollectionGameResponse(
            collection_id=collection_id,
            collection_name=collection.name,
            description=collection.description,
            cards=card_responses,
            total_cards=len(card_responses),
            repeatability=collection.repeatability,
            custom_rewards=collection.custom_points_enabled or collection.custom_credits_enabled,
            can_play_today=True,
            reason=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting collection game {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start collection game: {str(e)}")


@router.post("/{collection_id}/complete", response_model=CollectionCompletionResponse)
async def complete_collection_game(
    collection_id: UUID,
    completion_data: CollectionCompletionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Complete a collection game and record progress.
    
    - **Calculates rewards based on performance**
    - **Respects custom reward configurations**
    - **Updates user balance and progress**
    """
    try:
        # Get collection
        collection = db.query(MythFactCollection).filter(
            and_(
                MythFactCollection.id == collection_id,
                MythFactCollection.is_active == True
            )
        ).first()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found or inactive")
        
        # Verify user can play (double-check)
        can_play, reason = await _check_repeatability(
            db, current_user.id, collection_id, collection.repeatability
        )
        
        if not can_play:
            raise HTTPException(status_code=400, detail=reason)
        
        # Get collection cards count
        total_cards = db.query(CollectionMythFact).filter(
            CollectionMythFact.collection_id == collection_id
        ).count()
        
        if total_cards == 0:
            raise HTTPException(status_code=400, detail="Collection has no cards")
        
        # Calculate score and tier
        answers_correct = len([a for a in completion_data.answers if a.get('correct', False)])
        score_percentage = completion_data.score_percentage
        tier = calculate_tier(score_percentage)
        
        # Calculate rewards
        if collection.custom_points_enabled and collection.custom_points:
            points_earned = collection.custom_points.get(tier.lower(), 0)
        else:
            points_earned = get_rewards_for_tier(tier)['points']
        
        if collection.custom_credits_enabled and collection.custom_credits:
            credits_earned = collection.custom_credits.get(tier.lower(), 0)
        else:
            credits_earned = get_rewards_for_tier(tier)['credits']
        
        # Apply any bonuses (can be extended)
        bonus_applied = False
        if score_percentage == 100 and completion_data.time_taken < 60:  # Perfect score in under 1 minute
            points_earned = int(points_earned * 1.5)
            credits_earned = int(credits_earned * 1.5)
            bonus_applied = True
        
        # Create progress record
        progress = UserCollectionProgress(
            id=uuid4(),
            user_id=current_user.id,
            collection_id=collection_id,
            play_date=date.today(),
            completed=True,
            score_percentage=score_percentage,
            time_taken=completion_data.time_taken,
            answers_correct=answers_correct,
            total_questions=total_cards,
            points_earned=points_earned,
            credits_earned=credits_earned,
            tier=tier,
            bonus_applied=bonus_applied,
            game_session_id=completion_data.game_session_id,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        db.add(progress)
        
        # Update user balance
        current_user.points = (current_user.points or 0) + points_earned
        current_user.credits = (current_user.credits or 0) + credits_earned
        
        db.commit()
        
        # Check for achievements in background
        background_tasks.add_task(
            check_achievements,
            current_user.id,
            "collection_completion",
            {
                "collection_id": str(collection_id),
                "score": score_percentage,
                "tier": tier,
                "answers_correct": answers_correct,
                "total_questions": total_cards
            }
        )
        
        # Determine next play time
        can_play_again, next_play_time = await _get_next_play_time(
            collection.repeatability
        )
        
        # Build response
        breakdown = {
            "base_points": get_rewards_for_tier(tier)['points'],
            "base_credits": get_rewards_for_tier(tier)['credits'],
            "custom_rewards_applied": collection.custom_points_enabled or collection.custom_credits_enabled,
            "bonus_multiplier": 1.5 if bonus_applied else 1.0,
            "answers_correct": answers_correct,
            "total_questions": total_cards,
            "time_taken": completion_data.time_taken
        }
        
        logger.info(f"Collection completed: {collection.name} by user {current_user.id} - {tier} tier, {points_earned} points, {credits_earned} credits")
        
        return CollectionCompletionResponse(
            success=True,
            message=f"Collection completed! You earned {points_earned} points and {credits_earned} credits.",
            progress_id=progress.id,
            points_earned=points_earned,
            credits_earned=credits_earned,
            tier=tier,
            bonus_applied=bonus_applied,
            can_play_again=can_play_again,
            next_play_time=next_play_time,
            breakdown=breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing collection game {collection_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to complete collection game: {str(e)}")


# User Progress Endpoints
@router.get("/user/progress", response_model=List[UserCollectionProgressResponse])
async def get_user_progress(
    limit: int = Query(20, ge=1, le=100),
    collection_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's collection progress history.
    """
    try:
        query = db.query(UserCollectionProgress).options(
            joinedload(UserCollectionProgress.collection)
        ).filter(UserCollectionProgress.user_id == current_user.id)
        
        if collection_id:
            query = query.filter(UserCollectionProgress.collection_id == collection_id)
        
        progress_records = query.order_by(
            UserCollectionProgress.created_at.desc()
        ).limit(limit).all()
        
        responses = []
        for progress in progress_records:
            response = UserCollectionProgressResponse(
                id=progress.id,
                user_id=progress.user_id,
                collection_id=progress.collection_id,
                play_date=progress.play_date,
                completed=progress.completed,
                score_percentage=progress.score_percentage,
                time_taken=progress.time_taken,
                answers_correct=progress.answers_correct,
                total_questions=progress.total_questions,
                points_earned=progress.points_earned,
                credits_earned=progress.credits_earned,
                tier=progress.tier,
                bonus_applied=progress.bonus_applied,
                game_session_id=progress.game_session_id,
                created_at=progress.created_at,
                completed_at=progress.completed_at,
                collection_name=progress.collection.name if progress.collection else None
            )
            responses.append(response)
        
        return responses
        
    except Exception as e:
        logger.error(f"Error getting user progress: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user progress: {str(e)}")


@router.get("/user/summary", response_model=UserProgressSummary)
async def get_user_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's overall collection progress summary.
    """
    try:
        # Get summary statistics
        summary_query = db.query(
            func.count(UserCollectionProgress.id).label('total_played'),
            func.count(func.nullif(UserCollectionProgress.completed, False)).label('total_completed'),
            func.sum(UserCollectionProgress.points_earned).label('total_points'),
            func.sum(UserCollectionProgress.credits_earned).label('total_credits'),
            func.avg(UserCollectionProgress.score_percentage).label('avg_score'),
            func.max(UserCollectionProgress.play_date).label('last_play_date')
        ).filter(UserCollectionProgress.user_id == current_user.id).first()
        
        # Calculate current streak
        current_streak = await _calculate_current_streak(db, current_user.id)
        
        # Get favorite category (most played)
        favorite_category_query = db.query(
            Category.name,
            func.count(UserCollectionProgress.id).label('play_count')
        ).join(
            MythFactCollection, UserCollectionProgress.collection_id == MythFactCollection.id
        ).join(
            Category, MythFactCollection.category_id == Category.id
        ).filter(
            UserCollectionProgress.user_id == current_user.id
        ).group_by(Category.name).order_by(
            func.count(UserCollectionProgress.id).desc()
        ).first()
        
        favorite_category = favorite_category_query.name if favorite_category_query else None
        
        return UserProgressSummary(
            user_id=current_user.id,
            total_collections_played=summary_query.total_played or 0,
            total_collections_completed=summary_query.total_completed or 0,
            total_points_earned=summary_query.total_points or 0,
            total_credits_earned=summary_query.total_credits or 0,
            average_score=float(summary_query.avg_score or 0),
            favorite_category=favorite_category,
            current_streak=current_streak,
            last_play_date=summary_query.last_play_date
        )
        
    except Exception as e:
        logger.error(f"Error getting user summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get user summary: {str(e)}")


# Analytics Endpoints (Admin Only)
@router.get("/analytics/stats", response_model=List[CollectionStats])
async def get_collection_analytics(
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_admin_user)
):
    """
    Get analytics for all collections.
    
    - **Admin only endpoint**
    - **Returns comprehensive statistics for each collection**
    """
    try:
        # Use the analytics view we created
        analytics_query = db.execute("""
            SELECT * FROM collection_analytics_view
            ORDER BY total_plays DESC
        """).fetchall()
        
        stats = []
        for row in analytics_query:
            stat = CollectionStats(
                id=row.collection_id,
                name=row.collection_name,
                description=row.description,
                is_active=row.is_active,
                repeatability=row.repeatability,
                category_name=row.category_name,
                total_cards=row.total_cards,
                unique_players=row.unique_players or 0,
                total_plays=row.total_plays or 0,
                completions=row.completions or 0,
                avg_score=float(row.avg_score) if row.avg_score else None,
                avg_time=float(row.avg_time) if row.avg_time else None,
                completion_rate=float(row.completion_rate) if row.completion_rate else None
            )
            stats.append(stat)
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting collection analytics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get collection analytics: {str(e)}")


# Helper Functions
async def _check_repeatability(
    db: Session, 
    user_id: UUID, 
    collection_id: UUID, 
    repeatability: str
) -> tuple[bool, Optional[str]]:
    """Check if user can play collection based on repeatability rules."""
    if repeatability == RepeatabilityType.UNLIMITED.value:
        return True, None
    
    today = date.today()
    
    if repeatability == RepeatabilityType.DAILY.value:
        # Check if played today
        existing_play = db.query(UserCollectionProgress).filter(
            and_(
                UserCollectionProgress.user_id == user_id,
                UserCollectionProgress.collection_id == collection_id,
                UserCollectionProgress.play_date == today
            )
        ).first()
        
        if existing_play:
            return False, "You have already played this collection today. Come back tomorrow!"
    
    elif repeatability == RepeatabilityType.WEEKLY.value:
        # Check if played this week
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        existing_play = db.query(UserCollectionProgress).filter(
            and_(
                UserCollectionProgress.user_id == user_id,
                UserCollectionProgress.collection_id == collection_id,
                UserCollectionProgress.play_date >= week_start,
                UserCollectionProgress.play_date <= week_end
            )
        ).first()
        
        if existing_play:
            return False, "You have already played this collection this week. Come back next week!"
    
    return True, None


async def _get_next_play_time(repeatability: str) -> tuple[bool, Optional[datetime]]:
    """Get when user can play again."""
    if repeatability == RepeatabilityType.UNLIMITED.value:
        return True, None
    
    now = datetime.utcnow()
    
    if repeatability == RepeatabilityType.DAILY.value:
        # Next day at midnight
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return False, tomorrow
    
    elif repeatability == RepeatabilityType.WEEKLY.value:
        # Next Monday at midnight
        days_until_monday = (7 - now.weekday()) % 7
        if days_until_monday == 0:  # Today is Monday
            days_until_monday = 7
        next_monday = (now + timedelta(days=days_until_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return False, next_monday
    
    return True, None


async def _calculate_current_streak(db: Session, user_id: UUID) -> int:
    """Calculate user's current daily play streak."""
    try:
        # Get last 30 days of play dates (should be enough to calculate any reasonable streak)
        thirty_days_ago = date.today() - timedelta(days=30)
        
        play_dates = db.query(
            func.distinct(UserCollectionProgress.play_date)
        ).filter(
            and_(
                UserCollectionProgress.user_id == user_id,
                UserCollectionProgress.play_date >= thirty_days_ago,
                UserCollectionProgress.completed == True
            )
        ).order_by(UserCollectionProgress.play_date.desc()).limit(30).all()
        
        if not play_dates:
            return 0
        
        # Convert to list of dates
        dates = [row[0] for row in play_dates]
        
        # Calculate streak from today backwards
        current_date = date.today()
        streak = 0
        
        for play_date in dates:
            if play_date == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            elif play_date == current_date:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        return streak
        
    except Exception:
        return 0