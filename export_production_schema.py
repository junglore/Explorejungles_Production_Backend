#!/usr/bin/env python3
"""
Export production database schema to JSON file
Run this from Railway environment: railway run python export_production_schema.py
"""

import asyncio
import os
import sys
import json
from typing import Dict, List

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.db.database import get_db_session
from sqlalchemy import text

async def export_production_schema():
    """Export production database schema to JSON file"""
    print("📤 Exporting Production Database Schema")
    print("=" * 45)

    try:
        # Override with production URL if needed
        if "DATABASE_PUBLIC_URL" in os.environ:
            os.environ["DATABASE_URL"] = os.environ["DATABASE_PUBLIC_URL"]
            print("Using production database connection")

        schema = {}

        async with get_db_session() as db:
            print("🔍 Analyzing production database...")

            # Get all table names
            tables_query = text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)

            result = await db.execute(tables_query)
            tables = result.fetchall()

            print(f"📋 Found {len(tables)} tables")

            for table_row in tables:
                table_name = table_row[0]
                print(f"  📊 Exporting {table_name}...")

                # Get column information
                columns_query = text("""
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default,
                        character_maximum_length,
                        numeric_precision,
                        numeric_scale
                    FROM information_schema.columns
                    WHERE table_name = :table_name
                    AND table_schema = 'public'
                    ORDER BY ordinal_position
                """)

                result = await db.execute(columns_query, {"table_name": table_name})
                columns = result.fetchall()

                # Get index information
                indexes_query = text("""
                    SELECT
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE tablename = :table_name
                    AND schemaname = 'public'
                """)

                result = await db.execute(indexes_query, {"table_name": table_name})
                indexes = result.fetchall()

                schema[table_name] = {
                    "columns": [
                        {
                            "name": col[0],
                            "type": col[1],
                            "nullable": col[2] == "YES",
                            "default": str(col[3]) if col[3] else None,
                            "max_length": col[4],
                            "precision": col[5],
                            "scale": col[6]
                        } for col in columns
                    ],
                    "indexes": [
                        {
                            "name": idx[0],
                            "definition": idx[1]
                        } for idx in indexes
                    ]
                }

        # Save to file
        output_file = "production_schema.json"
        with open(output_file, 'w') as f:
            json.dump(schema, f, indent=2)

        print(f"\n✅ Production schema exported to {output_file}")
        print(f"   Tables: {len(schema)}")
        print(f"   Total columns: {sum(len(table['columns']) for table in schema.values())}")

        return True

    except Exception as e:
        print(f"❌ Error exporting schema: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(export_production_schema())
    if success:
        print("\n🎉 Schema export completed!")
        print("Now run: python compare_schemas.py")
    else:
        print("\n💥 Schema export failed!")
        sys.exit(1)