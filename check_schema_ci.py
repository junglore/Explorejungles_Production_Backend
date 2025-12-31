#!/usr/bin/env python3
"""
Schema Consistency Check for CI/CD
Exits with code 0 if schemas match, 1 if they differ
"""

import asyncio
import os
import sys
import json

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.db.database import get_db_session
from sqlalchemy import text

async def check_schema_consistency():
    """Check if local and production schemas are consistent"""
    print("🔍 Schema Consistency Check")

    try:
        # Get local schema
        print("📊 Getting local schema...")
        async with get_db_session() as db:
            local_tables = await get_table_info(db)

        # Get production schema
        print("📊 Getting production schema...")
        if "DATABASE_PUBLIC_URL" not in os.environ:
            print("❌ DATABASE_PUBLIC_URL not found - run this from Railway environment:")
            print("   railway run python check_schema_ci.py")
            return False

        original_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = os.environ["DATABASE_PUBLIC_URL"]

        async with get_db_session() as db:
            prod_tables = await get_table_info(db)

        if original_url:
            os.environ["DATABASE_URL"] = original_url

        # Compare
        differences = compare_table_info(local_tables, prod_tables)

        if not differences:
            print("✅ SCHEMAS ARE CONSISTENT")
            return True

        print("❌ SCHEMA INCONSISTENCIES FOUND:")
        print(json.dumps(differences, indent=2))
        return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

async def get_table_info(db_session):
    """Get basic table and column info"""
    tables_query = text("""
        SELECT
            t.table_name,
            array_agg(
                json_build_object(
                    'name', c.column_name,
                    'type', c.data_type,
                    'nullable', c.is_nullable = 'YES'
                ) ORDER BY c.ordinal_position
            ) as columns
        FROM information_schema.tables t
        LEFT JOIN information_schema.columns c ON
            t.table_name = c.table_name AND
            t.table_schema = c.table_schema AND
            c.table_schema = 'public'
        WHERE t.table_schema = 'public'
        AND t.table_type = 'BASE TABLE'
        GROUP BY t.table_name
        ORDER BY t.table_name
    """)

    result = await db_session.execute(tables_query)
    rows = result.fetchall()

    return {row[0]: row[1] for row in rows}

def compare_table_info(local, prod):
    """Compare table information"""
    differences = {}

    # Check for missing tables
    missing_in_prod = set(local.keys()) - set(prod.keys())
    if missing_in_prod:
        differences["tables_missing_in_production"] = list(missing_in_prod)

    missing_in_local = set(prod.keys()) - set(local.keys())
    if missing_in_local:
        differences["tables_missing_in_local"] = list(missing_in_local)

    # Check column differences for common tables
    common_tables = set(local.keys()) & set(prod.keys())
    column_diffs = {}

    for table in common_tables:
        local_cols = {col["name"]: col for col in local[table]}
        prod_cols = {col["name"]: col for col in prod[table]}

        # Missing columns
        missing_cols = set(local_cols.keys()) - set(prod_cols.keys())
        if missing_cols:
            column_diffs[table] = {"missing_in_production": list(missing_cols)}

    if column_diffs:
        differences["column_differences"] = column_diffs

    return differences

if __name__ == "__main__":
    success = asyncio.run(check_schema_consistency())
    sys.exit(0 if success else 1)