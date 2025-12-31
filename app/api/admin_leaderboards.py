"""
Admin endpoints for leaderboard management
Provides manual control over leaderboard jobs and maintenance
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import datetime

from ..db.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..services.leaderboard_jobs import job_manager
from ..models.weekly_leaderboard_cache import WeeklyLeaderboardCache

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/leaderboards/refresh")
async def refresh_leaderboards(
    leaderboard_type: Optional[str] = Query(None, description="Type of leaderboard to refresh (weekly, monthly, or all)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually refresh leaderboard caches
    Only accessible by superusers
    """
    try:
        logger.info(f"Admin {current_user.username} requested leaderboard refresh: {leaderboard_type}")
        
        if leaderboard_type and leaderboard_type not in ['weekly', 'monthly', 'all']:
            raise HTTPException(
                status_code=400, 
                detail="Invalid leaderboard type. Must be 'weekly', 'monthly', or 'all'"
            )
        
        # Force refresh through job manager
        await job_manager.force_refresh(
            leaderboard_type if leaderboard_type != 'all' else None
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": f"Leaderboard refresh completed for {leaderboard_type or 'all'} leaderboards",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error refreshing leaderboards: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh leaderboards: {str(e)}")

@router.post("/leaderboards/reset-weekly")
async def reset_weekly_leaderboards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually reset weekly leaderboards
    Only accessible by superusers
    """
    try:
        logger.info(f"Admin {current_user.username} requested weekly leaderboard reset")
        
        await job_manager.reset_weekly_leaderboards()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Weekly leaderboard reset completed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error resetting weekly leaderboards: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset weekly leaderboards: {str(e)}")

@router.post("/leaderboards/reset-monthly")
async def reset_monthly_leaderboards(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually reset monthly leaderboards
    Only accessible by superusers
    """
    try:
        logger.info(f"Admin {current_user.username} requested monthly leaderboard reset")
        
        await job_manager.reset_monthly_leaderboards()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Monthly leaderboard reset completed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error resetting monthly leaderboards: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset monthly leaderboards: {str(e)}")

@router.post("/leaderboards/cleanup")
async def cleanup_old_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Manually cleanup old leaderboard data
    Only accessible by superusers
    """
    try:
        logger.info(f"Admin {current_user.username} requested leaderboard cleanup")
        
        await job_manager.cleanup_old_data()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Leaderboard cleanup completed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error cleaning up leaderboard data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to cleanup leaderboard data: {str(e)}")

@router.get("/leaderboards/status")
async def get_leaderboard_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current leaderboard system status
    Only accessible by superusers
    """
    try:
        # Get cache statistics
        weekly_cache_count = db.query(WeeklyLeaderboardCache).count()
        monthly_cache_count = 0  # Monthly cache disabled
        
        # Get latest cache update times
        latest_weekly = db.query(WeeklyLeaderboardCache.last_calculated_at)\
            .order_by(WeeklyLeaderboardCache.last_calculated_at.desc())\
            .first()
        
        latest_monthly = None  # Monthly cache disabled
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "job_manager_running": job_manager.is_running,
                "active_tasks": len(job_manager.tasks),
                "cache_stats": {
                    "weekly_entries": weekly_cache_count,
                    "monthly_entries": monthly_cache_count,
                    "latest_weekly_update": latest_weekly[0].isoformat() if latest_weekly else None,
                    "latest_monthly_update": latest_monthly[0].isoformat() if latest_monthly else None
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error getting leaderboard status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard status: {str(e)}")

@router.post("/leaderboards/start-jobs")
async def start_leaderboard_jobs(
    current_user: User = Depends(get_current_user)
):
    """
    Start leaderboard background jobs
    Only accessible by superusers
    """
    try:
        logger.info(f"Admin {current_user.username} requested to start leaderboard jobs")
        
        if job_manager.is_running:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Leaderboard jobs are already running",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        await job_manager.start()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Leaderboard background jobs started",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error starting leaderboard jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start leaderboard jobs: {str(e)}")

@router.post("/leaderboards/stop-jobs")
async def stop_leaderboard_jobs(
    current_user: User = Depends(get_current_user)
):
    """
    Stop leaderboard background jobs
    Only accessible by superusers
    """
    try:
        logger.info(f"Admin {current_user.username} requested to stop leaderboard jobs")
        
        if not job_manager.is_running:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Leaderboard jobs are already stopped",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        
        await job_manager.stop()
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Leaderboard background jobs stopped",
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error stopping leaderboard jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to stop leaderboard jobs: {str(e)}")
