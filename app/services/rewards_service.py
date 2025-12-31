"""
Rewards Processing Service for the Knowledge Engine
Handles reward calculation and distribution based on user performance
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from uuid import UUID
import structlog

from app.models.rewards import (
    RewardsConfiguration, 
    RewardTierEnum, 
    ActivityTypeEnum,
    UserDailyActivity
)
from app.models import UserQuizResult
from app.models.user import User
from app.models.site_setting import SiteSetting
from app.services.currency_service import currency_service, CurrencyTypeEnum
from app.core.rewards_config import ANTI_GAMING_CONFIG  # Only use non-deprecated configs

logger = structlog.get_logger()


class RewardsService:
    """Service for processing and distributing rewards"""
    
    def __init__(self):
        self.logger = logger.bind(service="RewardsService")
    
    async def _check_pure_scoring_mode(self, db: AsyncSession) -> bool:
        """Check if pure scoring mode is enabled (no multipliers/bonuses)"""
        try:
            result = await db.execute(
                select(SiteSetting).where(SiteSetting.key == 'pure_scoring_mode')
            )
            setting = result.scalar_one_or_none()
            if setting:
                return setting.parsed_value
            return False  # Default to False if setting not found
        except Exception as e:
            self.logger.warning("Error checking pure scoring mode", error=str(e))
            return False
    
    async def process_quiz_completion_reward(
        self,
        db: AsyncSession,
        user_id: UUID,
        quiz_result_id: UUID,
        quiz_id: UUID,
        score_percentage: int,
        time_taken: Optional[int] = None,
        perfect_score_bonus: bool = False
    ) -> Dict:
        """Process rewards for quiz completion"""
        
        try:
            # Check if pure scoring mode is enabled
            pure_scoring_mode = await self._check_pure_scoring_mode(db)
            
            # Determine reward tier based on performance
            reward_tier = self._calculate_quiz_reward_tier(score_percentage)
            
            # Get reward configuration
            rewards_config = await self._get_rewards_config(db, ActivityTypeEnum.QUIZ_COMPLETION, reward_tier)
            
            if not rewards_config:
                self.logger.warning("No rewards configuration found", activity="quiz", tier=reward_tier.value)
                return {"points_earned": 0, "credits_earned": 0, "reward_tier": reward_tier.value}
            
            # Check if user has reached daily limits
            daily_activity = await self._get_daily_activity(db, user_id)
            if not await self._check_daily_reward_limits(daily_activity, rewards_config):
                return {"points_earned": 0, "credits_earned": 0, "reward_tier": reward_tier.value, "reason": "daily_limit_reached"}
            
            # Calculate base rewards
            points_earned = rewards_config.points_reward
            credits_earned = rewards_config.credits_reward
            
            # Apply bonuses ONLY if NOT in pure scoring mode
            time_bonus_applied = False
            perfect_bonus_applied = False
            
            if not pure_scoring_mode:
                # Apply time bonus if eligible
                if (rewards_config.time_bonus_threshold and 
                    time_taken and 
                    time_taken <= rewards_config.time_bonus_threshold and 
                    score_percentage >= 80):  # Must have good performance for time bonus
                    
                    time_bonus_points = int(points_earned * 0.5)  # 50% bonus
                    time_bonus_credits = int(credits_earned * 0.3)  # 30% bonus
                    points_earned += time_bonus_points
                    credits_earned += time_bonus_credits
                    time_bonus_applied = True
                
                # Apply perfect score bonus
                if perfect_score_bonus and score_percentage == 100:
                    perfect_bonus_points = int(points_earned * 0.2)  # 20% bonus
                    perfect_bonus_credits = int(credits_earned * 0.2)  # 20% bonus
                    points_earned += perfect_bonus_points
                    credits_earned += perfect_bonus_credits
                    perfect_bonus_applied = True
            
            # Award currency
            metadata = {
                "quiz_id": str(quiz_id),
                "score_percentage": score_percentage,
                "time_taken": time_taken,
                "reward_tier": reward_tier.value,
                "time_bonus_applied": time_bonus_applied,
                "perfect_score_bonus": perfect_score_bonus
            }
            
            # Add points
            if points_earned > 0:
                await currency_service.add_currency(
                    db=db,
                    user_id=user_id,
                    currency_type=CurrencyTypeEnum.POINTS,
                    amount=points_earned,
                    activity_type=ActivityTypeEnum.QUIZ_COMPLETION,
                    activity_reference_id=quiz_result_id,
                    transaction_metadata=metadata
                )
            
            # Add credits
            if credits_earned > 0:
                await currency_service.add_currency(
                    db=db,
                    user_id=user_id,
                    currency_type=CurrencyTypeEnum.CREDITS,
                    amount=credits_earned,
                    activity_type=ActivityTypeEnum.QUIZ_COMPLETION,
                    activity_reference_id=quiz_result_id,
                    transaction_metadata=metadata
                )
            
            # Update daily activity
            daily_activity.quiz_completions += 1
            
            # Update quiz result with reward info
            quiz_result = await db.get(UserQuizResult, quiz_result_id)
            if quiz_result:
                quiz_result.points_earned = points_earned
                quiz_result.credits_earned = credits_earned
                quiz_result.reward_tier = reward_tier
                quiz_result.time_bonus_applied = time_bonus_applied
            
            result = {
                "points_earned": points_earned,
                "credits_earned": credits_earned,
                "reward_tier": reward_tier.value,
                "time_bonus_applied": time_bonus_applied,
                "perfect_score_bonus": perfect_score_bonus,
                "metadata": metadata
            }
            
            self.logger.info(
                "Quiz completion reward processed",
                user_id=str(user_id),
                quiz_id=str(quiz_id),
                **result
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Error processing quiz reward", user_id=str(user_id), error=str(e))
            raise
    
    async def process_myths_facts_reward(
        self,
        db: AsyncSession,
        user_id: UUID,
        game_session_id: UUID,
        score_percentage: int,
        time_taken: Optional[int] = None,
        perfect_accuracy: bool = False
    ) -> Dict:
        """Process rewards for myths vs facts game completion"""
        
        try:
            # Check if pure scoring mode is enabled
            pure_scoring_mode = await self._check_pure_scoring_mode(db)
            
            # Determine reward tier
            reward_tier = self._calculate_myths_facts_reward_tier(score_percentage)
            
            # Get reward configuration
            rewards_config = await self._get_rewards_config(db, ActivityTypeEnum.MYTHS_FACTS_GAME, reward_tier)
            
            if not rewards_config:
                self.logger.warning("No rewards configuration found", activity="myths_facts", tier=reward_tier.value)
                return {"points_earned": 0, "credits_earned": 0, "reward_tier": reward_tier.value}
            
            # Check daily limits
            daily_activity = await self._get_daily_activity(db, user_id)
            if not await self._check_daily_reward_limits(daily_activity, rewards_config):
                return {"points_earned": 0, "credits_earned": 0, "reward_tier": reward_tier.value, "reason": "daily_limit_reached"}
            
            # Calculate rewards
            base_points = rewards_config.points_reward
            base_credits = rewards_config.credits_reward
            points_earned = base_points
            credits_earned = base_credits
            
            # Initialize bonus tracking
            time_bonus_points = 0
            time_bonus_credits = 0
            perfect_bonus_points = 0
            perfect_bonus_credits = 0
            time_bonus_applied = False
            
            # Apply bonuses ONLY if NOT in pure scoring mode
            if not pure_scoring_mode:
                # Apply time bonus
                if (rewards_config.time_bonus_threshold and 
                    time_taken and 
                    time_taken <= rewards_config.time_bonus_threshold and 
                    score_percentage >= 70):  # Lower threshold for myths vs facts
                    
                    time_bonus_points = int(base_points * 0.4)  # 40% bonus
                    time_bonus_credits = int(base_credits * 0.3)  # 30% bonus
                    points_earned += time_bonus_points
                    credits_earned += time_bonus_credits
                    time_bonus_applied = True
                
                # Perfect accuracy bonus
                if perfect_accuracy and score_percentage == 100:
                    # Apply perfect bonus on top of time bonus
                    current_points = points_earned
                    current_credits = credits_earned
                    perfect_bonus_points = int(current_points * 0.25)  # 25% bonus on total
                    perfect_bonus_credits = int(current_credits * 0.25)  # 25% bonus on total
                    points_earned += perfect_bonus_points
                    credits_earned += perfect_bonus_credits
            
            # Award currency
            metadata = {
                "game_session_id": str(game_session_id),
                "base_points": base_points,
                "base_credits": base_credits,
                "time_bonus_points": time_bonus_points,
                "time_bonus_credits": time_bonus_credits,
                "perfect_bonus_points": perfect_bonus_points,
                "perfect_bonus_credits": perfect_bonus_credits,
                "score_percentage": score_percentage,
                "time_taken": time_taken,
                "reward_tier": reward_tier.value,
                "time_bonus_applied": time_bonus_applied,
                "perfect_accuracy": perfect_accuracy,
                "pure_scoring_mode": pure_scoring_mode  # ADD PURE SCORING MODE STATUS
            }
            
            if points_earned > 0:
                await currency_service.add_currency(
                    db=db,
                    user_id=user_id,
                    currency_type=CurrencyTypeEnum.POINTS,
                    amount=points_earned,
                    activity_type=ActivityTypeEnum.MYTHS_FACTS_GAME,
                    activity_reference_id=game_session_id,
                    transaction_metadata=metadata
                )
            
            if credits_earned > 0:
                await currency_service.add_currency(
                    db=db,
                    user_id=user_id,
                    currency_type=CurrencyTypeEnum.CREDITS,
                    amount=credits_earned,
                    activity_type=ActivityTypeEnum.MYTHS_FACTS_GAME,
                    activity_reference_id=game_session_id,
                    transaction_metadata=metadata
                )
            
            # Update daily activity
            daily_activity.myths_facts_games += 1
            
            result = {
                "points_earned": points_earned,
                "credits_earned": credits_earned,
                "reward_tier": reward_tier.value,
                "time_bonus_applied": time_bonus_applied,
                "perfect_accuracy": perfect_accuracy,
                "metadata": metadata
            }
            
            self.logger.info(
                "Myths vs facts reward processed",
                user_id=str(user_id),
                **result
            )
            
            return result
            
        except Exception as e:
            self.logger.error("Error processing myths facts reward", user_id=str(user_id), error=str(e))
            raise
    
    async def process_daily_login_reward(self, db: AsyncSession, user_id: UUID) -> Dict:
        """Process daily login reward"""
        
        try:
            # Check if already rewarded today
            daily_activity = await self._get_daily_activity(db, user_id)
            
            # Get login reward configuration
            rewards_config = await self._get_rewards_config(db, ActivityTypeEnum.DAILY_LOGIN, RewardTierEnum.BRONZE)
            
            if not rewards_config:
                return {"points_earned": 0, "credits_earned": 0, "reason": "no_config"}
            
            # Award base login reward
            points_earned = rewards_config.points_reward
            credits_earned = rewards_config.credits_reward
            
            # Streak bonuses
            streak_bonus_points = 0
            streak_bonus_credits = 0
            
            if daily_activity.login_streak >= 7:  # Weekly streak bonus
                streak_bonus_points = 10
                streak_bonus_credits = 2
            
            if daily_activity.login_streak >= 30:  # Monthly streak bonus
                streak_bonus_points = 50
                streak_bonus_credits = 10
            
            total_points = points_earned + streak_bonus_points
            total_credits = credits_earned + streak_bonus_credits
            
            metadata = {
                "login_streak": daily_activity.login_streak,
                "streak_bonus_points": streak_bonus_points,
                "streak_bonus_credits": streak_bonus_credits
            }
            
            # Award currency
            if total_points > 0:
                await currency_service.add_currency(
                    db=db,
                    user_id=user_id,
                    currency_type=CurrencyTypeEnum.POINTS,
                    amount=total_points,
                    activity_type=ActivityTypeEnum.DAILY_LOGIN,
                    transaction_metadata=metadata
                )
            
            if total_credits > 0:
                await currency_service.add_currency(
                    db=db,
                    user_id=user_id,
                    currency_type=CurrencyTypeEnum.CREDITS,
                    amount=total_credits,
                    activity_type=ActivityTypeEnum.DAILY_LOGIN,
                    transaction_metadata=metadata
                )
            
            result = {
                "points_earned": total_points,
                "credits_earned": total_credits,
                "login_streak": daily_activity.login_streak,
                "streak_bonus_applied": streak_bonus_points > 0,
                "metadata": metadata
            }
            
            self.logger.info("Daily login reward processed", user_id=str(user_id), **result)
            
            return result
            
        except Exception as e:
            self.logger.error("Error processing daily login reward", user_id=str(user_id), error=str(e))
            raise
    
    def _calculate_quiz_reward_tier(self, score_percentage: int) -> RewardTierEnum:
        """Calculate reward tier based on quiz performance"""
        if score_percentage >= 95:
            return RewardTierEnum.PLATINUM
        elif score_percentage >= 80:
            return RewardTierEnum.GOLD
        elif score_percentage >= 60:
            return RewardTierEnum.SILVER
        else:
            return RewardTierEnum.BRONZE
    
    def _calculate_myths_facts_reward_tier(self, score_percentage: int) -> RewardTierEnum:
        """Calculate reward tier for myths vs facts game"""
        if score_percentage >= 95:
            return RewardTierEnum.PLATINUM
        elif score_percentage >= 85:
            return RewardTierEnum.GOLD
        elif score_percentage >= 70:
            return RewardTierEnum.SILVER
        else:
            return RewardTierEnum.BRONZE
    
    async def _get_rewards_config(
        self, 
        db: AsyncSession, 
        activity_type: ActivityTypeEnum, 
        reward_tier: RewardTierEnum
    ) -> Optional[RewardsConfiguration]:
        """Get reward configuration for activity type and tier"""
        
        result = await db.execute(
            select(RewardsConfiguration)
            .where(and_(
                RewardsConfiguration.activity_type == activity_type,
                RewardsConfiguration.reward_tier == reward_tier,
                RewardsConfiguration.is_active == True
            ))
        )
        
        return result.scalar_one_or_none()
    
    async def _get_daily_activity(self, db: AsyncSession, user_id: UUID) -> UserDailyActivity:
        """Get or create today's daily activity record"""
        return await currency_service._get_or_create_daily_activity(db, user_id)
    
    async def _check_daily_reward_limits(
        self, 
        daily_activity: UserDailyActivity, 
        rewards_config: RewardsConfiguration
    ) -> bool:
        """Check if user has reached daily reward limits"""
        
        if not rewards_config.daily_cap:
            return True  # No limit
        
        # Check if adding this reward would exceed the daily cap
        if rewards_config.activity_type == ActivityTypeEnum.QUIZ_COMPLETION:
            return daily_activity.points_earned_today < rewards_config.daily_cap
        elif rewards_config.activity_type == ActivityTypeEnum.MYTHS_FACTS_GAME:
            return daily_activity.points_earned_today < rewards_config.daily_cap
        
        return True
    
    async def get_available_rewards_summary(self, db: AsyncSession, user_id: UUID) -> Dict:
        """Get summary of available rewards for user"""
        
        try:
            daily_activity = await self._get_daily_activity(db, user_id)
            
            # Get all active reward configurations
            result = await db.execute(
                select(RewardsConfiguration)
                .where(RewardsConfiguration.is_active == True)
                .order_by(RewardsConfiguration.activity_type, RewardsConfiguration.reward_tier)
            )
            
            configs = result.scalars().all()
            
            # Organize by activity type
            rewards_summary = {}
            for config in configs:
                activity = config.activity_type.value
                if activity not in rewards_summary:
                    rewards_summary[activity] = {"tiers": [], "daily_cap": config.daily_cap}
                
                rewards_summary[activity]["tiers"].append({
                    "tier": config.reward_tier.value,
                    "points_reward": config.points_reward,
                    "credits_reward": config.credits_reward,
                    "minimum_score_percentage": config.minimum_score_percentage,
                    "time_bonus_threshold": config.time_bonus_threshold
                })
            
            return {
                "rewards_structure": rewards_summary,
                "daily_progress": {
                    "points_earned_today": daily_activity.points_earned_today,
                    "credits_earned_today": daily_activity.credits_earned_today,
                    "quiz_completions": daily_activity.quiz_completions,
                    "myths_facts_games": daily_activity.myths_facts_games,
                    "login_streak": daily_activity.login_streak
                }
            }
            
        except Exception as e:
            self.logger.error("Error getting rewards summary", user_id=str(user_id), error=str(e))
            raise


# Global service instance
rewards_service = RewardsService()