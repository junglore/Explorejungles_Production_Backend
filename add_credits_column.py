#!/usr/bin/env python3
"""
Simple script to add credits_on_completion column to quizzes table
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.db.database import get_db_session
from sqlalchemy import text

async def add_credits_column():
    """Add credits_on_completion column to quizzes table if it doesn't exist"""
    try:
        async with get_db_session() as db:
            # Check if the column already exists
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'quizzes' 
                AND column_name = 'credits_on_completion'
            """)
            
            result = await db.execute(check_query)
            column_exists = result.fetchone()
            
            if not column_exists:
                print("Adding credits_on_completion column to quizzes table...")
                
                # Add the column with default value
                alter_query = text("""
                    ALTER TABLE quizzes 
                    ADD COLUMN credits_on_completion INTEGER DEFAULT 50 NOT NULL
                """)
                
                await db.execute(alter_query)
                await db.commit()
                
                print("✅ Successfully added credits_on_completion column")
                print("   Default value: 50 credits per quiz completion")
            else:
                print("✅ credits_on_completion column already exists")
                
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Database Migration: Adding Credits Column")
    print("=" * 50)
    
    success = asyncio.run(add_credits_column())
    
    if success:
        print("\n🎉 Migration completed successfully!")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)