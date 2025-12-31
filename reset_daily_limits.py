#!/usr/bin/env python3
"""
Reset Daily Currency Limits for Testing

This script resets the daily activity tracking for a user to allow testing
of the rewards system without hitting daily limits.
"""

import asyncio
from datetime import date
from sqlalchemy import select, delete
from app.db.database import get_db_session
from app.models.rewards import UserDailyActivity
from app.models.user import User

async def reset_daily_limits():
    """Reset daily limits for all users or specific user"""
    async with get_db_session() as db:
        try:
            # Option 1: Delete all daily activity records for today
            today = date.today()
            delete_stmt = delete(UserDailyActivity).where(
                UserDailyActivity.activity_date == today
            )
            result = await db.execute(delete_stmt)
            await db.commit()
            
            print(f"✅ Reset daily limits for {result.rowcount} users on {today}")
            
            # Show current user balances for verification
            users_query = select(User.id, User.username, User.credits_balance, User.total_credits_earned)
            users_result = await db.execute(users_query)
            users = users_result.fetchall()
            
            print("\n📊 Current User Balances:")
            for user in users:
                print(f"  {user.username}: Credits={user.credits_balance}, Total Earned={user.total_credits_earned}")
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Error: {e}")
            raise

async def check_admin_mvf_config():
    """Check admin MVP configuration from database"""
    async with get_db_session() as db:
        try:
            from app.models.site_setting import SiteSetting
            
            # Get all MVP-related settings
            mvf_settings_query = select(SiteSetting).where(
                SiteSetting.key.like('%mvf%')
            )
            result = await db.execute(mvf_settings_query)
            settings = result.scalars().all()
            
            print("\n🎯 Admin MVP Configuration:")
            for setting in settings:
                print(f"  {setting.key}: {setting.parsed_value} ({setting.description})")
            
            # Check categories with MVP enabled
            from app.models.category import Category
            categories_query = select(Category).where(Category.mvf_enabled == True)
            categories_result = await db.execute(categories_query)
            categories = categories_result.scalars().all()
            
            print(f"\n📁 Categories with MVP Enabled ({len(categories)}):")
            for category in categories:
                print(f"  {category.name}: {category.custom_credits} credits (Featured: {category.is_featured})")
            
            # Check myths/facts count per category
            from app.models.content import MythsFacts
            from sqlalchemy import func
            
            mvf_count_query = select(
                Category.name,
                func.count(MythsFacts.id).label('mvf_count')
            ).join(
                MythsFacts, Category.id == MythsFacts.category_id, isouter=True
            ).where(
                Category.mvf_enabled == True
            ).group_by(Category.id, Category.name)
            
            mvf_result = await db.execute(mvf_count_query)
            mvf_counts = mvf_result.fetchall()
            
            print(f"\n🃏 Myths/Facts Cards per Category:")
            for category_name, count in mvf_counts:
                print(f"  {category_name}: {count} cards")
                
        except Exception as e:
            print(f"❌ Error checking configuration: {e}")
            raise

if __name__ == "__main__":
    print("🔄 Resetting Daily Currency Limits...")
    asyncio.run(reset_daily_limits())
    
    print("\n🔍 Checking Admin MVP Configuration...")
    asyncio.run(check_admin_mvf_config())
    
    print("\n✅ All done! You can now test the rewards system.")