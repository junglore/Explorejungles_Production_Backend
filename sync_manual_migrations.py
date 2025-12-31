"""
Helper script for manual file sharing workflow
Use this when colleague gives you migration files manually
"""

import asyncio
import sys
from sqlalchemy import text, select
from app.db.database import get_db_session
from pathlib import Path

async def check_migration_status():
    """Check which migrations exist vs what's in database"""
    
    async with get_db_session() as db:
        # Get current alembic version
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        current_version = result.scalar_one_or_none()
        
        print("=" * 70)
        print("🔍 MIGRATION STATUS CHECK")
        print("=" * 70)
        print(f"\n📊 Current Database Version: {current_version or 'None (empty database)'}")
        
        # List all migration files
        migrations_dir = Path("alembic/versions")
        migration_files = sorted([f.stem for f in migrations_dir.glob("*.py") if not f.name.startswith("__")])
        
        print(f"\n📁 Found {len(migration_files)} migration files:")
        for i, filename in enumerate(migration_files, 1):
            # Extract revision ID (first part before underscore)
            revision_id = filename.split("_")[0]
            status = "✅ APPLIED" if revision_id == current_version else "⏳ PENDING"
            print(f"  {i}. {filename[:60]}... {status}")
        
        print("\n" + "=" * 70)
        print("💡 WHAT TO DO NEXT:")
        print("=" * 70)
        
        if current_version:
            print("""
1. If colleague gave you NEW migration files:
   → Run: alembic upgrade head
   → This applies only NEW migrations after your current version

2. If tables already exist (causing errors):
   → The migrations need defensive checks (inspector pattern)
   → Or manually update alembic_version to skip them

3. If completely out of sync:
   → Consider Option 3 below (stamp command)
""")
        else:
            print("""
⚠️  No alembic version found! Your database might be:
   - Completely empty (need to run all migrations)
   - Created manually (need to stamp current version)

Run: alembic upgrade head
""")

async def list_tables():
    """List all tables in database"""
    async with get_db_session() as db:
        result = await db.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        tables = [row[0] for row in result.fetchall()]
        
        print("\n" + "=" * 70)
        print(f"📋 EXISTING TABLES ({len(tables)})")
        print("=" * 70)
        for table in tables:
            print(f"  ✓ {table}")

if __name__ == "__main__":
    print("\n🔧 Manual Migration Sync Helper\n")
    asyncio.run(check_migration_status())
    asyncio.run(list_tables())
