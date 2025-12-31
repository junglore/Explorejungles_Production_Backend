"""
Quick check to verify the 4 missing tables now exist
"""
import asyncio
import asyncpg

async def check_tables():
    conn = await asyncpg.connect('postgresql://postgres:850redred@localhost:5432/Junglore_KE')
    
    tables = await conn.fetch("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' 
        AND table_name IN ('video_channels', 'general_knowledge_videos', 'national_parks', 'temp_user_registrations')
        ORDER BY table_name
    """)
    
    print("Checking for missing tables:")
    print("=" * 50)
    
    expected = ['general_knowledge_videos', 'national_parks', 'temp_user_registrations', 'video_channels']
    found = [row['table_name'] for row in tables]
    
    for table in expected:
        if table in found:
            print(f"✅ {table}")
        else:
            print(f"❌ {table}")
    
    print(f"\nTotal found: {len(found)}/4")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_tables())
