#!/usr/bin/env python3
"""
Railway Deployment Diagnostic Tool
Checks your local and Railway setup to identify issues
"""

import subprocess
import sys
import os
import json

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def print_check(status, message):
    """Print a check result"""
    icon = "✅" if status else "❌"
    print(f"{icon} {message}")

def run_command(command, silent=False):
    """Run a command and return success status and output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        if not silent and result.stdout:
            print(result.stdout)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        if not silent and e.stderr:
            print(e.stderr)
        return False, e.stderr if e.stderr else str(e)
    except Exception as e:
        if not silent:
            print(f"Error: {e}")
        return False, str(e)

def check_railway_cli():
    """Check if Railway CLI is installed"""
    print_header("1. Railway CLI Check")
    status, output = run_command("railway --version", silent=True)
    if status:
        print_check(True, f"Railway CLI installed: {output.strip()}")
        return True
    else:
        print_check(False, "Railway CLI not installed")
        print("\n📦 Install with: npm install -g @railway/cli")
        return False

def check_railway_connection():
    """Check Railway project connection"""
    print_header("2. Railway Connection Check")
    status, output = run_command("railway status", silent=True)
    if status and "Not linked" not in output:
        print_check(True, "Connected to Railway project")
        print(output)
        return True
    else:
        print_check(False, "Not connected to Railway project")
        print("\n🔗 Link with: railway link")
        return False

def check_local_environment():
    """Check local environment files"""
    print_header("3. Local Environment Check")
    
    # Check .env file
    env_path = ".env"
    if os.path.exists(env_path):
        print_check(True, f"Local .env file exists")
        with open(env_path, 'r') as f:
            content = f.read()
            has_db = "DATABASE_URL" in content
            print_check(has_db, "DATABASE_URL configured")
    else:
        print_check(False, "Local .env file not found")
    
    # Check .env.production
    prod_env_path = ".env.production"
    if os.path.exists(prod_env_path):
        print_check(True, "Production .env file exists")
        with open(prod_env_path, 'r') as f:
            content = f.read()
            has_placeholder = "your-frontend.vercel.app" in content
            print_check(not has_placeholder, "CORS_ORIGINS configured (not placeholder)")
            if has_placeholder:
                print("   ⚠️  Update CORS_ORIGINS with your actual Vercel URL")
    else:
        print_check(False, "Production .env file not found")

def check_alembic_migrations():
    """Check Alembic migrations"""
    print_header("4. Database Migrations Check")
    
    # Check if alembic.ini exists
    if os.path.exists("alembic.ini"):
        print_check(True, "Alembic configuration found")
    else:
        print_check(False, "Alembic configuration not found")
        return False
    
    # Check migrations directory
    versions_path = "alembic/versions"
    if os.path.exists(versions_path):
        migrations = [f for f in os.listdir(versions_path) if f.endswith('.py') and f != '__pycache__']
        print_check(True, f"Found {len(migrations)} migration files")
        
        # Show latest migrations
        print("\n📋 Recent migrations:")
        migrations.sort(reverse=True)
        for m in migrations[:5]:
            print(f"   • {m}")
    else:
        print_check(False, "Migrations directory not found")
        return False
    
    return True

def check_railway_env_vars():
    """Check Railway environment variables"""
    print_header("5. Railway Environment Variables")
    
    print("\n🔍 Fetching Railway environment variables...")
    status, output = run_command("railway variables", silent=False)
    
    if status:
        # Check for important variables
        important_vars = ['DATABASE_URL', 'REDIS_URL', 'SECRET_KEY', 'CORS_ORIGINS']
        print("\n📊 Key variables status:")
        for var in important_vars:
            has_var = var in output
            print_check(has_var, f"{var} configured")
    else:
        print_check(False, "Could not fetch Railway variables")

def check_model_files():
    """Check if model files exist with new tables"""
    print_header("6. Database Models Check")
    
    models_to_check = [
        ("app/models/user.py", ["google_id", "facebook_id", "organization"]),
        ("app/models/myth_fact_collection.py", ["MythFactCollection"]),
        ("app/models/site_setting.py", ["SiteSetting"]),
    ]
    
    for model_file, keywords in models_to_check:
        if os.path.exists(model_file):
            print_check(True, f"{model_file} exists")
            with open(model_file, 'r') as f:
                content = f.read()
                for keyword in keywords:
                    has_keyword = keyword in content
                    print(f"   • {keyword}: {'✓' if has_keyword else '✗'}")
        else:
            print_check(False, f"{model_file} not found")

def provide_recommendations():
    """Provide recommendations based on checks"""
    print_header("📋 Recommendations")
    
    print("""
Based on the diagnostic results above, follow these steps:

1. ✅ If Railway CLI is not installed:
   npm install -g @railway/cli

2. ✅ If not connected to Railway:
   railway login
   railway link

3. ✅ Run migrations on Railway:
   railway run alembic upgrade head

4. ✅ Update CORS_ORIGINS on Railway:
   - Go to Railway dashboard
   - Add/update: CORS_ORIGINS=https://your-vercel-url.vercel.app

5. ✅ Verify Vercel environment variables:
   - Check VITE_API_BASE_URL points to Railway

6. ✅ Run the automated fix:
   python fix_railway_deployment.py

7. ✅ Test login on hosted site after fixes
    """)

def main():
    """Main diagnostic function"""
    print("""
╔════════════════════════════════════════════════════════════╗
║                                                            ║
║        Railway Deployment Diagnostic Tool                 ║
║        Checking your deployment configuration             ║
║                                                            ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    # Change to backend directory if needed
    if "KE_Junglore_Backend" not in os.getcwd():
        backend_path = os.path.join(os.getcwd(), "KE_Junglore_Backend")
        if os.path.exists(backend_path):
            os.chdir(backend_path)
            print(f"📂 Changed directory to: {backend_path}\n")
    
    all_checks = [
        check_railway_cli(),
        check_railway_connection(),
        check_local_environment(),
        check_alembic_migrations(),
        check_railway_env_vars(),
        check_model_files(),
    ]
    
    provide_recommendations()
    
    # Summary
    passed = sum(1 for check in all_checks if check)
    total = len(all_checks)
    
    print_header("Summary")
    print(f"\n✅ Passed: {passed}/{total} checks")
    
    if passed == total:
        print("\n🎉 All checks passed! Your setup looks good.")
        print("   Run: python fix_railway_deployment.py")
    else:
        print(f"\n⚠️  {total - passed} issue(s) found. Follow recommendations above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
