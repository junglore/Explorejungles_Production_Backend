#!/usr/bin/env python3
"""
Simple Collection System Test
Tests core functionality without complex database operations
"""

import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

async def test_basic_connectivity():
    """Test basic database connectivity using project's async setup"""
    try:
        from app.db.database import engine
        
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.scalar()
        print("✅ Database connectivity working")
        return True
    except Exception as e:
        print(f"❌ Database connectivity failed: {e}")
        return False

async def test_table_existence():
    """Test that our new tables exist"""
    try:
        from app.db.database import engine
        
        tables_to_check = [
            'myth_fact_collections',
            'collection_myth_facts', 
            'user_collection_progress'
        ]
        
        async with engine.begin() as conn:
            all_exist = True
            for table in tables_to_check:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = '{table}'
                    );
                """))
                exists = result.scalar()
                if exists:
                    print(f"✅ Table '{table}' exists")
                else:
                    print(f"❌ Table '{table}' missing")
                    all_exist = False
            
            return all_exist
    except Exception as e:
        print(f"❌ Table check failed: {e}")
        return False

def test_pydantic_schemas():
    """Test that our Pydantic schemas work correctly"""
    try:
        # Import the schemas we created
        from app.schemas.collection_schemas import (
            CollectionCreate, CollectionResponse, CollectionUpdate
        )
        
        # Test valid data
        valid_data = {
            "name": "Test Collection",
            "description": "A test collection",
            "is_active": True,
            "repeatability": "daily"
        }
        
        schema = CollectionCreate(**valid_data)
        print(f"✅ Schema validation passed: {schema.name}")
        
        # Test invalid repeatability
        try:
            invalid_data = valid_data.copy()
            invalid_data["repeatability"] = "invalid_value"
            CollectionCreate(**invalid_data)
            print("❌ Schema should have rejected invalid repeatability")
            return False
        except Exception:
            print("✅ Schema correctly rejected invalid data")
        
        return True
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        return False

def test_reward_calculation():
    """Test reward tier calculation"""
    try:
        from app.services.rewards_service import RewardsService
        
        rewards_service = RewardsService()
        
        test_cases = [
            (95, "platinum"),
            (85, "gold"),
            (75, "silver"),
            (65, "bronze"),
            (45, "bronze")
        ]
        
        for score, expected_tier in test_cases:
            tier = rewards_service._calculate_myths_facts_reward_tier(score)
            if tier == expected_tier:
                print(f"✅ Score {score}% = {tier}")
            else:
                print(f"❌ Score {score}% = {tier}, expected {expected_tier}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Reward calculation test failed: {e}")
        return False

async def test_views_exist():
    """Test that our database views were created"""
    try:
        from app.db.database import engine
        
        views_to_check = [
            'collection_stats',
            'user_daily_collection_summary'
        ]
        
        async with engine.begin() as conn:
            all_exist = True
            for view in views_to_check:
                result = await conn.execute(text(f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.views 
                        WHERE table_name = '{view}'
                    );
                """))
                exists = result.scalar()
                if exists:
                    print(f"✅ View '{view}' exists")
                else:
                    print(f"❌ View '{view}' missing")
                    all_exist = False
            
            return all_exist
    except Exception as e:
        print(f"❌ View check failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 Simple Collection System Test")
    print("=" * 50)
    
    # Tests that don't require database
    schema_result = test_pydantic_schemas()
    reward_result = test_reward_calculation()
    
    # Database tests
    connectivity_result = await test_basic_connectivity()
    table_result = await test_table_existence() if connectivity_result else False
    view_result = await test_views_exist() if connectivity_result else False
    
    print("\n📋 Test Summary")
    print("=" * 50)
    print(f"Database Connectivity: {'✅ PASS' if connectivity_result else '❌ FAIL'}")
    print(f"Tables Created: {'✅ PASS' if table_result else '❌ FAIL'}")
    print(f"Views Created: {'✅ PASS' if view_result else '❌ FAIL'}")
    print(f"Schema Validation: {'✅ PASS' if schema_result else '❌ FAIL'}")
    print(f"Reward Calculation: {'✅ PASS' if reward_result else '❌ FAIL'}")
    
    total_tests = 5
    passed_tests = sum([connectivity_result, table_result, view_result, schema_result, reward_result])
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 All tests passed! Collection system is ready for Phase 3.")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review issues above.")

if __name__ == "__main__":
    asyncio.run(main())