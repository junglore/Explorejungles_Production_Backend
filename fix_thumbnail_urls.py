#!/usr/bin/env python3
"""
Fix thumbnail URLs in database - ensure all are relative paths
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db_session
from app.models.video_series import SeriesVideo
from app.models.video_channel import GeneralKnowledgeVideo
from app.models.media import Media
from sqlalchemy import text

async def fix_thumbnail_urls():
    """Fix thumbnail URLs to be relative paths without /uploads/ prefix"""

    async with get_db_session() as session:
        try:
            # Fix SeriesVideo thumbnails
            series_videos = await session.execute(
                text("SELECT id, thumbnail_url FROM series_videos WHERE thumbnail_url LIKE '/uploads/%'")
            )
            series_rows = series_videos.fetchall()

            for row in series_rows:
                video_id = row[0]
                old_url = row[1]
                # Remove /uploads/ prefix
                new_url = old_url.replace('/uploads/', '', 1) if old_url.startswith('/uploads/') else old_url

                await session.execute(
                    text("UPDATE series_videos SET thumbnail_url = :new_url WHERE id = :video_id"),
                    {"new_url": new_url, "video_id": video_id}
                )
                print(f"Fixed SeriesVideo {video_id}: {old_url} -> {new_url}")

            # Fix GeneralKnowledgeVideo thumbnails
            gk_videos = await session.execute(
                text("SELECT id, thumbnail_url FROM general_knowledge_videos WHERE thumbnail_url LIKE '/uploads/%'")
            )
            gk_rows = gk_videos.fetchall()

            for row in gk_rows:
                video_id = row[0]
                old_url = row[1]
                # Remove /uploads/ prefix
                new_url = old_url.replace('/uploads/', '', 1) if old_url.startswith('/uploads/') else old_url

                await session.execute(
                    text("UPDATE general_knowledge_videos SET thumbnail_url = :new_url WHERE id = :video_id"),
                    {"new_url": new_url, "video_id": video_id}
                )
                print(f"Fixed GeneralKnowledgeVideo {video_id}: {old_url} -> {new_url}")

            # Fix Media thumbnails
            media_items = await session.execute(
                text("SELECT id, thumbnail_url FROM media WHERE thumbnail_url LIKE '/uploads/%'")
            )
            media_rows = media_items.fetchall()

            for row in media_rows:
                media_id = row[0]
                old_url = row[1]
                # Remove /uploads/ prefix
                new_url = old_url.replace('/uploads/', '', 1) if old_url.startswith('/uploads/') else old_url

                await session.execute(
                    text("UPDATE media SET thumbnail_url = :new_url WHERE id = :media_id"),
                    {"new_url": new_url, "media_id": media_id}
                )
                print(f"Fixed Media {media_id}: {old_url} -> {new_url}")

            await session.commit()
            print("Thumbnail URL fix completed successfully!")

        except Exception as e:
            print(f"Error fixing thumbnail URLs: {e}")
            await session.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(fix_thumbnail_urls())