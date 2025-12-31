"""
Credits System Service - Handles daily caps and smart awarding
Enhanced with leaderboard integration
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.user import User
from app.models.quiz_extended import Quiz, UserQuizResult
from app.models.site_setting import SiteSetting
from app.models.user_quiz_best_score import UserQuizBestScore
from app.models.weekly_leaderboard_cache import WeeklyLeaderboardCache

logger = structlog.get_logger()


class CreditsService:
    """Service for managing credits with daily caps and smart awarding"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_setting_value(self, key: str, default_value: int) -> int:
        """Get a setting value from the database"""
        try:
            result = await self.db.execute(
                select(SiteSetting).where(SiteSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting and setting.parsed_value is not None:
                return int(setting.parsed_value)
            else:
                return default_value
                
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default_value
    
    async def get_daily_credits_earned_today(self, user_id: str) -> int:
        """Get total credits earned by user today"""
        try:
            today = datetime.now(timezone.utc).date()
            tomorrow = today + timedelta(days=1)
            
            result = await self.db.execute(
                select(func.coalesce(func.sum(UserQuizResult.credits_earned), 0))
                .where(
                    and_(
                        UserQuizResult.user_id == user_id,
                        UserQuizResult.completed_at >= today,
                        UserQuizResult.completed_at < tomorrow,
                        UserQuizResult.credits_earned.isnot(None)
                    )
                )
            )
            
            total_today = result.scalar() or 0
            return int(total_today)
            
        except Exception as e:
            logger.error(f"Error getting daily credits for user {user_id}: {e}")
            return 0
    
    async def check_daily_credit_cap(self, user_id: str, proposed_credits: int) -> Tuple[bool, int, str]:
        """
        Check if user can receive proposed credits without exceeding daily cap
        
        Returns:
            - can_award: bool - whether any credits can be awarded
            - actual_credits: int - credits that can actually be awarded
            - message: str - explanation message
        """
        try:
            daily_cap = await self.get_setting_value('daily_credit_cap_quizzes', 60)
            credits_today = await self.get_daily_credits_earned_today(user_id)
            remaining_credits = max(0, daily_cap - credits_today)
            
            if remaining_credits == 0:
                return False, 0, f"Daily credit cap of {daily_cap} already reached"
            
            if proposed_credits <= remaining_credits:
                return True, proposed_credits, f"Credits awarded successfully"
            else:
                # Partial award - give what we can
                return True, remaining_credits, f"Partial credit awarded due to daily cap ({remaining_credits}/{proposed_credits})"
        
        except Exception as e:
            logger.error(f"Error checking daily credit cap for user {user_id}: {e}")
            return False, 0, "Error checking credit cap"
    
    async def calculate_quiz_credits(self, quiz: Quiz, user_result: UserQuizResult) -> Tuple[int, str]:
        """
        Calculate credits for a quiz completion with bonuses
        
        Returns:
            - credits: int - total credits to award
            - breakdown: str - explanation of calculation
        """
        try:
            # Base credits from quiz configuration (now defaults to 10 instead of 50)
            base_credits = quiz.credits_on_completion or 10
            
            # Performance bonus (example: extra credits for high scores)
            performance_bonus = 0
            if user_result.percentage >= 90:
                performance_bonus = int(base_credits * 0.5)  # 50% bonus for 90%+
            elif user_result.percentage >= 80:
                performance_bonus = int(base_credits * 0.25)  # 25% bonus for 80%+
            
            # Time bonus (if completed quickly)
            time_bonus = 0
            if user_result.time_taken and hasattr(quiz, 'estimated_time_minutes'):
                estimated_seconds = quiz.estimated_time_minutes * 60
                if user_result.time_taken < estimated_seconds * 0.75:  # Completed in < 75% of estimated time
                    time_bonus = int(base_credits * 0.1)  # 10% bonus for speed
            
            total_credits = base_credits + performance_bonus + time_bonus
            
            # Create breakdown explanation
            breakdown_parts = [f"Base: {base_credits}"]
            if performance_bonus > 0:
                breakdown_parts.append(f"Performance: +{performance_bonus}")
            if time_bonus > 0:
                breakdown_parts.append(f"Speed: +{time_bonus}")
            
            breakdown = ", ".join(breakdown_parts) + f" = {total_credits}"
            
            return total_credits, breakdown
            
        except Exception as e:
            logger.error(f"Error calculating quiz credits: {e}")
            # Return base credits on error (now 10 instead of 50)
            return quiz.credits_on_completion or 10, "Base credits only"
    
    async def award_quiz_credits(self, user_id: str, quiz_id: str, score_percentage: int, time_taken: int = None) -> int:
        """
        Main method to award credits for quiz completion - simplified interface
        
        Args:
            user_id: UUID of the user
            quiz_id: UUID of the quiz
            score_percentage: Percentage score achieved
            time_taken: Time taken in seconds (optional)
            
        Returns:
            int: Number of credits actually awarded
        """
        try:
            # Get quiz details
            result = await self.db.execute(select(Quiz).where(Quiz.id == quiz_id))
            quiz = result.scalar_one_or_none()
            if not quiz:
                logger.error(f"Quiz {quiz_id} not found for credits calculation")
                return 0
            
            # Create a mock user result for calculation
            from uuid import uuid4
            mock_result = UserQuizResult(
                id=uuid4(),
                user_id=user_id,
                quiz_id=quiz_id,
                score=0,  # Not needed for credits calculation
                max_score=100,  # Not needed for credits calculation
                percentage=score_percentage,
                answers=[],  # Not needed for credits calculation
                time_taken=time_taken,
                completed_at=datetime.utcnow()
            )
            
            # Calculate credits
            calculated_credits, breakdown = await self.calculate_quiz_credits(quiz, mock_result)
            
            # Check daily cap
            can_award, actual_credits, cap_message = await self.check_daily_credit_cap(
                user_id, calculated_credits
            )
            
            if not can_award:
                logger.info(f"Credits capped for user {user_id}: {cap_message}")
                return 0
            
            # Update leaderboard data
            await self._update_leaderboard_data(user_id, quiz_id, actual_credits, score_percentage, time_taken)
            
            logger.info(f"Awarded {actual_credits} credits to user {user_id} for quiz {quiz_id}")
            return actual_credits
            
        except Exception as e:
            logger.error(f"Error awarding quiz credits for user {user_id}: {e}")
            return 0
    
    async def _update_leaderboard_data(self, user_id: str, quiz_id: str, credits_earned: int, 
                                     score_percentage: int, time_taken: int = None):
        """Update user's best scores and weekly leaderboard cache"""
        try:
            # Update best score for this specific quiz
            best_score_record, is_new_best = await UserQuizBestScore.update_or_create_best_score(
                self.db, user_id, quiz_id,
                score=0,  # We'll calculate this properly later
                percentage=score_percentage,
                time_taken=time_taken,
                credits_earned=credits_earned,
                points_earned=0,  # Will be set by the calling method
                reward_tier=None
            )
            
            # Update weekly leaderboard cache
            weekly_entry = await WeeklyLeaderboardCache.update_user_weekly_stats(
                self.db,
                user_id=user_id,
                credits_earned=credits_earned,
                points_earned=0,  # Points will be handled separately in quiz completion
                quiz_completed=True,
                is_perfect_score=(score_percentage == 100),
                score_percentage=score_percentage
            )
            
            if is_new_best:
                logger.info(f"New personal best for user {user_id} on quiz {quiz_id}: {score_percentage}%")
            
        except Exception as e:
            logger.error(f"Error updating leaderboard data for user {user_id}: {e}")
            # Don't fail the whole operation if leaderboard update fails
    
    async def calculate_quiz_points(self, quiz: Quiz, user_result: UserQuizResult) -> int:
        """Calculate points (different from credits) for a quiz"""
        try:
            base_points = quiz.base_points_reward or 10
            
            # Points are based on actual score performance
            score_multiplier = user_result.percentage / 100
            earned_points = int(base_points * score_multiplier)
            
            # Perfect score bonus
            if user_result.percentage == 100:
                earned_points += quiz.perfect_score_bonus or 5
            
            return max(1, earned_points)  # Minimum 1 point for participation
        
        except Exception as e:
            logger.error(f"Error calculating quiz points: {e}")
            return 1
    
    async def get_user_credits_summary(self, user_id: str) -> dict:
        """Get comprehensive credits summary for a user"""
        try:
            daily_cap = await self.get_setting_value('daily_credit_cap_quizzes', 60)
            credits_today = await self.get_daily_credits_earned_today(user_id)
            remaining_today = max(0, daily_cap - credits_today)
            
            return {
                'daily_cap': daily_cap,
                'earned_today': credits_today,
                'remaining_today': remaining_today,
                'progress_percentage': round((credits_today / daily_cap) * 100, 1) if daily_cap > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting credits summary for user {user_id}: {e}")
            return {
                'daily_cap': 60,
                'earned_today': 0,
                'remaining_today': 60,
                'progress_percentage': 0
            }