"""
Collection Management API - Working Implementation

Simple, working collection management endpoints that integrate with
the existing myths_facts system and support daily repeatability.

Features:
- List available collections for users
- Track user progress with daily limits
- Integration with existing reward system

Author: Junglore Development Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, text
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime, timedelta

from app.db.database import get_db
from app.models.myth_fact_collection import MythFactCollection, CollectionMythFact, UserCollectionProgress
from app.models.myth_fact import MythFact
from app.models.user import User
from app.schemas.collection_schemas import (
    CollectionResponse, UserCollectionProgressResponse
)

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.get("/", response_model=List[CollectionResponse])
async def list_collections(
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(True, description="Filter by active status"),
    db: AsyncSession = Depends(get_db)
):
    """List all active collections with optional filtering."""
    try:
        # Build query with filters
        query = select(MythFactCollection)
        
        if category_id:
            query = query.where(MythFactCollection.category_id == category_id)
        if is_active is not None:
            query = query.where(MythFactCollection.is_active == is_active)
        
        query = query.order_by(MythFactCollection.created_at.desc())
        
        result = await db.execute(query)
        collections = result.scalars().all()
        
        return [CollectionResponse.from_orm(collection) for collection in collections]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@router.get("/{collection_id}")
async def get_collection_details(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific collection."""
    try:
        # Get collection basic info
        collection_query = select(MythFactCollection).where(MythFactCollection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Get cards count
        cards_query = select(func.count(CollectionMythFact.id)).where(
            CollectionMythFact.collection_id == collection_id
        )
        cards_result = await db.execute(cards_query)
        cards_count = cards_result.scalar() or 0
        
        return {
            "id": collection.id,
            "name": collection.name,
            "description": collection.description,
            "is_active": collection.is_active,
            "cards_count": cards_count,
            "repeatability": collection.repeatability,
            "category_id": collection.category_id,
            "custom_points_enabled": collection.custom_points_enabled,
            "custom_credits_enabled": collection.custom_credits_enabled,
            "created_at": collection.created_at
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection: {str(e)}")


@router.get("/user/{user_id}/available")
async def get_available_collections_for_user(
    user_id: UUID,
    target_date: Optional[date] = Query(default_factory=date.today, description="Target play date"),
    db: AsyncSession = Depends(get_db)
):
    """Get collections available for a user to play based on repeatability rules."""
    try:
        # Get all active collections
        collections_query = select(MythFactCollection).where(
            MythFactCollection.is_active == True
        )
        collections_result = await db.execute(collections_query)
        all_collections = collections_result.scalars().all()
        
        available_collections = []
        played_today = []
        
        for collection in all_collections:
            # Check if user can play this collection
            can_play = await _can_user_play_collection(
                db, user_id, collection.id, target_date, collection.repeatability
            )
            
            collection_info = {
                "id": collection.id,
                "name": collection.name,
                "description": collection.description,
                "cards_count": collection.cards_count,
                "repeatability": collection.repeatability,
                "category_id": collection.category_id
            }
            
            if can_play:
                available_collections.append(collection_info)
            else:
                played_today.append(collection_info)
        
        return {
            "available_collections": available_collections,
            "played_today": played_today,
            "date": target_date,
            "total_collections": len(all_collections)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available collections: {str(e)}")


@router.get("/{collection_id}/cards")
async def get_collection_cards(
    collection_id: UUID,
    limit: int = Query(10, ge=1, le=50, description="Number of cards to return"),
    random_order: bool = Query(True, description="Randomize card order"),
    db: AsyncSession = Depends(get_db)
):
    """Get myth-fact cards for a specific collection."""
    try:
        # Verify collection exists
        collection_query = select(MythFactCollection).where(MythFactCollection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Get cards for this collection
        if random_order:
            # Random order using PostgreSQL RANDOM()
            cards_query = text("""
                SELECT mf.id, mf.title, mf.myth_content, mf.fact_content, mf.image_url, mf.is_featured
                FROM myths_facts mf
                JOIN collection_myth_facts cmf ON mf.id = cmf.myth_fact_id
                WHERE cmf.collection_id = :collection_id
                ORDER BY RANDOM()
                LIMIT :limit
            """)
            cards_result = await db.execute(cards_query, {
                "collection_id": str(collection_id),
                "limit": limit
            })
            cards_rows = cards_result.fetchall()
            
            cards = []
            for row in cards_rows:
                cards.append({
                    "id": row[0],
                    "title": row[1],
                    "myth_content": row[2],
                    "fact_content": row[3],
                    "image_url": row[4],
                    "is_featured": row[5]
                })
        else:
            # Ordered by collection order_index
            cards_query = text("""
                SELECT mf.id, mf.title, mf.myth_content, mf.fact_content, mf.image_url, mf.is_featured
                FROM myths_facts mf
                JOIN collection_myth_facts cmf ON mf.id = cmf.myth_fact_id
                WHERE cmf.collection_id = :collection_id
                ORDER BY cmf.order_index
                LIMIT :limit
            """)
            cards_result = await db.execute(cards_query, {
                "collection_id": str(collection_id),
                "limit": limit
            })
            cards_rows = cards_result.fetchall()
            
            cards = []
            for row in cards_rows:
                cards.append({
                    "id": row[0],
                    "title": row[1],
                    "myth_content": row[2],
                    "fact_content": row[3],
                    "image_url": row[4],
                    "is_featured": row[5]
                })
        
        return {
            "collection_id": collection_id,
            "collection_name": collection.name,
            "cards": cards,
            "total_available": len(cards),
            "random_order": random_order
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection cards: {str(e)}")


@router.post("/{collection_id}/complete")
async def complete_collection(
    collection_id: UUID,
    completion_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Record completion of a collection for a user."""
    try:
        user_id = completion_data.get("user_id")
        score_percentage = completion_data.get("score_percentage", 0)
        answers_correct = completion_data.get("answers_correct", 0)
        total_questions = completion_data.get("total_questions", 0)
        time_taken = completion_data.get("time_taken")
        points_earned = completion_data.get("points_earned", 0)
        credits_earned = completion_data.get("credits_earned", 0)
        tier = completion_data.get("tier")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id is required")
        
        # Verify collection exists
        collection_query = select(MythFactCollection).where(MythFactCollection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        # Check if already completed today (for daily collections)
        today = date.today()
        existing_query = select(UserCollectionProgress).where(
            and_(
                UserCollectionProgress.user_id == user_id,
                UserCollectionProgress.collection_id == collection_id,
                UserCollectionProgress.play_date == today
            )
        )
        existing_result = await db.execute(existing_query)
        existing_progress = existing_result.scalar_one_or_none()
        
        if existing_progress and collection.repeatability == "daily":
            raise HTTPException(status_code=400, detail="Collection already completed today")
        
        # Create progress record
        progress = UserCollectionProgress(
            user_id=user_id,
            collection_id=collection_id,
            play_date=today,
            completed=True,
            score_percentage=score_percentage,
            time_taken=time_taken,
            answers_correct=answers_correct,
            total_questions=total_questions,
            points_earned=points_earned,
            credits_earned=credits_earned,
            tier=tier,
            completed_at=datetime.utcnow()
        )
        
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
        
        return {
            "message": "Collection completed successfully",
            "progress_id": progress.id,
            "points_earned": points_earned,
            "credits_earned": credits_earned,
            "tier": tier,
            "completed_at": progress.completed_at
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to complete collection: {str(e)}")


async def _can_user_play_collection(
    db: AsyncSession,
    user_id: UUID,
    collection_id: UUID,
    target_date: date,
    repeatability: str
) -> bool:
    """Check if a user can play a collection based on repeatability rules."""
    try:
        if repeatability == "unlimited":
            return True
        
        # Check if user has played this collection on the target date
        progress_query = select(UserCollectionProgress).where(
            and_(
                UserCollectionProgress.user_id == user_id,
                UserCollectionProgress.collection_id == collection_id,
                UserCollectionProgress.play_date == target_date
            )
        )
        
        if repeatability == "daily":
            # Daily: Can't play if already played today
            result = await db.execute(progress_query)
            existing_progress = result.scalar_one_or_none()
            return existing_progress is None
        
        elif repeatability == "weekly":
            # Weekly: Can't play if already played this week
            days_since_monday = target_date.weekday()
            week_start = target_date - timedelta(days=days_since_monday)
            week_end = week_start + timedelta(days=6)
            
            weekly_progress_query = select(UserCollectionProgress).where(
                and_(
                    UserCollectionProgress.user_id == user_id,
                    UserCollectionProgress.collection_id == collection_id,
                    UserCollectionProgress.play_date >= week_start,
                    UserCollectionProgress.play_date <= week_end
                )
            )
            
            result = await db.execute(weekly_progress_query)
            existing_progress = result.scalar_one_or_none()
            return existing_progress is None
        
        return True
        
    except Exception:
        # Default to allowing play if there's an error
        return True