#!/usr/bin/env python3
"""
Phase 3 Collection API Test
Tests the collection management and integration endpoints
"""

import asyncio
import sys
import os
from datetime import date
from uuid import uuid4

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

async def test_collection_endpoints_available():
    """Test that our collection API endpoints are properly set up"""
    try:
        from app.api.endpoints.collection_management_working import router as collection_router
        from app.api.endpoints.myths_facts import router as myths_facts_router
        
        # Check that routers have the expected endpoints
        collection_routes = [route.path for route in collection_router.routes]
        myths_facts_routes = [route.path for route in myths_facts_router.routes]
        
        print("✅ Collection Management Routes:")
        for route in collection_routes:
            print(f"   - {route}")
        
        print("✅ Myths & Facts Routes (last 3):")
        for route in myths_facts_routes[-3:]:
            print(f"   - {route}")
        
        # Check for our new collection completion endpoint
        if "/collection/complete" in [route.path for route in myths_facts_router.routes]:
            print("✅ Collection completion endpoint found")
        else:
            print("❌ Collection completion endpoint missing")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Router test failed: {e}")
        return False

async def test_collection_data_structure():
    """Test that we can create a sample collection in the database"""
    try:
        from app.db.database import engine
        from app.models.myth_fact_collection import MythFactCollection
        from datetime import datetime
        
        # Create a test collection
        test_collection_id = uuid4()
        
        async with engine.begin() as conn:
            # Insert test collection
            await conn.execute(text("""
                INSERT INTO myth_fact_collections (
                    id, name, description, is_active, repeatability, 
                    custom_points_enabled, custom_credits_enabled, created_at, updated_at
                ) VALUES (
                    :id, :name, :description, :is_active, :repeatability,
                    :custom_points_enabled, :custom_credits_enabled, :created_at, :updated_at
                )
            """), {
                "id": str(test_collection_id),
                "name": "Test Wildlife Collection",
                "description": "A test collection for Phase 3",
                "is_active": True,
                "repeatability": "daily",
                "custom_points_enabled": False,
                "custom_credits_enabled": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            # Verify it was created
            result = await conn.execute(text("""
                SELECT name, repeatability FROM myth_fact_collections WHERE id = :id
            """), {"id": str(test_collection_id)})
            
            row = result.fetchone()
            if row:
                print(f"✅ Test collection created: {row[0]} ({row[1]})")
                
                # Clean up
                await conn.execute(text("""
                    DELETE FROM myth_fact_collections WHERE id = :id
                """), {"id": str(test_collection_id)})
                print("🧹 Test collection cleaned up")
                
                return True
            else:
                print("❌ Test collection not found after creation")
                return False
        
    except Exception as e:
        print(f"❌ Collection data test failed: {e}")
        return False

async def test_repeatability_logic():
    """Test the daily repeatability logic"""
    try:
        from app.api.endpoints.collection_management_working import _can_user_play_collection
        from app.db.database import engine
        
        test_user_id = uuid4()
        test_collection_id = uuid4()
        today = date.today()
        
        async with engine.begin() as conn:
            # Test unlimited repeatability
            can_play_unlimited = await _can_user_play_collection(
                conn, test_user_id, test_collection_id, today, "unlimited"
            )
            
            if can_play_unlimited:
                print("✅ Unlimited repeatability allows play")
            else:
                print("❌ Unlimited repeatability should allow play")
                return False
            
            # Test daily repeatability without existing progress
            can_play_daily = await _can_user_play_collection(
                conn, test_user_id, test_collection_id, today, "daily"
            )
            
            if can_play_daily:
                print("✅ Daily repeatability allows first play")
            else:
                print("❌ Daily repeatability should allow first play")
                return False
            
            return True
        
    except Exception as e:
        print(f"❌ Repeatability logic test failed: {e}")
        return False

async def test_schema_integration():
    """Test that the collection schemas work with the endpoints"""
    try:
        from app.schemas.collection_schemas import CollectionResponse
        from datetime import datetime
        
        # Test schema with sample data
        sample_data = {
            "id": str(uuid4()),
            "name": "Wildlife Conservation Facts",
            "description": "Learn about wildlife conservation",
            "is_active": True,
            "cards_count": 10,
            "repeatability": "daily",
            "category_id": None,
            "custom_points_enabled": False,
            "custom_credits_enabled": False,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "created_by": None
        }
        
        # This should work without errors
        schema = CollectionResponse(**sample_data)
        print(f"✅ Collection schema validation: {schema.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema integration test failed: {e}")
        return False

async def main():
    """Run all Phase 3 tests"""
    print("🚀 Phase 3 Collection API Tests")
    print("=" * 50)
    
    # Test API structure
    endpoints_result = await test_collection_endpoints_available()
    
    # Test database operations
    data_result = await test_collection_data_structure()
    
    # Test business logic
    repeatability_result = await test_repeatability_logic()
    
    # Test schema integration
    schema_result = await test_schema_integration()
    
    print("\n📋 Phase 3 Test Summary")
    print("=" * 50)
    print(f"API Endpoints Setup: {'✅ PASS' if endpoints_result else '❌ FAIL'}")
    print(f"Database Operations: {'✅ PASS' if data_result else '❌ FAIL'}")
    print(f"Repeatability Logic: {'✅ PASS' if repeatability_result else '❌ FAIL'}")
    print(f"Schema Integration: {'✅ PASS' if schema_result else '❌ FAIL'}")
    
    total_tests = 4
    passed_tests = sum([endpoints_result, data_result, repeatability_result, schema_result])
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 Phase 3 tests passed! Collection API is ready.")
        print("\n📝 Next: Test the API with a frontend integration")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review issues above.")

if __name__ == "__main__":
    asyncio.run(main())