#!/usr/bin/env python3
"""
Automated Schema Synchronization Script
Generates Alembic migrations for production schema differences
"""

import asyncio
import os
import sys
import subprocess
from datetime import datetime
from typing import List, Dict

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.db.database import get_db_session
from sqlalchemy import text, MetaData, Table, Column
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, INTEGER, VARCHAR, BOOLEAN, TEXT

class SchemaSynchronizer:
    def __init__(self):
        self.local_schema = {}
        self.production_schema = {}

    async def get_table_columns(self, db_session, table_name: str) -> List[Dict]:
        """Get column information for a table"""
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

        return [
            {
                "name": col[0],
                "type": col[1],
                "nullable": col[2] == "YES",
                "default": col[3],
                "max_length": col[4],
                "precision": col[5],
                "scale": col[6]
            } for col in columns
        ]

    async def get_database_tables(self, db_session) -> List[str]:
        """Get all table names"""
        tables_query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        result = await db_session.execute(tables_query)
        return [row[0] for row in result.fetchall()]

    def find_missing_columns(self) -> Dict[str, List[Dict]]:
        """Find columns that exist locally but not in production"""
        missing_columns = {}

        for table_name, local_columns in self.local_schema.items():
            if table_name in self.production_schema:
                prod_columns = {col["name"]: col for col in self.production_schema[table_name]}
                local_columns_list = local_columns

                missing = []
                for local_col in local_columns_list:
                    if local_col["name"] not in prod_columns:
                        missing.append(local_col)

                if missing:
                    missing_columns[table_name] = missing

        return missing_columns

    def generate_migration_script(self, missing_columns: Dict[str, List[Dict]]) -> str:
        """Generate Alembic migration script for missing columns"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        revision_id = f"{timestamp}_sync_production_schema"

        # Generate upgrade function
        upgrade_lines = []
        for table_name, columns in missing_columns.items():
            for col in columns:
                col_type = self.map_sql_type_to_alembic(col)
                nullable = "nullable=True" if col["nullable"] else "nullable=False"
                default = f", default={repr(col['default'])}" if col["default"] else ""

                upgrade_lines.append(f"    op.add_column('{table_name}', sa.Column('{col['name']}', {col_type}, {nullable}{default}))")

        # Generate downgrade function (remove columns in reverse order)
        downgrade_lines = []
        for table_name, columns in reversed(list(missing_columns.items())):
            for col in reversed(columns):
                downgrade_lines.append(f"    op.drop_column('{table_name}', '{col['name']}')")

        # Create the migration file content
        migration_content = f'''"""Sync production schema with local

Revision ID: {revision_id}
Revises: d869f2f395fa
Create Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = 'd869f2f395fa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add missing columns to match local schema"""
'''

        if upgrade_lines:
            migration_content += "\n".join(upgrade_lines) + "\n"

        migration_content += '''
def downgrade() -> None:
    """Remove added columns"""
'''

        if downgrade_lines:
            migration_content += "\n".join(downgrade_lines) + "\n"

        return migration_content, revision_id

    def map_sql_type_to_alembic(self, col: Dict) -> str:
        """Map SQL data types to Alembic/SQLAlchemy types"""
        type_mapping = {
            "uuid": "postgresql.UUID(as_uuid=True)",
            "character varying": f"sa.String(length={col['max_length']})" if col['max_length'] else "sa.Text()",
            "text": "sa.Text()",
            "integer": "sa.Integer()",
            "boolean": "sa.Boolean()",
            "timestamp with time zone": "sa.DateTime(timezone=True)",
            "timestamp without time zone": "sa.DateTime()",
            "numeric": f"sa.Numeric({col['precision']}, {col['scale']})" if col['precision'] else "sa.Numeric()",
        }

        return type_mapping.get(col["type"], f"sa.String(length={col['max_length']})")

async def sync_schemas():
    """Main function to synchronize schemas"""
    synchronizer = SchemaSynchronizer()

    print("🔄 Schema Synchronization Tool")
    print("=" * 40)

    try:
        # Get local schema
        print("📊 Analyzing local database...")
        async with get_db_session() as db:
            tables = await synchronizer.get_database_tables(db)
            for table in tables:
                synchronizer.local_schema[table] = await synchronizer.get_table_columns(db, table)

        print(f"✅ Local schema: {len(synchronizer.local_schema)} tables")

        # Get production schema
        print("📊 Analyzing production database...")
        original_url = os.environ.get("DATABASE_URL")
        if "DATABASE_PUBLIC_URL" in os.environ:
            os.environ["DATABASE_URL"] = os.environ["DATABASE_PUBLIC_URL"]

            async with get_db_session() as db:
                tables = await synchronizer.get_database_tables(db)
                for table in tables:
                    synchronizer.production_schema[table] = await synchronizer.get_table_columns(db, table)

            if original_url:
                os.environ["DATABASE_URL"] = original_url

        print(f"✅ Production schema: {len(synchronizer.production_schema)} tables")

        # Find differences
        missing_columns = synchronizer.find_missing_columns()

        if not missing_columns:
            print("\n✅ SCHEMAS ARE SYNCHRONIZED!")
            return True

        print(f"\n🔍 Found {sum(len(cols) for cols in missing_columns.values())} missing columns in production")

        # Generate migration
        migration_content, revision_id = synchronizer.generate_migration_script(missing_columns)

        # Write migration file
        migration_dir = os.path.join(os.path.dirname(__file__), "alembic", "versions")
        migration_file = os.path.join(migration_dir, f"{revision_id}_.py")

        with open(migration_file, 'w') as f:
            f.write(migration_content)

        print(f"\n📝 Generated migration file: {migration_file}")

        print("\n🛠️  COLUMNS TO BE ADDED:")
        for table_name, columns in missing_columns.items():
            print(f"  📋 {table_name}:")
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                default = f" DEFAULT {col['default']}" if col["default"] else ""
                print(f"    + {col['name']} ({col['type']}) {nullable}{default}")

        print("\n🚀 TO APPLY THIS MIGRATION:")
        print("  1. Test locally: alembic upgrade head")
        print("  2. Apply to production: railway run 'cd KE_Junglore_Backend && alembic upgrade head'")
        print("  3. Verify: python compare_schemas.py")

        return False

    except Exception as e:
        print(f"❌ Error during synchronization: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(sync_schemas())
    if success:
        print("\n🎉 Schemas are already synchronized!")
    else:
        print("\n📋 Migration generated for schema synchronization!")