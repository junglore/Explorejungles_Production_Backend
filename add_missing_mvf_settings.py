#!/usr/bin/env python3
"""
Add missing MVF settings to production database
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
from app.models.site_setting import SiteSetting
from sqlalchemy import text


async def add_missing_mvf_settings():
    """Add the missing MVF settings that the admin panel requires"""

    missing_settings = [
        {
            'key': 'mvf_base_points_per_card',
            'value': '5',
            'data_type': 'int',
            'category': 'mythsVsFacts',
            'label': 'Base Points per Card',
            'description': 'Base points awarded for each myth vs fact card completed',
            'is_public': False
        },
        {
            'key': 'mvf_base_credits_per_game',
            'value': '3',
            'data_type': 'int',
            'category': 'mythsVsFacts',
            'label': 'Base Credits per Game',
            'description': 'Base credits awarded for completing a myths vs facts game',
            'is_public': False
        },
        {
            'key': 'mvf_cards_per_game',
            'value': '10',
            'data_type': 'int',
            'category': 'mythsVsFacts',
            'label': 'Cards per Game',
            'description': 'Number of cards shown in each myths vs facts game',
            'is_public': False
        },
        {
            'key': 'mythsVsFacts_config',
            'value': '{"basePointsPerCard": 5, "baseCreditsPerGame": 3, "performanceTiers": {"bronze": {"multiplier": 1.0, "threshold": 50}, "silver": {"multiplier": 1.2, "threshold": 70}, "gold": {"multiplier": 1.5, "threshold": 85}, "platinum": {"multiplier": 2.0, "threshold": 95}}, "userTiers": {"bronze": {"bonusMultiplier": 1.0, "maxLevel": 10}, "silver": {"bonusMultiplier": 1.1, "maxLevel": 25}, "gold": {"bonusMultiplier": 1.3, "maxLevel": 50}, "platinum": {"bonusMultiplier": 1.5, "maxLevel": 100}}, "dailyLimits": {"maxGamesPerDay": 20, "maxPointsPerDay": 500, "maxCreditsPerDay": 200}, "gameParameters": {"cardsPerGame": 10, "timePerCard": 30, "passingScore": 60}}',
            'data_type': 'json',
            'category': 'mythsVsFacts',
            'label': 'Myths vs Facts Configuration',
            'description': 'Complete configuration for the Myths vs Facts game system',
            'is_public': False
        }
    ]

    try:
        async with get_db_session() as db:
            print("🔧 Adding missing MVF settings to production database...")

            # Check existing settings
            existing_result = await db.execute(text("SELECT key FROM site_settings WHERE key IN ('mvf_base_points_per_card', 'mvf_base_credits_per_game', 'mvf_cards_per_game', 'mythsVsFacts_config')"))
            existing_keys = {row.key for row in existing_result.all()}

            created_count = 0

            for setting_data in missing_settings:
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

            print(f"\n✅ Missing MVF settings addition complete!")
            print(f"   📝 Created {created_count} new settings")

    except Exception as e:
        print(f"❌ Error adding missing MVF settings: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_missing_mvf_settings())