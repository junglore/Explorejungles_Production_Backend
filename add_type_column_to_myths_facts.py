"""
Add type column to myths_facts table
This column controls which content (myth or fact) displays to users during gameplay
"""

import asyncio
from sqlalchemy import text
from app.db.database import get_db_session

async def add_type_column():
    """Add type column to myths_facts table with default value 'myth'"""
    async with get_db_session() as session:
        try:
            # Check if column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'myths_facts' AND column_name = 'type'
            """)
            result = await session.execute(check_query)
            exists = result.fetchone()
            
            if exists:
                print("✓ Column 'type' already exists in myths_facts table")
                return
            
            # Add the type column with default value
            alter_query = text("""
                ALTER TABLE myths_facts 
                ADD COLUMN type VARCHAR(10) NOT NULL DEFAULT 'myth'
            """)
            await session.execute(alter_query)
            await session.commit()
            
            print("✓ Successfully added 'type' column to myths_facts table")
            print("  Default value: 'myth'")
            print("  All existing records will show myth cards by default")
            
        except Exception as e:
            print(f"✗ Error adding type column: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    print("Adding 'type' column to myths_facts table...")
    asyncio.run(add_type_column())
    print("\n✓ Migration completed successfully!")
