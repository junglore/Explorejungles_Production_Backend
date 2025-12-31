"""
Analytics service for tracking user behavior and system metrics
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from app.db.database import get_db_session
from app.models.content import Content
from app.models.media import Media
from app.models.user import User
from app.core.cache import cache_manager
import structlog
import json

logger = structlog.get_logger()

class AnalyticsService:
    """Analytics service for tracking and reporting"""
    
    def __init__(self):
        self.metrics_cache_ttl = 300  # 5 minutes
        self.daily_cache_ttl = 3600   # 1 hour
        self.weekly_cache_ttl = 7200  # 2 hours
    
    async def track_page_view(
        self,
        content_id: str,
        user_id: Optional[str] = None,
        ip_address: str = "",
        user_agent: str = "",
        referrer: str = ""
    ):
        """Track page view for content"""
        
        try:
            async with get_db_session() as db:
                # Update view count
                await db.execute(
                    text("UPDATE content SET view_count = view_count + 1 WHERE id = :content_id"),
                    {"content_id": content_id}
                )
                await db.commit()
                
                # Store detailed analytics (in production, use a separate analytics table)
                analytics_data = {
                    "event": "page_view",
                    "content_id": content_id,
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "referrer": referrer,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Cache recent views for real-time analytics
                cache_key = f"analytics:recent_views:{datetime.now().strftime('%Y%m%d%H')}"
                recent_views = await cache_manager.get(cache_key) or []
                recent_views.append(analytics_data)
                
                # Keep only last 1000 views per hour
                if len(recent_views) > 1000:
                    recent_views = recent_views[-1000:]
                
                await cache_manager.set(cache_key, recent_views, ttl=3600)
                
                logger.info("Page view tracked", content_id=content_id, user_id=user_id)
                
        except Exception as e:
            logger.error(f"Failed to track page view: {e}")
    
    async def track_media_interaction(
        self,
        media_id: str,
        interaction_type: str,  # view, download, share
        user_id: Optional[str] = None,
        ip_address: str = ""
    ):
        """Track media interactions"""
        
        try:
            analytics_data = {
                "event": "media_interaction",
                "media_id": media_id,
                "interaction_type": interaction_type,
                "user_id": user_id,
                "ip_address": ip_address,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Cache for real-time analytics
            cache_key = f"analytics:media_interactions:{datetime.now().strftime('%Y%m%d')}"
            interactions = await cache_manager.get(cache_key) or []
            interactions.append(analytics_data)
            
            await cache_manager.set(cache_key, interactions, ttl=86400)  # 24 hours
            
            logger.info("Media interaction tracked", 
                       media_id=media_id, 
                       interaction_type=interaction_type, 
                       user_id=user_id)
                       
        except Exception as e:
            logger.error(f"Failed to track media interaction: {e}")
    
    async def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics"""
        
        cache_key = "analytics:dashboard_metrics"
        cached_metrics = await cache_manager.get(cache_key)
        
        if cached_metrics:
            return cached_metrics
        
        try:
            async with get_db_session() as db:
                # Content metrics
                total_content = await db.execute(select(func.count(Content.id)))
                published_content = await db.execute(
                    select(func.count(Content.id)).where(Content.status == 'PUBLISHED')
                )
                
                # Media metrics
                total_media = await db.execute(select(func.count(Media.id)))
                total_media_size = await db.execute(select(func.sum(Media.file_size)))
                
                # User metrics
                total_users = await db.execute(select(func.count(User.id)))
                active_users = await db.execute(
                    select(func.count(User.id)).where(User.is_active == True)
                )
                
                # Popular content (last 30 days)
                thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
                popular_content = await db.execute(
                    select(Content.title, Content.view_count, Content.slug)
                    .where(and_(
                        Content.status == 'PUBLISHED',
                        Content.created_at >= thirty_days_ago
                    ))
                    .order_by(desc(Content.view_count))
                    .limit(10)
                )
                
                # Recent activity
                recent_content = await db.execute(
                    select(Content.title, Content.created_at, Content.type)
                    .where(Content.status == 'PUBLISHED')
                    .order_by(desc(Content.created_at))
                    .limit(5)
                )
                
                metrics = {
                    "content": {
                        "total": total_content.scalar() or 0,
                        "published": published_content.scalar() or 0,
                        "draft": (total_content.scalar() or 0) - (published_content.scalar() or 0)
                    },
                    "media": {
                        "total_files": total_media.scalar() or 0,
                        "total_size_bytes": total_media_size.scalar() or 0,
                        "total_size_mb": round((total_media_size.scalar() or 0) / (1024 * 1024), 2)
                    },
                    "users": {
                        "total": total_users.scalar() or 0,
                        "active": active_users.scalar() or 0
                    },
                    "popular_content": [
                        {
                            "title": row[0],
                            "views": row[1],
                            "slug": row[2]
                        }
                        for row in popular_content.fetchall()
                    ],
                    "recent_activity": [
                        {
                            "title": row[0],
                            "created_at": row[1].isoformat() if row[1] else None,
                            "type": row[2]
                        }
                        for row in recent_content.fetchall()
                    ],
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Cache for 5 minutes
                await cache_manager.set(cache_key, metrics, ttl=self.metrics_cache_ttl)
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_content_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get content analytics for specified period"""
        
        cache_key = f"analytics:content:{days}days"
        cached_analytics = await cache_manager.get(cache_key)
        
        if cached_analytics:
            return cached_analytics
        
        try:
            async with get_db_session() as db:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Content creation over time
                content_by_day = await db.execute(
                    select(
                        func.date(Content.created_at).label('date'),
                        func.count(Content.id).label('count')
                    )
                    .where(Content.created_at >= start_date)
                    .group_by(func.date(Content.created_at))
                    .order_by(func.date(Content.created_at))
                )
                
                # Content by type
                content_by_type = await db.execute(
                    select(
                        Content.type,
                        func.count(Content.id).label('count')
                    )
                    .where(Content.created_at >= start_date)
                    .group_by(Content.type)
                )
                
                # Most viewed content
                most_viewed = await db.execute(
                    select(
                        Content.title,
                        Content.view_count,
                        Content.slug,
                        Content.type
                    )
                    .where(and_(
                        Content.status == 'PUBLISHED',
                        Content.created_at >= start_date
                    ))
                    .order_by(desc(Content.view_count))
                    .limit(20)
                )
                
                # Content performance metrics
                avg_views = await db.execute(
                    select(func.avg(Content.view_count))
                    .where(and_(
                        Content.status == 'PUBLISHED',
                        Content.created_at >= start_date
                    ))
                )
                
                total_views = await db.execute(
                    select(func.sum(Content.view_count))
                    .where(and_(
                        Content.status == 'PUBLISHED',
                        Content.created_at >= start_date
                    ))
                )
                
                analytics = {
                    "period": {
                        "days": days,
                        "start_date": start_date.isoformat(),
                        "end_date": datetime.now(timezone.utc).isoformat()
                    },
                    "content_creation": [
                        {
                            "date": str(row[0]),
                            "count": row[1]
                        }
                        for row in content_by_day.fetchall()
                    ],
                    "content_by_type": [
                        {
                            "type": row[0],
                            "count": row[1]
                        }
                        for row in content_by_type.fetchall()
                    ],
                    "most_viewed": [
                        {
                            "title": row[0],
                            "views": row[1],
                            "slug": row[2],
                            "type": row[3]
                        }
                        for row in most_viewed.fetchall()
                    ],
                    "performance": {
                        "average_views": round(avg_views.scalar() or 0, 2),
                        "total_views": total_views.scalar() or 0
                    },
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Cache based on period
                cache_ttl = self.daily_cache_ttl if days <= 7 else self.weekly_cache_ttl
                await cache_manager.set(cache_key, analytics, ttl=cache_ttl)
                
                return analytics
                
        except Exception as e:
            logger.error(f"Failed to get content analytics: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_media_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get media analytics for specified period"""
        
        cache_key = f"analytics:media:{days}days"
        cached_analytics = await cache_manager.get(cache_key)
        
        if cached_analytics:
            return cached_analytics
        
        try:
            async with get_db_session() as db:
                start_date = datetime.now(timezone.utc) - timedelta(days=days)
                
                # Media uploads over time
                uploads_by_day = await db.execute(
                    select(
                        func.date(Media.created_at).label('date'),
                        func.count(Media.id).label('count'),
                        func.sum(Media.file_size).label('total_size')
                    )
                    .where(Media.created_at >= start_date)
                    .group_by(func.date(Media.created_at))
                    .order_by(func.date(Media.created_at))
                )
                
                # Media by type
                media_by_type = await db.execute(
                    select(
                        Media.media_type,
                        func.count(Media.id).label('count'),
                        func.sum(Media.file_size).label('total_size')
                    )
                    .where(Media.created_at >= start_date)
                    .group_by(Media.media_type)
                )
                
                # Storage usage
                total_storage = await db.execute(
                    select(func.sum(Media.file_size))
                    .where(Media.created_at >= start_date)
                )
                
                analytics = {
                    "period": {
                        "days": days,
                        "start_date": start_date.isoformat(),
                        "end_date": datetime.now(timezone.utc).isoformat()
                    },
                    "uploads_by_day": [
                        {
                            "date": str(row[0]),
                            "count": row[1],
                            "total_size_mb": round((row[2] or 0) / (1024 * 1024), 2)
                        }
                        for row in uploads_by_day.fetchall()
                    ],
                    "media_by_type": [
                        {
                            "type": row[0],
                            "count": row[1],
                            "total_size_mb": round((row[2] or 0) / (1024 * 1024), 2)
                        }
                        for row in media_by_type.fetchall()
                    ],
                    "storage": {
                        "total_bytes": total_storage.scalar() or 0,
                        "total_mb": round((total_storage.scalar() or 0) / (1024 * 1024), 2),
                        "total_gb": round((total_storage.scalar() or 0) / (1024 * 1024 * 1024), 2)
                    },
                    "generated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Cache based on period
                cache_ttl = self.daily_cache_ttl if days <= 7 else self.weekly_cache_ttl
                await cache_manager.set(cache_key, analytics, ttl=cache_ttl)
                
                return analytics
                
        except Exception as e:
            logger.error(f"Failed to get media analytics: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time metrics from cache"""
        
        try:
            current_hour = datetime.now().strftime('%Y%m%d%H')
            
            # Recent page views
            recent_views_key = f"analytics:recent_views:{current_hour}"
            recent_views = await cache_manager.get(recent_views_key) or []
            
            # Recent media interactions
            today = datetime.now().strftime('%Y%m%d')
            media_interactions_key = f"analytics:media_interactions:{today}"
            media_interactions = await cache_manager.get(media_interactions_key) or []
            
            # Calculate metrics
            unique_visitors = len(set(
                view.get('ip_address', '') for view in recent_views
                if view.get('ip_address')
            ))
            
            page_views_last_hour = len(recent_views)
            media_interactions_today = len(media_interactions)
            
            return {
                "current_hour": current_hour,
                "page_views_last_hour": page_views_last_hour,
                "unique_visitors_last_hour": unique_visitors,
                "media_interactions_today": media_interactions_today,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get real-time metrics: {e}")
            return {
                "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat()
            }

# Global analytics service instance
analytics_service = AnalyticsService()