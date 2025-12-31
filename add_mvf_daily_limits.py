#!/usr/bin/env python3
"""
Add Myths vs Facts Daily Limits to Site Settings

This script adds the new MVF-specific daily limits to the site_settings table
if they don't already exist. This ensures MVF has its own dedicated limits
separate from general quiz/game limits.
"""

import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.models.site_setting import SiteSetting


async def add_mvf_settings():
    """Add MVF daily limit settings to database"""
    
    # Define the new MVF settings
    mvf_settings = [
        {
            'key': 'mvf_daily_points_limit',
            'value': '200',
            'data_type': 'int',
            'category': 'myths_vs_facts',
            'label': 'MVF Daily Points Limit',
            'description': 'Maximum points a user can earn per day from Myths vs Facts games',
            'is_public': False
        },
        {
            'key': 'mvf_daily_credits_limit',
            'value': '50',
            'data_type': 'int',
            'category': 'myths_vs_facts',
            'label': 'MVF Daily Credits Limit',
            'description': 'Maximum credits a user can earn per day from Myths vs Facts games',
            'is_public': False
        },
        {
            'key': 'mvf_max_games_per_day',
            'value': '10',
            'data_type': 'int',
            'category': 'myths_vs_facts',
            'label': 'MVF Max Games Per Day',
            'description': 'Maximum number of Myths vs Facts games a user can play per day',
            'is_public': False
        }
    ]
    
    try:
        async with get_db_session() as db:
            added_count = 0
            
            for setting_data in mvf_settings:
                # Check if setting already exists
                result = await db.execute(
                    text("SELECT COUNT(*) FROM site_settings WHERE key = :key"),
                    {"key": setting_data['key']}
                )
                exists = result.scalar() > 0
                
                if not exists:
                    # Add the new setting
                    setting = SiteSetting(**setting_data)
                    db.add(setting)
                    added_count += 1
                    print(f"✅ Added setting: {setting_data['key']} = {setting_data['value']}")
                else:
                    print(f"⚠️  Setting already exists: {setting_data['key']}")
            
            if added_count > 0:
                await db.commit()
                print(f"\n🎉 Successfully added {added_count} new MVF settings!")
            else:
                print("\n🔍 All MVF settings already exist. No changes needed.")
                
            # Show current MVF settings
            print("\n📋 Current MVF Settings:")
            result = await db.execute(
                text("SELECT key, value, label FROM site_settings WHERE category = 'myths_vs_facts' ORDER BY key")
            )
            mvf_current = result.fetchall()
            
            if mvf_current:
                for setting in mvf_current:
                    print(f"   • {setting.label}: {setting.value}")
            else:
                print("   No MVF settings found in database.")
                
    except Exception as e:
        print(f"❌ Error adding MVF settings: {e}")
        return False
    
    return True


async def verify_mvf_integration():
    """Verify that MVF system will use the new limits"""
    
    print("\n🔍 Verifying MVF Integration...")
    
    try:
        async with get_db_session() as db:
            # Check if the required settings exist
            result = await db.execute(
                text("""
                SELECT key, value 
                FROM site_settings 
                WHERE key IN ('mvf_daily_points_limit', 'mvf_daily_credits_limit', 'mvf_max_games_per_day')
                ORDER BY key
                """)
            )
            settings = result.fetchall()
            
            if len(settings) == 3:
                print("✅ All required MVF daily limit settings are present")
                print("✅ MVF system will now use dedicated limits instead of general limits")
                print("\n📊 MVF Daily Limits Configuration:")
                for setting in settings:
                    label = {
                        'mvf_daily_credits_limit': 'Daily Credits Limit',
                        'mvf_daily_points_limit': 'Daily Points Limit', 
                        'mvf_max_games_per_day': 'Max Games Per Day'
                    }.get(setting.key, setting.key)
                    print(f"   • {label}: {setting.value}")
                    
                print("\n🎯 Next Steps:")
                print("   1. Restart the backend server to load new settings")
                print("   2. Test MVF game completion to verify limits are enforced")
                print("   3. Check admin panel for new 'Myths vs Facts Game' section")
                
                return True
            else:
                print(f"❌ Missing settings. Found {len(settings)}/3 required settings")
                return False
                
    except Exception as e:
        print(f"❌ Error verifying integration: {e}")
        return False


async def main():
    """Main execution function"""
    
    print("🚀 Adding Myths vs Facts Daily Limits to Site Settings")
    print("=" * 60)
    
    # Add the settings
    success = await add_mvf_settings()
    
    if success:
        # Verify integration
        await verify_mvf_integration()
        print("\n🎉 MVF Daily Limits Setup Complete!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    print("🔧 Setting up MVF Daily Limits...")
    asyncio.run(main())