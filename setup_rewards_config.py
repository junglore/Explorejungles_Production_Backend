"""
Script to set up default rewards configurations for the Knowledge Engine
This will create the necessary reward configurations for quizzes and other activities
"""

import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Add the app directory to the path
sys.path.append(str(Path(__file__).parent))

from app.db.database import get_db_session
from app.models.rewards import RewardsConfiguration, ActivityTypeEnum, RewardTierEnum


async def create_quiz_reward_configurations():
    """Create reward configurations for quiz completion"""
    
    # Quiz completion rewards for different tiers
    quiz_configs = [
        {
            "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
            "reward_tier": RewardTierEnum.BRONZE,
            "points_reward": 10,
            "credits_reward": 5,
            "minimum_score_percentage": 0,
            "time_bonus_threshold": 300,  # 5 minutes
            "daily_cap": 100,
            "is_active": True
        },
        {
            "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
            "reward_tier": RewardTierEnum.SILVER,
            "points_reward": 20,
            "credits_reward": 10,
            "minimum_score_percentage": 60,
            "time_bonus_threshold": 240,  # 4 minutes
            "daily_cap": 150,
            "is_active": True
        },
        {
            "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
            "reward_tier": RewardTierEnum.GOLD,
            "points_reward": 35,
            "credits_reward": 20,
            "minimum_score_percentage": 80,
            "time_bonus_threshold": 180,  # 3 minutes
            "daily_cap": 200,
            "is_active": True
        },
        {
            "activity_type": ActivityTypeEnum.QUIZ_COMPLETION,
            "reward_tier": RewardTierEnum.PLATINUM,
            "points_reward": 50,
            "credits_reward": 30,
            "minimum_score_percentage": 95,
            "time_bonus_threshold": 120,  # 2 minutes
            "daily_cap": 300,
            "is_active": True
        }
    ]
    
    async with get_db_session() as db:
        for config_data in quiz_configs:
            config = RewardsConfiguration(**config_data)
            db.add(config)
        
        await db.commit()
        print(f"Created {len(quiz_configs)} quiz reward configurations")


async def create_myths_facts_reward_configurations():
    """Create reward configurations for myths vs facts game"""
    
    myths_facts_configs = [
        {
            "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
            "reward_tier": RewardTierEnum.BRONZE,
            "points_reward": 5,
            "credits_reward": 2,
            "minimum_score_percentage": 0,
            "daily_cap": 50,
            "is_active": True
        },
        {
            "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
            "reward_tier": RewardTierEnum.SILVER,
            "points_reward": 8,
            "credits_reward": 4,
            "minimum_score_percentage": 60,
            "daily_cap": 80,
            "is_active": True
        },
        {
            "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
            "reward_tier": RewardTierEnum.GOLD,
            "points_reward": 12,
            "credits_reward": 6,
            "minimum_score_percentage": 80,
            "daily_cap": 100,
            "is_active": True
        },
        {
            "activity_type": ActivityTypeEnum.MYTHS_FACTS_GAME,
            "reward_tier": RewardTierEnum.PLATINUM,
            "points_reward": 20,
            "credits_reward": 10,
            "minimum_score_percentage": 95,
            "daily_cap": 150,
            "is_active": True
        }
    ]
    
    async with get_db_session() as db:
        for config_data in myths_facts_configs:
            config = RewardsConfiguration(**config_data)
            db.add(config)
        
        await db.commit()
        print(f"Created {len(myths_facts_configs)} myths vs facts reward configurations")


async def create_daily_login_reward_configurations():
    """Create reward configurations for daily login"""
    
    daily_login_configs = [
        {
            "activity_type": ActivityTypeEnum.DAILY_LOGIN,
            "reward_tier": RewardTierEnum.BRONZE,
            "points_reward": 5,
            "credits_reward": 3,
            "daily_cap": 5,  # Can only get daily login once per day
            "is_active": True
        }
    ]
    
    async with get_db_session() as db:
        for config_data in daily_login_configs:
            config = RewardsConfiguration(**config_data)
            db.add(config)
        
        await db.commit()
        print(f"Created {len(daily_login_configs)} daily login reward configurations")


async def create_content_interaction_reward_configurations():
    """Create reward configurations for content interactions"""
    
    # Skip for now - these activity types don't exist yet
    print("Skipping content interaction configs - activity types not implemented yet")
    return


async def check_existing_configurations():
    """Check if reward configurations already exist"""
    from sqlalchemy import select, func
    
    async with get_db_session() as db:
        result = await db.execute(select(func.count(RewardsConfiguration.id)))
        count = result.scalar()
        
        if count > 0:
            print(f"Found {count} existing reward configurations")
            return True
        return False


async def main():
    """Main function to set up all reward configurations"""
    try:
        print("Setting up rewards configurations...")
        
        # Check if configurations already exist
        if await check_existing_configurations():
            response = input("Reward configurations already exist. Do you want to continue and add more? (y/n): ")
            if response.lower() != 'y':
                print("Skipping rewards configuration setup")
                return
        
        print("Creating quiz reward configurations...")
        await create_quiz_reward_configurations()
        
        print("Creating myths vs facts reward configurations...")
        await create_myths_facts_reward_configurations()
        
        print("Creating daily login reward configurations...")
        await create_daily_login_reward_configurations()
        
        print("Creating content interaction reward configurations...")
        await create_content_interaction_reward_configurations()
        
        print("✅ All reward configurations have been created successfully!")
        print("\nReward Structure Summary:")
        print("📝 Quiz Completion:")
        print("   - Bronze (0-59%): 10 points, 5 credits")
        print("   - Silver (60-79%): 20 points, 10 credits")
        print("   - Gold (80-94%): 35 points, 20 credits")
        print("   - Platinum (95-100%): 50 points, 30 credits")
        print("\n🧠 Myths vs Facts:")
        print("   - Bronze: 5 points, 2 credits")
        print("   - Silver: 8 points, 4 credits")
        print("   - Gold: 12 points, 6 credits")
        print("   - Platinum: 20 points, 10 credits")
        print("\n📅 Daily Login: 5 points, 3 credits")
        print("📖 Content View: 2 points, 1 credit")
        print("📤 Content Share: 5 points, 3 credits")
        
    except Exception as e:
        print(f"Error setting up reward configurations: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())