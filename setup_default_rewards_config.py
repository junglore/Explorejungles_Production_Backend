"""
Default Rewards Configuration Setup
This script populates the rewards_configuration table with default values
"""

import asyncio
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text
from app.core.config import settings

# Default rewards configuration data
default_rewards_config = [
    # Quiz Completion Rewards
    {
        "activity_type": "QUIZ_COMPLETION",
        "reward_tier": "BRONZE",
        "points_reward": 10,
        "credits_reward": 1,
        "minimum_score_percentage": 60,
        "time_bonus_threshold": 300,  # 5 minutes
        "daily_cap": 100,
        "is_active": True
    },
    {
        "activity_type": "QUIZ_COMPLETION",
        "reward_tier": "SILVER", 
        "points_reward": 20,
        "credits_reward": 2,
        "minimum_score_percentage": 75,
        "time_bonus_threshold": 240,  # 4 minutes
        "daily_cap": 150,
        "is_active": True
    },
    {
        "activity_type": "QUIZ_COMPLETION",
        "reward_tier": "GOLD",
        "points_reward": 35,
        "credits_reward": 3,
        "minimum_score_percentage": 85,
        "time_bonus_threshold": 180,  # 3 minutes
        "daily_cap": 200,
        "is_active": True
    },
    {
        "activity_type": "QUIZ_COMPLETION",
        "reward_tier": "PLATINUM",
        "points_reward": 50,
        "credits_reward": 5,
        "minimum_score_percentage": 95,
        "time_bonus_threshold": 120,  # 2 minutes
        "daily_cap": 300,
        "is_active": True
    },
    
    # Myths vs Facts Game Rewards
    {
        "activity_type": "MYTHS_FACTS_GAME",
        "reward_tier": "BRONZE",
        "points_reward": 5,
        "credits_reward": 0,
        "minimum_score_percentage": 60,
        "time_bonus_threshold": 60,  # 1 minute
        "daily_cap": 50,
        "is_active": True
    },
    {
        "activity_type": "MYTHS_FACTS_GAME",
        "reward_tier": "SILVER",
        "points_reward": 10,
        "credits_reward": 1,
        "minimum_score_percentage": 80,
        "time_bonus_threshold": 45,
        "daily_cap": 75,
        "is_active": True
    },
    {
        "activity_type": "MYTHS_FACTS_GAME",
        "reward_tier": "GOLD",
        "points_reward": 15,
        "credits_reward": 1,
        "minimum_score_percentage": 90,
        "time_bonus_threshold": 30,
        "daily_cap": 100,
        "is_active": True
    },
    {
        "activity_type": "MYTHS_FACTS_GAME",
        "reward_tier": "PLATINUM",
        "points_reward": 25,
        "credits_reward": 2,
        "minimum_score_percentage": 100,
        "time_bonus_threshold": 20,
        "daily_cap": 150,
        "is_active": True
    },
    
    # Daily Login Rewards
    {
        "activity_type": "DAILY_LOGIN",
        "reward_tier": "BRONZE",
        "points_reward": 5,
        "credits_reward": 0,
        "daily_cap": 5,
        "is_active": True
    },
    {
        "activity_type": "DAILY_LOGIN",
        "reward_tier": "SILVER",
        "points_reward": 10,
        "credits_reward": 1,
        "daily_cap": 10,
        "is_active": True
    },
    
    # Streak Bonus Rewards
    {
        "activity_type": "STREAK_BONUS",
        "reward_tier": "BRONZE",
        "points_reward": 10,
        "credits_reward": 1,
        "is_active": True
    },
    {
        "activity_type": "STREAK_BONUS", 
        "reward_tier": "SILVER",
        "points_reward": 25,
        "credits_reward": 2,
        "is_active": True
    },
    {
        "activity_type": "STREAK_BONUS",
        "reward_tier": "GOLD", 
        "points_reward": 50,
        "credits_reward": 5,
        "is_active": True
    },
    
    # Achievement Unlock Rewards
    {
        "activity_type": "ACHIEVEMENT_UNLOCK",
        "reward_tier": "BRONZE",
        "points_reward": 50,
        "credits_reward": 5,
        "is_active": True
    },
    {
        "activity_type": "ACHIEVEMENT_UNLOCK",
        "reward_tier": "SILVER",
        "points_reward": 100,
        "credits_reward": 10,
        "is_active": True
    },
    {
        "activity_type": "ACHIEVEMENT_UNLOCK",
        "reward_tier": "GOLD",
        "points_reward": 200,
        "credits_reward": 20,
        "is_active": True
    },
    {
        "activity_type": "ACHIEVEMENT_UNLOCK",
        "reward_tier": "PLATINUM",
        "points_reward": 500,
        "credits_reward": 50,
        "is_active": True
    }
]

# SQL INSERT statements for PostgreSQL
sql_inserts = []

for config in default_rewards_config:
    values = (
        f"'{uuid4()}'",  # id
        f"'{config['activity_type']}'",  # activity_type
        f"'{config['reward_tier']}'",  # reward_tier
        str(config['points_reward']),  # points_reward
        str(config['credits_reward']),  # credits_reward
        str(config.get('minimum_score_percentage', 'NULL')),  # minimum_score_percentage
        str(config.get('time_bonus_threshold', 'NULL')),  # time_bonus_threshold
        str(config.get('daily_cap', 'NULL')),  # daily_cap
        str(config['is_active']).lower(),  # is_active
        'NOW()',  # created_at
        'NOW()'   # updated_at
    )
    
    sql_inserts.append(f"""
INSERT INTO rewards_configuration (
    id, activity_type, reward_tier, points_reward, credits_reward,
    minimum_score_percentage, time_bonus_threshold, daily_cap, is_active, 
    created_at, updated_at
) VALUES ({', '.join(values)});""")

print("-- Default Rewards Configuration Setup")
print("-- Run these SQL statements to populate the rewards_configuration table")
print("")
for insert in sql_inserts:
    print(insert)

# Execute the inserts
async def populate_rewards():
    # Use external URL for railway run
    import os
    db_url = os.environ.get('DATABASE_PUBLIC_URL') or settings.DATABASE_URL
    if db_url and not db_url.startswith("postgresql+asyncpg"):
        if db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        for config in default_rewards_config:
            await conn.execute(text("""
                INSERT INTO rewards_configuration (
                    id, activity_type, reward_tier, points_reward, credits_reward,
                    minimum_score_percentage, time_bonus_threshold, daily_cap, is_active,
                    created_at, updated_at
                ) VALUES (:id, :activity_type, :reward_tier, :points_reward, :credits_reward,
                         :minimum_score_percentage, :time_bonus_threshold, :daily_cap, :is_active,
                         NOW(), NOW())
                ON CONFLICT DO NOTHING
            """), {
                'id': str(uuid4()),
                'activity_type': config['activity_type'],
                'reward_tier': config['reward_tier'],
                'points_reward': config['points_reward'],
                'credits_reward': config['credits_reward'],
                'minimum_score_percentage': config.get('minimum_score_percentage'),
                'time_bonus_threshold': config.get('time_bonus_threshold'),
                'daily_cap': config.get('daily_cap'),
                'is_active': config['is_active']
            })
        print("Rewards configuration populated successfully!")

if __name__ == "__main__":
    asyncio.run(populate_rewards())