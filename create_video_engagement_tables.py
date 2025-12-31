"""
Create video engagement tables (likes, comments)
"""

import asyncio
import asyncpg
from app.core.config import settings


async def create_engagement_tables():
    """Create video likes, comments, and comment likes tables"""
    
    conn = await asyncpg.connect(settings.DATABASE_URL)
    
    try:
        print("Creating video engagement tables...")
        
        # Create video_likes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS video_likes (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                video_slug VARCHAR(255) NOT NULL,
                video_type VARCHAR(50) NOT NULL,
                vote INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT uq_user_video_like UNIQUE (user_id, video_slug)
            );
        """)
        print("✓ Created video_likes table")
        
        # Create indexes for video_likes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_video_likes_user_video 
            ON video_likes (user_id, video_slug);
        """)
        
        # Create video_comments table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS video_comments (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                video_slug VARCHAR(255) NOT NULL,
                video_type VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                parent_id UUID REFERENCES video_comments(id) ON DELETE CASCADE,
                likes_count INTEGER DEFAULT 0 NOT NULL,
                replies_count INTEGER DEFAULT 0 NOT NULL,
                is_edited INTEGER DEFAULT 0 NOT NULL,
                is_deleted INTEGER DEFAULT 0 NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        print("✓ Created video_comments table")
        
        # Create indexes for video_comments
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_video_comments_video 
            ON video_comments (video_slug, created_at);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_video_comments_user 
            ON video_comments (user_id, created_at);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_video_comments_parent 
            ON video_comments (parent_id);
        """)
        
        # Create video_comment_likes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS video_comment_likes (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                comment_id UUID NOT NULL REFERENCES video_comments(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                CONSTRAINT uq_user_comment_like UNIQUE (user_id, comment_id)
            );
        """)
        print("✓ Created video_comment_likes table")
        
        # Create indexes for video_comment_likes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_video_comment_likes_user_comment 
            ON video_comment_likes (user_id, comment_id);
        """)
        
        print("\n✅ All video engagement tables created successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(create_engagement_tables())