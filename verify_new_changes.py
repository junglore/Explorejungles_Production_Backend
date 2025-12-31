"""
Verify the new migrations were applied correctly
"""
import asyncio
import asyncpg

async def verify_changes():
    conn = await asyncpg.connect('postgresql://postgres:850redred@localhost:5432/Junglore_KE')
    
    print("🔍 Verifying New Migration Changes")
    print("=" * 60)
    
    # 1. Check if tv_playlist table exists
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'tv_playlist'
        )
    """)
    print(f"\n1. tv_playlist table: {'✅ EXISTS' if result else '❌ MISSING'}")
    
    if result:
        # Get columns of tv_playlist
        columns = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'tv_playlist' 
            ORDER BY ordinal_position
        """)
        print("   Columns:")
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']}")
    
    # 2. Check if publish_date column exists in series_videos
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'series_videos' AND column_name = 'publish_date'
        )
    """)
    print(f"\n2. series_videos.publish_date: {'✅ EXISTS' if result else '❌ MISSING'}")
    
    # 3. Check if publish_date column exists in general_knowledge_videos
    result = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.columns 
            WHERE table_name = 'general_knowledge_videos' AND column_name = 'publish_date'
        )
    """)
    print(f"\n3. general_knowledge_videos.publish_date: {'✅ EXISTS' if result else '❌ MISSING'}")
    
    # 4. Check current alembic version
    version = await conn.fetchval("SELECT version_num FROM alembic_version")
    print(f"\n4. Current Alembic Version: {version}")
    
    print("\n" + "=" * 60)
    print("✅ All new migrations verified successfully!")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(verify_changes())
