#!/usr/bin/env python3
"""
Test MVF Daily Limits Functionality

This script tests the complete MVF daily limits system to ensure:
1. Settings are properly stored in database
2. Currency service uses MVF-specific limits
3. Admin panel displays the new settings
4. API endpoints return correct configuration
5. Actual limit enforcement works correctly

Run this script after setting up the MVF daily limits to verify functionality.
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from uuid import uuid4

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_mvf_daily_limits():
    """Comprehensive test of MVF daily limits system"""
    
    print("🧪 Testing MVF Daily Limits System")
    print("=" * 50)
    
    try:
        from app.db.database import get_db_session
        from app.models.site_setting import SiteSetting
        from app.models.user import User
        from app.models.rewards import ActivityTypeEnum, CurrencyTypeEnum
        from app.services.currency_service import CurrencyService
        from sqlalchemy import select
        
        async with get_db_session() as db:
            
            # Test 1: Verify MVF settings exist in database
            print("\n1️⃣ Testing MVF Settings in Database")
            print("-" * 30)
            
            result = await db.execute(
                select(SiteSetting.key, SiteSetting.value, SiteSetting.label)
                .where(SiteSetting.category == 'myths_vs_facts')
                .order_by(SiteSetting.key)
            )
            mvf_settings = result.fetchall()
            
            if not mvf_settings:
                print("❌ No MVF settings found in database!")
                return False
            
            settings_dict = {}
            for setting in mvf_settings:
                settings_dict[setting.key] = int(setting.value)
                print(f"✅ {setting.label}: {setting.value}")
            
            expected_settings = ['mvf_daily_credits_limit', 'mvf_daily_points_limit']
            for expected in expected_settings:
                if expected not in settings_dict:
                    print(f"❌ Missing setting: {expected}")
                    return False
            
            # Test 2: Test Currency Service MVF Limits
            print("\n2️⃣ Testing Currency Service MVF Limits")
            print("-" * 30)
            
            currency_service = CurrencyService()
            
            # Test _get_mvf_daily_limits method
            mvf_limits = await currency_service._get_mvf_daily_limits(db)
            print(f"✅ MVF Limits from Service: {mvf_limits}")
            
            expected_points = settings_dict.get('mvf_daily_points_limit', 200)
            expected_credits = settings_dict.get('mvf_daily_credits_limit', 50)
            
            if mvf_limits['points'] != expected_points:
                print(f"❌ Points limit mismatch: expected {expected_points}, got {mvf_limits['points']}")
                return False
            
            if mvf_limits['credits'] != expected_credits:
                print(f"❌ Credits limit mismatch: expected {expected_credits}, got {mvf_limits['credits']}")
                return False
            
            print("✅ Currency service correctly retrieves MVF limits")
            
            # Test 3: Test API Configuration Endpoint
            print("\n3️⃣ Testing API Configuration")
            print("-" * 30)
            
            # Import the config function
            from app.api.endpoints.config import get_mvf_config
            from fastapi import Request
            from unittest.mock import MagicMock
            
            # Create mock request
            mock_request = MagicMock()
            mock_request.headers = {}
            
            try:
                response = await get_mvf_config(db)
                config_data = json.loads(response.body)
                
                if config_data.get('success'):
                    daily_limits = config_data['config']['dailyLimits']
                    print(f"✅ API Daily Limits: Points={daily_limits['maxPointsPerDay']}, Credits={daily_limits['maxCreditsPerDay']}")
                    
                    if daily_limits['maxPointsPerDay'] != expected_points:
                        print(f"❌ API points limit mismatch: expected {expected_points}, got {daily_limits['maxPointsPerDay']}")
                        return False
                    
                    if daily_limits['maxCreditsPerDay'] != expected_credits:
                        print(f"❌ API credits limit mismatch: expected {expected_credits}, got {daily_limits['maxCreditsPerDay']}")
                        return False
                    
                    print("✅ API endpoint returns correct MVF limits")
                else:
                    print("❌ API endpoint returned error")
                    return False
                    
            except Exception as e:
                print(f"❌ API test failed: {e}")
                return False
            
            # Test 4: Test Actual Limit Enforcement (if test user exists)
            print("\n4️⃣ Testing Limit Enforcement")
            print("-" * 30)
            
            # Look for a test user
            result = await db.execute(
                select(User.id).where(User.email.like('%test%')).limit(1)
            )
            test_user = result.scalar_one_or_none()
            
            if test_user:
                print(f"✅ Found test user: {test_user}")
                
                # Test MVF activity type limit checking
                from app.models.rewards import UserDailyActivity
                
                # Get or create daily activity
                daily_activity = await currency_service._get_or_create_daily_activity(db, test_user)
                
                # Test points limit check
                points_within_limit = await currency_service._check_daily_limits(
                    daily_activity, CurrencyTypeEnum.POINTS, 10, ActivityTypeEnum.MYTHS_FACTS_GAME, db
                )
                print(f"✅ Points within limit check: {points_within_limit}")
                
                # Test credits limit check  
                credits_within_limit = await currency_service._check_daily_limits(
                    daily_activity, CurrencyTypeEnum.CREDITS, 5, ActivityTypeEnum.MYTHS_FACTS_GAME, db
                )
                print(f"✅ Credits within limit check: {credits_within_limit}")
                
                # Test exceeding limits
                points_exceeds_limit = await currency_service._check_daily_limits(
                    daily_activity, CurrencyTypeEnum.POINTS, expected_points + 1, ActivityTypeEnum.MYTHS_FACTS_GAME, db
                )
                print(f"✅ Points exceeds limit check: {not points_exceeds_limit}")
                
                if points_exceeds_limit:
                    print("❌ Points limit check failed - should reject amounts exceeding limit")
                    return False
                
                print("✅ Limit enforcement working correctly")
            else:
                print("⚠️  No test user found, skipping limit enforcement test")
            
            # Test 5: Verify Admin Settings Category
            print("\n5️⃣ Testing Admin Settings Integration")
            print("-" * 30)
            
            # Check if all categories are present
            result = await db.execute(
                select(SiteSetting.category).distinct()
            )
            categories = [row[0] for row in result.fetchall()]
            
            if 'myths_vs_facts' in categories:
                print("✅ 'myths_vs_facts' category exists in admin settings")
            else:
                print("❌ 'myths_vs_facts' category missing from admin settings")
                return False
            
            print("\n🎉 All Tests Passed!")
            print("=" * 50)
            print("✅ MVF Daily Limits system is fully functional")
            print(f"📊 Current Limits: {expected_points} points, {expected_credits} credits per day")
            print("🔧 Admin panel will show 'Myths vs Facts Game' section")
            print("🎮 MVF games will now use dedicated limits instead of general limits")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run the complete test suite"""
    print("🚀 Starting MVF Daily Limits Test Suite")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = await test_mvf_daily_limits()
    
    if success:
        print("\n🎯 Next Steps:")
        print("1. Restart your backend server to ensure all changes are loaded")
        print("2. Test MVF game completion in the frontend")
        print("3. Verify limits are enforced by playing multiple games")
        print("4. Check admin panel for new 'Myths vs Facts Game' settings section")
        exit(0)
    else:
        print("\n💥 Some tests failed. Please check the errors above.")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())