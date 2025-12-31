@echo off
REM Schema Synchronization Check Script (Windows)
REM Add to package.json scripts or CI/CD pipeline

echo 🔍 Running Schema Synchronization Checks
echo =========================================

REM Check if we're in the backend directory
if not exist "alembic\env.py" (
    echo ❌ Error: Must be run from KE_Junglore_Backend directory
    exit /b 1
)

REM Check if required environment variables exist
if "%DATABASE_PUBLIC_URL%"=="" (
    echo ❌ Error: DATABASE_PUBLIC_URL environment variable not set
    exit /b 1
)

echo 📊 Step 1: Checking schema consistency...
python check_schema_ci.py
if %ERRORLEVEL% EQU 0 (
    echo ✅ Schemas are consistent!
) else (
    echo ❌ Schema inconsistencies found!
    echo.
    echo 🔧 Running detailed comparison...
    python compare_schemas.py
    echo.
    echo 🛠️  To fix inconsistencies:
    echo    1. Review the differences above
    echo    2. Generate migration: python sync_schemas.py
    echo    3. Test locally: alembic upgrade head
    echo    4. Apply to production: railway run "cd KE_Junglore_Backend && alembic upgrade head"
    exit /b 1
)

echo.
echo 🎉 All schema checks passed!
echo Local and production databases are synchronized.