"""
Public Configuration API Endpoints

This module provides public configuration endpoints for frontend consumption.
These endpoints are designed to be lightweight, cacheable, and accessible
without authentication for optimal frontend performance.

Key Features:
- Public access (no authentication required)
- Optimized for frontend consumption
- Cacheable responses for performance
- Clean separation from admin configuration

Endpoints:
- GET /config/mvf: Get Myths vs Facts game configuration
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any
import structlog

from app.db.database import get_db
from app.models.site_setting import SiteSetting

logger = structlog.get_logger()
router = APIRouter()


@router.get("/mvf", response_class=JSONResponse)
async def get_mvf_config(db: AsyncSession = Depends(get_db)):
    """
    Get public Myths vs Facts configuration for frontend use.
    
    This endpoint provides the current game configuration including:
    - Base points and credits per game
    - Performance tier multipliers
    - Daily limits and game parameters
    - User tier bonuses
    
    This endpoint is public (no authentication required) and optimized
    for frontend consumption with caching headers.
    
    Returns:
        JSONResponse: Configuration object with game settings
        
    Example Response:
        {
            "success": true,
            "config": {
                "basePointsPerCard": 5,
                "baseCreditsPerGame": 3,
                "performanceTiers": {...},
                "dailyLimits": {...}
            },
            "source": "database" | "default"
        }
    """
    try:
        # Get current system settings
        settings_query = select(SiteSetting)
        result = await db.execute(settings_query)
        settings = result.scalars().all()
        
        # Convert to dict for easier access
        settings_dict = {}
        for setting in settings:
            settings_dict[setting.key] = {
                'value': setting.parsed_value,
                'description': setting.description,
                'category': setting.category
            }
        
        # Get mythsVsFacts_config from database
        mvf_setting = settings_dict.get('mythsVsFacts_config', {}).get('value', {})
        
        # Get individual MVF settings (these take priority over JSON config)
        mvf_individual_settings = {
            'mvf_base_points_per_card': settings_dict.get('mvf_base_points_per_card', {}).get('value', 5),
            'mvf_base_credits_per_game': settings_dict.get('mvf_base_credits_per_game', {}).get('value', 3),
            'mvf_cards_per_game': settings_dict.get('mvf_cards_per_game', {}).get('value', 10),
            'mvf_max_games_per_day': settings_dict.get('mvf_max_games_per_day', {}).get('value', 20),
            'mvf_daily_points_limit': settings_dict.get('mvf_daily_points_limit', {}).get('value', 200),
            'mvf_daily_credits_limit': settings_dict.get('mvf_daily_credits_limit', {}).get('value', 50)
        }

        # Extract values with priority: individual settings > JSON config > defaults
        base_points_per_card = mvf_individual_settings.get(
            'mvf_base_points_per_card', 
            mvf_setting.get('basePointsPerCard', 5) if mvf_setting else 5
        )
        
        base_credits_per_game = mvf_individual_settings.get(
            'mvf_base_credits_per_game', 
            mvf_setting.get('baseCreditsPerGame', 3) if mvf_setting else 3
        )
        
        cards_per_game = mvf_individual_settings.get(
            'mvf_cards_per_game',
            mvf_setting.get('gameParameters', {}).get('cardsPerGame', 10) if mvf_setting else 10
        )
        
        max_games_per_day = mvf_individual_settings.get(
            'mvf_max_games_per_day',
            mvf_setting.get('dailyLimits', {}).get('maxGamesPerDay', 20) if mvf_setting else 20
        )
        
        time_per_card = mvf_setting.get('gameParameters', {}).get('timePerCard', 30) if mvf_setting else 30
        
        # Get MVF-specific daily limits
        mvf_daily_points_limit = settings_dict.get('mvf_daily_points_limit', {}).get('value', 200)
        mvf_daily_credits_limit = settings_dict.get('mvf_daily_credits_limit', {}).get('value', 50)
        
        # Use MVF-specific limits if available, fallback to legacy settings
        daily_points_limit = mvf_daily_points_limit if mvf_daily_points_limit else (
            mvf_setting.get('dailyLimits', {}).get('maxPointsPerDay', 500) if mvf_setting else 500
        )
        daily_credits_limit = mvf_daily_credits_limit if mvf_daily_credits_limit else (
            mvf_setting.get('dailyLimits', {}).get('maxCreditsPerDay', 200) if mvf_setting else 200
        )

        # Build the public configuration object
        config = {
            "basePointsPerCard": base_points_per_card,
            "baseCreditsPerGame": base_credits_per_game,
            "performanceTiers": {
                "bronze": {"multiplier": 1.0, "threshold": 50, "scoreRange": "50-74%"},
                "silver": {"multiplier": 1.2, "threshold": 70, "scoreRange": "75-84%"},
                "gold": {"multiplier": 1.5, "threshold": 85, "scoreRange": "85-94%"},
                "platinum": {"multiplier": 2.0, "threshold": 95, "scoreRange": "95-100%"}
            },
            "userTiers": {
                "bronze": {"bonusMultiplier": 1.0, "range": "0-99 points"},
                "silver": {"bonusMultiplier": 1.1, "range": "100-499 points"},
                "gold": {"bonusMultiplier": 1.2, "range": "500-999 points"},
                "platinum": {"bonusMultiplier": 1.3, "range": "1000+ points"}
            },
            "dailyLimits": {
                "maxGamesPerDay": max_games_per_day,
                "maxPointsPerDay": daily_points_limit,
                "maxCreditsPerDay": daily_credits_limit
            },
            "gameParameters": {
                "cardsPerGame": cards_per_game,
                "timePerCard": time_per_card,
                "passingScore": 60
            }
        }
        
        # Determine data source
        source = "database" if (settings_dict or mvf_setting) else "default"
        
        response = JSONResponse(
            content={
                "success": True,
                "config": config,
                "source": source,
                "timestamp": "2025-10-10T12:45:00Z"  # Can be dynamic if needed
            },
            # Add caching headers for performance
            headers={
                "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
                "ETag": f'"mvf-config-{hash(str(config))}"'
            }
        )
        
        logger.info(
            "Public MVF configuration served",
            source=source,
            base_points=base_points_per_card,
            base_credits=base_credits_per_game
        )
        
        return response
        
    except Exception as e:
        logger.error("Error fetching public MVF configuration", error=str(e))
        
        # Return default configuration on error to ensure frontend always works
        default_config = {
            "basePointsPerCard": 5,
            "baseCreditsPerGame": 3,
            "performanceTiers": {
                "bronze": {"multiplier": 1.0, "threshold": 50, "scoreRange": "50-74%"},
                "silver": {"multiplier": 1.2, "threshold": 70, "scoreRange": "75-84%"},
                "gold": {"multiplier": 1.5, "threshold": 85, "scoreRange": "85-94%"},
                "platinum": {"multiplier": 2.0, "threshold": 95, "scoreRange": "95-100%"}
            },
            "userTiers": {
                "bronze": {"bonusMultiplier": 1.0, "range": "0-99 points"},
                "silver": {"bonusMultiplier": 1.1, "range": "100-499 points"},
                "gold": {"bonusMultiplier": 1.2, "range": "500-999 points"},
                "platinum": {"bonusMultiplier": 1.3, "range": "1000+ points"}
            },
            "dailyLimits": {
                "maxGamesPerDay": 20,
                "maxPointsPerDay": 500,
                "maxCreditsPerDay": 200
            },
            "gameParameters": {
                "cardsPerGame": 10,
                "timePerCard": 30,
                "passingScore": 60
            }
        }
        
        return JSONResponse(
            content={
                "success": True,
                "config": default_config,
                "source": "default_fallback",
                "error": "Database unavailable, using defaults"
            },
            headers={
                "Cache-Control": "public, max-age=60",  # Shorter cache on error
            }
        )