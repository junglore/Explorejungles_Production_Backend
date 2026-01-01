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

async def get_table_columns(database_url, table_name):
    """Get all columns for a specific table"""
    try:
        engine = create_async_engine(database_url, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
                ORDER BY ordinal_position
            """), {"table_name": table_name})
            columns = {row[0]: {
                "data_type": row[1],
                "is_nullable": row[2],
                "column_default": row[3]
            } for row in result}
            await engine.dispose()
            return columns
    except Exception as e:
        print(f"❌ Error getting columns for {table_name}: {e}")
        return {}

async def compare_table_columns(table_name, local_url, railway_url):
    """Compare columns between local and railway for a specific table"""
    local_columns = await get_table_columns(local_url, table_name)
    railway_columns = await get_table_columns(railway_url, table_name)
    
    missing_in_railway = set(local_columns.keys()) - set(railway_columns.keys())
    extra_in_railway = set(railway_columns.keys()) - set(local_columns.keys())
    
    return {
        "missing_in_railway": missing_in_railway,
        "extra_in_railway": extra_in_railway,
        "local_columns": local_columns,
        "railway_columns": railway_columns
    }

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
    print("TABLE COMPARISON RESULTS")
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
    
    # Now compare columns for common tables
    print("\n" + "=" * 80)
    print("COLUMN COMPARISON FOR COMMON TABLES")
    print("=" * 80)
    print("\n🔍 Analyzing columns in each table...")
    
    tables_with_missing_columns = {}
    tables_with_extra_columns = {}
    
    for table in sorted(common_tables):
        column_comparison = await compare_table_columns(table, LOCAL_DATABASE_URL, RAILWAY_DATABASE_URL)
        
        if column_comparison["missing_in_railway"]:
            tables_with_missing_columns[table] = column_comparison["missing_in_railway"]
        
        if column_comparison["extra_in_railway"]:
            tables_with_extra_columns[table] = column_comparison["extra_in_railway"]
    
    if tables_with_missing_columns:
        print(f"\n⚠️  Tables with MISSING columns in RAILWAY ({len(tables_with_missing_columns)}):")
        for table, missing_cols in sorted(tables_with_missing_columns.items()):
            print(f"\n   📋 Table: {table}")
            for col in sorted(missing_cols):
                print(f"      ❌ Missing column: {col}")
    else:
        print("\n✅ All columns from local tables exist in Railway tables!")
    
    if tables_with_extra_columns:
        print(f"\n📌 Tables with EXTRA columns in RAILWAY ({len(tables_with_extra_columns)}):")
        for table, extra_cols in sorted(tables_with_extra_columns.items()):
            print(f"\n   📋 Table: {table}")
            for col in sorted(extra_cols):
                print(f"      ➕ Extra column: {col}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Local tables:    {len(local_tables)}")
    print(f"Railway tables:  {len(railway_tables)}")
    print(f"Common tables:   {len(common_tables)}")
    print(f"Missing tables in Railway: {len(missing_in_railway)}")
    print(f"Extra tables in Railway:   {len(extra_in_railway)}")
    print(f"\nTables with missing columns in Railway: {len(tables_with_missing_columns)}")
    print(f"Tables with extra columns in Railway:   {len(tables_with_extra_columns)}")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
