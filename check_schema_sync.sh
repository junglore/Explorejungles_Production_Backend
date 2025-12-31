#!/bin/bash
# Schema Synchronization Check Script
# Add to package.json scripts or CI/CD pipeline

set -e  # Exit on any error

echo "🔍 Running Schema Synchronization Checks"
echo "========================================="

# Check if we're in the backend directory
if [ ! -f "alembic/env.py" ]; then
    echo "❌ Error: Must be run from KE_Junglore_Backend directory"
    exit 1
fi

# Check if required environment variables exist
if [ -z "$DATABASE_PUBLIC_URL" ]; then
    echo "❌ Error: DATABASE_PUBLIC_URL environment variable not set"
    exit 1
fi

echo "📊 Step 1: Checking schema consistency..."
if python check_schema_ci.py; then
    echo "✅ Schemas are consistent!"
else
    echo "❌ Schema inconsistencies found!"
    echo ""
    echo "🔧 Running detailed comparison..."
    python compare_schemas.py
    echo ""
    echo "🛠️  To fix inconsistencies:"
    echo "   1. Review the differences above"
    echo "   2. Generate migration: python sync_schemas.py"
    echo "   3. Test locally: alembic upgrade head"
    echo "   4. Apply to production: railway run 'cd KE_Junglore_Backend && alembic upgrade head'"
    exit 1
fi

echo ""
echo "🎉 All schema checks passed!"
echo "Local and production databases are synchronized."