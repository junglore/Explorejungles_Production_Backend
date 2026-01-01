#!/usr/bin/env python3
"""
Railway Database Setup Diagnostic
Run this to check if your environment is properly configured
"""

import os
import sys
import subprocess

def check_item(description, check_func):
    """Run a check and print result"""
    try:
        result, message = check_func()
        status = "✅" if result else "❌"
        print(f"{status} {description}")
        if message:
            print(f"   {message}")
        return result
    except Exception as e:
        print(f"❌ {description}")
        print(f"   Error: {e}")
        return False

def check_database_url():
    """Check if DATABASE_URL is set"""
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        return False, "DATABASE_URL not found in environment"
    
    # Check format
    if db_url.startswith('postgresql://') or db_url.startswith('postgres://'):
        return True, f"Set: {db_url[:50]}..."
    else:
        return False, f"Invalid format: {db_url[:30]}..."

def check_alembic():
    """Check if Alembic is accessible"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr
    except FileNotFoundError:
        return False, "Alembic not installed or not accessible"
    except Exception as e:
        return False, str(e)

def check_asyncpg():
    """Check if asyncpg is available"""
    try:
        import asyncpg
        return True, f"Version available"
    except ImportError:
        return False, "Module not installed"

def check_alembic_current():
    """Check current migration state"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "current"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            if not output or "None" in output:
                return False, "No migrations applied yet"
            return True, output
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def check_alembic_heads():
    """Check for multiple migration heads"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "heads"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            heads = [line for line in result.stdout.strip().split('\n') if line]
            if len(heads) > 1:
                return False, f"Multiple heads detected ({len(heads)}). May need merge."
            return True, f"Single head: {heads[0] if heads else 'None'}"
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

def check_migration_files():
    """Check if migration files exist"""
    versions_dir = "alembic/versions"
    if not os.path.exists(versions_dir):
        return False, f"Directory not found: {versions_dir}"
    
    migration_files = [f for f in os.listdir(versions_dir) 
                      if f.endswith('.py') and f != '__init__.py']
    
    if not migration_files:
        return False, "No migration files found"
    
    return True, f"Found {len(migration_files)} migration files"

def check_database_connection():
    """Try to connect to database"""
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        return False, "DATABASE_URL not set"
    
    try:
        import asyncpg
        import asyncio
        
        # Clean URL for asyncpg
        if db_url.startswith("postgresql+asyncpg://"):
            clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        elif db_url.startswith("postgres://"):
            clean_url = db_url.replace("postgres://", "postgresql://")
        else:
            clean_url = db_url
        
        async def test_connection():
            try:
                conn = await asyncio.wait_for(
                    asyncpg.connect(clean_url),
                    timeout=10
                )
                await conn.close()
                return True, "Connection successful"
            except asyncio.TimeoutError:
                return False, "Connection timeout (database may be sleeping)"
            except Exception as e:
                return False, f"Connection failed: {str(e)[:100]}"
        
        return asyncio.run(test_connection())
    except Exception as e:
        return False, f"Error: {str(e)[:100]}"

def main():
    print("=" * 70)
    print("🔍 Railway Database Setup Diagnostic")
    print("=" * 70)
    print()
    
    results = []
    
    print("📋 Environment Variables")
    print("-" * 70)
    results.append(check_item("DATABASE_URL configured", check_database_url))
    print()
    
    print("📦 Required Packages")
    print("-" * 70)
    results.append(check_item("Alembic installed", check_alembic))
    results.append(check_item("asyncpg installed", check_asyncpg))
    print()
    
    print("📁 Migration Files")
    print("-" * 70)
    results.append(check_item("Migration files exist", check_migration_files))
    results.append(check_item("Migration heads status", check_alembic_heads))
    print()
    
    print("🔌 Database Connection")
    print("-" * 70)
    results.append(check_item("Can connect to database", check_database_connection))
    print()
    
    print("📊 Migration State")
    print("-" * 70)
    results.append(check_item("Current migration state", check_alembic_current))
    print()
    
    # Summary
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All checks passed ({passed}/{total})!")
        print("\n🚀 Your environment is ready. Deploy to Railway.")
    else:
        print(f"⚠️  {passed}/{total} checks passed")
        print("\n❌ Fix the issues above before deploying to Railway.")
        print("   See RAILWAY_DATABASE_SETUP.md for detailed solutions.")
    
    print("=" * 70)
    return 0 if passed == total else 1

if __name__ == "__main__":
    sys.exit(main())
