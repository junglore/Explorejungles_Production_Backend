#!/usr/bin/env python3
"""
Create site_settings table and populate with default values
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.db.database import get_db_session
from app.models.site_setting import SiteSetting, DEFAULT_SETTINGS
from sqlalchemy import text

async def create_settings_table():
    """Create site_settings table and populate with defaults"""
    try:
        async with get_db_session() as db:
            # Check if site_settings table exists
            check_table_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'site_settings'
            """)
            
            result = await db.execute(check_table_query)
            table_exists = result.fetchone()
            
            if not table_exists:
                print("Creating site_settings table...")
                
                # Create the table
                create_table_query = text("""
                    CREATE TABLE site_settings (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        key VARCHAR(100) NOT NULL UNIQUE,
                        value TEXT NOT NULL,
                        data_type VARCHAR(20) NOT NULL,
                        category VARCHAR(50) NOT NULL DEFAULT 'general',
                        label VARCHAR(200) NOT NULL,
                        description TEXT,
                        is_public BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                await db.execute(create_table_query)
                
                # Create index on key column
                create_index_query = text("""
                    CREATE INDEX idx_site_settings_key ON site_settings(key)
                """)
                await db.execute(create_index_query)
                
                print("✅ site_settings table created successfully")
            else:
                print("✅ site_settings table already exists")
            
            # Check if default settings are populated
            check_settings_query = text("SELECT COUNT(*) FROM site_settings")
            result = await db.execute(check_settings_query)
            count = result.scalar()
            
            if count == 0:
                print("Populating default settings...")
                
                # Insert default settings
                for setting_data in DEFAULT_SETTINGS:
                    insert_query = text("""
                        INSERT INTO site_settings (key, value, data_type, category, label, description, is_public)
                        VALUES (:key, :value, :data_type, :category, :label, :description, :is_public)
                    """)
                    
                    await db.execute(insert_query, setting_data)
                
                print(f"✅ Inserted {len(DEFAULT_SETTINGS)} default settings")
            else:
                print(f"✅ Settings table already has {count} entries")
            
            await db.commit()
                
    except Exception as e:
        print(f"❌ Error creating settings table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Database Migration: Creating Site Settings")
    print("=" * 50)
    
    success = asyncio.run(create_settings_table())
    
    if success:
        print("\n🎉 Site settings migration completed successfully!")
    else:
        print("\n💥 Site settings migration failed!")
        sys.exit(1)