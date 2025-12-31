"""
Database migration script to add MVF-specific fields to categories and myths_facts tables

This script adds the required fields for category-based myths vs facts system:
- Categories: custom_credits, is_featured, mvf_enabled fields
- MythsFacts: custom_points field

Run this script after backing up your database.
"""

import asyncio
import logging
from sqlalchemy import text
from app.db.database import get_db_session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_mvf_enhancements():
    """Add MVF enhancement fields to existing tables"""
    
    logger.info("Starting MVF enhancement migration...")
    
    async with get_db_session() as db:
        try:
            # Add new fields to categories table
            logger.info("Adding custom_credits column to categories...")
            await db.execute(text("""
                ALTER TABLE categories 
                ADD COLUMN IF NOT EXISTS custom_credits INTEGER NULL
            """))
            
            logger.info("Adding is_featured column to categories...")
            await db.execute(text("""
                ALTER TABLE categories 
                ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE
            """))
            
            logger.info("Adding mvf_enabled column to categories...")
            await db.execute(text("""
                ALTER TABLE categories 
                ADD COLUMN IF NOT EXISTS mvf_enabled BOOLEAN DEFAULT TRUE
            """))
            
            # Add new fields to myths_facts table
            logger.info("Adding custom_points column to myths_facts...")
            await db.execute(text("""
                ALTER TABLE myths_facts 
                ADD COLUMN IF NOT EXISTS custom_points INTEGER NULL
            """))
            
            # Create indexes for performance
            logger.info("Creating performance indexes...")
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_categories_mvf_featured 
                ON categories (mvf_enabled, is_featured) 
                WHERE mvf_enabled = TRUE
            """))
            
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_categories_mvf_enabled 
                ON categories (mvf_enabled, is_active) 
                WHERE mvf_enabled = TRUE AND is_active = TRUE
            """))
            
            # Commit all changes
            await db.commit()
            logger.info("MVF enhancement migration completed successfully!")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            await db.rollback()
            raise

async def verify_migration():
    """Verify that the migration was successful"""
    
    logger.info("Verifying migration...")
    
    async with get_db_session() as db:
        try:
            # Check categories table columns
            result = await db.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'categories' 
                AND column_name IN ('custom_credits', 'is_featured', 'mvf_enabled')
                ORDER BY column_name
            """))
            category_columns = result.fetchall()
            
            # Check myths_facts table columns
            result = await db.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'myths_facts' 
                AND column_name = 'custom_points'
            """))
            myth_fact_columns = result.fetchall()
            
            logger.info("Categories table new columns:")
            for col in category_columns:
                logger.info(f"  {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")
            
            logger.info("MythsFacts table new columns:")
            for col in myth_fact_columns:
                logger.info(f"  {col.column_name}: {col.data_type} (nullable: {col.is_nullable})")
            
            # Verify we have at least 3 new columns in categories and 1 in myths_facts
            if len(category_columns) >= 3 and len(myth_fact_columns) >= 1:
                logger.info("✅ Migration verification successful!")
                return True
            else:
                logger.error("❌ Migration verification failed!")
                return False
                
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False

async def main():
    """Main migration function"""
    try:
        # Run migration
        await migrate_mvf_enhancements()
        
        # Verify results
        success = await verify_migration()
        
        if success:
            print("\n🎉 MVF Enhancement Migration Complete!")
            print("✅ Categories now support: custom_credits, is_featured, mvf_enabled")
            print("✅ MythsFacts now support: custom_points")
            print("✅ Performance indexes created")
            print("\nYou can now use the enhanced category management system!")
        else:
            print("\n❌ Migration completed but verification failed.")
            print("Please check the logs and database manually.")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        print(f"\n❌ Migration failed: {e}")
        print("Please check your database connection and try again.")

if __name__ == "__main__":
    asyncio.run(main())