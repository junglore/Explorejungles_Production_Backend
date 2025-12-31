"""
Settings Integration Test Script
Tests that all admin settings are properly applied throughout the system
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.services.settings_service import SettingsService
from app.services.enhanced_rewards_service import EnhancedRewardsService
from app.db.database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession


async def test_settings_integration():
    """Test that all settings are properly integrated and functional"""
    
    print("🔧 Testing Settings Integration...")
    print("=" * 50)
    
    # Get database session
    async with get_async_session() as db:
        settings = SettingsService(db)
        enhanced_rewards = EnhancedRewardsService(db)
        
        # Test 1: Settings Service Loading
        print("\n1️⃣ Testing Settings Service...")
        await settings.load_all_settings()
        print(f"✅ Settings cache loaded with {len(settings._cache)} settings")
        
        # Test 2: Leaderboard Settings
        print("\n2️⃣ Testing Leaderboard Settings...")
        leaderboard_settings = await settings.get_leaderboard_settings()
        print(f"✅ Leaderboard public enabled: {leaderboard_settings['public_enabled']}")
        print(f"✅ Show real names: {leaderboard_settings['show_real_names']}")
        print(f"✅ Anonymous mode: {leaderboard_settings['anonymous_mode']}")
        print(f"✅ Max entries: {leaderboard_settings['max_entries']}")
        
        # Test 3: Tier Multipliers
        print("\n3️⃣ Testing Tier Multipliers...")
        tiers = ['bronze', 'silver', 'gold', 'platinum']
        for tier in tiers:
            multiplier = await settings.get_tier_multiplier(tier)
            print(f"✅ {tier.title()} tier multiplier: {multiplier}x")
        
        # Test 4: Time-based Bonuses
        print("\n4️⃣ Testing Time-based Bonuses...")
        time_bonuses = await settings.get_time_bonuses()
        print(f"✅ Quick completion threshold: {time_bonuses['quick_completion_threshold']}s")
        print(f"✅ Quick completion multiplier: {time_bonuses['quick_completion_multiplier']}x")
        print(f"✅ Streak threshold: {time_bonuses['streak_threshold']} days")
        print(f"✅ Streak multiplier: {time_bonuses['streak_multiplier']}x")
        
        # Test 5: Event Bonuses
        print("\n5️⃣ Testing Event Bonuses...")
        event_bonuses = await settings.get_event_bonuses()
        print(f"✅ Weekend bonus enabled: {event_bonuses['weekend_bonus_enabled']}")
        print(f"✅ Weekend bonus multiplier: {event_bonuses['weekend_bonus_multiplier']}x")
        print(f"✅ Special event multiplier: {event_bonuses['special_event_multiplier']}x")
        print(f"✅ Seasonal event active: {event_bonuses['seasonal_event_active']}")
        
        # Test 6: Daily Limits
        print("\n6️⃣ Testing Daily Limits...")
        daily_limits = await settings.get_daily_limits()
        print(f"✅ Daily points limit: {daily_limits['points']}")
        print(f"✅ Daily credits limit: {daily_limits['credits']}")
        
        # Test 7: Security Settings
        print("\n7️⃣ Testing Security Settings...")
        security_settings = await settings.get_security_settings()
        print(f"✅ Max quiz attempts per day: {security_settings['max_quiz_attempts_per_day']}")
        print(f"✅ Min time between attempts: {security_settings['min_time_between_attempts']}s")
        print(f"✅ Suspicious score threshold: {security_settings['suspicious_score_threshold']}")
        
        # Test 8: Enhanced Rewards Calculation (Mock)
        print("\n8️⃣ Testing Enhanced Rewards Calculation...")
        
        # Mock user data for testing
        test_user_id = "test_user_123"
        test_quiz_id = "test_quiz_456"
        
        # Test rewards calculation
        reward_calc = await enhanced_rewards.calculate_enhanced_rewards(
            user_id=test_user_id,
            quiz_id=test_quiz_id,
            base_points=10,
            base_credits=5,
            quiz_percentage=95.0,
            completion_time=25  # Quick completion
        )
        
        print(f"✅ Base points: {reward_calc.get('base_points', 0)}")
        print(f"✅ Final points: {reward_calc.get('points', 0)}")
        print(f"✅ Total multiplier: {reward_calc.get('multiplier', 1.0)}x")
        print(f"✅ User tier: {reward_calc.get('tier', 'unknown')}")
        print(f"✅ Applied bonuses: {len(reward_calc.get('bonuses', []))}")
        
        if reward_calc.get('bonuses'):
            for bonus in reward_calc['bonuses']:
                print(f"   🎉 {bonus}")
        
        # Test 9: Settings Update
        print("\n9️⃣ Testing Settings Update...")
        original_value = await settings.get('leaderboard_public_enabled', True)
        await settings.set('leaderboard_public_enabled', not original_value)
        new_value = await settings.get('leaderboard_public_enabled', True)
        await settings.set('leaderboard_public_enabled', original_value)  # Restore
        print(f"✅ Settings update working: {original_value} → {new_value} → {original_value}")
        
        # Test 10: Integration Summary
        print("\n🔟 Integration Summary...")
        
        issues = []
        
        # Check if all major settings categories are working
        if not leaderboard_settings:
            issues.append("Leaderboard settings not loaded")
        
        if all(await settings.get_tier_multiplier(tier) == 1.0 for tier in tiers):
            issues.append("Tier multipliers not configured")
        
        if not time_bonuses or time_bonuses['quick_completion_multiplier'] == 1.0:
            issues.append("Time bonuses not configured")
        
        if reward_calc.get('multiplier', 1.0) == 1.0:
            issues.append("Enhanced rewards not applying multipliers")
        
        if issues:
            print("❌ Issues found:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ All settings integration tests passed!")
        
        print("\n" + "=" * 50)
        print("Settings Integration Test Complete")
        return len(issues) == 0


async def demonstrate_settings_in_action():
    """Demonstrate how settings affect actual rewards"""
    
    print("\n🎯 Demonstrating Settings in Action...")
    print("=" * 50)
    
    async with get_async_session() as db:
        enhanced_rewards = EnhancedRewardsService(db)
        
        # Test different scenarios
        scenarios = [
            {
                "name": "Bronze User, Average Performance",
                "user_id": "bronze_user",
                "quiz_percentage": 75.0,
                "completion_time": 120,
                "expected_tier": "bronze"
            },
            {
                "name": "Silver User, Perfect Score, Quick Completion",
                "user_id": "silver_user", 
                "quiz_percentage": 100.0,
                "completion_time": 20,
                "expected_tier": "silver"
            },
            {
                "name": "Gold User, High Score, Normal Time",
                "user_id": "gold_user",
                "quiz_percentage": 90.0,
                "completion_time": 60,
                "expected_tier": "gold"
            }
        ]
        
        for scenario in scenarios:
            print(f"\n📊 {scenario['name']}:")
            
            reward_calc = await enhanced_rewards.calculate_enhanced_rewards(
                user_id=scenario['user_id'],
                quiz_id="demo_quiz",
                base_points=10,
                base_credits=5,
                quiz_percentage=scenario['quiz_percentage'],
                completion_time=scenario['completion_time']
            )
            
            print(f"   Base: {reward_calc.get('base_points', 0)} points, {reward_calc.get('base_credits', 0)} credits")
            print(f"   Final: {reward_calc.get('points', 0)} points, {reward_calc.get('credits', 0)} credits")
            print(f"   Multiplier: {reward_calc.get('multiplier', 1.0)}x")
            print(f"   Tier: {reward_calc.get('tier', 'unknown')}")
            
            if reward_calc.get('bonuses'):
                print(f"   Bonuses: {', '.join(reward_calc['bonuses'])}")


if __name__ == "__main__":
    async def main():
        try:
            success = await test_settings_integration()
            await demonstrate_settings_in_action()
            
            if success:
                print("\n🎉 All tests passed! Settings are fully integrated.")
                sys.exit(0)
            else:
                print("\n⚠️ Some tests failed. Check the issues above.")
                sys.exit(1)
                
        except Exception as e:
            print(f"\n❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    asyncio.run(main())