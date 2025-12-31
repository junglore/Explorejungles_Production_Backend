"""
Background Jobs System for Leaderboard Maintenance
Handles automated cache updates, weekly resets, and data maintenance
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, text, select, delete
from contextlib import asynccontextmanager

from app.db.database import get_db_session
from app.models.user import User
from app.models.quiz_extended import UserQuizResult
from app.models.user_quiz_best_score import UserQuizBestScore
from app.models.weekly_leaderboard_cache import WeeklyLeaderboardCache
from app.utils.date_utils import get_current_week_start, get_current_month_start

logger = logging.getLogger(__name__)

class LeaderboardJobManager:
    """Manages background jobs for leaderboard maintenance"""
    
    def __init__(self):
        self.is_running = False
        self.tasks = []

    async def start(self):
        """Start all background jobs"""
        if self.is_running:
            logger.warning("LeaderboardJobManager is already running")
            return
        
        self.is_running = True
        logger.info("Starting LeaderboardJobManager...")
        
        # Start all periodic tasks
        self.tasks = [
            asyncio.create_task(self._periodic_cache_refresh()),
            asyncio.create_task(self._periodic_weekly_reset()),
            asyncio.create_task(self._periodic_monthly_reset()),
            asyncio.create_task(self._periodic_cleanup()),
        ]
        
        logger.info("LeaderboardJobManager started successfully")

    async def stop(self):
        """Stop all background jobs"""
        if not self.is_running:
            return
        
        logger.info("Stopping LeaderboardJobManager...")
        self.is_running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.cancelled():
                task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.tasks.clear()
        
        logger.info("LeaderboardJobManager stopped")

    async def _periodic_cache_refresh(self):
        """Refresh leaderboard caches every 30 minutes"""
        while self.is_running:
            try:
                logger.info("Starting periodic cache refresh...")
                await self.refresh_all_caches()
                logger.info("Periodic cache refresh completed")
                
                # Wait 30 minutes
                await asyncio.sleep(30 * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cache refresh: {e}")
                await asyncio.sleep(5 * 60)  # Wait 5 minutes on error

    async def _periodic_weekly_reset(self):
        """Check for weekly resets every hour"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                # Check if it's Monday at 00:00 UTC (start of new week)
                if current_time.weekday() == 0 and current_time.hour == 0 and current_time.minute < 5:
                    logger.info("Starting weekly leaderboard reset...")
                    await self.reset_weekly_leaderboards()
                    logger.info("Weekly leaderboard reset completed")
                
                # Wait 1 hour
                await asyncio.sleep(60 * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic weekly reset: {e}")
                await asyncio.sleep(10 * 60)  # Wait 10 minutes on error

    async def _periodic_monthly_reset(self):
        """Check for monthly resets every day at 1 AM"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                # Check if it's the 1st day of the month at 1 AM
                if current_time.day == 1 and current_time.hour == 1 and current_time.minute < 5:
                    logger.info("Starting monthly leaderboard reset...")
                    await self.reset_monthly_leaderboards()
                    logger.info("Monthly leaderboard reset completed")
                
                # Wait 24 hours
                await asyncio.sleep(24 * 60 * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic monthly reset: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour on error

    async def _periodic_cleanup(self):
        """Clean up old data every day at 2 AM"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                if current_time.hour == 2 and current_time.minute < 5:
                    logger.info("Starting periodic cleanup...")
                    await self.cleanup_old_data()
                    logger.info("Periodic cleanup completed")
                
                # Wait 24 hours
                await asyncio.sleep(24 * 60 * 60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(60 * 60)  # Wait 1 hour on error

    @asynccontextmanager
    async def get_db_session(self):
        """Get async database session"""
        async with get_db_session() as db:
            yield db

    async def refresh_all_caches(self):
        """Refresh all leaderboard caches"""
        async with self.get_db_session() as db:
            await self.refresh_weekly_cache(db)
            await self.refresh_monthly_cache(db)
            logger.info("All leaderboard caches refreshed")

    async def refresh_weekly_cache(self, db: AsyncSession):
        """Refresh weekly leaderboard cache"""
        try:
            logger.info("Refreshing weekly leaderboard cache...")
            
            current_week_start = get_current_week_start()
            week_end = current_week_start + timedelta(days=6)
            week_number = current_week_start.isocalendar()[1]
            year = current_week_start.isocalendar()[0]
            
            # Delete existing cache for current week
            delete_stmt = delete(WeeklyLeaderboardCache).where(
                WeeklyLeaderboardCache.week_start_date == current_week_start
            )
            await db.execute(delete_stmt)
            
            # Calculate weekly rankings using async session
            stmt = select(
                UserQuizResult.user_id,
                func.sum(UserQuizResult.credits_earned).label('total_credits'),
                func.count(UserQuizResult.id).label('quizzes_completed'),
                func.avg(UserQuizResult.percentage).label('average_score')
            ).select_from(
                UserQuizResult.__table__.join(User.__table__, UserQuizResult.user_id == User.id)
            ).where(
                UserQuizResult.completed_at >= current_week_start
            ).where(
                UserQuizResult.completed_at < week_end
            ).group_by(
                UserQuizResult.user_id
            ).order_by(
                func.sum(UserQuizResult.credits_earned).desc()
            )
            
            result = await db.execute(stmt)
            weekly_rankings = result.fetchall()
            
            # Insert new cache entries
            cache_entries = []
            for rank, ranking in enumerate(weekly_rankings, start=1):
                cache_entry = WeeklyLeaderboardCache(
                    user_id=ranking.user_id,
                    week_start_date=current_week_start,
                    week_end_date=week_end,
                    week_number=week_number,
                    year=year,
                    credits_rank=rank,
                    total_credits_earned=int(ranking.total_credits or 0),
                    quizzes_completed=ranking.quizzes_completed,
                    average_percentage=round(float(ranking.average_score or 0), 1),
                    last_calculated_at=datetime.utcnow()
                )
                cache_entries.append(cache_entry)
            
            if cache_entries:
                db.add_all(cache_entries)
                await db.commit()
                logger.info(f"Weekly cache refreshed with {len(cache_entries)} entries")
            else:
                logger.info("No weekly data to cache")
                
        except Exception as e:
            logger.error(f"Error refreshing weekly cache: {e}")
            await db.rollback()
            raise

    async def refresh_monthly_cache(self, db: AsyncSession):
        """Monthly cache functionality disabled - using real-time calculations"""
        try:
            logger.info("Monthly leaderboard cache disabled, using real-time calculations")
            # Skip monthly cache processing
            pass
                
        except Exception as e:
            logger.error(f"Error refreshing monthly cache: {e}")
            await db.rollback()
            raise

    async def reset_weekly_leaderboards(self):
        """Reset weekly leaderboards (archive old data and start fresh)"""
        async with self.get_db_session() as db:
            try:
                logger.info("Resetting weekly leaderboards...")
                
                # Archive old weekly cache (keep for historical purposes)
                last_week_start = get_current_week_start() - timedelta(days=7)
                
                # Count old entries for archival
                count_stmt = select(func.count()).select_from(WeeklyLeaderboardCache).where(
                    WeeklyLeaderboardCache.week_start_date == last_week_start
                )
                result = await db.execute(count_stmt)
                archived_count = result.scalar()
                
                if archived_count > 0:
                    logger.info(f"Archived {archived_count} weekly leaderboard entries")
                
                # Refresh cache for new week
                await self.refresh_weekly_cache(db)
                
                logger.info("Weekly leaderboard reset completed")
                
            except Exception as e:
                logger.error(f"Error resetting weekly leaderboards: {e}")
                raise

    async def reset_monthly_leaderboards(self):
        """Reset monthly leaderboards"""
        async with self.get_db_session() as db:
            try:
                logger.info("Resetting monthly leaderboards...")
                
                # Monthly cache functionality disabled
                # Archive old monthly cache
                # last_month_start = get_current_month_start() - timedelta(days=32)
                # last_month_start = last_month_start.replace(day=1)
                
                # archived_count = db.query(MonthlyLeaderboardCache)\
                #     .filter(MonthlyLeaderboardCache.month_start == last_month_start)\
                #     .count()
                
                # if archived_count > 0:
                #     logger.info(f"Archived {archived_count} monthly leaderboard entries")
                
                # Refresh cache for new month
                await self.refresh_monthly_cache(db)
                
                logger.info("Monthly leaderboard reset completed")
                
            except Exception as e:
                logger.error(f"Error resetting monthly leaderboards: {e}")
                raise

    async def cleanup_old_data(self):
        """Clean up old leaderboard data"""
        async with self.get_db_session() as db:
            try:
                logger.info("Starting leaderboard data cleanup...")
                
                # Keep last 12 weeks of weekly cache
                cutoff_week = get_current_week_start() - timedelta(weeks=12)
                
                # Count entries to delete
                count_stmt = select(func.count()).select_from(WeeklyLeaderboardCache).where(
                    WeeklyLeaderboardCache.week_start < cutoff_week
                )
                result = await db.execute(count_stmt)
                deleted_weekly = result.scalar()
                
                if deleted_weekly > 0:
                    delete_stmt = delete(WeeklyLeaderboardCache).where(
                        WeeklyLeaderboardCache.week_start < cutoff_week
                    )
                    await db.execute(delete_stmt)
                    logger.info(f"Deleted {deleted_weekly} old weekly cache entries")
                
                # Monthly cache functionality disabled
                
                # Optimize database tables
                await db.execute(text("VACUUM ANALYZE weekly_leaderboard_cache"))
                
                await db.commit()
                logger.info("Leaderboard data cleanup completed")
                
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")
                await db.rollback()
                raise

    async def force_refresh(self, leaderboard_type: Optional[str] = None):
        """Force refresh of specific or all leaderboard caches"""
        async with self.get_db_session() as db:
            try:
                if leaderboard_type == 'weekly' or leaderboard_type is None:
                    await self.refresh_weekly_cache(db)
                
                if leaderboard_type == 'monthly' or leaderboard_type is None:
                    await self.refresh_monthly_cache(db)
                
                logger.info(f"Force refresh completed for {leaderboard_type or 'all'} leaderboards")
                
            except Exception as e:
                logger.error(f"Error in force refresh: {e}")
                raise

# Global job manager instance
job_manager = LeaderboardJobManager()