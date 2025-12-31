"""
Currency Management Service for the Knowledge Engine Rewards System
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from uuid import UUID, uuid4
import structlog

from app.models.rewards import (
    UserCurrencyTransaction, 
    TransactionTypeEnum, 
    CurrencyTypeEnum, 
    ActivityTypeEnum,
    UserDailyActivity
)
from app.models.user import User
from app.models.site_setting import SiteSetting
from app.db.database import get_db_session
from app.core.rewards_config import DAILY_LIMITS

logger = structlog.get_logger()


class CurrencyService:
    """Service for managing user currency (Points and Credits)"""
    
    def __init__(self):
        self.logger = logger.bind(service="CurrencyService")
    
    async def get_user_balance(self, db: AsyncSession, user_id: UUID) -> Dict[str, int]:
        """Get user's current currency balances"""
        try:
            result = await db.execute(
                select(User.points_balance, User.credits_balance, User.total_points_earned, User.total_credits_earned)
                .where(User.id == user_id)
            )
            balance_data = result.first()
            
            if not balance_data:
                raise ValueError(f"User {user_id} not found")
            
            return {
                "points_balance": balance_data.points_balance,
                "credits_balance": balance_data.credits_balance,
                "total_points_earned": balance_data.total_points_earned,
                "total_credits_earned": balance_data.total_credits_earned
            }
        except Exception as e:
            self.logger.error("Error getting user balance", user_id=str(user_id), error=str(e))
            raise
    
    async def add_currency(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        currency_type: CurrencyTypeEnum,
        amount: int,
        activity_type: ActivityTypeEnum,
        activity_reference_id: Optional[UUID] = None,
        transaction_metadata: Optional[Dict] = None
    ) -> UserCurrencyTransaction:
        """Add currency to user account with full transaction tracking"""
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        try:
            # Get current user balance
            user = await db.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Check daily limits
            daily_activity = await self._get_or_create_daily_activity(db, user_id)
            if not await self._check_daily_limits(daily_activity, currency_type, amount, activity_type, db):
                # Provide specific error message for MVF limits
                if activity_type == ActivityTypeEnum.MYTHS_FACTS_GAME:
                    mvf_limits = await self._get_mvf_daily_limits(db)
                    limit_type = "points" if currency_type == CurrencyTypeEnum.POINTS else "credits"
                    current_earned = daily_activity.points_earned_today if currency_type == CurrencyTypeEnum.POINTS else daily_activity.credits_earned_today
                    raise ValueError(f"Daily Myths vs Facts {limit_type} limit exceeded. Current: {current_earned}, Limit: {mvf_limits[limit_type]}, Attempting to add: {amount}")
                else:
                    raise ValueError("Daily currency limit exceeded")
            
            # Calculate new balance
            if currency_type == CurrencyTypeEnum.POINTS:
                new_balance = user.points_balance + amount
                user.points_balance = new_balance
                user.total_points_earned += amount
                daily_activity.points_earned_today += amount
                transaction_type = TransactionTypeEnum.POINTS_EARNED
            else:  # CREDITS
                new_balance = user.credits_balance + amount
                user.credits_balance = new_balance  
                user.total_credits_earned += amount
                daily_activity.credits_earned_today += amount
                transaction_type = TransactionTypeEnum.CREDITS_EARNED
            
            # Create transaction record
            transaction = UserCurrencyTransaction(
                user_id=user_id,
                transaction_type=transaction_type,
                currency_type=currency_type,
                amount=amount,
                balance_after=new_balance,
                activity_type=activity_type,
                activity_reference_id=activity_reference_id,
                transaction_metadata=transaction_metadata or {},
                processed_at=datetime.now(timezone.utc)
            )
            
            # Save to database
            db.add(transaction)
            await db.flush()  # Get transaction ID
            
            self.logger.info(
                "Currency added successfully", 
                user_id=str(user_id),
                currency_type=currency_type.value,
                amount=amount,
                new_balance=new_balance,
                transaction_id=str(transaction.id)
            )
            
            return transaction
            
        except Exception as e:
            await db.rollback()
            self.logger.error("Error adding currency", user_id=str(user_id), error=str(e))
            raise
    
    async def spend_credits(
        self,
        db: AsyncSession,
        user_id: UUID,
        amount: int,
        activity_type: ActivityTypeEnum,
        activity_reference_id: Optional[UUID] = None,
        transaction_metadata: Optional[Dict] = None
    ) -> UserCurrencyTransaction:
        """Spend credits from user account"""
        
        if amount <= 0:
            raise ValueError("Amount must be positive")
        
        try:
            # Get current user balance
            user = await db.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Check sufficient balance
            if user.credits_balance < amount:
                raise ValueError(f"Insufficient credits. Balance: {user.credits_balance}, Required: {amount}")
            
            # Deduct credits
            new_balance = user.credits_balance - amount
            user.credits_balance = new_balance
            
            # Create transaction record
            transaction = UserCurrencyTransaction(
                user_id=user_id,
                transaction_type=TransactionTypeEnum.CREDITS_SPENT,
                currency_type=CurrencyTypeEnum.CREDITS,
                amount=-amount,  # Negative for spending
                balance_after=new_balance,
                activity_type=activity_type,
                activity_reference_id=activity_reference_id,
                transaction_metadata=transaction_metadata or {},
                processed_at=datetime.now(timezone.utc)
            )
            
            db.add(transaction)
            await db.flush()
            
            self.logger.info(
                "Credits spent successfully",
                user_id=str(user_id),
                amount=amount,
                new_balance=new_balance,
                transaction_id=str(transaction.id)
            )
            
            return transaction
            
        except Exception as e:
            await db.rollback()
            self.logger.error("Error spending credits", user_id=str(user_id), error=str(e))
            raise
    
    async def get_transaction_history(
        self,
        db: AsyncSession,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
        currency_type: Optional[CurrencyTypeEnum] = None,
        activity_type: Optional[ActivityTypeEnum] = None
    ) -> List[UserCurrencyTransaction]:
        """Get user's transaction history with filtering"""
        
        try:
            query = select(UserCurrencyTransaction).where(
                UserCurrencyTransaction.user_id == user_id
            )
            
            if currency_type:
                query = query.where(UserCurrencyTransaction.currency_type == currency_type)
            
            if activity_type:
                query = query.where(UserCurrencyTransaction.activity_type == activity_type)
            
            query = query.order_by(desc(UserCurrencyTransaction.created_at))
            query = query.offset(offset).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error("Error getting transaction history", user_id=str(user_id), error=str(e))
            raise
    
    async def get_daily_earnings_summary(self, db: AsyncSession, user_id: UUID) -> Dict:
        """Get today's earnings summary for the user"""
        
        try:
            daily_activity = await self._get_or_create_daily_activity(db, user_id)
            
            return {
                "points_earned_today": daily_activity.points_earned_today,
                "credits_earned_today": daily_activity.credits_earned_today,
                "quiz_attempts": daily_activity.quiz_attempts,
                "quiz_completions": daily_activity.quiz_completions,
                "myths_facts_games": daily_activity.myths_facts_games,
                "login_streak": daily_activity.login_streak,
                "daily_limits": {
                    "max_points_remaining": max(0, DAILY_LIMITS["max_total_points_per_day"] - daily_activity.points_earned_today),
                    "max_credits_remaining": max(0, DAILY_LIMITS["max_credits_per_day"] - daily_activity.credits_earned_today),
                    "quiz_attempts_remaining": max(0, DAILY_LIMITS["max_quiz_attempts"] - daily_activity.quiz_attempts),
                    "myths_games_remaining": max(0, DAILY_LIMITS["max_myths_facts_games"] - daily_activity.myths_facts_games)
                }
            }
            
        except Exception as e:
            self.logger.error("Error getting daily summary", user_id=str(user_id), error=str(e))
            raise
    
    async def _get_or_create_daily_activity(self, db: AsyncSession, user_id: UUID) -> UserDailyActivity:
        """Get or create daily activity record for today"""
        
        today = datetime.now(timezone.utc).date()
        
        result = await db.execute(
            select(UserDailyActivity)
            .where(and_(
                UserDailyActivity.user_id == user_id,
                UserDailyActivity.activity_date == today
            ))
        )
        
        daily_activity = result.scalar_one_or_none()
        
        if not daily_activity:
            # Calculate login streak
            login_streak = await self._calculate_login_streak(db, user_id)
            
            daily_activity = UserDailyActivity(
                user_id=user_id,
                activity_date=today,
                login_streak=login_streak
            )
            db.add(daily_activity)
            await db.flush()
        
        return daily_activity
    
    async def _calculate_login_streak(self, db: AsyncSession, user_id: UUID) -> int:
        """Calculate current login streak for user"""
        
        try:
            # Get recent daily activities in descending order
            result = await db.execute(
                select(UserDailyActivity)
                .where(UserDailyActivity.user_id == user_id)
                .order_by(desc(UserDailyActivity.activity_date))
                .limit(100)  # Look back 100 days max
            )
            
            activities = result.scalars().all()
            
            if not activities:
                return 1  # First day
            
            # Check for consecutive days
            streak = 1
            today = datetime.now(timezone.utc).date()
            expected_date = today - timedelta(days=1)
            
            for activity in activities:
                if activity.activity_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                else:
                    break
            
            return streak
            
        except Exception as e:
            self.logger.error("Error calculating login streak", user_id=str(user_id), error=str(e))
            return 1
    
    async def _check_daily_limits(
        self, 
        daily_activity: UserDailyActivity, 
        currency_type: CurrencyTypeEnum, 
        amount: int,
        activity_type: Optional[ActivityTypeEnum] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """Check if adding currency would exceed daily limits"""
        
        # For MVF activities, use MVF-specific limits
        if activity_type == ActivityTypeEnum.MYTHS_FACTS_GAME and db:
            mvf_limits = await self._get_mvf_daily_limits(db)
            if currency_type == CurrencyTypeEnum.POINTS:
                return (daily_activity.points_earned_today + amount) <= mvf_limits['points']
            else:  # CREDITS
                return (daily_activity.credits_earned_today + amount) <= mvf_limits['credits']
        
        # Use general limits for other activities
        if currency_type == CurrencyTypeEnum.POINTS:
            return (daily_activity.points_earned_today + amount) <= DAILY_LIMITS["max_total_points_per_day"]
        else:  # CREDITS
            return (daily_activity.credits_earned_today + amount) <= DAILY_LIMITS["max_credits_per_day"]
    
    async def _get_mvf_daily_limits(self, db: AsyncSession) -> Dict[str, int]:
        """Get MVF-specific daily limits from site settings"""
        try:
            # Get MVF daily limits from database
            result = await db.execute(
                select(SiteSetting.key, SiteSetting.value)
                .where(SiteSetting.key.in_(['mvf_daily_points_limit', 'mvf_daily_credits_limit']))
            )
            settings = dict(result.fetchall())
            
            return {
                'points': int(settings.get('mvf_daily_points_limit', '200')),
                'credits': int(settings.get('mvf_daily_credits_limit', '50'))
            }
        except Exception as e:
            self.logger.warning("Failed to get MVF daily limits from database, using defaults", error=str(e))
            # Return default values if database query fails
            return {
                'points': 200,
                'credits': 50
            }
    
    async def apply_penalty(
        self,
        db: AsyncSession,
        user_id: UUID,
        currency_type: CurrencyTypeEnum,
        amount: int,
        reason: str,
        admin_id: Optional[UUID] = None
    ) -> UserCurrencyTransaction:
        """Apply currency penalty for rule violations"""
        
        if amount <= 0:
            raise ValueError("Penalty amount must be positive")
        
        try:
            user = await db.get(User, user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Apply penalty
            if currency_type == CurrencyTypeEnum.POINTS:
                new_balance = max(0, user.points_balance - amount)  # Don't go below 0
                user.points_balance = new_balance
                transaction_type = TransactionTypeEnum.POINTS_PENALTY
            else:  # CREDITS
                new_balance = max(0, user.credits_balance - amount)
                user.credits_balance = new_balance
                transaction_type = TransactionTypeEnum.CREDITS_PENALTY
            
            # Create penalty transaction
            transaction = UserCurrencyTransaction(
                user_id=user_id,
                transaction_type=transaction_type,
                currency_type=currency_type,
                amount=-amount,  # Negative for penalty
                balance_after=new_balance,
                activity_type=ActivityTypeEnum.ADMIN_GRANT,  # Use admin grant for penalties
                transaction_metadata={"reason": reason, "admin_id": str(admin_id) if admin_id else None},
                processed_at=datetime.now(timezone.utc)
            )
            
            db.add(transaction)
            await db.flush()
            
            self.logger.warning(
                "Currency penalty applied",
                user_id=str(user_id),
                currency_type=currency_type.value,
                amount=amount,
                reason=reason,
                admin_id=str(admin_id) if admin_id else None
            )
            
            return transaction
            
        except Exception as e:
            await db.rollback()
            self.logger.error("Error applying penalty", user_id=str(user_id), error=str(e))
            raise


# Global service instance
currency_service = CurrencyService()