#!/usr/bin/env python3
"""
Migration Runner for Railway Deployment
This script runs Alembic migrations during deployment
"""

import subprocess
import sys
import os

def run_migrations():
    """Run Alembic migrations"""
    print("=" * 60)
    print("🚀 Running Database Migrations")
    print("=" * 60)
    
    try:
        # Run alembic upgrade head
        print("\n📊 Executing: alembic upgrade head")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
            
        print("\n✅ Migrations completed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Migration failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("\n❌ Alembic not found. Make sure it's installed:")
        print("   pip install alembic")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
