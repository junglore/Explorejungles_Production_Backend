#!/usr/bin/env python3
"""
Database Schema Comparison Tool
Compares local and production database schemas
"""

import asyncio
import os
import sys
from typing import Dict, List, Set
import json

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.db.database import get_db_session
from sqlalchemy import text

class SchemaComparator:
    def __init__(self):
        self.local_schema = {}
        self.production_schema = {}

    async def get_table_schema(self, db_session, table_name: str) -> Dict:
        """Get detailed schema information for a table"""
        try:
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

            result = await db_session.execute(columns_query, {"table_name": table_name})
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

            result = await db_session.execute(indexes_query, {"table_name": table_name})
            indexes = result.fetchall()

            return {
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
        except Exception as e:
            print(f"Error getting schema for {table_name}: {e}")
            return {"error": str(e)}

    async def get_database_schema(self, db_session) -> Dict[str, Dict]:
        """Get schema for all tables in the database"""
        schema = {}

        # Get all table names
        tables_query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        result = await db_session.execute(tables_query)
        tables = result.fetchall()

        for table_row in tables:
            table_name = table_row[0]
            schema[table_name] = await self.get_table_schema(db_session, table_name)

        return schema

    def compare_schemas(self) -> Dict:
        """Compare local and production schemas"""
        differences = {
            "missing_in_production": {},
            "missing_in_local": {},
            "differences": {}
        }

        # Find tables missing in production
        for table_name, table_schema in self.local_schema.items():
            if table_name not in self.production_schema:
                differences["missing_in_production"][table_name] = table_schema
            else:
                # Compare table schemas
                table_diff = self.compare_table_schemas(table_name, table_schema, self.production_schema[table_name])
                if table_diff:
                    differences["differences"][table_name] = table_diff

        # Find tables missing in local
        for table_name in self.production_schema:
            if table_name not in self.local_schema:
                differences["missing_in_local"][table_name] = self.production_schema[table_name]

        return differences

    def compare_table_schemas(self, table_name: str, local_schema: Dict, prod_schema: Dict) -> Dict:
        """Compare schemas of a specific table"""
        differences = {}

        # Compare columns
        local_columns = {col["name"]: col for col in local_schema.get("columns", [])}
        prod_columns = {col["name"]: col for col in prod_schema.get("columns", [])}

        # Missing columns in production (exist in local but not in prod)
        missing_cols_prod = []
        for col_name, col_info in local_columns.items():
            if col_name not in prod_columns:
                missing_cols_prod.append(col_info)

        # Extra columns in production (exist in prod but not in local)
        extra_cols_prod = []
        for col_name, col_info in prod_columns.items():
            if col_name not in local_columns:
                extra_cols_prod.append(col_info)

        # Different column definitions
        diff_cols = []
        for col_name in local_columns:
            if col_name in prod_columns:
                local_col = local_columns[col_name]
                prod_col = prod_columns[col_name]
                if not self.columns_equal(local_col, prod_col):
                    diff_cols.append({
                        "column": col_name,
                        "local": local_col,
                        "production": prod_col
                    })

        if missing_cols_prod or extra_cols_prod or diff_cols:
            differences["columns"] = {
                "missing_in_production": missing_cols_prod,
                "extra_in_production": extra_cols_prod,
                "different_definitions": diff_cols
            }

        # Compare indexes (simplified)
        local_indexes = {idx["name"]: idx for idx in local_schema.get("indexes", [])}
        prod_indexes = {idx["name"]: idx for idx in prod_schema.get("indexes", [])}

        missing_indexes_prod = []
        for idx_name, idx_info in local_indexes.items():
            if idx_name not in prod_indexes:
                missing_indexes_prod.append(idx_info)

        extra_indexes_prod = []
        for idx_name, idx_info in prod_indexes.items():
            if idx_name not in local_indexes:
                extra_indexes_prod.append(idx_info)

        if missing_indexes_prod or extra_indexes_prod:
            differences["indexes"] = {
                "missing_in_production": missing_indexes_prod,
                "extra_in_production": extra_indexes_prod
            }

        return differences

    def columns_equal(self, col1: Dict, col2: Dict) -> bool:
        """Check if two column definitions are equal"""
        # Compare key attributes
        attrs_to_compare = ["type", "nullable", "max_length", "precision", "scale"]
        for attr in attrs_to_compare:
            if col1.get(attr) != col2.get(attr):
                return False
        return True

async def compare_databases():
    """Main function to compare local and production databases"""
    comparator = SchemaComparator()

    print("🔍 Comparing Local vs Production Database Schemas")
    print("=" * 60)

    try:
        # Get local schema
        print("📊 Getting local database schema...")
        async with get_db_session() as db:
            comparator.local_schema = await comparator.get_database_schema(db)

        print(f"✅ Local schema loaded: {len(comparator.local_schema)} tables")

        # Get production schema
        print("📊 Getting production database schema...")
        production_schema_file = "production_schema.json"

        if os.path.exists(production_schema_file):
            print(f"Loading production schema from {production_schema_file}")
            try:
                with open(production_schema_file, 'r') as f:
                    comparator.production_schema = json.load(f)
                print(f"✅ Production schema loaded: {len(comparator.production_schema)} tables")
            except Exception as e:
                print(f"❌ Error loading production schema file: {e}")
                return False
        else:
            print(f"❌ Production schema file not found: {production_schema_file}")
            print("   Run this first: railway run python export_production_schema.py")
            return False

        # Compare schemas
        differences = comparator.compare_schemas()

        # Report results
        print("\n📋 COMPARISON RESULTS")
        print("=" * 30)

        if not differences["missing_in_production"] and not differences["missing_in_local"] and not differences["differences"]:
            print("✅ SCHEMAS ARE IDENTICAL!")
            return True

        # Tables missing in production
        if differences["missing_in_production"]:
            print(f"\n❌ TABLES MISSING IN PRODUCTION ({len(differences['missing_in_production'])}):")
            for table_name in differences["missing_in_production"]:
                print(f"  - {table_name}")

        # Tables missing in local
        if differences["missing_in_local"]:
            print(f"\n⚠️  TABLES MISSING IN LOCAL ({len(differences['missing_in_local'])}):")
            for table_name in differences["missing_in_local"]:
                print(f"  - {table_name}")

        # Schema differences
        if differences["differences"]:
            print(f"\n🔄 SCHEMA DIFFERENCES ({len(differences['differences'])}):")
            for table_name, table_diff in differences["differences"].items():
                print(f"  📋 {table_name}:")

                if "columns" in table_diff:
                    cols = table_diff["columns"]
                    if cols["missing_in_production"]:
                        col_names = [c['name'] for c in cols['missing_in_production']]
                        print(f"    ❌ Missing columns in production ({len(col_names)}): {col_names}")
                    if cols["extra_in_production"]:
                        col_names = [c['name'] for c in cols['extra_in_production']]
                        print(f"    ⚠️  Extra columns in production ({len(col_names)}): {col_names}")
                    if cols["different_definitions"]:
                        print(f"    🔄 Different column definitions ({len(cols['different_definitions'])}):")
                        for diff in cols["different_definitions"]:
                            print(f"      - {diff['column']}: {diff['local']['type']} vs {diff['production']['type']}")

                if "indexes" in table_diff:
                    if table_diff["indexes"]["missing_in_production"]:
                        idx_names = [i['name'] for i in table_diff['indexes']['missing_in_production']]
                        print(f"    ❌ Missing indexes in production ({len(idx_names)}): {idx_names}")
                    if table_diff["indexes"].get("extra_in_production"):
                        idx_names = [i['name'] for i in table_diff['indexes']['extra_in_production']]
                        print(f"    ⚠️  Extra indexes in production ({len(idx_names)}): {idx_names}")

        # Generate migration suggestions
        print("\n🛠️  MIGRATION SUGGESTIONS")
        print("=" * 25)

        if differences["missing_in_production"]:
            print("To sync production with local:")
            print("1. Create Alembic migration for missing tables/columns")
            print("2. Test migration locally")
            print("3. Apply to production: railway run 'cd KE_Junglore_Backend && alembic upgrade head'")

        if differences["missing_in_local"]:
            print("To sync local with production:")
            print("1. Pull latest changes from production")
            print("2. Update local Alembic migrations")
            print("3. Run: alembic upgrade head")

        return len(differences["missing_in_production"]) == 0 and len(differences["differences"]) == 0

    except Exception as e:
        print(f"❌ Error during comparison: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(compare_databases())
    if success:
        print("\n🎉 Schema comparison completed successfully!")
    else:
        print("\n💥 Schema comparison found issues!")
        sys.exit(1)