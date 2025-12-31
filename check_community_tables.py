"""Check for community, discussion, and category tables"""
import asyncio
from sqlalchemy import inspect
from app.db.database import engine

async def check_tables():
    async with engine.begin() as conn:
        def get_tables(connection):
            inspector = inspect(connection)
            all_tables = inspector.get_table_names()
            
            # Filter for community/discussion/category related tables
            community_tables = [t for t in all_tables if any(keyword in t.lower() for keyword in ['discussion', 'category', 'community'])]
            
            print("=" * 70)
            print("🔍 COMMUNITY & CATEGORY TABLES CHECK")
            print("=" * 70)
            
            if community_tables:
                print(f"\n✅ Found {len(community_tables)} related tables:\n")
                for table in sorted(community_tables):
                    print(f"  ✓ {table}")
            else:
                print("\n❌ No discussion/community/category tables found")
            
            print("\n" + "=" * 70)
            print(f"Total tables in database: {len(all_tables)}")
            print("=" * 70)
        
        await conn.run_sync(get_tables)

if __name__ == "__main__":
    asyncio.run(check_tables())
