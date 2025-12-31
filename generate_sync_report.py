"""
Generate a detailed sync report before running migrations
Shows exactly what will happen when you run alembic upgrade head
"""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import text, inspect
from app.db.database import get_db_session, engine

async def generate_sync_report():
    """Generate comprehensive report of migration status"""
    
    print("=" * 80)
    print("📋 MIGRATION SYNC REPORT")
    print("=" * 80)
    print(f"Generated at: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with get_db_session() as db:
        # 1. Get current alembic version
        try:
            result = await db.execute(text("SELECT version_num FROM alembic_version"))
            current_version = result.scalar_one_or_none()
        except:
            current_version = None
        
        print(f"\n📍 Current Database Version: {current_version or 'NONE (Empty database)'}")
        
        # 2. List all migration files
        migrations_dir = Path("alembic/versions")
        migration_files = []
        
        for f in sorted(migrations_dir.glob("*.py")):
            if not f.name.startswith("__"):
                revision_id = f.stem.split('_')[0]
                name = '_'.join(f.stem.split('_')[1:]) if '_' in f.stem else f.stem
                migration_files.append({
                    'file': f.name,
                    'revision': revision_id,
                    'name': name,
                    'path': f
                })
        
        print(f"\n📁 Total Migration Files Found: {len(migration_files)}")
        
        # 3. Determine which migrations will run
        pending = []
        applied = []
        
        if current_version:
            found_current = False
            for mig in migration_files:
                if mig['revision'] == current_version:
                    found_current = True
                    applied.append(mig)
                elif found_current:
                    pending.append(mig)
                else:
                    applied.append(mig)
        else:
            pending = migration_files
        
        # 4. Show pending migrations
        print("\n" + "=" * 80)
        print(f"⏳ PENDING MIGRATIONS ({len(pending)}) - Will be applied")
        print("=" * 80)
        
        if pending:
            for i, mig in enumerate(pending, 1):
                print(f"\n{i}. {mig['revision']}")
                print(f"   Name: {mig['name']}")
                print(f"   File: {mig['file']}")
                
                # Try to read what this migration does
                try:
                    with open(mig['path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Extract docstring
                        if '"""' in content:
                            parts = content.split('"""')
                            if len(parts) >= 2:
                                docstring = parts[1].strip()
                                print(f"   Description: {docstring[:100]}")
                        
                        # Check for table operations
                        tables_created = []
                        tables_modified = []
                        
                        if 'create_table' in content:
                            # Simple extraction
                            for line in content.split('\n'):
                                if 'create_table' in line and "'" in line:
                                    table_name = line.split("'")[1]
                                    tables_created.append(table_name)
                        
                        if 'add_column' in content:
                            for line in content.split('\n'):
                                if 'add_column' in line and "'" in line:
                                    table_name = line.split("'")[1]
                                    if table_name not in tables_modified:
                                        tables_modified.append(table_name)
                        
                        if tables_created:
                            print(f"   Creates tables: {', '.join(tables_created)}")
                        if tables_modified:
                            print(f"   Modifies tables: {', '.join(tables_modified)}")
                
                except Exception as e:
                    print(f"   (Could not analyze file)")
        else:
            print("\n✅ No pending migrations - database is up to date!")
        
        # 5. Show applied migrations
        print("\n" + "=" * 80)
        print(f"✅ ALREADY APPLIED MIGRATIONS ({len(applied)})")
        print("=" * 80)
        
        if applied:
            print("\nMost recent 5:")
            for mig in applied[-5:]:
                print(f"  ✓ {mig['revision']} - {mig['name'][:50]}")
            if len(applied) > 5:
                print(f"  ... and {len(applied) - 5} more")
        else:
            print("\nNone yet")
        
        # 6. Check existing tables
        print("\n" + "=" * 80)
        print("📊 EXISTING TABLES IN DATABASE")
        print("=" * 80)
        
    async with engine.begin() as conn:
        def get_tables(connection):
            inspector = inspect(connection)
            return inspector.get_table_names()
        
        tables = await conn.run_sync(get_tables)
        
        print(f"\nTotal tables: {len(tables)}")
        
        # Categorize tables
        video_tables = [t for t in tables if 'video' in t]
        discussion_tables = [t for t in tables if 'discussion' in t]
        system_tables = [t for t in tables if t in ['users', 'categories', 'alembic_version']]
        other_tables = [t for t in tables if t not in video_tables + discussion_tables + system_tables]
        
        if system_tables:
            print("\n📌 System tables:")
            for t in system_tables:
                print(f"  ✓ {t}")
        
        if video_tables:
            print("\n🎬 Video tables:")
            for t in video_tables:
                print(f"  ✓ {t}")
        
        if discussion_tables:
            print("\n💬 Discussion tables:")
            for t in discussion_tables:
                print(f"  ✓ {t}")
        
        if other_tables:
            print("\n📁 Other tables:")
            for t in other_tables:
                print(f"  ✓ {t}")
    
    # 7. Risk assessment
    print("\n" + "=" * 80)
    print("⚠️  RISK ASSESSMENT")
    print("=" * 80)
    
    if not pending:
        print("\n✅ NO RISK - No migrations to apply")
    else:
        print(f"\n📊 {len(pending)} migration(s) will be applied")
        
        # Check for potential conflicts
        async with get_db_session() as db:
            async with engine.begin() as conn:
                def check_conflicts(connection):
                    inspector = inspect(connection)
                    existing_tables = inspector.get_table_names()
                    
                    conflicts = []
                    for mig in pending:
                        try:
                            with open(mig['path'], 'r') as f:
                                content = f.read()
                                # Check if migration tries to create existing tables
                                for line in content.split('\n'):
                                    if 'create_table' in line and "'" in line:
                                        table_name = line.split("'")[1]
                                        if table_name in existing_tables:
                                            # Check if has defensive code
                                            if 'inspector' not in content or 'existing_tables' not in content:
                                                conflicts.append((mig['revision'], table_name))
                        except:
                            pass
                    
                    return conflicts
                
                conflicts = await conn.run_sync(check_conflicts)
                
                if conflicts:
                    print("\n⚠️  WARNING: Potential conflicts detected!")
                    print("\nThese migrations try to create tables that already exist:")
                    for rev, table in conflicts:
                        print(f"  ⚠️  Migration {rev} creates '{table}' (already exists)")
                    print("\n💡 RECOMMENDATION:")
                    print("   Option 1: Use 'alembic stamp head' to skip migrations")
                    print("   Option 2: Edit migrations to add inspector checks")
                    print("   Option 3: Backup and recreate database")
                else:
                    print("\n✅ No obvious conflicts detected")
                    print("   Migrations appear safe to run")
    
    # 8. Recommendations
    print("\n" + "=" * 80)
    print("💡 RECOMMENDED NEXT STEPS")
    print("=" * 80)
    
    if not pending:
        print("\n✅ Your database is up to date!")
        print("   No action needed.")
    else:
        print("\n1️⃣  BACKUP FIRST (IMPORTANT!):")
        print("   pg_dump -U postgres Junglore_KE > backup_$(date +%Y%m%d).sql")
        
        print("\n2️⃣  CHOOSE YOUR APPROACH:")
        print("\n   Option A - If migrations have inspector checks:")
        print("   → Run: alembic upgrade head")
        print("   → Safe: Will skip existing tables")
        
        print("\n   Option B - If tables already match:")
        print("   → Run: alembic stamp head")
        print("   → Marks migrations as applied without running them")
        
        print("\n   Option C - If unsure:")
        print("   → Run: python check_database_status.py")
        print("   → Verify what tables exist")
        print("   → Then choose Option A or B")
        
        print("\n3️⃣  AFTER MIGRATION:")
        print("   → Run: python check_database_status.py")
        print("   → Verify everything looks correct")
        print("   → Test your application")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(generate_sync_report())
