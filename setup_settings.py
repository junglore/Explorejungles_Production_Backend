#!/usr/bin/env python3
"""
Script to initialize default site settings in the database
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Override DATABASE_URL for railway run
if 'DATABASE_PUBLIC_URL' in os.environ:
    os.environ['DATABASE_URL'] = os.environ['DATABASE_PUBLIC_URL']
    # Ensure asyncpg driver
    if os.environ['DATABASE_URL'].startswith('postgresql://'):
        os.environ['DATABASE_URL'] = os.environ['DATABASE_URL'].replace('postgresql://', 'postgresql+asyncpg://', 1)

from app.db.database import get_db_session
from app.models.site_setting import SiteSetting, DEFAULT_SETTINGS
from sqlalchemy import select


async def init_settings():
    """Initialize default settings in the database"""
    
    try:
        async with get_db_session() as db:
            print("🔧 Initializing site settings...")
            
            # Check existing settings
            existing_result = await db.execute(select(SiteSetting.key))
            existing_keys = {row.key for row in existing_result.all()}
            
            created_count = 0
            updated_count = 0
            
            for setting_data in DEFAULT_SETTINGS:
                key = setting_data['key']
                
                if key not in existing_keys:
                    # Create new setting
                    setting = SiteSetting(
                        key=setting_data['key'],
                        value=setting_data['value'],
                        data_type=setting_data['data_type'],
                        category=setting_data['category'],
                        label=setting_data['label'],
                        description=setting_data['description'],
                        is_public=setting_data['is_public']
                    )
                    db.add(setting)
                    created_count += 1
                    print(f"  ✅ Created setting: {key}")
                else:
                    print(f"  ⏭️  Skipped existing setting: {key}")
            
            await db.commit()
            
            print(f"\n✅ Settings initialization complete!")
            print(f"   📝 Created {created_count} new settings")
            print(f"   🔄 Total settings available: {len(DEFAULT_SETTINGS)}")
            
            # Display categories
            categories = {}
            for setting in DEFAULT_SETTINGS:
                category = setting['category']
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
            
            print(f"\n📊 Settings by category:")
            for category, count in categories.items():
                print(f"   {category.title()}: {count} settings")
                
    except Exception as e:
        print(f"❌ Error initializing settings: {e}")
        import traceback
        traceback.print_exc()


async def show_settings():
    """Display all current settings"""
    
    try:
        async with get_db_session() as db:
            result = await db.execute(
                select(SiteSetting).order_by(SiteSetting.category, SiteSetting.key)
            )
            settings = result.scalars().all()
            
            print(f"\n📋 Current Site Settings ({len(settings)} total):")
            
            current_category = None
            for setting in settings:
                if setting.category != current_category:
                    current_category = setting.category
                    print(f"\n  📁 {current_category.upper()}:")
                
                print(f"    🔧 {setting.key}")
                print(f"       Value: {setting.value}")
                print(f"       Type: {setting.data_type}")
                print(f"       Public: {setting.is_public}")
                print(f"       Description: {setting.description}")
                print()
                
    except Exception as e:
        print(f"❌ Error displaying settings: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Manage site settings')
    parser.add_argument('--init', action='store_true', help='Initialize default settings')
    parser.add_argument('--show', action='store_true', help='Show all current settings')
    
    args = parser.parse_args()
    
    if args.init:
        asyncio.run(init_settings())
    elif args.show:
        asyncio.run(show_settings())
    else:
        print("Usage: python setup_settings.py --init|--show")
        print("  --init: Initialize default settings in database")
        print("  --show: Display all current settings")