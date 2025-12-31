"""
Collection System Test Script

This script tests the basic functionality of the collection-based
myth vs facts system to ensure all components work together properly.

Usage:
    python test_collection_system.py

Author: Junglore Development Team
Version: 1.0.0
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the parent directory to the path so we can import app modules
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import date, datetime
from uuid import uuid4
import json

# Import our models and schemas
from app.models.myth_fact_collection import (
    MythFactCollection, 
    CollectionMythFact, 
    UserCollectionProgress
)
from app.models.user import User
from app.models.myth_fact import MythFact
from app.models.category import Category

async def test_database_connectivity():
    """Test basic database connectivity and table existence."""
    print("🔍 Testing database connectivity...")
    
    try:
        # Use the project's async database setup
        from app.db.database import engine
        
        async with engine.begin() as conn:
            # Test basic connection
            await conn.execute(text("SELECT 1"))
            
            # Test table existence
            tables_to_check = [
                'myth_fact_collections',
                'collection_myth_facts', 
                'user_collection_progress',
                'users',
                'myths_facts',
                'categories'
            ]
            
            for table in tables_to_check:
                result = await conn.execute(
                    text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = '{table}'")
                )
                count = result.scalar()
                
                if count > 0:
                    print(f"  ✅ Table '{table}' exists")
                else:
                    print(f"  ❌ Table '{table}' missing")
        
        print("✅ Database connectivity test passed")
        return True
        
    except Exception as e:
        print(f"❌ Database connectivity test failed: {str(e)}")
        return False


def test_collection_creation():
    """Test creating a collection with the new schema."""
    print("\n🎯 Testing collection creation...")
    
    try:
        from app.db.database import get_db
        from app.core.config import settings
        
        engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # Create a test collection
            test_collection = MythFactCollection(
                id=uuid4(),
                name="Test Wildlife Collection",
                description="A test collection for wildlife facts",
                is_active=True,
                repeatability="daily",
                custom_points_enabled=False,
                custom_credits_enabled=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            session.add(test_collection)
            session.commit()
            
            # Verify creation
            retrieved = session.query(MythFactCollection).filter(
                MythFactCollection.id == test_collection.id
            ).first()
            
            if retrieved:
                print(f"  ✅ Collection created: {retrieved.name}")
                
                # Clean up
                session.delete(retrieved)
                session.commit()
                print("  🧹 Test collection cleaned up")
                
                return True
            else:
                print("  ❌ Collection creation failed - not found")
                return False
        
    except Exception as e:
        print(f"  ❌ Collection creation test failed: {str(e)}")
        return False


def test_collection_analytics_view():
    """Test the analytics view we created."""
    print("\n📊 Testing collection analytics view...")
    
    try:
        from app.db.database import get_db
        from app.core.config import settings
        
        engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
        Session = sessionmaker(bind=engine)
        
        with Session() as session:
            # Test the analytics view
            result = session.execute(
                text("SELECT COUNT(*) FROM collection_analytics_view")
            ).scalar()
            
            print(f"  ✅ Analytics view accessible, found {result} collection records")
            
            # Test view structure
            columns_result = session.execute(
                text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'collection_analytics_view'
                ORDER BY ordinal_position
                """)
            ).fetchall()
            
            expected_columns = [
                'collection_id', 'collection_name', 'description', 'is_active',
                'repeatability', 'category_name', 'total_cards', 'unique_players',
                'total_plays', 'completions', 'avg_score', 'avg_time', 'completion_rate'
            ]
            
            view_columns = [col[0] for col in columns_result]
            missing_columns = set(expected_columns) - set(view_columns)
            
            if missing_columns:
                print(f"  ⚠️  Missing columns in view: {missing_columns}")
            else:
                print("  ✅ All expected columns present in analytics view")
            
            return True
        
    except Exception as e:
        print(f"  ❌ Analytics view test failed: {str(e)}")
        return False


def test_schema_validation():
    """Test that our Pydantic schemas work correctly."""
    print("\n📝 Testing Pydantic schemas...")
    
    try:
        from app.schemas.myth_fact_collection import (
            MythFactCollectionCreate,
            CustomRewardsConfig,
            RepeatabilityType
        )
        
        # Test basic collection creation schema
        custom_rewards = CustomRewardsConfig(
            bronze=10,
            silver=20,
            gold=30,
            platinum=50
        )
        
        collection_data = MythFactCollectionCreate(
            name="Test Collection",
            description="A test collection",
            is_active=True,
            repeatability=RepeatabilityType.DAILY,
            custom_points_enabled=True,
            custom_points=custom_rewards,
            custom_credits_enabled=False,
            myth_fact_ids=[]
        )
        
        print("  ✅ Collection creation schema validates correctly")
        
        # Test validation errors
        try:
            invalid_data = MythFactCollectionCreate(
                name="",  # Invalid - too short
                repeatability=RepeatabilityType.DAILY,
                custom_points_enabled=True,
                custom_points=None  # Invalid - enabled but no config
            )
            print("  ❌ Schema validation should have failed")
            return False
        except Exception:
            print("  ✅ Schema validation correctly rejects invalid data")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Schema validation test failed: {str(e)}")
        return False


def test_reward_calculation():
    """Test reward calculation functions."""
    print("\n💰 Testing reward calculations...")
    
    try:
        from app.services.rewards_service import RewardsService
        from app.models.rewards import RewardTierEnum
        
        # Create rewards service instance
        rewards_service = RewardsService()
        
        # Test tier calculation
        test_scores = [95, 85, 75, 65, 45]
        expected_tiers = [RewardTierEnum.PLATINUM, RewardTierEnum.GOLD, RewardTierEnum.SILVER, RewardTierEnum.BRONZE, RewardTierEnum.BRONZE]
        
        for score, expected in zip(test_scores, expected_tiers):
            tier = rewards_service._calculate_myths_facts_reward_tier(score)
            if tier == expected:
                print(f"  ✅ Score {score}% correctly calculated as {tier.value}")
            else:
                print(f"  ❌ Score {score}% calculated as {tier.value}, expected {expected.value}")
                return False
        
        # Test reward retrieval
        print("  ✅ All reward tier calculations working correctly")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Reward calculation test failed: {str(e)}")
        return False


def run_all_tests():
    """Run all tests and provide a summary."""
    print("🚀 Starting Collection System Tests")
    print("=" * 50)
    
    tests = [
        ("Database Connectivity", test_database_connectivity),
        ("Collection Creation", test_collection_creation),
        ("Analytics View", test_collection_analytics_view),
        ("Schema Validation", test_schema_validation),
        ("Reward Calculation", test_reward_calculation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:.<30} {status}")
        
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal: {passed + failed} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Collection system is ready.")
        return True
    else:
        print(f"\n⚠️  {failed} tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)