#!/usr/bin/env python3
"""
Automated Railway Deployment Fix Script
This script ensures your Railway database is in sync with your code
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and print results"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        if e.stderr:
            print(e.stderr)
        return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 Railway Deployment Fix Script")
    print("=" * 60)
    
    # Step 1: Check Railway CLI
    print("\n📋 Checking prerequisites...")
    if not run_command("railway --version", "Checking Railway CLI"):
        print("\n⚠️  Railway CLI not found. Installing...")
        print("   Run: npm install -g @railway/cli")
        print("   Then run this script again")
        return False
    
    # Step 2: Check if linked to Railway project
    print("\n🔗 Checking Railway project connection...")
    if not run_command("railway status", "Verifying Railway link"):
        print("\n⚠️  Not linked to Railway project")
        print("   Run: railway link")
        print("   Then run this script again")
        return False
    
    # Step 3: Run migrations
    print("\n📊 Running database migrations on Railway...")
    if not run_command("railway run alembic upgrade head", "Running database migrations"):
        print("\n⚠️  Migrations failed. Possible reasons:")
        print("   1. Database connection issue")
        print("   2. Migration files have errors")
        print("   3. Railway service is not running")
        print("\nCheck Railway logs: railway logs")
        return False
    
    # Step 4: Export production schema
    print("\n📤 Exporting production schema...")
    if not run_command("railway run python export_production_schema.py", "Exporting production schema"):
        print("\n⚠️  Schema export failed")
        return False
    
    # Step 5: Compare schemas
    print("\n🔍 Comparing local and production schemas...")
    if not run_command("python compare_schemas.py", "Comparing schemas"):
        print("\n⚠️  Schema comparison found differences")
        print("   Check the output above for details")
    
    print("\n" + "=" * 60)
    print("✅ Railway deployment fix completed!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. ✅ Database migrations applied")
    print("2. 🔍 Check Railway dashboard to ensure service is running")
    print("3. 🌐 Verify CORS_ORIGINS on Railway matches your Vercel URL")
    print("4. 🎨 Verify VITE_API_BASE_URL on Vercel matches Railway URL")
    print("5. 🔄 Redeploy frontend on Vercel if env vars changed")
    print("6. 🧪 Test login on your hosted website")
    print("\n🔗 Useful commands:")
    print("   View logs:    railway logs")
    print("   Open Railway: railway open")
    print("   Check status: railway status")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
