"""
Compare local PostgreSQL database with Railway database to find missing tables
"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect
from dotenv import load_dotenv

load_dotenv()

# Railway database URL
RAILWAY_DATABASE_URL = "postgresql+asyncpg://postgres:QONZYLRjVQtrDLnchpMHQMwxZnxKDzsV@caboose.proxy.rlwy.net:17005/railway"

# Local database URL
LOCAL_DATABASE_URL = "postgresql+asyncpg://postgres:850redred@localhost:5432/Junglore_KE"

print("=" * 80)
print("DATABASE COMPARISON TOOL")
print("=" * 80)

async def get_tables(database_url, db_name):
    """Get all table names from a database"""
    try:
        engine = create_async_engine(database_url, echo=False)
        async with engine.connect() as conn:
            # Get all tables
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            await engine.dispose()
            return set(tables)
    except Exception as e:
        print(f"❌ Error connecting to {db_name}: {e}")
        return set()

async def main():
    print("\n🔍 Fetching tables from LOCAL database...")
    local_tables = await get_tables(LOCAL_DATABASE_URL, "LOCAL")
    
    print(f"✅ Found {len(local_tables)} tables in LOCAL database\n")
    
    print("🔍 Fetching tables from RAILWAY database...")
    railway_tables = await get_tables(RAILWAY_DATABASE_URL, "RAILWAY")
    
    print(f"✅ Found {len(railway_tables)} tables in RAILWAY database\n")
    
    # Calculate differences
    missing_in_railway = local_tables - railway_tables
    extra_in_railway = railway_tables - local_tables
    common_tables = local_tables & railway_tables
    
    # Display results
    print("=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)
    
    print(f"\n✅ Common tables ({len(common_tables)}):")
    for table in sorted(common_tables):
        print(f"   • {table}")
    
    if missing_in_railway:
        print(f"\n⚠️  Tables in LOCAL but MISSING in RAILWAY ({len(missing_in_railway)}):")
        for table in sorted(missing_in_railway):
            print(f"   ❌ {table}")
    else:
        print("\n✅ All local tables exist in Railway!")
    
    if extra_in_railway:
        print(f"\n📌 Tables in RAILWAY but NOT in LOCAL ({len(extra_in_railway)}):")
        for table in sorted(extra_in_railway):
            print(f"   • {table}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Local tables:    {len(local_tables)}")
    print(f"Railway tables:  {len(railway_tables)}")
    print(f"Common:          {len(common_tables)}")
    print(f"Missing in Railway: {len(missing_in_railway)}")
    print(f"Extra in Railway:   {len(extra_in_railway)}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
