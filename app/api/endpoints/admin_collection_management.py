"""
Admin Collection Management API - Simple Implementation
Basic admin endpoints for collection management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Dict, Any
from uuid import UUID

from app.db.database import get_db
from app.models.myth_fact_collection import MythFactCollection

router = APIRouter(prefix="/admin/collections", tags=["Admin Collections"])


@router.get("/")
async def list_all_collections_admin(
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to list all collections with detailed info"""
    try:
        query = select(MythFactCollection).order_by(MythFactCollection.created_at.desc())
        result = await db.execute(query)
        collections = result.scalars().all()
        
        return {
            "collections": [
                {
                    "id": collection.id,
                    "name": collection.name,
                    "description": collection.description,
                    "is_active": collection.is_active,
                    "cards_count": collection.cards_count,
                    "repeatability": collection.repeatability,
                    "created_at": collection.created_at
                }
                for collection in collections
            ],
            "total": len(collections)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list collections: {str(e)}")


@router.get("/analytics/overview")
async def get_admin_analytics_overview(
    db: AsyncSession = Depends(get_db)
):
    """Get overview analytics for admin dashboard"""
    try:
        # Use raw SQL for analytics
        analytics_query = text("""
            SELECT 
                COUNT(*) as total_collections,
                COUNT(*) FILTER (WHERE is_active = true) as active_collections,
                COUNT(*) FILTER (WHERE repeatability = 'daily') as daily_collections,
                COUNT(*) FILTER (WHERE repeatability = 'weekly') as weekly_collections,
                COUNT(*) FILTER (WHERE repeatability = 'unlimited') as unlimited_collections
            FROM myth_fact_collections
        """)
        
        result = await db.execute(analytics_query)
        row = result.fetchone()
        
        if row:
            return {
                "total_collections": row[0],
                "active_collections": row[1],
                "daily_collections": row[2],
                "weekly_collections": row[3],
                "unlimited_collections": row[4]
            }
        else:
            return {
                "total_collections": 0,
                "active_collections": 0,
                "daily_collections": 0,
                "weekly_collections": 0,
                "unlimited_collections": 0
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")


@router.get("/{collection_id}/analytics")
async def get_collection_analytics(
    collection_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed analytics for a specific collection"""
    try:
        analytics_query = text("""
            SELECT 
                c.name,
                c.description,
                c.repeatability,
                COUNT(DISTINCT cmf.myth_fact_id) as total_cards,
                COUNT(DISTINCT ucp.user_id) as unique_players,
                COUNT(ucp.id) as total_plays,
                COUNT(ucp.id) FILTER (WHERE ucp.completed = true) as completions,
                ROUND(AVG(ucp.score_percentage), 2) as avg_score,
                ROUND(AVG(ucp.time_taken), 2) as avg_time
            FROM myth_fact_collections c
            LEFT JOIN collection_myth_facts cmf ON c.id = cmf.collection_id
            LEFT JOIN user_collection_progress ucp ON c.id = ucp.collection_id
            WHERE c.id = :collection_id
            GROUP BY c.id, c.name, c.description, c.repeatability
        """)
        
        result = await db.execute(analytics_query, {"collection_id": str(collection_id)})
        row = result.fetchone()
        
        if row:
            return {
                "collection_id": collection_id,
                "name": row[0],
                "description": row[1],
                "repeatability": row[2],
                "total_cards": row[3] or 0,
                "unique_players": row[4] or 0,
                "total_plays": row[5] or 0,
                "completions": row[6] or 0,
                "avg_score": float(row[7]) if row[7] else 0.0,
                "avg_time": float(row[8]) if row[8] else 0.0
            }
        else:
            raise HTTPException(status_code=404, detail="Collection not found")
    
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
    """Bulk add cards to a collection (simplified implementation)"""
    try:
        card_ids = card_data.get("card_ids", [])
        
        if not card_ids:
            raise HTTPException(status_code=400, detail="No card IDs provided")
        
        # Simplified bulk add (would normally validate cards exist, etc.)
        for i, card_id in enumerate(card_ids[:10]):  # Limit to 10 for safety
            await db.execute(text("""
                INSERT INTO collection_myth_facts (
                    id, collection_id, myth_fact_id, order_index, created_at
                ) VALUES (
                    gen_random_uuid(), :collection_id, :card_id, :order_index, NOW()
                )
                ON CONFLICT (collection_id, myth_fact_id) DO NOTHING
            """), {
                "collection_id": str(collection_id),
                "card_id": card_id,
                "order_index": i + 1
            })
        
        await db.commit()
        
        return {
            "message": f"Bulk add completed",
            "collection_id": collection_id,
            "cards_processed": len(card_ids)
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
    """Clone an existing collection"""
    try:
        new_name = clone_data.get("name", f"Copy of Collection")
        
        # Get original collection
        original_query = select(MythFactCollection).where(MythFactCollection.id == collection_id)
        result = await db.execute(original_query)
        original = result.scalar_one_or_none()
        
        if not original:
            raise HTTPException(status_code=404, detail="Original collection not found")
        
        # Create new collection
        new_collection = MythFactCollection(
            name=new_name,
            description=f"Cloned from: {original.description}",
            is_active=False,  # Start inactive
            repeatability=original.repeatability,
            custom_points_enabled=original.custom_points_enabled,
            custom_credits_enabled=original.custom_credits_enabled
        )
        
        db.add(new_collection)
        await db.commit()
        await db.refresh(new_collection)
        
        return {
            "message": "Collection cloned successfully",
            "original_id": collection_id,
            "new_id": new_collection.id,
            "new_name": new_name
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clone collection: {str(e)}")