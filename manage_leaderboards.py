#!/usr/bin/env python3
"""
Leaderboard Management CLI
Provides command-line tools for managing leaderboard operations
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.leaderboard_jobs import job_manager
from app.core.database import get_db
from app.models.leaderboard import WeeklyLeaderboardCache, MonthlyLeaderboardCache
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def refresh_caches(leaderboard_type=None):
    """Refresh leaderboard caches"""
    try:
        print(f"Refreshing {leaderboard_type or 'all'} leaderboard caches...")
        await job_manager.force_refresh(leaderboard_type)
        print(f"✅ Successfully refreshed {leaderboard_type or 'all'} leaderboard caches")
    except Exception as e:
        print(f"❌ Error refreshing caches: {e}")
        return False
    return True

async def reset_weekly():
    """Reset weekly leaderboards"""
    try:
        print("Resetting weekly leaderboards...")
        await job_manager.reset_weekly_leaderboards()
        print("✅ Successfully reset weekly leaderboards")
    except Exception as e:
        print(f"❌ Error resetting weekly leaderboards: {e}")
        return False
    return True

async def reset_monthly():
    """Reset monthly leaderboards"""
    try:
        print("Resetting monthly leaderboards...")
        await job_manager.reset_monthly_leaderboards()
        print("✅ Successfully reset monthly leaderboards")
    except Exception as e:
        print(f"❌ Error resetting monthly leaderboards: {e}")
        return False
    return True

async def cleanup_old_data():
    """Cleanup old leaderboard data"""
    try:
        print("Cleaning up old leaderboard data...")
        await job_manager.cleanup_old_data()
        print("✅ Successfully cleaned up old data")
    except Exception as e:
        print(f"❌ Error cleaning up data: {e}")
        return False
    return True

async def show_status():
    """Show leaderboard system status"""
    try:
        db = next(get_db())
        
        # Get cache statistics
        weekly_count = db.query(WeeklyLeaderboardCache).count()
        monthly_count = db.query(MonthlyLeaderboardCache).count()
        
        # Get latest update times
        latest_weekly = db.query(WeeklyLeaderboardCache.last_updated)\
            .order_by(WeeklyLeaderboardCache.last_updated.desc())\
            .first()
        
        latest_monthly = db.query(MonthlyLeaderboardCache.last_updated)\
            .order_by(MonthlyLeaderboardCache.last_updated.desc())\
            .first()
        
        print("\n📊 Leaderboard System Status")
        print("=" * 40)
        print(f"Job Manager Running: {'✅ Yes' if job_manager.is_running else '❌ No'}")
        print(f"Active Background Tasks: {len(job_manager.tasks)}")
        print(f"Weekly Cache Entries: {weekly_count}")
        print(f"Monthly Cache Entries: {monthly_count}")
        
        if latest_weekly:
            print(f"Latest Weekly Update: {latest_weekly[0]}")
        else:
            print("Latest Weekly Update: Never")
            
        if latest_monthly:
            print(f"Latest Monthly Update: {latest_monthly[0]}")
        else:
            print("Latest Monthly Update: Never")
        
        print(f"Status Check Time: {datetime.utcnow()}")
        print()
        
    except Exception as e:
        print(f"❌ Error getting status: {e}")
        return False
    return True

async def start_jobs():
    """Start background jobs"""
    try:
        if job_manager.is_running:
            print("ℹ️  Background jobs are already running")
            return True
        
        print("Starting background jobs...")
        await job_manager.start()
        print("✅ Background jobs started successfully")
    except Exception as e:
        print(f"❌ Error starting jobs: {e}")
        return False
    return True

async def stop_jobs():
    """Stop background jobs"""
    try:
        if not job_manager.is_running:
            print("ℹ️  Background jobs are already stopped")
            return True
        
        print("Stopping background jobs...")
        await job_manager.stop()
        print("✅ Background jobs stopped successfully")
    except Exception as e:
        print(f"❌ Error stopping jobs: {e}")
        return False
    return True

async def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(
        description="Leaderboard Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_leaderboards.py refresh --type weekly
  python manage_leaderboards.py refresh --type monthly
  python manage_leaderboards.py refresh  # Refresh all
  python manage_leaderboards.py reset-weekly
  python manage_leaderboards.py reset-monthly
  python manage_leaderboards.py cleanup
  python manage_leaderboards.py status
  python manage_leaderboards.py start-jobs
  python manage_leaderboards.py stop-jobs
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Refresh command
    refresh_parser = subparsers.add_parser('refresh', help='Refresh leaderboard caches')
    refresh_parser.add_argument('--type', choices=['weekly', 'monthly'], 
                               help='Type of leaderboard to refresh (default: all)')
    
    # Reset commands
    subparsers.add_parser('reset-weekly', help='Reset weekly leaderboards')
    subparsers.add_parser('reset-monthly', help='Reset monthly leaderboards')
    
    # Other commands
    subparsers.add_parser('cleanup', help='Cleanup old leaderboard data')
    subparsers.add_parser('status', help='Show leaderboard system status')
    subparsers.add_parser('start-jobs', help='Start background jobs')
    subparsers.add_parser('stop-jobs', help='Stop background jobs')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    success = True
    
    try:
        if args.command == 'refresh':
            success = await refresh_caches(args.type)
        elif args.command == 'reset-weekly':
            success = await reset_weekly()
        elif args.command == 'reset-monthly':
            success = await reset_monthly()
        elif args.command == 'cleanup':
            success = await cleanup_old_data()
        elif args.command == 'status':
            success = await show_status()
        elif args.command == 'start-jobs':
            success = await start_jobs()
        elif args.command == 'stop-jobs':
            success = await stop_jobs()
        else:
            print(f"❌ Unknown command: {args.command}")
            success = False
    
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
        success = False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        success = False
    finally:
        # Always try to stop the job manager cleanly
        if job_manager.is_running:
            try:
                await job_manager.stop()
            except:
                pass
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())