#!/usr/bin/env python3
"""
Sync production database schema to match local exactly
"""

import asyncio
import sys
import os
from typing import Dict, List, Set

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, MetaData, Table, Column, Integer, String, Boolean, DateTime, Text, JSON, UUID
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.core.config import Settings

# Production database connection
prod_settings = Settings()
prod_engine = create_async_engine(prod_settings.DATABASE_URL, echo=True)
prod_session = sessionmaker(prod_engine, class_=AsyncSession, expire_on_commit=False)


async def get_local_schema() -> Dict[str, List[Dict]]:
    """Get local database schema"""
    # Local database connection
    local_engine = create_async_engine(
        "postgresql+asyncpg://postgres:850redred@localhost:5432/Junglore_KE",
        echo=False
    )
    local_session_factory = sessionmaker(local_engine, class_=AsyncSession, expire_on_commit=False)

    schema = {}

    async with local_session_factory() as session:
        # Get all tables
        result = await session.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]

        for table_name in tables:
            # Get columns
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

            schema[table_name] = columns

    await local_engine.dispose()
    return schema


async def sync_production_to_local():
    """Sync production database to match local schema exactly"""

    print("🔄 SYNCING PRODUCTION DATABASE TO MATCH LOCAL")
    print("=" * 50)

    try:
        # Get local schema
        print("📊 Getting local database schema...")
        local_schema = await get_local_schema()
        print(f"✅ Local schema: {len(local_schema)} tables")

        # Get production schema
        print("📊 Getting production database schema...")
        prod_schema = {}

        async with prod_session() as session:
            # Get all tables in production
            result = await session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            prod_tables = {row[0] for row in result.fetchall()}

            for table_name in prod_tables:
                # Get columns
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

                prod_schema[table_name] = columns

        print(f"✅ Production schema: {len(prod_schema)} tables")

        # Compare and sync
        local_tables = set(local_schema.keys())
        prod_tables = set(prod_schema.keys())

        tables_to_add = local_tables - prod_tables
        tables_to_drop = prod_tables - local_tables
        tables_to_check = local_tables & prod_tables

        print(f"\n📋 SYNC PLAN:")
        print(f"   Tables to add: {len(tables_to_add)}")
        print(f"   Tables to drop: {len(tables_to_drop)}")
        print(f"   Tables to check: {len(tables_to_check)}")

        # Drop extra tables in production
        if tables_to_drop:
            print(f"\n🗑️  Dropping extra tables in production...")
            async with prod_session() as session:
                for table_name in sorted(tables_to_drop):
                    print(f"   Dropping table: {table_name}")
                    await session.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                await session.commit()
            print("✅ Extra tables dropped")

        # Add missing tables (this is complex - would need full table definitions)
        if tables_to_add:
            print(f"\n⚠️  Missing tables in production: {sorted(tables_to_add)}")
            print("   These need to be created via Alembic migrations or manual SQL")
            print("   Run: railway run alembic upgrade head")

        # Check and fix columns in common tables
        print(f"\n🔍 Checking columns in {len(tables_to_check)} common tables...")

        async with prod_session() as session:
            for table_name in sorted(tables_to_check):
                local_cols = {col['name']: col for col in local_schema[table_name]}
                prod_cols = {col['name']: col for col in prod_schema[table_name]}

                # Find missing columns
                missing_cols = set(local_cols.keys()) - set(prod_cols.keys())
                extra_cols = set(prod_cols.keys()) - set(local_cols.keys())

                # Drop extra columns
                for col_name in extra_cols:
                    print(f"   Dropping extra column {table_name}.{col_name}")
                    try:
                        await session.execute(text(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS {col_name}"))
                    except Exception as e:
                        print(f"     ❌ Error dropping column: {e}")

                # Add missing columns
                for col_name in missing_cols:
                    local_col = local_cols[col_name]
                    col_type = map_sql_type(local_col)
                    nullable = "NULL" if local_col['nullable'] else "NOT NULL"
                    default = f"DEFAULT {local_col['default']}" if local_col['default'] else ""

                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type} {nullable} {default}".strip()
                    print(f"   Adding missing column: {alter_sql}")

                    try:
                        await session.execute(text(alter_sql))
                    except Exception as e:
                        print(f"     ❌ Error adding column: {e}")

            await session.commit()

        print(f"\n✅ Production database sync completed!")
        print("   Note: Table creation should be done via Alembic migrations")

    except Exception as e:
        print(f"❌ Error during sync: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await prod_engine.dispose()


def map_sql_type(col_info: Dict) -> str:
    """Map column info to SQL type string"""
    col_type = col_info['type'].upper()

    if col_type == 'CHARACTER VARYING':
        if col_info['max_length']:
            return f"VARCHAR({col_info['max_length']})"
        return "TEXT"
    elif col_type == 'INTEGER':
        return "INTEGER"
    elif col_type == 'BOOLEAN':
        return "BOOLEAN"
    elif col_type == 'TIMESTAMP WITH TIME ZONE':
        return "TIMESTAMPTZ"
    elif col_type == 'TIMESTAMP WITHOUT TIME ZONE':
        return "TIMESTAMP"
    elif col_type == 'UUID':
        return "UUID"
    elif col_type == 'JSON':
        return "JSONB"
    elif col_type == 'TEXT':
        return "TEXT"
    elif col_type == 'BIGINT':
        return "BIGINT"
    elif col_type == 'DOUBLE PRECISION':
        return "DOUBLE PRECISION"
    else:
        return col_type


if __name__ == "__main__":
    asyncio.run(sync_production_to_local())