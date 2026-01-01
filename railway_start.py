# #!/usr/bin/env python3
# """
# Railway Production Server
# Simple startup for Railway deployment without Redis dependency
# """

# import os
# import sys
# import subprocess
# import uvicorn
# import time

# def wait_for_database(max_attempts=30, delay=2):
#     """Wait for database to be ready before running migrations"""
#     print("\n⏳ Waiting for database to be ready...")
    
#     # Check if we have DATABASE_URL
#     db_url = os.environ.get('DATABASE_URL', '')
#     if not db_url:
#         print("⚠️  No DATABASE_URL found, skipping database wait")
#         return False
    
#     for attempt in range(1, max_attempts + 1):
#         try:
#             # Try to connect using psycopg2 for a quick connection test
#             import asyncpg
#             import asyncio
            
#             # Parse the URL to get connection params
#             if db_url.startswith("postgresql+asyncpg://"):
#                 clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
#             else:
#                 clean_url = db_url
            
#             # Try to connect
#             async def test_connection():
#                 conn = await asyncpg.connect(clean_url)
#                 await conn.close()
            
#             asyncio.run(test_connection())
#             print(f"✅ Database is ready after {attempt} attempt(s)")
#             return True
            
#         except Exception as e:
#             print(f"⏳ Attempt {attempt}/{max_attempts}: Database not ready yet ({str(e)[:50]}...)")
#             if attempt < max_attempts:
#                 time.sleep(delay)
#             else:
#                 print("⚠️  Database connection timeout - will try migrations anyway")
#                 return False
    
#     return False

# def run_migrations():
#     """Run database migrations before starting the app"""
#     print("\n🔄 Running database migrations...")
    
#     # Wait for database to be ready
#     wait_for_database()
    
#     # Run custom migration for type column (one-time)
#     try:
#         print("\n🔧 Running custom migration: add_type_column...")
#         result = subprocess.run(
#             [sys.executable, "add_type_column_production.py"],
#             capture_output=True,
#             text=True,
#             timeout=30
#         )
#         if result.returncode == 0:
#             print("✅ Type column migration completed!")
#             if result.stdout:
#                 print(result.stdout)
#         else:
#             print(f"⚠️  Type column migration had issues (may already exist)")
#             if result.stderr:
#                 print(result.stderr)
#     except Exception as e:
#         print(f"⚠️  Type column migration error: {e}")
#         print("⚠️  Continuing anyway...")
    
#     # Run alembic migrations
#     try:
#         result = subprocess.run(
#             ["alembic", "upgrade", "head"],
#             capture_output=True,
#             text=True,
#             check=True
#         )
#         print("✅ Alembic migrations completed successfully!")
#         if result.stdout:
#             print(result.stdout)
#     except subprocess.CalledProcessError as e:
#         print(f"⚠️  Migration error: {e}")
#         if e.stdout:
#             print(e.stdout)
#         if e.stderr:
#             print(e.stderr)
#         print("⚠️  Continuing despite migration error...")
#         # Don't exit - let app start anyway
#     except Exception as e:
#         print(f"⚠️  Could not run migrations: {e}")
#         print("⚠️  Continuing anyway...")

# def main():
#     """Main startup function"""
#     print("🚀 Starting Junglore Backend on Railway...")
    
#     # Run migrations first
#     run_migrations()
    
#     # Debug environment variables
#     print("\n🔍 Environment Debug:")
#     db_url = os.environ.get('DATABASE_URL', 'NOT SET')
#     if db_url != 'NOT SET':
#         print(f"DATABASE_URL (raw): {db_url[:50]}...")
#         # Fix DATABASE_URL to use asyncpg if needed
#         if db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
#             fixed_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
#             os.environ["DATABASE_URL"] = fixed_url
#             print(f"DATABASE_URL (fixed): {fixed_url[:50]}...")
#     else:
#         print(f"DATABASE_URL: {db_url}")
    
#     print(f"REDISURL: {os.environ.get('REDISURL', 'NOT SET')[:50]}...")
#     print(f"REDIS_URL: {os.environ.get('REDIS_URL', 'NOT SET')[:50]}...")
#     print(f"SECRET_KEY: {os.environ.get('SECRET_KEY', 'NOT SET')[:20]}...")
#     print(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'NOT SET')}")
    
#     # Get Railway environment variables
#     port = int(os.environ.get("PORT", 8000))
#     host = "0.0.0.0"  # Railway requires 0.0.0.0
    
#     print(f"📍 Environment: {os.environ.get('ENVIRONMENT', 'production')}")
#     print(f"🌐 Host: {host}")
#     print(f"🔌 Port: {port}")
    
#     # Set required environment variables for large uploads
#     os.environ["MAX_CONTENT_LENGTH"] = str(100 * 1024 * 1024)  # 100MB
#     os.environ["UVICORN_MAX_CONTENT_SIZE"] = str(100 * 1024 * 1024)  # 100MB
    
#     try:
#         # Import app after setting environment
#         from app.main import app
        
#         print("✅ App imported successfully")
#         print(f"🏥 Health check available at: http://{host}:{port}/health")
#         print(f"🎯 API docs at: http://{host}:{port}/api/docs")
#         print(f"👑 Admin panel at: http://{host}:{port}/admin")
        
#         # Use subprocess to call uvicorn CLI for better control
#         print("\n🚀 Starting Uvicorn server with production optimizations...")
#         result = subprocess.run([
#             sys.executable, "-m", "uvicorn",
#             "app.main:app",
#             "--host", host,
#             "--port", str(port),
#             "--log-level", "info",
#             "--access-log",
#             "--timeout-keep-alive", "65",
#             "--limit-max-requests", "5000"  # 5x improvement over default 1000
#         ], check=False)
        
#         # Exit with same code as uvicorn
#         sys.exit(result.returncode)
        
#     except Exception as e:
#         print(f"❌ Failed to start server: {e}")
#         import traceback
#         traceback.print_exc()
#         sys.exit(1)

# if __name__ == "__main__":
#     main()




#!/usr/bin/env python3
"""
Railway Production Server
Simple startup for Railway deployment without Redis dependency
"""

import os
import sys
import subprocess
import uvicorn
import time

def wait_for_database(max_attempts=30, delay=2):
    """Wait for database to be ready before running migrations"""
    print("\n⏳ Waiting for database to be ready...")
    
    # Check if we have DATABASE_URL
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        print("⚠️  No DATABASE_URL found, skipping database wait")
        return False
    
    for attempt in range(1, max_attempts + 1):
        try:
            # Try to connect using psycopg2 for a quick connection test
            import asyncpg
            import asyncio
            
            # Parse the URL to get connection params
            if db_url.startswith("postgresql+asyncpg://"):
                clean_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            else:
                clean_url = db_url
            
            # Try to connect
            async def test_connection():
                conn = await asyncpg.connect(clean_url)
                await conn.close()
            
            asyncio.run(test_connection())
            print(f"✅ Database is ready after {attempt} attempt(s)")
            return True
            
        except Exception as e:
            print(f"⏳ Attempt {attempt}/{max_attempts}: Database not ready yet ({str(e)[:50]}...)")
            if attempt < max_attempts:
                time.sleep(delay)
            else:
                print("⚠️  Database connection timeout - will try migrations anyway")
                return False
    
    return False

def validate_environment():
    """Validate that all required environment variables and tools are available"""
    print("\n🔍 Validating environment...")
    
    # Check DATABASE_URL
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        print("❌ CRITICAL: DATABASE_URL environment variable is not set!")
        print("   Please configure DATABASE_URL in Railway dashboard")
        sys.exit(1)
    
    print(f"✅ DATABASE_URL is set: {db_url[:50]}...")
    
    # Check if alembic is accessible
    try:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Alembic is accessible: {result.stdout.strip()}")
        else:
            print(f"❌ Alembic check failed: {result.stderr}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ CRITICAL: Cannot access Alembic module: {e}")
        print("   Make sure 'alembic' is in requirements.txt and installed")
        sys.exit(1)
    
    # Check if asyncpg is accessible (required for PostgreSQL)
    try:
        import asyncpg
        print(f"✅ asyncpg module is available")
    except ImportError as e:
        print(f"❌ CRITICAL: asyncpg module not available: {e}")
        print("   Make sure 'asyncpg' is in requirements.txt")
        sys.exit(1)
    
    print("✅ Environment validation passed!")
    return True


def run_migrations():
    """Run database migrations before starting the app"""
    print("\n🔄 Running database migrations...")
    
    # Wait for database to be ready
    db_ready = wait_for_database()
    if not db_ready:
        print("⚠️  Database connection timeout - attempting migrations anyway...")
    
    # 1. Run custom migration for type column (one-time)
    # We keep this permissive (continue on error) as it might be a specific legacy script
    try:
        print("\n🔧 Running custom migration: add_type_column...")
        result = subprocess.run(
            [sys.executable, "add_type_column_production.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✅ Type column migration completed!")
        else:
            print(f"⚠️  Type column migration had issues (may already exist)")
            # specific script errors usually shouldn't stop deployment unless critical
    except Exception as e:
        print(f"⚠️  Type column migration error: {e}")
        print("⚠️  Continuing...")
    
    # 2. Run Alembic Migrations (CRITICAL)
    # If this fails, we MUST exit, otherwise the app runs with no tables.
    print("\n⚗️  Running Alembic migrations...")
    print(f"   Working directory: {os.getcwd()}")
    print(f"   Python executable: {sys.executable}")
    
    try:
        # CRITICAL: Use sys.executable -m alembic to ensure we use the correct environment
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True,
            cwd=os.getcwd()  # Ensure we're in the right directory
        )
        print("✅ Alembic migrations completed successfully!")
        if result.stdout:
            print("--- Migration Output ---")
            print(result.stdout)
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ CRITICAL MIGRATION ERROR (Return code: {e.returncode})")
        if e.stdout:
            print("--- STDOUT ---")
            print(e.stdout)
        if e.stderr:
            print("--- STDERR ---")
            print(e.stderr)
        
        print("\n🛑 DEPLOYMENT FAILED: Database tables could not be created.")
        print("   Check the error above and fix the migration issues.")
        print("   Common issues:")
        print("   - DATABASE_URL not set correctly in Railway")
        print("   - Database not accessible from Railway")
        print("   - Migration conflicts (run 'alembic current' to check)")
        sys.exit(1)  # Exit with error code to fail the deployment
        
    except FileNotFoundError as e:
        print(f"\n❌ CRITICAL: Alembic command not found: {e}")
        print("   This should not happen after validation. Check installation.")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR during migrations: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main startup function"""
    print("🚀 Starting Junglore Backend on Railway...")
    
    # Validate environment first
    validate_environment()
    
    # Run migrations
    run_migrations()
    
    # Debug environment variables
    print("\n🔍 Environment Debug:")
    db_url = os.environ.get('DATABASE_URL', 'NOT SET')
    if db_url != 'NOT SET':
        print(f"DATABASE_URL (raw): {db_url[:50]}...")
        # Fix DATABASE_URL to use asyncpg if needed
        if db_url.startswith("postgresql://") and not db_url.startswith("postgresql+asyncpg://"):
            fixed_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            os.environ["DATABASE_URL"] = fixed_url
            print(f"DATABASE_URL (fixed): {fixed_url[:50]}...")
    else:
        print(f"DATABASE_URL: {db_url}")
    
    print(f"REDISURL: {os.environ.get('REDISURL', 'NOT SET')[:50]}...")
    print(f"REDIS_URL: {os.environ.get('REDIS_URL', 'NOT SET')[:50]}...")
    print(f"SECRET_KEY: {os.environ.get('SECRET_KEY', 'NOT SET')[:20]}...")
    print(f"ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'NOT SET')}")
    
    # Get Railway environment variables
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"  # Railway requires 0.0.0.0
    
    print(f"📍 Environment: {os.environ.get('ENVIRONMENT', 'production')}")
    print(f"🌐 Host: {host}")
    print(f"🔌 Port: {port}")
    
    # Set required environment variables for large uploads
    os.environ["MAX_CONTENT_LENGTH"] = str(100 * 1024 * 1024)  # 100MB
    os.environ["UVICORN_MAX_CONTENT_SIZE"] = str(100 * 1024 * 1024)  # 100MB
    
    try:
        # Import app after setting environment
        from app.main import app
        
        print("✅ App imported successfully")
        print(f"🏥 Health check available at: http://{host}:{port}/health")
        print(f"🎯 API docs at: http://{host}:{port}/api/docs")
        print(f"👑 Admin panel at: http://{host}:{port}/admin")
        
        # Use subprocess to call uvicorn CLI for better control
        print("\n🚀 Starting Uvicorn server with production optimizations...")
        result = subprocess.run([
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", host,
            "--port", str(port),
            "--log-level", "info",
            "--access-log",
            "--timeout-keep-alive", "65",
            "--limit-max-requests", "5000"
        ], check=False)
        
        # Exit with same code as uvicorn
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()