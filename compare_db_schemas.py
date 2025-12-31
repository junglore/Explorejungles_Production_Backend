#!/usr/bin/env python3
"""
Direct database schema comparison between local and production
"""

import asyncio
import sys
import os
from typing import Dict, List, Set, Tuple

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Local database connection
local_engine = create_async_engine(
    "postgresql+asyncpg://postgres:850redred@localhost:5432/Junglore_KE",
    echo=False
)
local_session = sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)

# Production database connection (will use Railway env vars)
from app.core.config import Settings
prod_settings = Settings()
prod_engine = create_async_engine(prod_settings.DATABASE_URL, echo=False)
prod_session = sessionmaker(prod_engine, class_=AsyncSession, expire_on_commit=False)


async def get_table_list(engine, session_factory) -> Set[str]:
    """Get list of all tables"""
    async with session_factory() as session:
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        return {row[0] for row in result.fetchall()}


async def get_table_columns(engine, session_factory, table_name: str) -> List[Dict]:
    """Get columns for a specific table"""
    async with session_factory() as session:
        result = await session.execute(text("""
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_schema = 'public'
            AND table_name = :table_name
            ORDER BY ordinal_position
        """), {"table_name": table_name})

        columns = []
        for row in result.fetchall():
            columns.append({
                'name': row[0],
                'type': row[1],
                'nullable': row[2] == 'YES',
                'default': row[3],
                'max_length': row[4],
                'precision': row[5],
                'scale': row[6]
            })
        return columns


async def get_table_indexes(engine, session_factory, table_name: str) -> List[Dict]:
    """Get indexes for a specific table"""
    async with session_factory() as session:
        result = await session.execute(text("""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = :table_name
            ORDER BY indexname
        """), {"table_name": table_name})

        indexes = []
        for row in result.fetchall():
            indexes.append({
                'name': row[0],
                'definition': row[1]
            })
        return indexes


async def compare_databases():
    """Compare local and production databases comprehensively"""

    print("🔍 COMPREHENSIVE DATABASE SCHEMA COMPARISON")
    print("=" * 60)

    try:
        # Get table lists
        print("📊 Gathering table information...")
        local_tables = await get_table_list(local_engine, local_session)
        prod_tables = await get_table_list(prod_engine, prod_session)

        print(f"   Local tables: {len(local_tables)}")
        print(f"   Production tables: {len(prod_tables)}")

        # Compare tables
        missing_in_prod = local_tables - prod_tables
        extra_in_prod = prod_tables - local_tables
        common_tables = local_tables & prod_tables

        print(f"\n📋 TABLE COMPARISON:")
        print(f"   Common tables: {len(common_tables)}")
        print(f"   Missing in production: {len(missing_in_prod)}")
        print(f"   Extra in production: {len(extra_in_prod)}")

        if missing_in_prod:
            print(f"\n❌ TABLES MISSING IN PRODUCTION:")
            for table in sorted(missing_in_prod):
                print(f"   - {table}")

        if extra_in_prod:
            print(f"\n⚠️  EXTRA TABLES IN PRODUCTION:")
            for table in sorted(extra_in_prod):
                print(f"   - {table}")

        # Compare columns and indexes in common tables
        column_issues = []
        index_issues = []

        print(f"\n🔍 Checking {len(common_tables)} common tables...")

        for table_name in sorted(common_tables):
            # Compare columns
            local_cols = await get_table_columns(local_engine, local_session, table_name)
            prod_cols = await get_table_columns(prod_engine, prod_session, table_name)

            local_col_names = {col['name'] for col in local_cols}
            prod_col_names = {col['name'] for col in prod_cols}

            missing_cols = local_col_names - prod_col_names
            extra_cols = prod_col_names - local_col_names

            if missing_cols or extra_cols:
                column_issues.append({
                    'table': table_name,
                    'missing_in_prod': missing_cols,
                    'extra_in_prod': extra_cols
                })

            # Check column definitions
            for local_col in local_cols:
                col_name = local_col['name']
                prod_col = next((c for c in prod_cols if c['name'] == col_name), None)

                if prod_col:
                    differences = []
                    if local_col['type'] != prod_col['type']:
                        differences.append(f"type: {local_col['type']} vs {prod_col['type']}")
                    if local_col['nullable'] != prod_col['nullable']:
                        differences.append(f"nullable: {local_col['nullable']} vs {prod_col['nullable']}")

                    if differences:
                        column_issues.append({
                            'table': table_name,
                            'column': col_name,
                            'differences': differences
                        })

            # Compare indexes
            local_indexes = await get_table_indexes(local_engine, local_session, table_name)
            prod_indexes = await get_table_indexes(prod_engine, prod_session, table_name)

            local_index_names = {idx['name'] for idx in local_indexes}
            prod_index_names = {idx['name'] for idx in prod_indexes}

            missing_indexes = local_index_names - prod_index_names
            extra_indexes = prod_index_names - local_index_names

            if missing_indexes or extra_indexes:
                index_issues.append({
                    'table': table_name,
                    'missing_in_prod': missing_indexes,
                    'extra_in_prod': extra_indexes
                })

        # Report column issues
        if column_issues:
            print(f"\n⚠️  COLUMN DIFFERENCES ({len(column_issues)}):")
            for issue in column_issues:
                print(f"   📊 {issue['table']}:")
                if 'missing_in_prod' in issue and issue['missing_in_prod']:
                    print(f"      ❌ Missing: {', '.join(sorted(issue['missing_in_prod']))}")
                if 'extra_in_prod' in issue and issue['extra_in_prod']:
                    print(f"      ➕ Extra: {', '.join(sorted(issue['extra_in_prod']))}")
                if 'differences' in issue:
                    print(f"      🔄 {issue['column']}: {', '.join(issue['differences'])}")

        # Report index issues
        if index_issues:
            print(f"\n⚠️  INDEX DIFFERENCES ({len(index_issues)}):")
            for issue in index_issues:
                print(f"   📊 {issue['table']}:")
                if issue['missing_in_prod']:
                    print(f"      ❌ Missing indexes: {', '.join(sorted(issue['missing_in_prod']))}")
                if issue['extra_in_prod']:
                    print(f"      ➕ Extra indexes: {', '.join(sorted(issue['extra_in_prod']))}")

        # Summary
        total_issues = len(missing_in_prod) + len(extra_in_prod) + len(column_issues) + len(index_issues)

        print(f"\n" + "=" * 60)
        if total_issues == 0:
            print("✅ SUCCESS: Local and Production databases are identical!")
            return True
        else:
            print(f"⚠️  FOUND {total_issues} DIFFERENCES:")
            print(f"   - {len(missing_in_prod)} missing tables in production")
            print(f"   - {len(extra_in_prod)} extra tables in production")
            print(f"   - {len(column_issues)} column differences")
            print(f"   - {len(index_issues)} index differences")
            return False

    except Exception as e:
        print(f"❌ Error during comparison: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await local_engine.dispose()
        await prod_engine.dispose()


if __name__ == "__main__":
    success = asyncio.run(compare_databases())
    if not success:
        print(f"\n🔧 To sync production to match local, run:")
        print(f"   railway run python sync_prod_schema.py")
        sys.exit(1)
    else:
        print(f"\n🎉 Databases are in sync!")