"""
Admin Collection Management API

Enhanced admin endpoints for managing myth-fact collections with
advanced features like bulk operations, analytics, and collection building.

Features:
- Admin-only collection CRUD operations
- Bulk card assignment and management
- Collection analytics and statistics
- Collection cloning and templating
- Advanced filtering and search

Author: Junglore Development Team
Version: 1.0.0
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, text, desc
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import date, datetime, timedelta

from app.db.database import get_db
from app.models.myth_fact_collection import MythFactCollection, CollectionMythFact, UserCollectionProgress
from app.models.myth_fact import MythFact
from app.models.user import User
from app.models.category import Category
from app.schemas.collection_schemas import (
    CollectionCreate, CollectionResponse, CollectionUpdate, CollectionWithCards
)

router = APIRouter(prefix="/admin/collections", tags=["Admin Collections"])


@router.post("/", response_model=CollectionResponse)
async def admin_create_collection(
    collection_data: CollectionCreate,
    db: AsyncSession = Depends(get_db)
    # Note: Add admin authentication when available
    # current_admin: User = Depends(get_admin_user)
):
    """Admin endpoint to create a new collection."""
    try:
        new_collection = MythFactCollection(
            **collection_data.dict(),
            created_by=None  # Set to admin user when auth is available
        )
        
        db.add(new_collection)
        await db.commit()
        await db.refresh(new_collection)
        
        return CollectionResponse.from_orm(new_collection)
    
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create collection: {str(e)}")


@router.get("/", response_model=List[CollectionResponse])
async def admin_list_collections(
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    repeatability: Optional[str] = Query(None, description="Filter by repeatability"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    created_after: Optional[date] = Query(None, description="Filter by creation date"),
    has_custom_rewards: Optional[bool] = Query(None, description="Filter by custom rewards"),
    skip: int = Query(0, ge=0, description="Skip items for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Limit items for pagination"),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to list all collections with advanced filtering."""
    try:
        # Build complex query with filters
        query = select(MythFactCollection)
        
        # Apply filters
        if category_id:
            query = query.where(MythFactCollection.category_id == category_id)
        if is_active is not None:
            query = query.where(MythFactCollection.is_active == is_active)
        if repeatability:
            query = query.where(MythFactCollection.repeatability == repeatability)
        if search:
            search_filter = or_(
                MythFactCollection.name.ilike(f"%{search}%"),
                MythFactCollection.description.ilike(f"%{search}%")
            )
            query = query.where(search_filter)
        if created_after:
            query = query.where(MythFactCollection.created_at >= created_after)
        if has_custom_rewards is not None:
            if has_custom_rewards:
                query = query.where(
                    or_(
                        MythFactCollection.custom_points_enabled == True,
                        MythFactCollection.custom_credits_enabled == True
                    )
                )
            else:
                query = query.where(
                    and_(
                        MythFactCollection.custom_points_enabled == False,
                        MythFactCollection.custom_credits_enabled == False
                    )
                )
        
        # Add pagination and ordering
        query = query.offset(skip).limit(limit).order_by(desc(MythFactCollection.created_at))
        
        result = await db.execute(query)
        collections = result.scalars().all()
        
        return [CollectionResponse.from_orm(collection) for collection in collections]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@router.get("/analytics/overview")
async def get_collections_analytics_overview(
    date_range: int = Query(30, ge=1, le=365, description="Days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive analytics overview for all collections."""
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=date_range)
        
        # Get total collections count
        total_collections_query = select(func.count(MythFactCollection.id)).where(
            MythFactCollection.is_active == True
        )
        total_collections_result = await db.execute(total_collections_query)
        total_collections = total_collections_result.scalar() or 0
        
        # Get total plays in date range
        total_plays_query = select(func.count(UserCollectionProgress.id)).where(
            and_(
                UserCollectionProgress.play_date >= start_date,
                UserCollectionProgress.play_date <= end_date
            )
        )
        total_plays_result = await db.execute(total_plays_query)
        total_plays = total_plays_result.scalar() or 0
        
        # Get completion rate
        completed_plays_query = select(func.count(UserCollectionProgress.id)).where(
            and_(
                UserCollectionProgress.play_date >= start_date,
                UserCollectionProgress.play_date <= end_date,
                UserCollectionProgress.completed == True
            )
        )
        completed_plays_result = await db.execute(completed_plays_query)
        completed_plays = completed_plays_result.scalar() or 0
        
        completion_rate = (completed_plays / total_plays * 100) if total_plays > 0 else 0
        
        # Get average score
        avg_score_query = select(func.avg(UserCollectionProgress.score_percentage)).where(
            and_(
                UserCollectionProgress.play_date >= start_date,
                UserCollectionProgress.play_date <= end_date,
                UserCollectionProgress.completed == True
            )
        )
        avg_score_result = await db.execute(avg_score_query)
        avg_score = avg_score_result.scalar() or 0
        
        # Get unique players
        unique_players_query = select(func.count(func.distinct(UserCollectionProgress.user_id))).where(
            and_(
                UserCollectionProgress.play_date >= start_date,
                UserCollectionProgress.play_date <= end_date
            )
        )
        unique_players_result = await db.execute(unique_players_query)
        unique_players = unique_players_result.scalar() or 0
        
        # Get top performing collections
        top_collections_query = text("""
            SELECT 
                c.id,
                c.name,
                COUNT(ucp.id) as play_count,
                COUNT(CASE WHEN ucp.completed = true THEN 1 END) as completion_count,
                ROUND(AVG(ucp.score_percentage), 2) as avg_score
            FROM myth_fact_collections c
            LEFT JOIN user_collection_progress ucp ON c.id = ucp.collection_id
                AND ucp.play_date >= :start_date AND ucp.play_date <= :end_date
            WHERE c.is_active = true
            GROUP BY c.id, c.name
            HAVING COUNT(ucp.id) > 0
            ORDER BY play_count DESC
            LIMIT 5
        """)
        
        top_collections_result = await db.execute(top_collections_query, {
            "start_date": start_date,
            "end_date": end_date
        })
        top_collections_rows = top_collections_result.fetchall()
        
        top_collections = []
        for row in top_collections_rows:
            top_collections.append({
                "id": row[0],
                "name": row[1],
                "play_count": row[2],
                "completion_count": row[3],
                "avg_score": float(row[4]) if row[4] else 0
            })
        
        return {
            "overview": {
                "total_collections": total_collections,
                "total_plays": total_plays,
                "completed_plays": completed_plays,
                "completion_rate": round(completion_rate, 2),
                "avg_score": round(float(avg_score), 2) if avg_score else 0,
                "unique_players": unique_players,
                "date_range": f"{start_date} to {end_date}"
            },
            "top_collections": top_collections
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/{collection_id}/analytics")
async def get_collection_detailed_analytics(
    collection_id: UUID,
    date_range: int = Query(30, ge=1, le=365, description="Days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed analytics for a specific collection."""
    try:
        # Verify collection exists
        collection_query = select(MythFactCollection).where(MythFactCollection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=date_range)
        
        # Get daily play statistics
        daily_stats_query = text("""
            SELECT 
                play_date,
                COUNT(*) as plays,
                COUNT(CASE WHEN completed = true THEN 1 END) as completions,
                ROUND(AVG(score_percentage), 2) as avg_score,
                ROUND(AVG(time_taken), 2) as avg_time
            FROM user_collection_progress
            WHERE collection_id = :collection_id
                AND play_date >= :start_date AND play_date <= :end_date
            GROUP BY play_date
            ORDER BY play_date DESC
        """)
        
        daily_stats_result = await db.execute(daily_stats_query, {
            "collection_id": str(collection_id),
            "start_date": start_date,
            "end_date": end_date
        })
        daily_stats_rows = daily_stats_result.fetchall()
        
        daily_stats = []
        for row in daily_stats_rows:
            daily_stats.append({
                "date": str(row[0]),
                "plays": row[1],
                "completions": row[2],
                "avg_score": float(row[3]) if row[3] else 0,
                "avg_time": float(row[4]) if row[4] else 0
            })
        
        # Get tier distribution
        tier_distribution_query = text("""
            SELECT 
                tier,
                COUNT(*) as count
            FROM user_collection_progress
            WHERE collection_id = :collection_id
                AND play_date >= :start_date AND play_date <= :end_date
                AND completed = true
            GROUP BY tier
            ORDER BY count DESC
        """)
        
        tier_distribution_result = await db.execute(tier_distribution_query, {
            "collection_id": str(collection_id),
            "start_date": start_date,
            "end_date": end_date
        })
        tier_distribution_rows = tier_distribution_result.fetchall()
        
        tier_distribution = {}
        for row in tier_distribution_rows:
            tier_distribution[row[0]] = row[1]
        
        return {
            "collection": {
                "id": collection.id,
                "name": collection.name,
                "description": collection.description,
                "repeatability": collection.repeatability,
                "cards_count": collection.cards_count
            },
            "analytics": {
                "date_range": f"{start_date} to {end_date}",
                "daily_stats": daily_stats,
                "tier_distribution": tier_distribution
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get collection analytics: {str(e)}")


@router.post("/{collection_id}/bulk-add-cards")
async def bulk_add_cards_to_collection(
    collection_id: UUID,
    card_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Bulk add multiple cards to a collection."""
    try:
        # Verify collection exists
        collection_query = select(MythFactCollection).where(MythFactCollection.id == collection_id)
        collection_result = await db.execute(collection_query)
        collection = collection_result.scalar_one_or_none()
        
        if not collection:
            raise HTTPException(status_code=404, detail="Collection not found")
        
        card_ids = card_data.get("card_ids", [])
        if not card_ids:
            raise HTTPException(status_code=400, detail="card_ids list is required")
        
        # Verify all cards exist
        cards_query = select(MythFact.id).where(MythFact.id.in_(card_ids))
        cards_result = await db.execute(cards_query)
        existing_card_ids = [row[0] for row in cards_result.fetchall()]
        
        if len(existing_card_ids) != len(card_ids):
            missing_ids = set(card_ids) - set(existing_card_ids)
            raise HTTPException(
                status_code=400, 
                detail=f"Cards not found: {list(missing_ids)}"
            )
        
        # Check which cards are already assigned
        existing_assignments_query = select(CollectionMythFact.myth_fact_id).where(
            and_(
                CollectionMythFact.collection_id == collection_id,
                CollectionMythFact.myth_fact_id.in_(card_ids)
            )
        )
        existing_assignments_result = await db.execute(existing_assignments_query)
        already_assigned = [row[0] for row in existing_assignments_result.fetchall()]
        
        # Filter out already assigned cards
        new_card_ids = [card_id for card_id in card_ids if card_id not in already_assigned]
        
        if not new_card_ids:
            return {
                "message": "No new cards to add - all provided cards are already in the collection",
                "already_assigned": len(already_assigned),
                "newly_added": 0
            }
        
        # Get current max order index
        max_order_query = select(func.max(CollectionMythFact.order_index)).where(
            CollectionMythFact.collection_id == collection_id
        )
        max_order_result = await db.execute(max_order_query)
        max_order = max_order_result.scalar() or 0
        
        # Create bulk assignments
        assignments = []
        for i, card_id in enumerate(new_card_ids):
            assignments.append(CollectionMythFact(
                collection_id=collection_id,
                myth_fact_id=card_id,
                order_index=max_order + i + 1
            ))
        
        db.add_all(assignments)
        
        # Update collection cards count
        collection.cards_count = collection.cards_count + len(new_card_ids)
        collection.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return {
            "message": "Cards added to collection successfully",
            "newly_added": len(new_card_ids),
            "already_assigned": len(already_assigned),
            "total_cards_in_collection": collection.cards_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to bulk add cards: {str(e)}")


@router.post("/{collection_id}/clone")
async def clone_collection(
    collection_id: UUID,
    clone_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Clone an existing collection with new name and optional modifications."""
    try:
        # Get original collection with cards
        original_query = select(MythFactCollection).options(
            selectinload(MythFactCollection.collection_cards)
        ).where(MythFactCollection.id == collection_id)
        original_result = await db.execute(original_query)
        original_collection = original_result.scalar_one_or_none()
        
        if not original_collection:
            raise HTTPException(status_code=404, detail="Original collection not found")
        
        new_name = clone_data.get("name")
        if not new_name:
            raise HTTPException(status_code=400, detail="new name is required for cloning")
        
        # Create new collection
        new_collection = MythFactCollection(
            category_id=original_collection.category_id,
            name=new_name,
            description=clone_data.get("description", f"Cloned from: {original_collection.name}"),
            is_active=clone_data.get("is_active", True),
            repeatability=clone_data.get("repeatability", original_collection.repeatability),
            custom_points_enabled=original_collection.custom_points_enabled,
            custom_points_bronze=original_collection.custom_points_bronze,
            custom_points_silver=original_collection.custom_points_silver,
            custom_points_gold=original_collection.custom_points_gold,
            custom_points_platinum=original_collection.custom_points_platinum,
            custom_credits_enabled=original_collection.custom_credits_enabled,
            custom_credits_bronze=original_collection.custom_credits_bronze,
            custom_credits_silver=original_collection.custom_credits_silver,
            custom_credits_gold=original_collection.custom_credits_gold,
            custom_credits_platinum=original_collection.custom_credits_platinum
        )
        
        db.add(new_collection)
        await db.flush()  # Get the new collection ID
        
        # Clone card assignments
        if clone_data.get("clone_cards", True):
            card_assignments = []
            for original_assignment in original_collection.collection_cards:
                card_assignments.append(CollectionMythFact(
                    collection_id=new_collection.id,
                    myth_fact_id=original_assignment.myth_fact_id,
                    order_index=original_assignment.order_index
                ))
            
            db.add_all(card_assignments)
            new_collection.cards_count = len(card_assignments)
        
        await db.commit()
        await db.refresh(new_collection)
        
        return {
            "message": "Collection cloned successfully",
            "original_collection": {
                "id": original_collection.id,
                "name": original_collection.name
            },
            "new_collection": {
                "id": new_collection.id,
                "name": new_collection.name,
                "cards_count": new_collection.cards_count
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clone collection: {str(e)}")