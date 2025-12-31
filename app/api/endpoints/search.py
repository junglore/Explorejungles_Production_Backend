"""
Search API endpoints
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from app.db.database import get_db
from app.services.search import search_service
from app.core.cache import cache_manager

router = APIRouter()

@router.get("/content")
async def search_content(
    q: str = Query(..., description="Search query", min_length=2),
    category_id: Optional[str] = Query(None, description="Filter by category ID"),
    content_type: Optional[str] = Query(None, description="Filter by content type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db)
):
    """Search content with advanced filtering"""
    
    offset = (page - 1) * limit
    
    try:
        results = await search_service.search_content(
            db=db,
            query=q,
            category_id=category_id,
            content_type=content_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "query": q,
            "results": results["results"],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": results["total"],
                "has_more": results.get("has_more", False),
                "total_pages": (results["total"] + limit - 1) // limit
            },
            "filters": {
                "category_id": category_id,
                "content_type": content_type
            },
            "suggestions": results.get("suggestions", []),
            "processed_terms": results.get("processed_terms", [])
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/media")
async def search_media(
    q: str = Query(..., description="Search query", min_length=2),
    media_type: Optional[str] = Query(None, description="Filter by media type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    db: AsyncSession = Depends(get_db)
):
    """Search media files"""
    
    offset = (page - 1) * limit
    
    try:
        results = await search_service.search_media(
            db=db,
            query=q,
            media_type=media_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "query": q,
            "results": results["results"],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": results["total"],
                "has_more": results.get("has_more", False),
                "total_pages": (results["total"] + limit - 1) // limit
            },
            "filters": {
                "media_type": media_type
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Media search failed: {str(e)}"
        )

@router.get("/suggestions")
async def get_search_suggestions(
    q: str = Query(..., description="Partial search query", min_length=1),
    limit: int = Query(5, ge=1, le=10, description="Number of suggestions"),
    db: AsyncSession = Depends(get_db)
):
    """Get search suggestions for autocomplete"""
    
    cache_key = f"search:suggestions:{q}:{limit}"
    cached_suggestions = await cache_manager.get(cache_key)
    
    if cached_suggestions:
        return {"query": q, "suggestions": cached_suggestions}
    
    try:
        # Get suggestions from search service
        suggestions = await search_service._generate_suggestions(db, q, [q])
        
        # Cache suggestions for 1 hour
        await cache_manager.set(cache_key, suggestions, ttl=3600)
        
        return {
            "query": q,
            "suggestions": suggestions[:limit]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get suggestions: {str(e)}"
        )

@router.get("/popular")
async def get_popular_searches(
    limit: int = Query(10, ge=1, le=20, description="Number of popular searches"),
    db: AsyncSession = Depends(get_db)
):
    """Get popular search terms"""
    
    cache_key = f"search:popular:{limit}"
    cached_popular = await cache_manager.get(cache_key)
    
    if cached_popular:
        return {"popular_searches": cached_popular}
    
    try:
        # This would typically come from search analytics
        # For now, return popular content titles as search terms
        from sqlalchemy import select, func
        from app.models.content import Content
        
        query = (
            select(Content.title)
            .where(Content.status == 'PUBLISHED')
            .order_by(Content.view_count.desc())
            .limit(limit * 2)
        )
        
        result = await db.execute(query)
        titles = [row[0] for row in result.fetchall() if row[0]]
        
        # Extract keywords from titles
        popular_terms = []
        for title in titles:
            words = search_service.preprocess_query(title)
            popular_terms.extend(words)
        
        # Get most common terms
        from collections import Counter
        term_counts = Counter(popular_terms)
        popular_searches = [term for term, count in term_counts.most_common(limit)]
        
        # Cache for 6 hours
        await cache_manager.set(cache_key, popular_searches, ttl=21600)
        
        return {"popular_searches": popular_searches}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get popular searches: {str(e)}"
        )