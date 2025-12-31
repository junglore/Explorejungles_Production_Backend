"""
Add type column to myths_facts table for production Railway database
Run this ONCE after deploying to Railway
"""

import asyncio
import os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

async def add_type_column():
    """Add type column to myths_facts table with default value 'myth'"""
    
    # Get DATABASE_URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        return
    
    # Fix URL for asyncpg if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    print(f"🔗 Connecting to database...")
    
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
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
                print("✅ Column 'type' already exists in myths_facts table")
                return
            
            # Add the type column with default value
            print("➕ Adding 'type' column to myths_facts table...")
            alter_query = text("""
                ALTER TABLE myths_facts 
                ADD COLUMN type VARCHAR(10) NOT NULL DEFAULT 'myth'
            """)
            await session.execute(alter_query)
            await session.commit()
            
            print("✅ Successfully added 'type' column to myths_facts table")
            print("   Default value: 'myth'")
            print("   All existing records will show myth cards by default")
            
        except Exception as e:
            print(f"❌ Error adding type column: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 PRODUCTION DATABASE MIGRATION")
    print("   Adding 'type' column to myths_facts table")
    print("=" * 60)
    asyncio.run(add_type_column())
    print("\n✅ Migration completed successfully!")
    print("=" * 60)
