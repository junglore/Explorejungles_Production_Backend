"""
Settings Service - Centralized settings management with caching
"""

from typing import Any, Dict, Optional, Union
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import json

from app.models.site_setting import SiteSetting

logger = structlog.get_logger()


class SettingsService:
    """Service for managing site settings with caching"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Any] = {}
        self._cache_loaded = False
    
    async def load_all_settings(self) -> None:
        """Load all settings into cache"""
        try:
            result = await self.db.execute(select(SiteSetting))
            settings = result.scalars().all()
            
            self._cache = {}
            for setting in settings:
                self._cache[setting.key] = setting.parsed_value
            
            self._cache_loaded = True
            logger.info(f"Loaded {len(self._cache)} settings into cache")
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
            self._cache = {}
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        if not self._cache_loaded:
            await self.load_all_settings()
        
        return self._cache.get(key, default)
    
    async def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean setting"""
        value = await self.get(key, default)
        if isinstance(value, str):
            return value.lower() == 'true'
        return bool(value)
    
    async def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer setting"""
        value = await self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    async def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float setting"""
        value = await self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    async def get_str(self, key: str, default: str = "") -> str:
        """Get a string setting"""
        value = await self.get(key, default)
        return str(value) if value is not None else default
    
    async def get_json(self, key: str, default: Any = None) -> Any:
        """Get a JSON setting"""
        value = await self.get(key, default)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return default
        return value if value is not None else default
    
    async def set(self, key: str, value: Any) -> None:
        """Set a setting value"""
        try:
            # Update cache
            self._cache[key] = value
            
            # Update database
            result = await self.db.execute(
                select(SiteSetting).where(SiteSetting.key == key)
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.set_value(value)
            else:
                # Create new setting
                setting = SiteSetting(
                    key=key,
                    value=str(value),
                    data_type='str',
                    category='general',
                    label=key.replace('_', ' ').title(),
                    description=f'Setting: {key}'
                )
                self.db.add(setting)
            
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Error setting {key}: {e}")
            raise
    
    async def invalidate_cache(self) -> None:
        """Invalidate the cache"""
        self._cache = {}
        self._cache_loaded = False
    
    # Convenience methods for specific settings
    
    async def get_tier_multiplier(self, tier: str) -> float:
        """Get tier multiplier (bronze, silver, gold, platinum)"""
        key = f"tier_multiplier_{tier.lower()}"
        defaults = {
            'tier_multiplier_bronze': 1.0,
            'tier_multiplier_silver': 1.2,
            'tier_multiplier_gold': 1.5,
            'tier_multiplier_platinum': 2.0
        }
        return await self.get_float(key, defaults.get(key, 1.0))
    
    async def get_daily_limits(self) -> Dict[str, int]:
        """Get daily earning limits"""
        return {
            'points': await self.get_int('daily_points_limit', 500),
            'credits': await self.get_int('daily_credit_cap_quizzes', 200)
        }
    
    async def get_time_bonuses(self) -> Dict[str, Union[int, float]]:
        """Get time-based bonus settings"""
        return {
            'quick_completion_threshold': await self.get_int('quick_completion_bonus_threshold', 30),
            'quick_completion_multiplier': await self.get_float('quick_completion_bonus_multiplier', 1.25),
            'streak_threshold': await self.get_int('streak_bonus_threshold', 3),
            'streak_multiplier': await self.get_float('streak_bonus_multiplier', 1.1)
        }
    
    async def get_event_bonuses(self) -> Dict[str, Union[bool, float, str]]:
        """Get event and seasonal bonus settings"""
        return {
            'special_event_multiplier': await self.get_float('special_event_multiplier', 2.0),
            'weekend_bonus_enabled': await self.get_bool('weekend_bonus_enabled', False),
            'weekend_bonus_multiplier': await self.get_float('weekend_bonus_multiplier', 1.5),
            'seasonal_event_active': await self.get_bool('seasonal_event_active', False),
            'seasonal_event_name': await self.get_str('seasonal_event_name', ''),
            'seasonal_event_multiplier': await self.get_float('seasonal_event_multiplier', 1.8)
        }
    
    async def get_leaderboard_settings(self) -> Dict[str, Union[bool, int]]:
        """Get leaderboard configuration"""
        return {
            'public_enabled': await self.get_bool('leaderboard_public_enabled', True),
            'show_real_names': await self.get_bool('leaderboard_show_real_names', False),
            'anonymous_mode': await self.get_bool('leaderboard_anonymous_mode', False),
            'max_entries': await self.get_int('leaderboard_max_entries', 100),
            'reset_weekly': await self.get_bool('leaderboard_reset_weekly', True),
            'reset_monthly': await self.get_bool('leaderboard_reset_monthly', True)
        }
    
    async def get_security_settings(self) -> Dict[str, Union[int, float, bool]]:
        """Get security and anti-gaming settings"""
        return {
            'max_quiz_attempts_per_day': await self.get_int('max_quiz_attempts_per_day', 10),
            'min_time_between_attempts': await self.get_int('min_time_between_attempts', 300),
            'suspicious_score_threshold': await self.get_float('suspicious_score_threshold', 0.95),
            'rapid_completion_threshold': await self.get_int('rapid_completion_threshold', 30),
            'enable_ip_tracking': await self.get_bool('enable_ip_tracking', True),
            'enable_behavior_analysis': await self.get_bool('enable_behavior_analysis', True)
        }
    
    async def is_rewards_system_enabled(self) -> bool:
        """Check if rewards system is enabled"""
        return await self.get_bool('rewards_system_enabled', True)