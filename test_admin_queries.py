#!/usr/bin/env python3
"""
Simple test script to verify admin panel database queries work correctly.
This tests the specific queries that were failing due to missing columns.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.db.database import get_db_session
from sqlalchemy import text


async def test_admin_queries():
    """Test the specific queries used by the admin panel."""
    print("🧪 Testing Admin Panel Database Queries")
    print("=" * 50)

    try:
        async with get_db_session() as db:
            print("✅ Database connection established")

            # Test 1: Categories query (used in admin/quizzes)
            print("\n📋 Test 1: Categories query")
            try:
                result = await db.execute(text("""
                    SELECT id, name, custom_credits, is_featured
                    FROM categories
                    ORDER BY name
                    LIMIT 5
                """))
                categories = result.fetchall()
                print(f"✅ Found {len(categories)} categories")
                for cat in categories[:3]:  # Show first 3
                    print(f"  - {cat.name}: {cat.custom_credits} credits, featured: {cat.is_featured}")
            except Exception as e:
                print(f"❌ Categories query failed: {e}")
                return False

            # Test 2: Myths and facts query (used in admin/myths-facts)
            print("\n📋 Test 2: Myths and facts query")
            try:
                result = await db.execute(text("""
                    SELECT id, title, custom_points
                    FROM myths_facts
                    ORDER BY title
                    LIMIT 5
                """))
                myths_facts = result.fetchall()
                print(f"✅ Found {len(myths_facts)} myths/facts")
                for mf in myths_facts[:3]:  # Show first 3
                    print(f"  - {mf.title}: {mf.custom_points} points")
            except Exception as e:
                print(f"❌ Myths/facts query failed: {e}")
                return False

            # Test 3: Users query (used in admin/users)
            print("\n📋 Test 3: Users query")
            try:
                result = await db.execute(text("""
                    SELECT id, username, email, is_superuser
                    FROM users
                    ORDER BY username
                    LIMIT 5
                """))
                users = result.fetchall()
                print(f"✅ Found {len(users)} users")
                for user in users[:3]:  # Show first 3
                    print(f"  - {user.username} ({user.email}): superuser={user.is_superuser}")
            except Exception as e:
                print(f"❌ Users query failed: {e}")
                return False

            # Test 4: Quizzes query (used in admin/quizzes)
            print("\n📋 Test 4: Quizzes query")
            try:
                result = await db.execute(text("""
                    SELECT q.id, q.title, c.name as category_name, q.is_active
                    FROM quizzes q
                    JOIN categories c ON q.category_id = c.id
                    ORDER BY q.title
                    LIMIT 5
                """))
                quizzes = result.fetchall()
                print(f"✅ Found {len(quizzes)} quizzes")
                for quiz in quizzes[:3]:  # Show first 3
                    print(f"  - {quiz.title} ({quiz.category_name}): active={quiz.is_active}")
            except Exception as e:
                print(f"❌ Quizzes query failed: {e}")
                return False

            print("\n🎉 All admin panel queries working correctly!")
            return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_admin_queries())
    sys.exit(0 if success else 1)