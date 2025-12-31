"""
Analytics API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.db.database import get_db
from app.services.analytics import analytics_service
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get dashboard metrics (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access analytics"
        )
    
    try:
        metrics = await analytics_service.get_dashboard_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard metrics: {str(e)}"
        )

@router.get("/content")
async def get_content_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user)
):
    """Get content analytics (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access analytics"
        )
    
    try:
        analytics = await analytics_service.get_content_analytics(days=days)
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get content analytics: {str(e)}"
        )

@router.get("/media")
async def get_media_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user)
):
    """Get media analytics (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access analytics"
        )
    
    try:
        analytics = await analytics_service.get_media_analytics(days=days)
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get media analytics: {str(e)}"
        )

@router.get("/realtime")
async def get_realtime_metrics(
    current_user: User = Depends(get_current_user)
):
    """Get real-time metrics (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can access analytics"
        )
    
    try:
        metrics = await analytics_service.get_real_time_metrics()
        return metrics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get real-time metrics: {str(e)}"
        )

@router.post("/track/page-view")
async def track_page_view(
    content_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Track page view (Public endpoint)"""
    
    try:
        await analytics_service.track_page_view(content_id=content_id)
        return {"message": "Page view tracked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track page view: {str(e)}"
        )

@router.post("/track/media-interaction")
async def track_media_interaction(
    media_id: str,
    interaction_type: str = Query(..., description="Type of interaction (view, download, share)"),
    db: AsyncSession = Depends(get_db)
):
    """Track media interaction (Public endpoint)"""
    
    if interaction_type not in ["view", "download", "share"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid interaction type. Must be 'view', 'download', or 'share'"
        )
    
    try:
        await analytics_service.track_media_interaction(
            media_id=media_id,
            interaction_type=interaction_type
        )
        return {"message": "Media interaction tracked successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to track media interaction: {str(e)}"
        )