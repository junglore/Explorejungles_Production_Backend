"""
Script to manually add missing columns to users table
"""
import asyncio
import asyncpg
from app.core.config import settings

async def add_missing_columns():
    """Add missing columns to users table if they don't exist"""
    
    # Connect to database - remove +asyncpg from URL
    db_url = settings.DATABASE_URL.replace('+asyncpg', '')
    conn = await asyncpg.connect(db_url)
    
    try:
        # Check and add organization column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='organization'
            );
        """)
        
        if not result:
            print("Adding organization column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN organization VARCHAR(200);
            """)
            print("✓ Added organization column")
        else:
            print("✓ organization column already exists")
        
        # Check and add professional_title column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='professional_title'
            );
        """)
        
        if not result:
            print("Adding professional_title column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN professional_title VARCHAR(200);
            """)
            print("✓ Added professional_title column")
        else:
            print("✓ professional_title column already exists")
        
        # Check and add discussion_count column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='discussion_count'
            );
        """)
        
        if not result:
            print("Adding discussion_count column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN discussion_count INTEGER DEFAULT 0 NOT NULL;
            """)
            print("✓ Added discussion_count column")
        else:
            print("✓ discussion_count column already exists")
        
        # Check and add comment_count column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='comment_count'
            );
        """)
        
        if not result:
            print("Adding comment_count column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN comment_count INTEGER DEFAULT 0 NOT NULL;
            """)
            print("✓ Added comment_count column")
        else:
            print("✓ comment_count column already exists")
        
        # Check and add reputation_score column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='reputation_score'
            );
        """)
        
        if not result:
            print("Adding reputation_score column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN reputation_score INTEGER DEFAULT 0 NOT NULL;
            """)
            print("✓ Added reputation_score column")
        else:
            print("✓ reputation_score column already exists")
        
        # Check and add google_id column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='google_id'
            );
        """)
        
        if not result:
            print("Adding google_id column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN google_id VARCHAR(255);
            """)
            print("✓ Added google_id column")
        else:
            print("✓ google_id column already exists")
        
        # Check and add facebook_id column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='facebook_id'
            );
        """)
        
        if not result:
            print("Adding facebook_id column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN facebook_id VARCHAR(255);
            """)
            print("✓ Added facebook_id column")
        else:
            print("✓ facebook_id column already exists")
        
        # Check and add linkedin_id column
        result = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_name='users' AND column_name='linkedin_id'
            );
        """)
        
        if not result:
            print("Adding linkedin_id column...")
            await conn.execute("""
                ALTER TABLE users 
                ADD COLUMN linkedin_id VARCHAR(255);
            """)
            print("✓ Added linkedin_id column")
        else:
            print("✓ linkedin_id column already exists")
        
        print("\n✅ All missing columns have been added successfully!")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_missing_columns())
