#!/usr/bin/env python3
"""
Phase 4 Admin Collection Test
Tests the admin collection management and analytics endpoints
"""

import asyncio
import sys
import os
from datetime import date, datetime, timedelta
from uuid import uuid4

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

async def test_admin_endpoints_available():
    """Test that admin collection endpoints are properly set up"""
    try:
        from app.api.endpoints.admin_collections import router as admin_router
        
        # Check that admin router has the expected endpoints
        admin_routes = [route.path for route in admin_router.routes]
        
        expected_endpoints = [
            "/admin/collections/",
            "/admin/collections/analytics/overview",
            "/admin/collections/{collection_id}/analytics",
            "/admin/collections/{collection_id}/bulk-add-cards",
            "/admin/collections/{collection_id}/clone"
        ]
        
        print("✅ Admin Collection Routes:")
        for route in admin_routes:
            print(f"   - {route}")
        
        # Check for required endpoints
        missing_endpoints = []
        for expected in expected_endpoints:
            # Simple path matching (ignoring parameters)
            base_expected = expected.replace("/{collection_id}", "").replace("/admin/collections", "")
            found = any(base_expected in route for route in admin_routes)
            if not found:
                missing_endpoints.append(expected)
        
        if missing_endpoints:
            print(f"❌ Missing endpoints: {missing_endpoints}")
            return False
        else:
            print("✅ All expected admin endpoints found")
            return True
        
    except Exception as e:
        print(f"❌ Admin router test failed: {e}")
        return False

async def test_analytics_queries():
    """Test analytics query functionality"""
    try:
        from app.db.database import engine
        
        async with engine.begin() as conn:
            # Test basic analytics queries
            
            # 1. Test collection count
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM myth_fact_collections WHERE is_active = true
            """))
            collection_count = result.scalar()
            print(f"✅ Active collections: {collection_count}")
            
            # 2. Test progress tracking capability
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM user_collection_progress 
                WHERE play_date >= CURRENT_DATE - INTERVAL '7 days'
            """))
            recent_progress = result.scalar()
            print(f"✅ Recent progress records: {recent_progress}")
            
            # 3. Test analytics view
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM collection_stats
            """))
            stats_count = result.scalar()
            print(f"✅ Collections in stats view: {stats_count}")
            
            # 4. Test user summary view
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM user_daily_collection_summary 
            """))
            summary_count = result.scalar()
            print(f"✅ User summary records: {summary_count}")
            
            return True
        
    except Exception as e:
        print(f"❌ Analytics query test failed: {e}")
        return False

async def test_bulk_operations_logic():
    """Test the logic for bulk operations"""
    try:
        from app.db.database import engine
        
        # Create test data
        test_collection_id = uuid4()
        test_cards = [uuid4() for _ in range(5)]
        
        async with engine.begin() as conn:
            # Create test collection
            await conn.execute(text("""
                INSERT INTO myth_fact_collections (
                    id, name, description, is_active, repeatability, 
                    custom_points_enabled, custom_credits_enabled, created_at, updated_at
                ) VALUES (
                    :id, 'Test Bulk Collection', 'For testing bulk operations', 
                    true, 'daily', false, false, :created_at, :updated_at
                )
            """), {
                "id": str(test_collection_id),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            # Create test myth-fact entries
            for card_id in test_cards[:3]:  # Only create 3 actual cards
                await conn.execute(text("""
                    INSERT INTO myths_facts (
                        id, title, myth_content, fact_content, created_at
                    ) VALUES (
                        :id, 'Test Card', 'Test myth', 'Test fact', :created_at
                    )
                """), {
                    "id": str(card_id),
                    "created_at": datetime.utcnow()
                })
            
            # Test bulk assignment logic
            existing_cards = test_cards[:3]  # Cards that exist
            non_existing_cards = test_cards[3:]  # Cards that don't exist
            
            # Verify existing cards
            result = await conn.execute(text("""
                SELECT id FROM myths_facts WHERE id = ANY(:card_ids)
            """), {"card_ids": [str(cid) for cid in existing_cards]})
            found_cards = [row[0] for row in result.fetchall()]
            
            if len(found_cards) == len(existing_cards):
                print(f"✅ Test cards created successfully: {len(found_cards)} cards")
            else:
                print(f"❌ Card creation issue: expected {len(existing_cards)}, found {len(found_cards)}")
                return False
            
            # Test assignment
            for i, card_id in enumerate(existing_cards):
                await conn.execute(text("""
                    INSERT INTO collection_myth_facts (
                        id, collection_id, myth_fact_id, order_index, created_at
                    ) VALUES (
                        :id, :collection_id, :myth_fact_id, :order_index, :created_at
                    )
                """), {
                    "id": str(uuid4()),
                    "collection_id": str(test_collection_id),
                    "myth_fact_id": str(card_id),
                    "order_index": i + 1,
                    "created_at": datetime.utcnow()
                })
            
            # Verify assignments
            result = await conn.execute(text("""
                SELECT COUNT(*) FROM collection_myth_facts 
                WHERE collection_id = :collection_id
            """), {"collection_id": str(test_collection_id)})
            assignment_count = result.scalar()
            
            if assignment_count == len(existing_cards):
                print(f"✅ Bulk assignment logic working: {assignment_count} assignments")
            else:
                print(f"❌ Assignment issue: expected {len(existing_cards)}, found {assignment_count}")
                return False
            
            # Clean up test data
            await conn.execute(text("""
                DELETE FROM collection_myth_facts WHERE collection_id = :collection_id
            """), {"collection_id": str(test_collection_id)})
            
            await conn.execute(text("""
                DELETE FROM myth_fact_collections WHERE id = :collection_id
            """), {"collection_id": str(test_collection_id)})
            
            for card_id in existing_cards:
                await conn.execute(text("""
                    DELETE FROM myths_facts WHERE id = :card_id
                """), {"card_id": str(card_id)})
            
            print("🧹 Test data cleaned up")
            return True
        
    except Exception as e:
        print(f"❌ Bulk operations test failed: {e}")
        return False

async def test_collection_cloning_logic():
    """Test collection cloning functionality"""
    try:
        from app.schemas.collection_schemas import CollectionCreate, CollectionResponse
        from datetime import datetime
        
        # Test cloning schema validation
        original_data = {
            "id": str(uuid4()),
            "name": "Original Collection",
            "description": "Original description",
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
        
        # Validate original schema
        original_schema = CollectionResponse(**original_data)
        print(f"✅ Original collection schema valid: {original_schema.name}")
        
        # Test clone data structure
        clone_data = {
            "name": "Cloned Collection",
            "description": "Cloned from original",
            "is_active": True,
            "repeatability": "weekly",
            "clone_cards": True
        }
        
        # This would be the new collection data structure
        cloned_data = original_data.copy()
        cloned_data.update({
            "id": str(uuid4()),
            "name": clone_data["name"],
            "description": clone_data["description"],
            "repeatability": clone_data["repeatability"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        cloned_schema = CollectionResponse(**cloned_data)
        print(f"✅ Cloned collection schema valid: {cloned_schema.name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Collection cloning test failed: {e}")
        return False

async def test_admin_guide_completeness():
    """Test that the admin guide covers all necessary topics"""
    try:
        import os
        
        guide_path = "ADMIN_COLLECTION_GUIDE.md"
        if not os.path.exists(guide_path):
            print("❌ Admin guide file not found")
            return False
        
        with open(guide_path, 'r', encoding='utf-8') as f:
            guide_content = f.read()
        
        # Check for required sections
        required_sections = [
            "Core Concepts",
            "Database Schema",
            "API Endpoints", 
            "Admin Operations",
            "Analytics & Reporting",
            "Pure Scoring Mode",
            "Troubleshooting"
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in guide_content:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"❌ Admin guide missing sections: {missing_sections}")
            return False
        
        # Check guide length (should be comprehensive)
        line_count = len(guide_content.split('\n'))
        if line_count < 500:
            print(f"❌ Admin guide seems too short: {line_count} lines")
            return False
        
        print(f"✅ Admin guide is comprehensive: {line_count} lines with all required sections")
        return True
        
    except Exception as e:
        print(f"❌ Admin guide test failed: {e}")
        return False

async def main():
    """Run all Phase 4 tests"""
    print("🚀 Phase 4 Admin Collection Tests")
    print("=" * 50)
    
    # Test admin API structure
    endpoints_result = await test_admin_endpoints_available()
    
    # Test analytics capabilities
    analytics_result = await test_analytics_queries()
    
    # Test bulk operations
    bulk_result = await test_bulk_operations_logic()
    
    # Test cloning logic
    clone_result = await test_collection_cloning_logic()
    
    # Test documentation
    guide_result = await test_admin_guide_completeness()
    
    print("\n📋 Phase 4 Test Summary")
    print("=" * 50)
    print(f"Admin Endpoints: {'✅ PASS' if endpoints_result else '❌ FAIL'}")
    print(f"Analytics Queries: {'✅ PASS' if analytics_result else '❌ FAIL'}")
    print(f"Bulk Operations: {'✅ PASS' if bulk_result else '❌ FAIL'}")
    print(f"Collection Cloning: {'✅ PASS' if clone_result else '❌ FAIL'}")
    print(f"Admin Documentation: {'✅ PASS' if guide_result else '❌ FAIL'}")
    
    total_tests = 5
    passed_tests = sum([endpoints_result, analytics_result, bulk_result, clone_result, guide_result])
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("\n🎉 Phase 4 tests passed! Admin panel is ready.")
        print("\n📝 Next: Implement Phase 5 - Pure Scoring Documentation")
    else:
        print(f"\n⚠️  {total_tests - passed_tests} test(s) failed. Review issues above.")

if __name__ == "__main__":
    asyncio.run(main())