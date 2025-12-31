#!/usr/bin/env python3
"""
Apply missing columns directly to Railway database
"""
import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def apply_migrations():
    """Add missing columns to Railway database"""
    
    # Get DATABASE_PUBLIC_URL for external access (Railway provides this)
    database_url = os.environ.get('DATABASE_PUBLIC_URL') or os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return False
    
    # Convert to asyncpg if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    print(f"🔗 Connecting to database...")
    print(f"   URL: {database_url[:50]}...")
    
    try:
        engine = create_async_engine(database_url, echo=False)
        
        async with engine.begin() as conn:
            print("\n📊 Adding missing columns to users table...")
            
            # Add OAuth columns
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255);
            """))
            print("   ✅ google_id")
            
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255);
            """))
            print("   ✅ facebook_id")
            
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_id VARCHAR(255);
            """))
            print("   ✅ linkedin_id")
            
            # Add community columns
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(200);
            """))
            print("   ✅ organization")
            
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS professional_title VARCHAR(200);
            """))
            print("   ✅ professional_title")
            
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS discussion_count INTEGER DEFAULT 0;
            """))
            print("   ✅ discussion_count")
            
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS comment_count INTEGER DEFAULT 0;
            """))
            print("   ✅ comment_count")
            
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN IF NOT EXISTS reputation_score INTEGER DEFAULT 0;
            """))
            print("   ✅ reputation_score")
            
            # Update existing users to have default values
            await conn.execute(text("""
                UPDATE users 
                SET discussion_count = 0, 
                    comment_count = 0, 
                    reputation_score = 0 
                WHERE discussion_count IS NULL 
                   OR comment_count IS NULL 
                   OR reputation_score IS NULL;
            """))
            print("\n   ✅ Updated existing users with default values")
            
            # Make columns NOT NULL after setting defaults
            await conn.execute(text("""
                ALTER TABLE users ALTER COLUMN discussion_count SET NOT NULL;
            """))
            await conn.execute(text("""
                ALTER TABLE users ALTER COLUMN comment_count SET NOT NULL;
            """))
            await conn.execute(text("""
                ALTER TABLE users ALTER COLUMN reputation_score SET NOT NULL;
            """))
            print("   ✅ Set NOT NULL constraints")
            
            # Add unique constraints for OAuth IDs
            try:
                await conn.execute(text("""
                    ALTER TABLE users ADD CONSTRAINT uq_users_google_id UNIQUE (google_id);
                """))
                print("   ✅ Added unique constraint for google_id")
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Constraint uq_users_google_id already exists")
                else:
                    raise
            
            try:
                await conn.execute(text("""
                    ALTER TABLE users ADD CONSTRAINT uq_users_facebook_id UNIQUE (facebook_id);
                """))
                print("   ✅ Added unique constraint for facebook_id")
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Constraint uq_users_facebook_id already exists")
                else:
                    raise
            
            try:
                await conn.execute(text("""
                    ALTER TABLE users ADD CONSTRAINT uq_users_linkedin_id UNIQUE (linkedin_id);
                """))
                print("   ✅ Added unique constraint for linkedin_id")
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Constraint uq_users_linkedin_id already exists")
                else:
                    raise
            
            # Create indexes
            try:
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_google_id ON users(google_id);
                """))
                print("   ✅ Created index ix_users_google_id")
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Index ix_users_google_id already exists")
            
            try:
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_facebook_id ON users(facebook_id);
                """))
                print("   ✅ Created index ix_users_facebook_id")
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Index ix_users_facebook_id already exists")
            
            try:
                await conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS ix_users_linkedin_id ON users(linkedin_id);
                """))
                print("   ✅ Created index ix_users_linkedin_id")
            except Exception as e:
                if "already exists" in str(e):
                    print("   ⚠️  Index ix_users_linkedin_id already exists")
        
        await engine.dispose()
        
        print("\n" + "=" * 60)
        print("✅ ALL MIGRATIONS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n🎉 Your Railway database is now up to date!")
        print("   Login should work now on your hosted website.")
        return True
        
    except Exception as e:
        print(f"\n❌ Error applying migrations: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(apply_migrations())
    sys.exit(0 if success else 1)
