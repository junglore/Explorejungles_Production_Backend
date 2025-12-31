"""
Settings API endpoints for frontend integration testing
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import logging

from ..db.database import get_db
from ..core.security import get_current_user_optional
from ..services.settings_service import SettingsService
from ..models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/settings/public")
async def get_public_settings(
    db: AsyncSession = Depends(get_db)
):
    """
    Get public settings that can be displayed to all users
    """
    try:
        settings = SettingsService(db)
        
        public_settings = {
            "leaderboard": await settings.get_leaderboard_settings(),
            "rewards_enabled": await settings.is_rewards_system_enabled(),
            "daily_limits": await settings.get_daily_limits(),
            "event_bonuses": {
                "weekend_bonus_enabled": (await settings.get_event_bonuses())["weekend_bonus_enabled"],
                "special_event_active": (await settings.get_event_bonuses())["special_event_multiplier"] > 1.0,
                "seasonal_event_active": (await settings.get_event_bonuses())["seasonal_event_active"],
                "seasonal_event_name": (await settings.get_event_bonuses())["seasonal_event_name"]
            },
            "tier_multipliers": {
                "bronze": await settings.get_tier_multiplier("bronze"),
                "silver": await settings.get_tier_multiplier("silver"),
                "gold": await settings.get_tier_multiplier("gold"),
                "platinum": await settings.get_tier_multiplier("platinum")
            }
        }
        
        return {"settings": public_settings, "status": "active"}
        
    except Exception as e:
        logger.error(f"Error getting public settings: {e}")
        raise HTTPException(status_code=500, detail="Failed to get settings")


@router.get("/settings/user-tier")
async def get_user_tier_info(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's tier and related bonus information
    """
    if not current_user:
        return {"tier": "bronze", "multiplier": 1.0, "authenticated": False}
    
    try:
        from ..services.enhanced_rewards_service import EnhancedRewardsService
        enhanced_rewards = EnhancedRewardsService(db)
        settings = SettingsService(db)
        
        # Get user tier
        user_tier = await enhanced_rewards.get_user_tier(current_user.id)
        tier_multiplier = await settings.get_tier_multiplier(user_tier)
        
        # Get user streak
        user_streak = await enhanced_rewards.get_user_streak(current_user.id)
        
        # Get time bonuses info
        time_bonuses = await settings.get_time_bonuses()
        
        # Get current event bonuses
        event_bonuses = await settings.get_event_bonuses()
        is_weekend = await enhanced_rewards.is_weekend()
        
        active_bonuses = []
        if user_streak >= time_bonuses['streak_threshold']:
            active_bonuses.append(f"{user_streak} day streak")
        
        if event_bonuses['weekend_bonus_enabled'] and is_weekend:
            active_bonuses.append("Weekend bonus")
        
        if event_bonuses['special_event_multiplier'] > 1.0:
            active_bonuses.append("Special event")
        
        if event_bonuses['seasonal_event_active']:
            active_bonuses.append(event_bonuses['seasonal_event_name'] or "Seasonal event")
        
        return {
            "tier": user_tier,
            "multiplier": tier_multiplier,
            "streak": user_streak,
            "active_bonuses": active_bonuses,
            "authenticated": True
        }
        
    except Exception as e:
        logger.error(f"Error getting user tier info: {e}")
        return {"tier": "bronze", "multiplier": 1.0, "authenticated": True, "error": str(e)}


@router.get("/settings/integration-test")
async def test_settings_integration(
    db: AsyncSession = Depends(get_db)
):
    """
    Test endpoint to verify all settings are working
    """
    try:
        settings = SettingsService(db)
        
        # Load all settings
        await settings.load_all_settings()
        
        # Test each category
        test_results = {
            "settings_loaded": len(settings._cache) > 0,
            "leaderboard_settings": await settings.get_leaderboard_settings(),
            "tier_multipliers": {
                tier: await settings.get_tier_multiplier(tier)
                for tier in ["bronze", "silver", "gold", "platinum"]
            },
            "time_bonuses": await settings.get_time_bonuses(),
            "event_bonuses": await settings.get_event_bonuses(),
            "daily_limits": await settings.get_daily_limits(),
            "security_settings": await settings.get_security_settings(),
            "rewards_enabled": await settings.is_rewards_system_enabled()
        }
        
        # Check for potential issues
        issues = []
        
        if not test_results["settings_loaded"]:
            issues.append("Settings not loaded")
        
        if all(mult == 1.0 for mult in test_results["tier_multipliers"].values()):
            issues.append("Tier multipliers not configured")
        
        if test_results["time_bonuses"]["quick_completion_multiplier"] == 1.0:
            issues.append("Time bonuses not configured")
        
        return {
            "status": "success" if not issues else "warning",
            "issues": issues,
            "test_results": test_results,
            "total_settings": len(settings._cache)
        }
        
    except Exception as e:
        logger.error(f"Error in settings integration test: {e}")
        return {
            "status": "error", 
            "error": str(e),
            "test_results": {}
        }