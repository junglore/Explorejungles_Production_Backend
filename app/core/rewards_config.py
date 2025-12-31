"""
DEPRECATED: Static rewards configuration file - DATABASE IS SOURCE OF TRUTH

⚠️ WARNING: This file contains OBSOLETE configuration values that DO NOT match the database.
The authoritative source for all reward values is the `rewards_configuration` table in the database.

This file is kept only for:
1. Achievement definitions
2. Anti-gaming thresholds  
3. Daily limits
4. Leaderboard configuration

DO NOT use DEFAULT_REWARDS_CONFIG for actual rewards - it conflicts with database values!

For actual reward values, query the database:
- rewards_configuration table for base points/credits
- site_settings table for multipliers and limits
"""

from app.models.rewards import ActivityTypeEnum, RewardTierEnum

# DEPRECATED: Default Rewards Configuration - DO NOT USE FOR ACTUAL REWARDS
# Use database rewards_configuration table instead!
# These values DO NOT match the current database and will cause confusion.
DEPRECATED_REWARDS_CONFIG = [
    # Quiz Completion Rewards
    {
        "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
        "reward_tier": RewardTierEnum.BRONZE,
        "points_reward": 5,
        "credits_reward": 1,
        "minimum_score_percentage": 50,
        "time_bonus_threshold": None,
        "daily_cap": 50,  # Max 50 points per day from bronze quiz completions
    },
    {
        "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
        "reward_tier": RewardTierEnum.SILVER,
        "points_reward": 10,
        "credits_reward": 2,
        "minimum_score_percentage": 60,
        "time_bonus_threshold": None,
        "daily_cap": 100,
    },
    {
        "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
        "reward_tier": RewardTierEnum.GOLD,
        "points_reward": 20,
        "credits_reward": 5,
        "minimum_score_percentage": 80,
        "time_bonus_threshold": 300,  # 5 minutes for time bonus
        "daily_cap": 200,
    },
    {
        "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
        "reward_tier": RewardTierEnum.PLATINUM,
        "points_reward": 30,
        "credits_reward": 10,
        "minimum_score_percentage": 95,
        "time_bonus_threshold": 180,  # 3 minutes for time bonus
        "daily_cap": 300,
    },
    
    # Myths vs Facts Game Rewards
    {
        "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
        "reward_tier": RewardTierEnum.BRONZE,
        "points_reward": 3,
        "credits_reward": 1,
        "minimum_score_percentage": 50,
        "time_bonus_threshold": None,
        "daily_cap": 30,
    },
    {
        "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
        "reward_tier": RewardTierEnum.SILVER,
        "points_reward": 7,
        "credits_reward": 2,
        "minimum_score_percentage": 70,
        "time_bonus_threshold": None,
        "daily_cap": 70,
    },
    {
        "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
        "reward_tier": RewardTierEnum.GOLD,
        "points_reward": 15,
        "credits_reward": 3,
        "minimum_score_percentage": 85,
        "time_bonus_threshold": 120,  # 2 minutes for time bonus
        "daily_cap": 150,
    },
    {
        "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
        "reward_tier": RewardTierEnum.PLATINUM,
        "points_reward": 25,
        "credits_reward": 5,
        "minimum_score_percentage": 95,
        "time_bonus_threshold": 90,  # 1.5 minutes for time bonus
        "daily_cap": 250,
    },
    
    # Daily Login Rewards
    {
        "activity_type": ActivityTypeEnum.DAILY_LOGIN,
        "reward_tier": RewardTierEnum.BRONZE,
        "points_reward": 5,
        "credits_reward": 1,
        "minimum_score_percentage": None,
        "time_bonus_threshold": None,
        "daily_cap": 5,  # Once per day
    },
    
    # Streak Bonuses
    {
        "activity_type": ActivityTypeEnum.STREAK_BONUS,
        "reward_tier": RewardTierEnum.SILVER,  # 7-day streak
        "points_reward": 20,
        "credits_reward": 5,
        "minimum_score_percentage": None,
        "time_bonus_threshold": None,
        "daily_cap": 20,  # Once per week
    },
    {
        "activity_type": ActivityTypeEnum.STREAK_BONUS,
        "reward_tier": RewardTierEnum.GOLD,  # 30-day streak
        "points_reward": 100,
        "credits_reward": 25,
        "minimum_score_percentage": None,
        "time_bonus_threshold": None,
        "daily_cap": 100,  # Once per month
    },
    
    # Achievement Unlocks
    {
        "activity_type": ActivityTypeEnum.ACHIEVEMENT_UNLOCK,
        "reward_tier": RewardTierEnum.BRONZE,
        "points_reward": 25,
        "credits_reward": 5,
        "minimum_score_percentage": None,
        "time_bonus_threshold": None,
        "daily_cap": None,  # No daily cap on achievements
    },
    {
        "activity_type": ActivityTypeEnum.ACHIEVEMENT_UNLOCK,
        "reward_tier": RewardTierEnum.SILVER,
        "points_reward": 50,
        "credits_reward": 10,
        "minimum_score_percentage": None,
        "time_bonus_threshold": None,
        "daily_cap": None,
    },
    {
        "activity_type": ActivityTypeEnum.ACHIEVEMENT_UNLOCK,
        "reward_tier": RewardTierEnum.GOLD,
        "points_reward": 100,
        "credits_reward": 25,
        "minimum_score_percentage": None,
        "time_bonus_threshold": None,
        "daily_cap": None,
    },
    {
        "activity_type": ActivityTypeEnum.ACHIEVEMENT_UNLOCK,
        "reward_tier": RewardTierEnum.PLATINUM,
        "points_reward": 250,
        "credits_reward": 50,
        "minimum_score_percentage": None,
        "time_bonus_threshold": None,
        "daily_cap": None,
    },
]

# Anti-gaming thresholds
ANTI_GAMING_CONFIG = {
    "QUIZ_COMPLETION": {
        "min_time_seconds": 30,  # Minimum time to complete a quiz
        "max_perfect_scores_per_day": 5,  # Max perfect scores per day before flagging
        "max_attempts_per_hour": 10,  # Max quiz attempts per hour
        "suspicious_pattern_threshold": 0.7,  # Risk score threshold for flagging
    },
    "MYTHS_FACTS_GAME": {
        "min_time_seconds": 20,  # Minimum time to complete myths vs facts
        "max_perfect_scores_per_day": 10,  # Max perfect scores per day
        "max_attempts_per_hour": 15,  # Max game attempts per hour
        "suspicious_pattern_threshold": 0.8,  # Risk score threshold
    }
}

# Daily activity limits
DAILY_LIMITS = {
    "max_quiz_attempts": 50,
    "max_myths_facts_games": 100,
    "max_points_from_quizzes": 300,
    "max_points_from_games": 250,
    "max_total_points_per_day": 500,
    "max_credits_per_day": 50,
}

# Achievement definitions
ACHIEVEMENT_DEFINITIONS = [
    {
        "type": "QUIZ_MASTER",
        "name": "Quiz Master",
        "description": "Complete {target} quizzes",
        "levels": [
            {"level": 1, "target": 10, "points": 25, "credits": 5},
            {"level": 2, "target": 25, "points": 50, "credits": 10},
            {"level": 3, "target": 50, "points": 100, "credits": 25},
            {"level": 4, "target": 100, "points": 250, "credits": 50},
        ]
    },
    {
        "type": "MYTH_BUSTER",
        "name": "Myth Buster",
        "description": "Complete {target} myths vs facts games",
        "levels": [
            {"level": 1, "target": 20, "points": 25, "credits": 5},
            {"level": 2, "target": 50, "points": 50, "credits": 10},
            {"level": 3, "target": 100, "points": 100, "credits": 25},
            {"level": 4, "target": 200, "points": 250, "credits": 50},
        ]
    },
    {
        "type": "SPEED_DEMON",
        "name": "Speed Demon",
        "description": "Complete activities quickly {target} times",
        "levels": [
            {"level": 1, "target": 5, "points": 50, "credits": 10},
            {"level": 2, "target": 15, "points": 100, "credits": 20},
            {"level": 3, "target": 30, "points": 200, "credits": 40},
        ]
    },
    {
        "type": "PERFECT_SCORE",
        "name": "Perfectionist",
        "description": "Achieve perfect scores {target} times",
        "levels": [
            {"level": 1, "target": 3, "points": 50, "credits": 10},
            {"level": 2, "target": 10, "points": 100, "credits": 25},
            {"level": 3, "target": 25, "points": 250, "credits": 50},
        ]
    },
    {
        "type": "DAILY_WARRIOR",
        "name": "Daily Warrior",
        "description": "Login daily for {target} consecutive days",
        "levels": [
            {"level": 1, "target": 7, "points": 50, "credits": 10},
            {"level": 2, "target": 30, "points": 200, "credits": 40},
            {"level": 3, "target": 100, "points": 500, "credits": 100},
        ]
    },
]

# Leaderboard configuration
LEADERBOARD_CONFIG = {
    "GLOBAL_POINTS": {
        "name": "Global Points Leaders",
        "description": "Top users by total points earned",
        "update_frequency": "hourly",
        "top_count": 100,
    },
    "GLOBAL_QUIZ": {
        "name": "Quiz Champions",
        "description": "Top performers in quizzes",
        "update_frequency": "hourly",
        "top_count": 50,
    },
    "GLOBAL_MYTHS": {
        "name": "Myth Busters",
        "description": "Top performers in myths vs facts",
        "update_frequency": "hourly",
        "top_count": 50,
    },
    "WEEKLY_POINTS": {
        "name": "Weekly Champions",
        "description": "Top points earners this week",
        "update_frequency": "hourly",
        "top_count": 25,
    },
    "MONTHLY_POINTS": {
        "name": "Monthly Legends",
        "description": "Top points earners this month",
        "update_frequency": "daily",
        "top_count": 25,
    },
}