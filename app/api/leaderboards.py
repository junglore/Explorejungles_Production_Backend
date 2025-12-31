"""
Leaderboards endpoints for the API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import selectinload
from typing import Optional, List
import logging
from datetime import datetime, timedelta

from ..db.database import get_db
from ..core.security import get_current_user, get_current_user_optional
from ..models.user import User
from ..models.quiz_extended import Quiz, UserQuizResult
from ..models.user_quiz_best_score import UserQuizBestScore
from ..models.weekly_leaderboard_cache import WeeklyLeaderboardCache
from ..services.settings_service import SettingsService
from ..schemas.leaderboard import (
    LeaderboardRankingResponse,
    LeaderboardStatsResponse,
    GeneralLeaderboardStatsResponse,
    UserRankingResponse,
    LeaderboardParticipantResponse
)
from ..utils.date_utils import get_current_week_start, get_current_month_start

router = APIRouter()
logger = logging.getLogger(__name__)

def calculate_week_number(date: datetime) -> int:
    """Calculate ISO week number for a given date."""
    return date.isocalendar()[1]


@router.get("/weekly", response_model=LeaderboardRankingResponse)
async def get_weekly_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the weekly leaderboard rankings based on POINTS earned from quizzes
    """
    try:
        # Initialize settings service
        settings = SettingsService(db)
        
        # Check if leaderboards are enabled
        leaderboard_settings = await settings.get_leaderboard_settings()
        if not leaderboard_settings['public_enabled']:
            raise HTTPException(status_code=403, detail="Leaderboards are currently disabled")
        
        # Apply max entries limit from settings
        max_entries = leaderboard_settings['max_entries']
        limit = min(limit, max_entries)
        
        logger.info(f"Getting weekly leaderboard with limit={limit}, offset={offset}")
        
        # Get current week start
        current_week_start = get_current_week_start()
        current_week_start_date = current_week_start.date()
        
        logger.info("Using real-time calculation for weekly leaderboard")
        
        # Calculate weekly scores from UserQuizResult based on POINTS
        weekly_scores_query = select(
            UserQuizResult.user_id,
            User.username,
            User.full_name,
            User.avatar_url,
            func.sum(UserQuizResult.points_earned).label('total_points'),
            func.count(UserQuizResult.id).label('quizzes_completed'),
            func.avg(UserQuizResult.percentage).label('average_score')
        ).select_from(
            UserQuizResult.__table__.join(User.__table__, UserQuizResult.user_id == User.id)
        ).where(
            UserQuizResult.completed_at >= current_week_start,
            UserQuizResult.completed_at < current_week_start + timedelta(days=7)
        ).group_by(
            UserQuizResult.user_id, User.username, User.full_name, User.avatar_url
        ).order_by(
            func.sum(UserQuizResult.points_earned).desc(),
            User.username.asc()
        ).limit(limit).offset(offset)
        
        result = await db.execute(weekly_scores_query)
        weekly_scores = result.all()
        
        participants = []
        current_user_rank = None
        
        for rank, score_data in enumerate(weekly_scores, start=offset + 1):
            # Apply privacy settings
            display_name = score_data.username
            full_name = score_data.full_name
            avatar_url = score_data.avatar_url
            
            if leaderboard_settings['anonymous_mode']:
                display_name = f"Player {rank}"
                full_name = None
                avatar_url = None
            elif not leaderboard_settings['show_real_names']:
                full_name = None
            
            participant = LeaderboardParticipantResponse(
                user_id=score_data.user_id,
                username=display_name,
                full_name=full_name,
                avatar_url=avatar_url,
                rank=rank,
                score=int(score_data.total_points or 0),
                quizzes_completed=score_data.quizzes_completed,
                average_score=round(float(score_data.average_score or 0), 1),
                is_current_user=bool(current_user and score_data.user_id == current_user.id)
            )
            participants.append(participant)
            
            if current_user and score_data.user_id == current_user.id:
                current_user_rank = rank
        
        # Get total participants count
        total_count_query = select(func.count(distinct(UserQuizResult.user_id))).where(
            UserQuizResult.completed_at >= current_week_start,
            UserQuizResult.completed_at < current_week_start + timedelta(days=7)
        )
        total_participants_result = await db.execute(total_count_query)
        total_participants = total_participants_result.scalar() or 0
        
        return LeaderboardRankingResponse(
            type="weekly",
            period_start=current_week_start,
            participants=participants,
            total_participants=total_participants,
            current_user_rank=current_user_rank
        )
        
    except Exception as e:
        logger.error(f"Error getting weekly leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get weekly leaderboard")


@router.get("/monthly", response_model=LeaderboardRankingResponse)
async def get_monthly_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the monthly leaderboard rankings based on POINTS earned from quizzes
    """
    try:
        # Initialize settings service
        settings = SettingsService(db)
        
        # Check if leaderboards are enabled
        leaderboard_settings = await settings.get_leaderboard_settings()
        if not leaderboard_settings['public_enabled']:
            raise HTTPException(status_code=403, detail="Leaderboards are currently disabled")
        
        # Apply max entries limit from settings
        max_entries = leaderboard_settings['max_entries']
        limit = min(limit, max_entries)
        
        logger.info(f"Getting monthly leaderboard with limit={limit}, offset={offset}")
        
        # Calculate current month boundaries
        current_month_start = get_current_month_start()
        next_month = current_month_start.replace(day=28) + timedelta(days=4)
        current_month_end = next_month - timedelta(days=next_month.day)
        
        logger.info(f"Monthly period: {current_month_start} to {current_month_end}")
        
        # Calculate monthly scores from UserQuizResult based on POINTS
        monthly_scores_result = await db.execute(
            select(
                UserQuizResult.user_id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.sum(UserQuizResult.points_earned).label('total_points'),
                func.count(UserQuizResult.id).label('quizzes_completed'),
                func.avg(UserQuizResult.percentage).label('average_score')
            )
            .select_from(UserQuizResult.__table__.join(User.__table__, UserQuizResult.user_id == User.id))
            .where(UserQuizResult.completed_at >= current_month_start)
            .where(UserQuizResult.completed_at < current_month_end)
            .group_by(UserQuizResult.user_id, User.username, User.full_name, User.avatar_url)
            .order_by(func.sum(UserQuizResult.points_earned).desc(), User.username.asc())
            .limit(limit)
            .offset(offset)
        )
        monthly_scores = monthly_scores_result.all()
        
        logger.info(f"Found {len(monthly_scores)} monthly leaderboard entries")
        participants = []
        current_user_rank = None
        
        for rank, score_data in enumerate(monthly_scores, start=offset + 1):
            # Apply privacy settings
            display_name = score_data.username
            full_name = score_data.full_name
            avatar_url = score_data.avatar_url
            
            if leaderboard_settings['anonymous_mode']:
                display_name = f"Player {rank}"
                full_name = None
                avatar_url = None
            elif not leaderboard_settings['show_real_names']:
                full_name = None
            
            participant = LeaderboardParticipantResponse(
                user_id=score_data.user_id,
                username=display_name,
                full_name=full_name,
                avatar_url=avatar_url,
                rank=rank,
                score=int(score_data.total_points or 0),
                quizzes_completed=int(score_data.quizzes_completed or 0),
                average_score=float(score_data.average_score or 0),
                is_current_user=bool(current_user and score_data.user_id == current_user.id)
            )
            participants.append(participant)
            
            if current_user and score_data.user_id == current_user.id:
                current_user_rank = rank
        
        # Get total participants count for the month
        total_participants_result = await db.execute(
            select(func.count(distinct(UserQuizResult.user_id)))
            .where(UserQuizResult.completed_at >= current_month_start)
            .where(UserQuizResult.completed_at < current_month_end)
        )
        total_participants = total_participants_result.scalar() or 0
        
        return LeaderboardRankingResponse(
            type="monthly",
            period_start=current_month_start,
            participants=participants,
            total_participants=total_participants,
            current_user_rank=current_user_rank
        )
        
    except Exception as e:
        logger.error(f"Error getting monthly leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get monthly leaderboard")


@router.get("/alltime", response_model=LeaderboardRankingResponse)
async def get_alltime_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the all-time leaderboard rankings based on POINTS earned from quizzes
    """
    try:
        # Initialize settings service
        settings = SettingsService(db)
        
        # Check if leaderboards are enabled
        leaderboard_settings = await settings.get_leaderboard_settings()
        if not leaderboard_settings['public_enabled']:
            raise HTTPException(status_code=403, detail="Leaderboards are currently disabled")
        
        # Apply max entries limit from settings
        max_entries = leaderboard_settings['max_entries']
        limit = min(limit, max_entries)
        
        logger.info(f"Getting all-time leaderboard with limit={limit}, offset={offset}")
        
        # Calculate all-time scores from UserQuizResult based on POINTS
        alltime_query = select(
            UserQuizResult.user_id,
            User.username,
            User.full_name,
            User.avatar_url,
            func.sum(UserQuizResult.points_earned).label('total_points'),
            func.count(UserQuizResult.id).label('quizzes_completed'),
            func.avg(UserQuizResult.percentage).label('average_score')
        ).select_from(
            UserQuizResult.__table__.join(User.__table__, UserQuizResult.user_id == User.id)
        ).group_by(
            UserQuizResult.user_id, User.username, User.full_name, User.avatar_url
        ).order_by(
            func.sum(UserQuizResult.points_earned).desc(),
            User.username.asc()
        ).limit(limit).offset(offset)
        
        result = await db.execute(alltime_query)
        alltime_scores = result.all()
        
        participants = []
        current_user_rank = None
        
        for rank, score_data in enumerate(alltime_scores, start=offset + 1):
            # Apply privacy settings
            display_name = score_data.username
            full_name = score_data.full_name
            avatar_url = score_data.avatar_url
            
            if leaderboard_settings['anonymous_mode']:
                display_name = f"Player {rank}"
                full_name = None
                avatar_url = None
            elif not leaderboard_settings['show_real_names']:
                full_name = None
            
            participant = LeaderboardParticipantResponse(
                user_id=score_data.user_id,
                username=display_name,
                full_name=full_name,
                avatar_url=avatar_url,
                rank=rank,
                score=int(score_data.total_points or 0),
                quizzes_completed=score_data.quizzes_completed,
                average_score=round(float(score_data.average_score or 0), 1),
                is_current_user=bool(current_user and score_data.user_id == current_user.id)
            )
            participants.append(participant)
            
            if current_user and score_data.user_id == current_user.id:
                current_user_rank = rank
        
        # Get total participants count
        total_participants_result = await db.execute(
            select(func.count(distinct(UserQuizResult.user_id)))
        )
        total_participants = total_participants_result.scalar() or 0
        
        return LeaderboardRankingResponse(
            type="alltime",
            period_start=None,
            participants=participants,
            total_participants=total_participants,
            current_user_rank=current_user_rank
        )
        
    except Exception as e:
        logger.error(f"Error getting all-time leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get all-time leaderboard")


@router.get("/stats", response_model=GeneralLeaderboardStatsResponse)
async def get_leaderboard_stats(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get general leaderboard statistics
    """
    try:
        # Get total participants
        total_participants_result = await db.execute(
            select(func.count(distinct(UserQuizResult.user_id)))
        )
        total_participants = total_participants_result.scalar() or 0
        
        # Get total quizzes completed
        total_quizzes_result = await db.execute(
            select(func.count(UserQuizResult.id))
        )
        total_quizzes = total_quizzes_result.scalar() or 0
        
        return GeneralLeaderboardStatsResponse(
            total_participants=total_participants,
            total_quizzes_completed=total_quizzes,
            last_updated=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Error getting leaderboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get leaderboard stats")


@router.get("/user-ranking", response_model=UserRankingResponse)
async def get_user_ranking(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's ranking across all leaderboards
    """
    try:
        # Get user's rankings for different time periods
        current_week_start = get_current_week_start()
        current_month_start = get_current_month_start()
        
        # Weekly ranking based on POINTS - get user's weekly total first
        user_weekly_points_query = select(func.coalesce(func.sum(UserQuizResult.points_earned), 0)).where(
            UserQuizResult.user_id == current_user.id,
            UserQuizResult.completed_at >= current_week_start
        )
        user_weekly_points_result = await db.execute(user_weekly_points_query)
        user_weekly_points = user_weekly_points_result.scalar() or 0
        
        # Count users with higher weekly points
        weekly_rank_query = select(func.count(distinct(UserQuizResult.user_id))).select_from(
            select(UserQuizResult.user_id, func.sum(UserQuizResult.points_earned).label('total_points'))
            .where(UserQuizResult.completed_at >= current_week_start)
            .group_by(UserQuizResult.user_id)
            .having(func.sum(UserQuizResult.points_earned) > user_weekly_points)
            .subquery()
        )
        weekly_rank_result = await db.execute(weekly_rank_query)
        weekly_rank = (weekly_rank_result.scalar() or 0) + 1
        
        # Monthly ranking based on POINTS - get user's monthly total first
        user_monthly_points_query = select(func.coalesce(func.sum(UserQuizResult.points_earned), 0)).where(
            UserQuizResult.user_id == current_user.id,
            UserQuizResult.completed_at >= current_month_start
        )
        user_monthly_points_result = await db.execute(user_monthly_points_query)
        user_monthly_points = user_monthly_points_result.scalar() or 0
        
        # Count users with higher monthly points
        monthly_rank_query = select(func.count(distinct(UserQuizResult.user_id))).select_from(
            select(UserQuizResult.user_id, func.sum(UserQuizResult.points_earned).label('total_points'))
            .where(UserQuizResult.completed_at >= current_month_start)
            .group_by(UserQuizResult.user_id)
            .having(func.sum(UserQuizResult.points_earned) > user_monthly_points)
            .subquery()
        )
        monthly_rank_result = await db.execute(monthly_rank_query)
        monthly_rank = (monthly_rank_result.scalar() or 0) + 1
        
        # All-time ranking based on POINTS - get user's total first
        user_alltime_points_query = select(func.coalesce(func.sum(UserQuizResult.points_earned), 0)).where(
            UserQuizResult.user_id == current_user.id
        )
        user_alltime_points_result = await db.execute(user_alltime_points_query)
        user_alltime_points = user_alltime_points_result.scalar() or 0
        
        # Count users with higher all-time points
        alltime_rank_query = select(func.count(distinct(UserQuizResult.user_id))).select_from(
            select(UserQuizResult.user_id, func.sum(UserQuizResult.points_earned).label('total_points'))
            .group_by(UserQuizResult.user_id)
            .having(func.sum(UserQuizResult.points_earned) > user_alltime_points)
            .subquery()
        )
        alltime_rank_result = await db.execute(alltime_rank_query)
        alltime_rank = (alltime_rank_result.scalar() or 0) + 1
        
        return UserRankingResponse(
            user_id=current_user.id,
            username=current_user.username,
            weekly_rank=weekly_rank,
            monthly_rank=monthly_rank,
            alltime_rank=alltime_rank
        )
        
    except Exception as e:
        logger.error(f"Error getting user ranking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user ranking")