"""
Enhanced Rewards Service - Applies tier multipliers, bonuses, and comprehensive reward calculations
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple, Union
from sqlalchemy import select, func, and_, text, desc
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.user import User
from app.models.quiz_extended import Quiz, UserQuizResult
from app.models.user_quiz_best_score import UserQuizBestScore
from app.models.site_setting import SiteSetting
from app.services.settings_service import SettingsService

logger = structlog.get_logger()


class EnhancedRewardsService:
    """Service for enhanced rewards with tier multipliers and bonuses"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = SettingsService(db)
    
    async def get_user_tier(self, user_id: str) -> str:
        """Determine user tier based on total points earned"""
        try:
            # Get user's total points
            result = await self.db.execute(
                select(func.coalesce(func.sum(UserQuizResult.points_earned), 0))
                .where(UserQuizResult.user_id == user_id)
            )
            total_points = result.scalar() or 0
            
            # Define tier thresholds
            if total_points >= 10000:
                return "platinum"
            elif total_points >= 5000:
                return "gold"
            elif total_points >= 1000:
                return "silver"
            else:
                return "bronze"
                
        except Exception as e:
            logger.error(f"Error getting user tier for {user_id}: {e}")
            return "bronze"
    
    async def get_user_streak(self, user_id: str) -> int:
        """Calculate user's current streak of consecutive days with quiz completions"""
        try:
            # Get last 30 days of quiz results, grouped by date
            today = datetime.now(timezone.utc).date()
            thirty_days_ago = today - timedelta(days=30)
            
            result = await self.db.execute(
                select(
                    func.date(UserQuizResult.completed_at).label('completion_date'),
                    func.count(UserQuizResult.id).label('quizzes_count')
                )
                .where(
                    UserQuizResult.user_id == user_id,
                    UserQuizResult.completed_at >= thirty_days_ago
                )
                .group_by(func.date(UserQuizResult.completed_at))
                .order_by(desc('completion_date'))
            )
            
            daily_completions = result.all()
            
            # Calculate streak
            streak = 0
            current_date = today
            
            for completion in daily_completions:
                if completion.completion_date == current_date:
                    streak += 1
                    current_date -= timedelta(days=1)
                elif completion.completion_date == current_date - timedelta(days=1):
                    # Allow for one day gap (continuing yesterday's streak today)
                    streak += 1
                    current_date = completion.completion_date - timedelta(days=1)
                else:
                    break
            
            return streak
            
        except Exception as e:
            logger.error(f"Error calculating streak for {user_id}: {e}")
            return 0
    
    async def is_weekend(self) -> bool:
        """Check if current day is weekend"""
        return datetime.now(timezone.utc).weekday() >= 5  # Saturday = 5, Sunday = 6
    
    async def calculate_quiz_completion_time(self, quiz_id: str, completed_at: datetime, started_at: Optional[datetime] = None) -> int:
        """Calculate time taken to complete quiz in seconds"""
        if started_at:
            return int((completed_at - started_at).total_seconds())
        
        # If no start time, estimate based on quiz questions (assume 30 seconds per question)
        try:
            result = await self.db.execute(
                select(Quiz.num_questions).where(Quiz.id == quiz_id)
            )
            num_questions = result.scalar() or 10
            estimated_time = num_questions * 30  # 30 seconds per question
            return estimated_time
            
        except Exception as e:
            logger.error(f"Error getting quiz questions for {quiz_id}: {e}")
            return 300  # Default 5 minutes
    
    async def calculate_enhanced_rewards(
        self, 
        user_id: str, 
        quiz_id: str, 
        base_points: int, 
        base_credits: int,
        quiz_percentage: float,
        completion_time: Optional[int] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> Dict[str, Union[int, float, str]]:
        """
        Calculate enhanced rewards with dual-economy system:
        - Points: Get all bonuses and multipliers (engagement/gamification)
        - Credits: Only get conservative tier multipliers (business-safe)
        """
        try:
            # Check for pure scoring mode first
            pure_scoring = await self.settings.get_setting('pure_scoring_mode', False)
            if pure_scoring:
                return {
                    'points': base_points,
                    'credits': base_credits,
                    'bonuses': ['Pure scoring mode enabled'],
                    'multiplier': 1.0,
                    'credits_multiplier': 1.0,
                    'base_points': base_points,
                    'base_credits': base_credits,
                    'tier': 'bronze',
                    'total_multiplier': 1.0
                }
            
            # Initialize calculations
            applied_bonuses = []
            points_multiplier = 1.0
            credits_multiplier = 1.0
            
            # Check if rewards system is enabled
            if not await self.settings.is_rewards_system_enabled():
                return {
                    'points': base_points,
                    'credits': base_credits,
                    'bonuses': [],
                    'multiplier': 1.0,
                    'tier': 'bronze'
                }
            
            # Get user tier for both points and credits
            user_tier = await self.get_user_tier(user_id)
            user_streak = await self.get_user_streak(user_id)
            
            # === POINTS: Get ALL bonuses and multipliers (engagement) ===
            # Tier multiplier for points (aggressive)
            points_tier_multiplier = await self.settings.get_tier_multiplier(user_tier)
            points_multiplier *= points_tier_multiplier
            applied_bonuses.append(f"{user_tier.title()} Tier (Points): {points_tier_multiplier}x")
            
            # Get time-based bonus settings for points
            time_bonuses = await self.settings.get_time_bonuses()
            
            # Quick completion bonus (points only)
            if completion_time and completion_time <= time_bonuses['quick_completion_threshold']:
                quick_multiplier = time_bonuses['quick_completion_multiplier']
                points_multiplier *= quick_multiplier
                applied_bonuses.append(f"Quick Completion (Points): {quick_multiplier}x")
            
            # Streak bonus (points only)
            if user_streak >= time_bonuses['streak_threshold']:
                streak_multiplier = time_bonuses['streak_multiplier']
                streak_bonus_multiplier = 1 + (user_streak * 0.02)  # 2% per day in streak
                final_streak_multiplier = min(streak_multiplier * streak_bonus_multiplier, 2.0)  # Cap at 2x
                points_multiplier *= final_streak_multiplier
                applied_bonuses.append(f"{user_streak} Day Streak (Points): {final_streak_multiplier:.2f}x")
            
            # Event bonuses (points only)
            event_bonuses = await self.settings.get_event_bonuses()
            if event_bonuses['weekend_bonus_enabled'] and await self.is_weekend():
                weekend_multiplier = event_bonuses['weekend_bonus_multiplier']
                points_multiplier *= weekend_multiplier
                applied_bonuses.append(f"Weekend Bonus (Points): {weekend_multiplier}x")
            
            # Special event bonus (points only)
            if event_bonuses['special_event_multiplier'] > 1.0:
                event_multiplier = event_bonuses['special_event_multiplier']
                points_multiplier *= event_multiplier
                applied_bonuses.append(f"Special Event (Points): {event_multiplier}x")
            
            # Seasonal event bonus (points only)
            if event_bonuses['seasonal_event_active']:
                seasonal_multiplier = event_bonuses['seasonal_event_multiplier']
                seasonal_name = event_bonuses['seasonal_event_name'] or "Seasonal Event"
                points_multiplier *= seasonal_multiplier
                applied_bonuses.append(f"{seasonal_name} (Points): {seasonal_multiplier}x")
            
            # Performance bonuses (points only)
            if quiz_percentage >= 100.0:
                perfect_bonus = 1.25
                points_multiplier *= perfect_bonus
                applied_bonuses.append(f"Perfect Score (Points): {perfect_bonus}x")
            elif quiz_percentage >= 90.0:
                accuracy_bonus = 1.1
                points_multiplier *= accuracy_bonus
                applied_bonuses.append(f"High Accuracy (Points): {accuracy_bonus}x")
            
            # === CREDITS: Only conservative tier multipliers (business-safe) ===
            # Get conservative credit tier multiplier
            credit_tier_key = f"credit_tier_multiplier_{user_tier}"
            try:
                credit_tier_result = await self.db.execute(
                    select(SiteSetting.value).where(SiteSetting.key == credit_tier_key)
                )
                credit_tier_value = credit_tier_result.scalar()
                if credit_tier_value:
                    credits_multiplier = float(credit_tier_value)
                else:
                    # Fallback to conservative defaults
                    credit_defaults = {'bronze': 1.0, 'silver': 1.1, 'gold': 1.2, 'platinum': 1.3}
                    credits_multiplier = credit_defaults.get(user_tier, 1.0)
            except:
                # Fallback to conservative defaults
                credit_defaults = {'bronze': 1.0, 'silver': 1.1, 'gold': 1.2, 'platinum': 1.3}
                credits_multiplier = credit_defaults.get(user_tier, 1.0)
            
            applied_bonuses.append(f"{user_tier.title()} Tier (Credits): {credits_multiplier}x")
            
            # Apply multipliers
            final_points = int(base_points * points_multiplier)
            final_credits = int(base_credits * credits_multiplier)
            
            # Ensure minimum rewards
            final_points = max(final_points, 1)
            final_credits = max(final_credits, 1)
            
            return {
                'points': final_points,
                'credits': final_credits,
                'base_points': base_points,
                'base_credits': base_credits,
                'bonuses': applied_bonuses,
                'multiplier': round(points_multiplier, 2),  # Show points multiplier as main
                'credits_multiplier': round(credits_multiplier, 2),
                'tier': user_tier,
                'streak': user_streak
            }
            
        except Exception as e:
            logger.error(f"Error calculating enhanced rewards: {e}")
            # Return base rewards on error
            return {
                'points': base_points,
                'credits': base_credits,
                'bonuses': [],
                'multiplier': 1.0,
                'tier': 'bronze'
            }
    
    async def apply_daily_limits(
        self, 
        user_id: str, 
        calculated_points: int, 
        calculated_credits: int
    ) -> Tuple[int, int, bool]:
        """
        Apply daily limits to calculated rewards
        Returns: (final_points, final_credits, was_limited)
        """
        try:
            # Get daily limits
            daily_limits = await self.settings.get_daily_limits()
            daily_points_limit = daily_limits['points']
            daily_credits_limit = daily_limits['credits']
            
            # Get points earned today
            today = datetime.now(timezone.utc).date()
            tomorrow = today + timedelta(days=1)
            
            # Points earned today
            points_result = await self.db.execute(
                select(func.coalesce(func.sum(UserQuizResult.points_earned), 0))
                .where(
                    UserQuizResult.user_id == user_id,
                    UserQuizResult.completed_at >= today,
                    UserQuizResult.completed_at < tomorrow
                )
            )
            points_today = points_result.scalar() or 0
            
            # Credits earned today (from quiz results)
            credits_result = await self.db.execute(
                select(func.coalesce(func.sum(UserQuizResult.credits_earned), 0))
                .where(
                    UserQuizResult.user_id == user_id,
                    UserQuizResult.completed_at >= today,
                    UserQuizResult.completed_at < tomorrow
                )
            )
            credits_today = credits_result.scalar() or 0
            
            # Apply limits
            was_limited = False
            final_points = calculated_points
            final_credits = calculated_credits
            
            # Check points limit
            if points_today + calculated_points > daily_points_limit:
                final_points = max(0, daily_points_limit - points_today)
                was_limited = True
            
            # Check credits limit
            if credits_today + calculated_credits > daily_credits_limit:
                final_credits = max(0, daily_credits_limit - credits_today)
                was_limited = True
            
            return final_points, final_credits, was_limited
            
        except Exception as e:
            logger.error(f"Error applying daily limits: {e}")
            return calculated_points, calculated_credits, False
    
    async def award_quiz_completion(
        self,
        user_id: str,
        quiz_id: str,
        quiz_percentage: float,
        base_points: int = 10,
        base_credits: int = 5,
        completion_time: Optional[int] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> Dict[str, Union[int, float, str, bool]]:
        """
        Award enhanced rewards for quiz completion with all bonuses
        """
        try:
            # Calculate enhanced rewards
            reward_calculation = await self.calculate_enhanced_rewards(
                user_id=user_id,
                quiz_id=quiz_id,
                base_points=base_points,
                base_credits=base_credits,
                quiz_percentage=quiz_percentage,
                completion_time=completion_time,
                started_at=started_at,
                completed_at=completed_at
            )
            
            # Apply daily limits
            final_points, final_credits, was_limited = await self.apply_daily_limits(
                user_id=user_id,
                calculated_points=reward_calculation['points'],
                calculated_credits=reward_calculation['credits']
            )
            
            # Update the calculation with final values
            reward_calculation.update({
                'final_points': final_points,
                'final_credits': final_credits,
                'was_limited': was_limited,
                'message': self._generate_reward_message(reward_calculation, was_limited)
            })
            
            return reward_calculation
            
        except Exception as e:
            logger.error(f"Error awarding quiz completion: {e}")
            return {
                'points': base_points,
                'credits': base_credits,
                'final_points': base_points,
                'final_credits': base_credits,
                'bonuses': [],
                'multiplier': 1.0,
                'tier': 'bronze',
                'was_limited': False,
                'message': "Standard rewards awarded"
            }
    
    def _generate_reward_message(self, calculation: Dict, was_limited: bool) -> str:
        """Generate a user-friendly message about rewards earned"""
        messages = []
        
        if calculation.get('bonuses'):
            messages.append(f"🎉 Bonus Applied: {calculation['multiplier']}x multiplier!")
        
        if calculation.get('tier', 'bronze') != 'bronze':
            messages.append(f"⭐ {calculation['tier'].title()} Tier Benefits!")
        
        if calculation.get('streak', 0) >= 3:
            messages.append(f"🔥 {calculation['streak']} Day Streak!")
        
        if was_limited:
            messages.append("⚠️ Daily limit reached")
        
        if not messages:
            return "Rewards earned successfully!"
        
        return " ".join(messages)