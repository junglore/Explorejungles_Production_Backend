"""
Leaderboard Service for the Knowledge Engine
Manages multi-dimensional leaderboards and rankings
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from uuid import UUID
import structlog

from app.models.rewards import (
    LeaderboardEntry, 
    LeaderboardTypeEnum,
    UserCurrencyTransaction,
    CurrencyTypeEnum,
    ActivityTypeEnum
)
from app.models.user import User
from app.models import UserQuizResult
from app.models.category import Category
from app.core.rewards_config import LEADERBOARD_CONFIG

logger = structlog.get_logger()


class LeaderboardService:
    """Service for managing leaderboards and rankings"""
    
    def __init__(self):
        self.logger = logger.bind(service="LeaderboardService")
    
    async def get_global_points_leaderboard(
        self, 
        db: AsyncSession, 
        limit: int = 50,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get global points leaderboard"""
        
        try:
            # Get top users by total points earned
            query = select(
                User.id,
                User.username,
                User.full_name,
                User.avatar_url,
                User.total_points_earned,
                User.points_balance,
                func.row_number().over(
                    order_by=desc(User.total_points_earned)
                ).label('rank')
            ).where(
                and_(
                    User.is_active == True,
                    User.total_points_earned > 0
                )
            ).order_by(desc(User.total_points_earned)).limit(limit)
            
            result = await db.execute(query)
            leaderboard_data = result.fetchall()
            
            # Format leaderboard
            leaderboard = []
            user_rank = None
            
            for row in leaderboard_data:
                entry = {
                    "rank": row.rank,
                    "user_id": str(row.id),
                    "username": row.username,
                    "full_name": row.full_name,
                    "avatar_url": row.avatar_url,
                    "total_points_earned": row.total_points_earned,
                    "current_balance": row.points_balance
                }
                leaderboard.append(entry)
                
                if user_id and row.id == user_id:
                    user_rank = row.rank
            
            # Get user's rank if not in top results
            if user_id and user_rank is None:
                user_rank = await self._get_user_points_rank(db, user_id)
            
            return {
                "leaderboard_type": "global_points",
                "entries": leaderboard,
                "user_rank": user_rank,
                "total_entries": len(leaderboard),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting global points leaderboard", error=str(e))
            raise
    
    async def get_quiz_leaderboard(
        self, 
        db: AsyncSession, 
        limit: int = 50,
        category_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get quiz performance leaderboard"""
        
        try:
            # Base query for quiz performance
            base_query = select(
                User.id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.count(UserQuizResult.id).label('total_quizzes'),
                func.avg(UserQuizResult.percentage).label('avg_percentage'),
                func.sum(UserQuizResult.points_earned).label('total_points_from_quizzes'),
                func.max(UserQuizResult.percentage).label('best_score')
            ).select_from(
                User
            ).join(
                UserQuizResult, User.id == UserQuizResult.user_id
            )
            
            if category_id:
                base_query = base_query.join(
                    Quiz, UserQuizResult.quiz_id == Quiz.id
                ).where(Quiz.category_id == category_id)
            
            base_query = base_query.where(
                User.is_active == True
            ).group_by(
                User.id, User.username, User.full_name, User.avatar_url
            ).having(
                func.count(UserQuizResult.id) >= 3  # Minimum 3 quizzes completed
            ).order_by(
                desc(text('avg_percentage')),  # Primary sort by average percentage
                desc(text('total_quizzes'))   # Secondary sort by total quizzes
            ).limit(limit)
            
            result = await db.execute(base_query)
            quiz_data = result.fetchall()
            
            # Format leaderboard
            leaderboard = []
            user_rank = None
            
            for rank, row in enumerate(quiz_data, 1):
                entry = {
                    "rank": rank,
                    "user_id": str(row.id),
                    "username": row.username,
                    "full_name": row.full_name,
                    "avatar_url": row.avatar_url,
                    "total_quizzes": row.total_quizzes,
                    "average_percentage": round(float(row.avg_percentage), 1),
                    "total_points_from_quizzes": row.total_points_from_quizzes or 0,
                    "best_score": row.best_score
                }
                leaderboard.append(entry)
                
                if user_id and row.id == user_id:
                    user_rank = rank
            
            return {
                "leaderboard_type": "quiz_performance",
                "category_id": str(category_id) if category_id else None,
                "entries": leaderboard,
                "user_rank": user_rank,
                "total_entries": len(leaderboard),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting quiz leaderboard", error=str(e))
            raise
    
    async def get_weekly_leaderboard(
        self, 
        db: AsyncSession, 
        limit: int = 25,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get weekly points leaderboard"""
        
        try:
            # Calculate week boundaries
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            
            # Get points earned this week
            query = select(
                User.id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.sum(
                    func.case(
                        (UserCurrencyTransaction.currency_type == CurrencyTypeEnum.POINTS, UserCurrencyTransaction.amount),
                        else_=0
                    )
                ).label('weekly_points')
            ).select_from(
                User
            ).join(
                UserCurrencyTransaction, User.id == UserCurrencyTransaction.user_id
            ).where(
                and_(
                    User.is_active == True,
                    UserCurrencyTransaction.created_at >= week_start,
                    UserCurrencyTransaction.created_at < week_end,
                    UserCurrencyTransaction.amount > 0  # Only positive transactions
                )
            ).group_by(
                User.id, User.username, User.full_name, User.avatar_url
            ).having(
                func.sum(UserCurrencyTransaction.amount) > 0
            ).order_by(
                desc(text('weekly_points'))
            ).limit(limit)
            
            result = await db.execute(query)
            weekly_data = result.fetchall()
            
            # Format leaderboard
            leaderboard = []
            user_rank = None
            
            for rank, row in enumerate(weekly_data, 1):
                entry = {
                    "rank": rank,
                    "user_id": str(row.id),
                    "username": row.username,
                    "full_name": row.full_name,
                    "avatar_url": row.avatar_url,
                    "weekly_points": row.weekly_points or 0
                }
                leaderboard.append(entry)
                
                if user_id and row.id == user_id:
                    user_rank = rank
            
            return {
                "leaderboard_type": "weekly_points",
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "entries": leaderboard,
                "user_rank": user_rank,
                "total_entries": len(leaderboard),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting weekly leaderboard", error=str(e))
            raise
    
    async def get_monthly_leaderboard(
        self, 
        db: AsyncSession, 
        limit: int = 25,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get monthly points leaderboard"""
        
        try:
            # Calculate month boundaries
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Calculate next month start
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            # Get points earned this month
            query = select(
                User.id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.sum(
                    func.case(
                        (UserCurrencyTransaction.currency_type == CurrencyTypeEnum.POINTS, UserCurrencyTransaction.amount),
                        else_=0
                    )
                ).label('monthly_points')
            ).select_from(
                User
            ).join(
                UserCurrencyTransaction, User.id == UserCurrencyTransaction.user_id
            ).where(
                and_(
                    User.is_active == True,
                    UserCurrencyTransaction.created_at >= month_start,
                    UserCurrencyTransaction.created_at < month_end,
                    UserCurrencyTransaction.amount > 0
                )
            ).group_by(
                User.id, User.username, User.full_name, User.avatar_url
            ).having(
                func.sum(UserCurrencyTransaction.amount) > 0
            ).order_by(
                desc(text('monthly_points'))
            ).limit(limit)
            
            result = await db.execute(query)
            monthly_data = result.fetchall()
            
            # Format leaderboard
            leaderboard = []
            user_rank = None
            
            for rank, row in enumerate(monthly_data, 1):
                entry = {
                    "rank": rank,
                    "user_id": str(row.id),
                    "username": row.username,
                    "full_name": row.full_name,
                    "avatar_url": row.avatar_url,
                    "monthly_points": row.monthly_points or 0
                }
                leaderboard.append(entry)
                
                if user_id and row.id == user_id:
                    user_rank = rank
            
            return {
                "leaderboard_type": "monthly_points",
                "month_start": month_start.isoformat(),
                "month_end": month_end.isoformat(),
                "entries": leaderboard,
                "user_rank": user_rank,
                "total_entries": len(leaderboard),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting monthly leaderboard", error=str(e))
            raise
    
    async def get_category_leaderboard(
        self, 
        db: AsyncSession, 
        category_id: UUID,
        limit: int = 25,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get leaderboard for specific category"""
        
        try:
            # Get category info
            category = await db.get(Category, category_id)
            if not category:
                raise ValueError(f"Category {category_id} not found")
            
            # Get quiz performance for this category
            query = select(
                User.id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.count(UserQuizResult.id).label('category_quizzes'),
                func.avg(UserQuizResult.percentage).label('avg_percentage'),
                func.sum(UserQuizResult.points_earned).label('category_points')
            ).select_from(
                User
            ).join(
                UserQuizResult, User.id == UserQuizResult.user_id
            ).join(
                Quiz, UserQuizResult.quiz_id == Quiz.id
            ).where(
                and_(
                    User.is_active == True,
                    Quiz.category_id == category_id
                )
            ).group_by(
                User.id, User.username, User.full_name, User.avatar_url
            ).having(
                func.count(UserQuizResult.id) >= 2  # Minimum 2 quizzes in category
            ).order_by(
                desc(text('avg_percentage')),
                desc(text('category_points'))
            ).limit(limit)
            
            result = await db.execute(query)
            category_data = result.fetchall()
            
            # Format leaderboard
            leaderboard = []
            user_rank = None
            
            for rank, row in enumerate(category_data, 1):
                entry = {
                    "rank": rank,
                    "user_id": str(row.id),
                    "username": row.username,
                    "full_name": row.full_name,
                    "avatar_url": row.avatar_url,
                    "category_quizzes": row.category_quizzes,
                    "average_percentage": round(float(row.avg_percentage), 1),
                    "category_points": row.category_points or 0
                }
                leaderboard.append(entry)
                
                if user_id and row.id == user_id:
                    user_rank = rank
            
            return {
                "leaderboard_type": "category_specific",
                "category_id": str(category_id),
                "category_name": category.name,
                "entries": leaderboard,
                "user_rank": user_rank,
                "total_entries": len(leaderboard),
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting category leaderboard", category_id=str(category_id), error=str(e))
            raise
    
    async def get_user_leaderboard_positions(self, db: AsyncSession, user_id: UUID) -> Dict[str, Any]:
        """Get user's position across all leaderboards"""
        
        try:
            positions = {}
            
            # Global points rank
            positions["global_points"] = await self._get_user_points_rank(db, user_id)
            
            # Weekly rank
            positions["weekly_points"] = await self._get_user_weekly_rank(db, user_id)
            
            # Monthly rank
            positions["monthly_points"] = await self._get_user_monthly_rank(db, user_id)
            
            # Quiz performance rank
            positions["quiz_performance"] = await self._get_user_quiz_rank(db, user_id)
            
            return {
                "user_id": str(user_id),
                "positions": positions,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            self.logger.error("Error getting user leaderboard positions", user_id=str(user_id), error=str(e))
            raise
    
    async def _get_user_points_rank(self, db: AsyncSession, user_id: UUID) -> Optional[int]:
        """Get user's rank in global points leaderboard"""
        
        try:
            # Count users with higher total points
            result = await db.execute(
                select(func.count(User.id))
                .where(
                    and_(
                        User.is_active == True,
                        User.total_points_earned > select(User.total_points_earned).where(User.id == user_id).scalar_subquery()
                    )
                )
            )
            
            higher_count = result.scalar()
            return higher_count + 1 if higher_count is not None else None
            
        except Exception as e:
            self.logger.error("Error getting user points rank", user_id=str(user_id), error=str(e))
            return None
    
    async def _get_user_weekly_rank(self, db: AsyncSession, user_id: UUID) -> Optional[int]:
        """Get user's rank in weekly points leaderboard"""
        
        try:
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)
            
            # Get user's weekly points
            user_weekly_points_result = await db.execute(
                select(func.sum(UserCurrencyTransaction.amount))
                .where(
                    and_(
                        UserCurrencyTransaction.user_id == user_id,
                        UserCurrencyTransaction.currency_type == CurrencyTypeEnum.POINTS,
                        UserCurrencyTransaction.created_at >= week_start,
                        UserCurrencyTransaction.created_at < week_end,
                        UserCurrencyTransaction.amount > 0
                    )
                )
            )
            
            user_weekly_points = user_weekly_points_result.scalar() or 0
            
            if user_weekly_points == 0:
                return None
            
            # Count users with higher weekly points
            higher_count_result = await db.execute(
                select(func.count()).select_from(
                    select(
                        User.id,
                        func.sum(UserCurrencyTransaction.amount).label('weekly_points')
                    ).select_from(
                        User
                    ).join(
                        UserCurrencyTransaction, User.id == UserCurrencyTransaction.user_id
                    ).where(
                        and_(
                            User.is_active == True,
                            UserCurrencyTransaction.currency_type == CurrencyTypeEnum.POINTS,
                            UserCurrencyTransaction.created_at >= week_start,
                            UserCurrencyTransaction.created_at < week_end,
                            UserCurrencyTransaction.amount > 0
                        )
                    ).group_by(User.id)
                    .having(func.sum(UserCurrencyTransaction.amount) > user_weekly_points)
                    .subquery()
                )
            )
            
            higher_count = higher_count_result.scalar()
            return higher_count + 1 if higher_count is not None else None
            
        except Exception as e:
            self.logger.error("Error getting user weekly rank", user_id=str(user_id), error=str(e))
            return None
    
    async def _get_user_monthly_rank(self, db: AsyncSession, user_id: UUID) -> Optional[int]:
        """Get user's rank in monthly points leaderboard"""
        
        try:
            now = datetime.now(timezone.utc)
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if month_start.month == 12:
                month_end = month_start.replace(year=month_start.year + 1, month=1)
            else:
                month_end = month_start.replace(month=month_start.month + 1)
            
            # Get user's monthly points
            user_monthly_points_result = await db.execute(
                select(func.sum(UserCurrencyTransaction.amount))
                .where(
                    and_(
                        UserCurrencyTransaction.user_id == user_id,
                        UserCurrencyTransaction.currency_type == CurrencyTypeEnum.POINTS,
                        UserCurrencyTransaction.created_at >= month_start,
                        UserCurrencyTransaction.created_at < month_end,
                        UserCurrencyTransaction.amount > 0
                    )
                )
            )
            
            user_monthly_points = user_monthly_points_result.scalar() or 0
            
            if user_monthly_points == 0:
                return None
            
            # Count users with higher monthly points
            higher_count_result = await db.execute(
                select(func.count()).select_from(
                    select(
                        User.id,
                        func.sum(UserCurrencyTransaction.amount).label('monthly_points')
                    ).select_from(
                        User
                    ).join(
                        UserCurrencyTransaction, User.id == UserCurrencyTransaction.user_id
                    ).where(
                        and_(
                            User.is_active == True,
                            UserCurrencyTransaction.currency_type == CurrencyTypeEnum.POINTS,
                            UserCurrencyTransaction.created_at >= month_start,
                            UserCurrencyTransaction.created_at < month_end,
                            UserCurrencyTransaction.amount > 0
                        )
                    ).group_by(User.id)
                    .having(func.sum(UserCurrencyTransaction.amount) > user_monthly_points)
                    .subquery()
                )
            )
            
            higher_count = higher_count_result.scalar()
            return higher_count + 1 if higher_count is not None else None
            
        except Exception as e:
            self.logger.error("Error getting user monthly rank", user_id=str(user_id), error=str(e))
            return None
    
    async def _get_user_quiz_rank(self, db: AsyncSession, user_id: UUID) -> Optional[int]:
        """Get user's rank in quiz performance leaderboard"""
        
        try:
            # Get user's average quiz percentage
            user_avg_result = await db.execute(
                select(func.avg(UserQuizResult.percentage))
                .where(UserQuizResult.user_id == user_id)
            )
            
            user_avg = user_avg_result.scalar()
            
            if not user_avg:
                return None
            
            # Count users with higher average
            higher_count_result = await db.execute(
                select(func.count()).select_from(
                    select(
                        User.id,
                        func.avg(UserQuizResult.percentage).label('avg_percentage')
                    ).select_from(
                        User
                    ).join(
                        UserQuizResult, User.id == UserQuizResult.user_id
                    ).where(
                        User.is_active == True
                    ).group_by(User.id)
                    .having(
                        and_(
                            func.count(UserQuizResult.id) >= 3,  # Minimum 3 quizzes
                            func.avg(UserQuizResult.percentage) > user_avg
                        )
                    ).subquery()
                )
            )
            
            higher_count = higher_count_result.scalar()
            return higher_count + 1 if higher_count is not None else None
            
        except Exception as e:
            self.logger.error("Error getting user quiz rank", user_id=str(user_id), error=str(e))
            return None


# Global service instance
leaderboard_service = LeaderboardService()