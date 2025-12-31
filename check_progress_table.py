import asyncio
from sqlalchemy import inspect
from app.db.database import get_db_session, engine

async def check_table():
    # Check if table exists
    async with engine.begin() as conn:
        def check_tables(connection):
            inspector = inspect(connection)
            tables = inspector.get_table_names()
            print("All tables:", tables)
            
            if 'video_watch_progress' in tables:
                print("\n✓ video_watch_progress table exists")
                columns = inspector.get_columns('video_watch_progress')
                print("\nColumns:")
                for col in columns:
                    print(f"  - {col['name']}: {col['type']}")
            else:
                print("\n✗ video_watch_progress table does NOT exist")
                print("\nYou need to run: alembic revision --autogenerate -m 'add video watch progress'")
                print("Then: alembic upgrade head")
        
        await conn.run_sync(check_tables)

if __name__ == "__main__":
    asyncio.run(check_table())