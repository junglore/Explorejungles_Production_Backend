"""
Sync site settings from local database to Railway
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# Database URLs
LOCAL_DATABASE_URL = "postgresql+asyncpg://postgres:850redred@localhost:5432/Junglore_KE"
RAILWAY_DATABASE_URL = "postgresql+asyncpg://postgres:QONZYLRjVQtrDLnchpMHQMwxZnxKDzsV@caboose.proxy.rlwy.net:17005/railway"

async def sync_site_settings():
    print("=" * 80)
    print("SYNCING SITE SETTINGS FROM LOCAL TO RAILWAY")
    print("=" * 80)
    
    # Create engines
    local_engine = create_async_engine(LOCAL_DATABASE_URL, echo=False)
    railway_engine = create_async_engine(RAILWAY_DATABASE_URL, echo=False)
    
    try:
        # Fetch all settings from local
        async with local_engine.connect() as local_conn:
            result = await local_conn.execute(text("""
                SELECT id, key, value, data_type, category, label, description, is_public
                FROM site_settings
                ORDER BY category, key
            """))
            local_settings = result.fetchall()
            
        print(f"\n✅ Found {len(local_settings)} settings in LOCAL database\n")
        
        if not local_settings:
            print("⚠️  No settings found in local database!")
            return
        
        # Check existing settings in Railway
        async with railway_engine.connect() as railway_conn:
            result = await railway_conn.execute(text("""
                SELECT key FROM site_settings
            """))
            existing_keys = {row[0] for row in result.fetchall()}
            
        print(f"📊 Railway currently has {len(existing_keys)} settings\n")
        
        # Insert settings into Railway
        settings_added = 0
        settings_skipped = 0
        
        async with railway_engine.begin() as railway_conn:
            for setting in local_settings:
                setting_id, key, value, data_type, category, label, description, is_public = setting
                
                if key in existing_keys:
                    print(f"⏭️  Skipping existing: {key}")
                    settings_skipped += 1
                    continue
                
                # Insert the setting
                await railway_conn.execute(text("""
                    INSERT INTO site_settings (id, key, value, data_type, category, label, description, is_public, created_at, updated_at)
                    VALUES (:id, :key, :value, :data_type, :category, :label, :description, :is_public, NOW(), NOW())
                """), {
                    "id": setting_id,
                    "key": key,
                    "value": value,
                    "data_type": data_type,
                    "category": category,
                    "label": label,
                    "description": description,
                    "is_public": is_public or False
                })
                
                print(f"✅ Added: [{category}] {key} = {value[:50]}{'...' if len(value) > 50 else ''}")
                settings_added += 1
        
        print("\n" + "=" * 80)
        print("SYNC COMPLETE!")
        print("=" * 80)
        print(f"✅ Settings added to Railway: {settings_added}")
        print(f"⏭️  Settings already existed: {settings_skipped}")
        print(f"📊 Total settings in Railway: {settings_added + len(existing_keys)}")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await local_engine.dispose()
        await railway_engine.dispose()

if __name__ == "__main__":
    asyncio.run(sync_site_settings())
