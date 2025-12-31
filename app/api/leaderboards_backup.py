"""
Leaderboards endpoints for the API
"""
from fastapi import API            for index, entry in enumerate(cached_leaderboard, start=offset + 1):
                # Since we're ordering by total_points_earned DESC, use the index as the correct rank
                rank = index
                
                participant = LeaderboardParticipantResponse(
                    user_id=entry.user_id,
                    username=entry.user.username,
                    full_name=entry.user.full_name,
                    avatar_url=entry.user.avatar_url,
                    rank=rank,
                    score=entry.total_points_earned or 0,ends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import selectinload
from typing import Optional, List
import logging
from datetime import datetime, timedelta

from ..db.database import get_db
from ..core.security import get_current_user
from ..models.user import User
from ..models.quiz import Quiz, UserQuizResult
from ..models.user_quiz_best_score import UserQuizBestScore
from ..models.weekly_leaderboard_cache import WeeklyLeaderboardCache
from ..schemas.leaderboard import (
    LeaderboardRankingResponse,
    LeaderboardStatsResponse,
    UserRankingResponse,
    LeaderboardParticipantResponse
)
from ..utils.date_utils import get_current_week_start, get_current_month_start

router = APIRouter()
logger = logging.getLogger(__name__)

def calculate_week_number(date: datetime) -> int:
    """Calculate ISO week number for a given date."""
    return date.isocalendar()[1]

def calculate_month_number(date: datetime) -> int:
    """Calculate month number for a given date."""
    return date.month

@router.get("/weekly", response_model=LeaderboardRankingResponse)
async def get_weekly_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the weekly leaderboard rankings
    """
    try:
        logger.info(f"Getting weekly leaderboard with limit={limit}, offset={offset}")
        
        # Get current week start
        current_week_start = get_current_week_start()
        current_week = calculate_week_number(current_week_start)
        
        # First try to get from cache
        cached_leaderboard_query = select(WeeklyLeaderboardCache).options(
            selectinload(WeeklyLeaderboardCache.user)
        ).where(
            WeeklyLeaderboardCache.week_start_date == current_week_start
        ).order_by(WeeklyLeaderboardCache.total_points_earned.desc()).limit(limit).offset(offset)
        
        result = await db.execute(cached_leaderboard_query)
        cached_leaderboard = result.scalars().all()
        
        if cached_leaderboard:
            logger.info(f"Found {len(cached_leaderboard)} cached weekly leaderboard entries")
            participants = []
            current_user_rank = None
            
            for index, entry in enumerate(cached_leaderboard, start=offset + 1):
                # Since we're ordering by total_credits_earned DESC, use the index as the correct rank
                rank = index
                
                participant = LeaderboardParticipantResponse(
                    user_id=entry.user_id,
                    username=entry.user.username,
                    full_name=entry.user.full_name,
                    avatar_url=entry.user.avatar_url,
                    rank=rank,
                    score=entry.total_points_earned or 0,
                    quizzes_completed=entry.quizzes_completed or 0,
                    average_score=entry.average_percentage or 0.0,
                    is_current_user=(current_user and entry.user_id == current_user.id)
                )
                participants.append(participant)
                
                if current_user and entry.user_id == current_user.id:
                    current_user_rank = rank
            
            # Get total participants count
            total_participants_query = select(func.count(WeeklyLeaderboardCache.id)).where(
                WeeklyLeaderboardCache.week_start_date == current_week_start
            )
            total_result = await db.execute(total_participants_query)
            total_participants = total_result.scalar()
            
            return LeaderboardRankingResponse(
                type="weekly",
                period_start=current_week_start,
                participants=participants,
                total_participants=total_participants,
                current_user_rank=current_user_rank
            )
        
        # Fallback to real-time calculation if no cache
        logger.info("No cached weekly leaderboard found, calculating real-time")
        
        # Calculate weekly scores from UserQuizResult
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
            func.sum(UserQuizResult.points_earned).desc()
        ).limit(limit).offset(offset)
        
        result = await db.execute(weekly_scores_query)
        weekly_scores = result.all()
        
        participants = []
        current_user_rank = None
        
        for rank, score_data in enumerate(weekly_scores, start=offset + 1):
            participant = LeaderboardParticipantResponse(
                user_id=score_data.user_id,
                username=score_data.username,
                full_name=score_data.full_name,
                avatar_url=score_data.avatar_url,
                rank=rank,
                score=int(score_data.total_credits or 0),
                quizzes_completed=score_data.quizzes_completed,
                average_score=round(float(score_data.average_score or 0), 1),
                is_current_user=(current_user and score_data.user_id == current_user.id)
            )
            participants.append(participant)
            
            if current_user and score_data.user_id == current_user.id:
                current_user_rank = rank
        
        total_participants_result = await db.execute(
            select(func.count(func.distinct(UserQuizResult.user_id)))
            .where(UserQuizResult.completed_at >= current_week_start)
            .where(UserQuizResult.completed_at < current_week_start + timedelta(days=7))
        )
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
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the monthly leaderboard rankings
    """
    try:
        logger.info(f"Getting monthly leaderboard with limit={limit}, offset={offset}")
        
        # Get current month start and end dates
        current_month_start = get_current_month_start()
        current_month_end = current_month_start.replace(
            month=current_month_start.month + 1 if current_month_start.month < 12 else 1,
            year=current_month_start.year if current_month_start.month < 12 else current_month_start.year + 1
        )
        
        # Calculate real-time monthly rankings
        logger.info("Calculating real-time monthly leaderboard")
        monthly_scores_result = await db.execute(
            select(
                UserQuizResult.user_id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.sum(UserQuizResult.credits_earned).label('total_credits'),
                func.count(UserQuizResult.id).label('quizzes_completed'),
                func.avg(UserQuizResult.percentage).label('average_score')
            )
            .select_from(UserQuizResult.__table__.join(User.__table__, UserQuizResult.user_id == User.id))
            .where(UserQuizResult.completed_at >= current_month_start)
            .where(UserQuizResult.completed_at < current_month_end)
            .group_by(UserQuizResult.user_id, User.username, User.full_name, User.avatar_url)
            .order_by(func.sum(UserQuizResult.credits_earned).desc())
            .limit(limit)
            .offset(offset)
        )
        monthly_scores = monthly_scores_result.all()
        
        logger.info(f"Found {len(monthly_scores)} monthly leaderboard entries")
        participants = []
        current_user_rank = None
        
        for rank, score_data in enumerate(monthly_scores, start=offset + 1):
            participant = LeaderboardParticipantResponse(
                user_id=score_data.user_id,
                username=score_data.username,
                full_name=score_data.full_name,
                avatar_url=score_data.avatar_url,
                rank=rank,
                score=int(score_data.total_credits or 0),
                quizzes_completed=int(score_data.quizzes_completed or 0),
                average_score=float(score_data.average_score or 0),
                is_current_user=(current_user and score_data.user_id == current_user.id)
            )
            participants.append(participant)
            
            if current_user and score_data.user_id == current_user.id:
                current_user_rank = rank
        
        # Calculate monthly scores
        current_month_end = (current_month_start + timedelta(days=32)).replace(day=1)
        
        monthly_scores_result = await db.execute(
            select(
                UserQuizResult.user_id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.sum(UserQuizResult.credits_earned).label('total_credits'),
                func.count(UserQuizResult.id).label('quizzes_completed'),
                func.avg(UserQuizResult.percentage).label('average_score')
            )
            .select_from(UserQuizResult.__table__.join(User.__table__, UserQuizResult.user_id == User.id))
            .where(UserQuizResult.completed_at >= current_month_start)
            .where(UserQuizResult.completed_at < current_month_end)
            .group_by(UserQuizResult.user_id, User.username, User.full_name, User.avatar_url)
            .order_by(func.sum(UserQuizResult.credits_earned).desc())
            .limit(limit)
            .offset(offset)
        )
        monthly_scores = monthly_scores_result.all()
        
        participants = []
        current_user_rank = None
        
        for rank, score_data in enumerate(monthly_scores, start=offset + 1):
            participant = LeaderboardParticipantResponse(
                user_id=score_data.user_id,
                username=score_data.username,
                full_name=score_data.full_name,
                avatar_url=score_data.avatar_url,
                rank=rank,
                score=int(score_data.total_credits or 0),
                quizzes_completed=score_data.quizzes_completed,
                average_score=round(float(score_data.average_score or 0), 1),
                is_current_user=(current_user and score_data.user_id == current_user.id)
            )
            participants.append(participant)
            
            if current_user and score_data.user_id == current_user.id:
                current_user_rank = rank
        
        total_participants_result = await db.execute(
            select(func.count(func.distinct(UserQuizResult.user_id)))
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
    current_user: Optional[User] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the all-time leaderboard rankings
    """
    try:
        logger.info(f"Getting all-time leaderboard with limit={limit}, offset={offset}")
        
        # Calculate all-time scores from UserQuizResult
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
            func.sum(UserQuizResult.points_earned).desc()
        ).limit(limit).offset(offset)
        
        result = await db.execute(alltime_query)
        alltime_scores = result.all()
        
        participants = []
        current_user_rank = None
        
        for rank, score_data in enumerate(alltime_scores, start=offset + 1):
            participant = LeaderboardParticipantResponse(
                user_id=score_data.user_id,
                username=score_data.username,
                full_name=score_data.full_name,
                avatar_url=score_data.avatar_url,
                rank=rank,
                score=int(score_data.total_credits or 0),
                quizzes_completed=score_data.quizzes_completed,
                average_score=round(float(score_data.average_score or 0), 1),
                is_current_user=(current_user and score_data.user_id == current_user.id)
            )
            participants.append(participant)
            
            if current_user and score_data.user_id == current_user.id:
                current_user_rank = rank
        
        total_participants_query = select(func.count(distinct(UserQuizResult.user_id)))
        total_result = await db.execute(total_participants_query)
        total_participants = total_result.scalar()
        
        return LeaderboardRankingResponse(
            type="alltime",
            period_start=None,  # All-time has no specific start
            participants=participants,
            total_participants=total_participants,
            current_user_rank=current_user_rank
        )
        
    except Exception as e:
        logger.error(f"Error getting all-time leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get all-time leaderboard")

@router.get("/stats", response_model=LeaderboardStatsResponse)
async def get_leaderboard_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get leaderboard statistics for the current user
    """
    try:
        logger.info(f"Getting leaderboard stats for user {current_user.id}")
        
        # Get user's overall stats
        user_stats_query = select(
            func.count(UserQuizResult.id).label('total_quizzes'),
            func.sum(UserQuizResult.credits_earned).label('total_credits'),
            func.avg(UserQuizResult.percentage).label('average_score'),
            func.max(UserQuizResult.percentage).label('best_score')
        ).where(UserQuizResult.user_id == current_user.id)
        
        result = await db.execute(user_stats_query)
        user_stats = result.first()
        
        # Get weekly rank
        current_week_start = get_current_week_start()
        weekly_rank = None
        
        # Try from cache first
        cached_weekly_query = select(WeeklyLeaderboardCache).where(
            WeeklyLeaderboardCache.user_id == current_user.id,
            WeeklyLeaderboardCache.week_start_date == current_week_start
        )
        result = await db.execute(cached_weekly_query)
        cached_weekly = result.scalar_one_or_none()
        
        if cached_weekly:
            weekly_rank = cached_weekly.credits_rank
        else:
            # Calculate real-time weekly rank
            weekly_ranks_query = select(
                UserQuizResult.user_id,
                func.sum(UserQuizResult.credits_earned).label('total_credits')
            ).where(
                UserQuizResult.completed_at >= current_week_start,
                UserQuizResult.completed_at < current_week_start + timedelta(days=7)
            ).group_by(UserQuizResult.user_id).order_by(func.sum(UserQuizResult.credits_earned).desc())
            
            result = await db.execute(weekly_ranks_query)
            weekly_ranks = result.all()
            
            for rank, rank_data in enumerate(weekly_ranks, start=1):
                if rank_data.user_id == current_user.id:
                    weekly_rank = rank
                    break
        
        # Get all-time rank
        alltime_ranks_query = select(
            UserQuizResult.user_id,
            func.sum(UserQuizResult.credits_earned).label('total_credits')
        ).group_by(UserQuizResult.user_id).order_by(func.sum(UserQuizResult.credits_earned).desc())
        
        result = await db.execute(alltime_ranks_query)
        alltime_ranks = result.all()
        
        alltime_rank = None
        for rank, rank_data in enumerate(alltime_ranks, start=1):
            if rank_data.user_id == current_user.id:
                alltime_rank = rank
                break
        
        return LeaderboardStatsResponse(
            user_id=current_user.id,
            weekly_rank=weekly_rank,
            monthly_rank=None,  # TODO: Implement monthly rank
            alltime_rank=alltime_rank,
            total_quizzes_completed=user_stats.total_quizzes or 0,
            total_credits_earned=int(user_stats.total_credits or 0),
            average_score=round(float(user_stats.average_score or 0), 1),
            best_score=round(float(user_stats.best_score or 0), 1)
        )
        
    except Exception as e:
        logger.error(f"Error getting leaderboard stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get leaderboard stats")

@router.get("/user/{user_id}/rank", response_model=UserRankingResponse)
async def get_user_ranking(
    user_id: int,
    period: str = Query("alltime", regex="^(weekly|monthly|alltime)$"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific user's ranking in different leaderboards
    """
    try:
        logger.info(f"Getting user {user_id} ranking for period {period}")
        
        # Verify user exists
        user_query = select(User).where(User.id == user_id)
        result = await db.execute(user_query)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        rank = None
        total_score = 0
        
        if period == "weekly":
            current_week_start = get_current_week_start()
            
            # Try cache first
            cached_weekly_result = await db.execute(
                select(WeeklyLeaderboardCache)
                .filter(WeeklyLeaderboardCache.user_id == user_id)
                .filter(WeeklyLeaderboardCache.week_start_date == current_week_start)
            )
            cached_weekly = cached_weekly_result.scalar_one_or_none()
            
            if cached_weekly:
                rank = cached_weekly.credits_rank
                total_score = cached_weekly.total_credits_earned
            else:
                # Calculate real-time
                weekly_ranks_query = select(
                    UserQuizResult.user_id,
                    func.sum(UserQuizResult.credits_earned).label('total_credits')
                ).where(
                    UserQuizResult.completed_at >= current_week_start,
                    UserQuizResult.completed_at < current_week_start + timedelta(days=7)
                ).group_by(UserQuizResult.user_id)\
                 .order_by(func.sum(UserQuizResult.credits_earned).desc())
                
                result = await db.execute(weekly_ranks_query)
                weekly_ranks = result.all()
                
                for idx, rank_data in enumerate(weekly_ranks, start=1):
                    if rank_data.user_id == user_id:
                        rank = idx
                        total_score = int(rank_data.total_credits or 0)
                        break
        
        elif period == "alltime":
            # Calculate all-time rank
            alltime_ranks_result = await db.execute(
                select(
                    UserQuizResult.user_id,
                    func.sum(UserQuizResult.credits_earned).label('total_credits')
                )
                .group_by(UserQuizResult.user_id)
                .order_by(func.sum(UserQuizResult.credits_earned).desc())
            )
            alltime_ranks = alltime_ranks_result.all()
            
            for idx, rank_data in enumerate(alltime_ranks, start=1):
                if rank_data.user_id == user_id:
                    rank = idx
                    total_score = int(rank_data.total_credits or 0)
                    break
        
        return UserRankingResponse(
            user_id=user_id,
            username=user.username,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            period=period,
            rank=rank,
            total_score=total_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user ranking: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user ranking")