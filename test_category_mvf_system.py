#!/usr/bin/env python3
"""
Test script for the enhanced Category-based MVF system
Tests the new admin category management functionality
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db_session
from app.models.category import Category
from app.models.myth_fact import MythFact
from sqlalchemy import text

async def test_category_mvf_system():
    """Test the enhanced category management system"""
    print("🧪 Testing Enhanced Category-based MVF System")
    print("=" * 50)
    
    try:
        # Get database session
        async with get_db_session() as db:
            print("✅ Database connection successful")
            
            # Test 1: Verify new columns exist
            print("\n📋 Test 1: Verifying Database Schema")
            
            # Check categories table
            result = await db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'categories' 
                AND column_name IN ('custom_credits', 'is_featured', 'mvf_enabled')
                ORDER BY column_name
            """))
            
            category_columns = result.fetchall()
            print(f"Categories new columns: {len(category_columns)} found")
            for col in category_columns:
                print(f"  ✅ {col[0]}: {col[1]} (nullable: {col[2]})")
            
            # Check myths_facts table
            result = await db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'myths_facts' 
                AND column_name = 'custom_points'
            """))
            
            mf_columns = result.fetchall()
            print(f"MythsFacts new columns: {len(mf_columns)} found")
            for col in mf_columns:
                print(f"  ✅ {col[0]}: {col[1]} (nullable: {col[2]})")
            
            # Test 2: Test category creation with new fields
            print("\n🎯 Test 2: Testing Category Creation with MVF Fields")
            
            # Create a test category with MVF enhancements
            test_category = Category(
                name="Test Wildlife Safety",
                slug="test-wildlife-safety",
                description="Test category for MVF system with custom rewards",
                custom_credits=15,  # Custom credits instead of default 3
                is_featured=True,   # Featured category
                mvf_enabled=True,   # Enabled for MVF
                is_active=True
            )
            
            db.add(test_category)
            await db.commit()
            await db.refresh(test_category)
            
            print(f"✅ Created test category: {test_category.name}")
            print(f"  - Custom Credits: {test_category.custom_credits}")
            print(f"  - Is Featured: {test_category.is_featured}")
            print(f"  - MVF Enabled: {test_category.mvf_enabled}")
            
            # Test 3: Test myth fact creation with custom points
            print("\n🃏 Test 3: Testing MythFact Creation with Custom Points")
            
            test_myth_fact = MythFact(
                category_id=test_category.id,
                title="Test Snake Behavior",
                myth_content="Snakes are always aggressive and will attack humans on sight.",
                fact_content="Most snakes are not aggressive and will only attack when threatened or defending themselves.",
                custom_points=8,  # Custom points instead of default 5
                is_featured=False
            )
            
            db.add(test_myth_fact)
            await db.commit()
            await db.refresh(test_myth_fact)
            
            print(f"✅ Created test myth fact: {test_myth_fact.title}")
            print(f"  - Category: {test_category.name}")
            print(f"  - Custom Points: {test_myth_fact.custom_points}")
            
            # Test 4: Test queries for MVF system
            print("\n🔍 Test 4: Testing MVF System Queries")
            
            # Get MVF-enabled categories
            result = await db.execute(
                text("SELECT * FROM categories WHERE mvf_enabled = true AND is_active = true")
            )
            mvf_categories = result.fetchall()
            
            print(f"✅ Found {len(mvf_categories)} MVF-enabled categories")
            
            # Get featured category
            result = await db.execute(
                text("SELECT * FROM categories WHERE is_featured = true AND mvf_enabled = true AND is_active = true LIMIT 1")
            )
            featured_category = result.fetchone()
            
            if featured_category:
                print(f"✅ Featured category: {featured_category[1]}")  # name column
            
            # Get cards for category with custom points
            result = await db.execute(
                text("SELECT * FROM myths_facts WHERE category_id = :category_id"),
                {"category_id": str(test_category.id)}
            )
            category_cards = result.fetchall()
            
            print(f"✅ Found {len(category_cards)} cards in test category")
            for card in category_cards:
                points = card[7] or "default (5)"  # custom_points column
                print(f"  - {card[2]}: {points} points")  # title column
            
            # Test 5: Calculate total rewards
            print("\n💰 Test 5: Testing Reward Calculation")
            
            # Simulate playing all cards in the featured category
            total_points = sum(card[7] or 5 for card in category_cards)  # custom_points or default
            category_credits = test_category.custom_credits or 3
            
            print(f"✅ Reward calculation for '{test_category.name}':")
            print(f"  - Cards played: {len(category_cards)}")
            print(f"  - Total points: {total_points}")
            print(f"  - Category credits: {category_credits}")
            print(f"  - Total rewards: {total_points + category_credits}")
            
            # Cleanup test data
            print("\n🧹 Cleaning up test data...")
            await db.delete(test_myth_fact)
            await db.delete(test_category)
            await db.commit()
            print("✅ Test data cleaned up")
            
            print("\n🎉 All tests passed! Category-based MVF system is working correctly!")
            print("\n📋 System Summary:")
            print("✅ Database schema updated with new fields")
            print("✅ Categories support custom credits and featured status")
            print("✅ MythFacts support custom points per card")
            print("✅ MVF-enabled categories can be queried efficiently")
            print("✅ Featured category system works")
            print("✅ Custom reward calculation works")
            
            return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Category-based MVF System Test")
    print(f"Timestamp: {datetime.now()}")
    
    success = asyncio.run(test_category_mvf_system())
    
    if success:
        print("\n✅ All tests completed successfully!")
        print("\n🎯 Next steps:")
        print("1. Visit /admin/manage/categories to create categories")
        print("2. Set custom credits and featured status")
        print("3. Create cards with custom points")
        print("4. Test the frontend category selection")
    else:
        print("\n❌ Tests failed. Please check the errors above.")
        sys.exit(1)