#!/usr/bin/env python3
"""Quick production database diagnostic"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Production database
prod_url = "postgresql+asyncpg://postgres:tzhYjqKYRQbaovrEPQlzCoaEMgEpDlGS@nozomi.proxy.rlwy.net:22842/railway"
engine = create_async_engine(prod_url, echo=False)
session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def check_prod():
    print("🔍 PRODUCTION DATABASE DIAGNOSTIC")
    print("=" * 60)
    
    async with session_factory() as session:
        # Check alembic version
        print("\n📌 Current Alembic Version:")
        result = await session.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar()
        print(f"   {version}")
        
        # Get all tables
        print("\n📊 All Tables:")
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"   Total: {len(tables)} tables")
        for table in tables:
            print(f"   - {table}")
        
        # Check for missing tables
        print("\n🔍 Checking for specific tables:")
        missing = []
        for table_name in ['video_channels', 'general_knowledge_videos', 'national_parks', 'temp_user_registrations']:
            exists = table_name in tables
            status = "✅" if exists else "❌"
            print(f"   {status} {table_name}")
            if not exists:
                missing.append(table_name)
        
        if missing:
            print(f"\n⚠️  Missing {len(missing)} tables: {', '.join(missing)}")
        else:
            print("\n✅ All expected tables exist!")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_prod())
