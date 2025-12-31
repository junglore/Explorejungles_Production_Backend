"""
Create video series tables in the database
"""

import asyncio
from sqlalchemy import text
from app.db.database import get_db_session, engine
from app.models.video_series import VideoSeries, SeriesVideo


async def create_video_series_tables():
    """Create video series and series_videos tables"""
    
    create_video_series_table = """
    CREATE TABLE IF NOT EXISTS video_series (
        id UUID PRIMARY KEY,
        title VARCHAR(500) NOT NULL,
        subtitle VARCHAR(500),
        slug VARCHAR(255) NOT NULL UNIQUE,
        description TEXT,
        thumbnail_url VARCHAR(500),
        total_videos INTEGER DEFAULT 0 NOT NULL,
        total_views INTEGER DEFAULT 0 NOT NULL,
        is_published INTEGER DEFAULT 1 NOT NULL,
        created_by UUID REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS ix_video_series_slug ON video_series(slug);
    CREATE INDEX IF NOT EXISTS ix_video_series_published ON video_series(is_published, created_at);
    """
    
    create_series_videos_table = """
    CREATE TABLE IF NOT EXISTS series_videos (
        id UUID PRIMARY KEY,
        series_id UUID NOT NULL REFERENCES video_series(id) ON DELETE CASCADE,
        title VARCHAR(500) NOT NULL,
        subtitle VARCHAR(500),
        slug VARCHAR(255) NOT NULL,
        description TEXT,
        video_url VARCHAR(500) NOT NULL,
        thumbnail_url VARCHAR(500),
        duration INTEGER,
        position INTEGER NOT NULL,
        tags JSON DEFAULT '[]' NOT NULL,
        hashtags VARCHAR(500),
        views INTEGER DEFAULT 0 NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
    );
    
    CREATE INDEX IF NOT EXISTS ix_series_videos_series_position ON series_videos(series_id, position);
    CREATE INDEX IF NOT EXISTS ix_series_videos_slug ON series_videos(slug);
    """
    
    async with get_db_session() as session:
        try:
            # Create video_series table
            await session.execute(text(create_video_series_table))
            print("✅ Created video_series table")
            
            # Create series_videos table
            await session.execute(text(create_series_videos_table))
            print("✅ Created series_videos table")
            
            await session.commit()
            print("\n✅ All video series tables created successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ Error creating tables: {e}")
            raise


if __name__ == "__main__":
    print("Creating video series tables...")
    asyncio.run(create_video_series_tables())