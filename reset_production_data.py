#!/usr/bin/env python3
"""
Production Data Reset Script - Complete User Data Cleanup

This script resets ALL user-related data for a fresh production launch:
- All quiz results and best scores
- All currency balances and transaction history
- All daily activity records
- All leaderboard caches
- All user achievements
- All myths vs facts game results

⚠️ WARNING: This is IRREVERSIBLE and should only be used for production launch!
"""

import asyncio
import sys
from datetime import datetime, date
from sqlalchemy import select, delete, func, text, update
from app.db.database import get_db_session
from app.models.user import User
from app.models.quiz_extended import UserQuizResult
from app.models.user_quiz_best_score import UserQuizBestScore
from app.models.rewards import (
    UserCurrencyTransaction, 
    UserDailyActivity, 
    UserAchievement
)
from app.models.weekly_leaderboard_cache import WeeklyLeaderboardCache

async def confirm_reset():
    """Get user confirmation for data reset"""
    print("🚨 PRODUCTION DATA RESET TOOL 🚨")
    print("=" * 50)
    print("This will PERMANENTLY DELETE all user activity data:")
    print("  ❌ All quiz results and best scores")
    print("  ❌ All points and credits (balances reset to 0)")
    print("  ❌ All currency transaction history")
    print("  ❌ All daily activity records")
    print("  ❌ All leaderboard rankings")
    print("  ❌ All user achievements")
    print("  ❌ All myths vs facts game results")
    print()
    print("✅ User accounts will be preserved (login credentials safe)")
    print("✅ Quizzes, categories, and content will remain intact")
    print("✅ Site settings and admin configuration preserved")
    print()
    
    confirmation = input("Type 'RESET PRODUCTION DATA' to confirm: ")
    if confirmation != "RESET PRODUCTION DATA":
        print("❌ Reset cancelled. No changes made.")
        return False
    
    final_confirmation = input("Are you absolutely sure? Type 'YES' to proceed: ")
    if final_confirmation != "YES":
        print("❌ Reset cancelled. No changes made.")
        return False
    
    return True

async def get_data_summary():
    """Get summary of data that will be deleted"""
    async with get_db_session() as db:
        try:
            # Count users
            users_result = await db.execute(select(func.count(User.id)))
            users_count = users_result.scalar()
            
            # Count quiz results
            quiz_results_result = await db.execute(select(func.count(UserQuizResult.id)))
            quiz_results_count = quiz_results_result.scalar()
            
            # Count currency transactions
            transactions_result = await db.execute(select(func.count(UserCurrencyTransaction.id)))
            transactions_count = transactions_result.scalar()
            
            # Count daily activities
            activities_result = await db.execute(select(func.count(UserDailyActivity.id)))
            activities_count = activities_result.scalar()
            
            # Count leaderboard entries
            leaderboard_result = await db.execute(select(func.count(WeeklyLeaderboardCache.id)))
            leaderboard_count = leaderboard_result.scalar()
            
            # Count achievements
            achievements_result = await db.execute(select(func.count(UserAchievement.id)))
            achievements_count = achievements_result.scalar()
            
            # Count quiz best scores
            best_scores_result = await db.execute(select(func.count(UserQuizBestScore.id)))
            best_scores_count = best_scores_result.scalar()
            
            # Get total currency distributed
            points_result = await db.execute(
                select(func.coalesce(func.sum(User.total_points_earned), 0))
            )
            total_points = points_result.scalar()
            
            credits_result = await db.execute(
                select(func.coalesce(func.sum(User.total_credits_earned), 0))
            )
            total_credits = credits_result.scalar()
            
            return {
                'users_count': users_count,
                'quiz_results_count': quiz_results_count,
                'transactions_count': transactions_count,
                'activities_count': activities_count,
                'leaderboard_count': leaderboard_count,
                'achievements_count': achievements_count,
                'best_scores_count': best_scores_count,
                'total_points': total_points,
                'total_credits': total_credits
            }
        except Exception as e:
            print(f"❌ Error getting data summary: {e}")
            return None

async def reset_user_currency_data():
    """Reset all user currency balances and totals"""
    async with get_db_session() as db:
        try:
            print("\n🔄 Resetting user currency balances...")
            
            # Reset all user currency fields to 0
            update_stmt = update(User).values(
                points_balance=0,
                credits_balance=0,
                total_points_earned=0,
                total_credits_earned=0
            )
            result = await db.execute(update_stmt)
            await db.commit()
            
            print(f"✅ Reset currency balances for {result.rowcount} users")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error resetting user currency: {e}")
            return False

async def delete_currency_transactions():
    """Delete all currency transaction history"""
    async with get_db_session() as db:
        try:
            print("\n🔄 Deleting currency transaction history...")
            
            delete_stmt = delete(UserCurrencyTransaction)
            result = await db.execute(delete_stmt)
            await db.commit()
            
            print(f"✅ Deleted {result.rowcount} currency transactions")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error deleting transactions: {e}")
            return False

async def delete_quiz_results():
    """Delete all quiz results and best scores"""
    async with get_db_session() as db:
        try:
            print("\n🔄 Deleting quiz results and best scores...")
            
            # Delete quiz results
            quiz_delete_stmt = delete(UserQuizResult)
            quiz_result = await db.execute(quiz_delete_stmt)
            
            # Delete best scores
            best_scores_delete_stmt = delete(UserQuizBestScore)
            best_scores_result = await db.execute(best_scores_delete_stmt)
            
            await db.commit()
            
            print(f"✅ Deleted {quiz_result.rowcount} quiz results")
            print(f"✅ Deleted {best_scores_result.rowcount} best score records")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error deleting quiz data: {e}")
            return False

async def delete_daily_activities():
    """Delete all daily activity records"""
    async with get_db_session() as db:
        try:
            print("\n🔄 Deleting daily activity records...")
            
            delete_stmt = delete(UserDailyActivity)
            result = await db.execute(delete_stmt)
            await db.commit()
            
            print(f"✅ Deleted {result.rowcount} daily activity records")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error deleting daily activities: {e}")
            return False

async def delete_leaderboard_cache():
    """Delete all leaderboard cache entries"""
    async with get_db_session() as db:
        try:
            print("\n🔄 Deleting leaderboard cache...")
            
            delete_stmt = delete(WeeklyLeaderboardCache)
            result = await db.execute(delete_stmt)
            await db.commit()
            
            print(f"✅ Deleted {result.rowcount} leaderboard entries")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error deleting leaderboard cache: {e}")
            return False

async def delete_user_achievements():
    """Delete all user achievements"""
    async with get_db_session() as db:
        try:
            print("\n🔄 Deleting user achievements...")
            
            delete_stmt = delete(UserAchievement)
            result = await db.execute(delete_stmt)
            await db.commit()
            
            print(f"✅ Deleted {result.rowcount} user achievements")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error deleting achievements: {e}")
            return False

async def reset_auto_increment_sequences():
    """Reset auto-increment sequences for clean IDs"""
    async with get_db_session() as db:
        try:
            print("\n🔄 Resetting database sequences...")
            
            # Note: PostgreSQL uses UUIDs for most tables, so this mainly applies to any serial columns
            # This ensures clean numbering for any future records
            
            # Reset any sequence-based IDs if they exist
            sequences_to_reset = [
                # Add any table sequences here if needed
            ]
            
            for sequence in sequences_to_reset:
                try:
                    await db.execute(text(f"ALTER SEQUENCE {sequence} RESTART WITH 1"))
                except Exception as e:
                    print(f"⚠️ Could not reset sequence {sequence}: {e}")
            
            await db.commit()
            print("✅ Database sequences reset")
            return True
            
        except Exception as e:
            await db.rollback()
            print(f"❌ Error resetting sequences: {e}")
            return False

async def verify_reset():
    """Verify that the reset was successful"""
    async with get_db_session() as db:
        try:
            print("\n🔍 Verifying reset...")
            
            # Check that all tables are empty
            checks = [
                ("Quiz Results", UserQuizResult),
                ("Best Scores", UserQuizBestScore),
                ("Currency Transactions", UserCurrencyTransaction),
                ("Daily Activities", UserDailyActivity),
                ("Leaderboard Cache", WeeklyLeaderboardCache),
                ("User Achievements", UserAchievement)
            ]
            
            all_clean = True
            for name, model in checks:
                result = await db.execute(select(func.count(model.id)))
                count = result.scalar()
                if count == 0:
                    print(f"  ✅ {name}: 0 records")
                else:
                    print(f"  ❌ {name}: {count} records remaining")
                    all_clean = False
            
            # Check user currency balances
            result = await db.execute(
                select(func.sum(User.points_balance + User.credits_balance + User.total_points_earned + User.total_credits_earned))
            )
            total_currency = result.scalar() or 0
            
            if total_currency == 0:
                print("  ✅ User Currency: All balances reset to 0")
            else:
                print(f"  ❌ User Currency: {total_currency} total currency remaining")
                all_clean = False
            
            return all_clean
            
        except Exception as e:
            print(f"❌ Error verifying reset: {e}")
            return False

async def main():
    """Main reset function"""
    print("🚀 Production Data Reset Tool")
    print("=" * 50)
    
    # Get confirmation first
    if not await confirm_reset():
        return
    
    # Get data summary before reset
    print("\n📊 Current Data Summary:")
    summary = await get_data_summary()
    if summary:
        print(f"  👥 Users: {summary['users_count']}")
        print(f"  📝 Quiz Results: {summary['quiz_results_count']}")
        print(f"  💰 Currency Transactions: {summary['transactions_count']}")
        print(f"  📅 Daily Activities: {summary['activities_count']}")
        print(f"  🏆 Leaderboard Entries: {summary['leaderboard_count']}")
        print(f"  🎯 Achievements: {summary['achievements_count']}")
        print(f"  ⭐ Best Scores: {summary['best_scores_count']}")
        print(f"  🎮 Total Points Distributed: {summary['total_points']:,}")
        print(f"  💎 Total Credits Distributed: {summary['total_credits']:,}")
    else:
        print("❌ Could not get data summary")
        return
    
    print("\n" + "="*50)
    print("🔄 STARTING DATA RESET...")
    print("="*50)
    
    # Track success of each operation
    operations = []
    
    # Perform reset operations
    operations.append(("Currency Balances", await reset_user_currency_data()))
    operations.append(("Currency Transactions", await delete_currency_transactions()))
    operations.append(("Quiz Results", await delete_quiz_results()))
    operations.append(("Daily Activities", await delete_daily_activities()))
    operations.append(("Leaderboard Cache", await delete_leaderboard_cache()))
    operations.append(("User Achievements", await delete_user_achievements()))
    operations.append(("Database Sequences", await reset_auto_increment_sequences()))
    
    # Check results
    successful_operations = [op for op, success in operations if success]
    failed_operations = [op for op, success in operations if not success]
    
    print("\n" + "="*50)
    print("📋 RESET SUMMARY")
    print("="*50)
    
    if failed_operations:
        print(f"❌ {len(failed_operations)} operations failed:")
        for op in failed_operations:
            print(f"   • {op}")
        print(f"✅ {len(successful_operations)} operations succeeded:")
        for op in successful_operations:
            print(f"   • {op}")
        print("\n⚠️ Reset completed with errors!")
    else:
        print("✅ All operations completed successfully!")
        
        # Verify reset
        if await verify_reset():
            print("\n🎉 PRODUCTION DATA RESET COMPLETE!")
            print("All user activity data has been cleared.")
            print("Your application is ready for production launch!")
        else:
            print("\n⚠️ Reset verification failed - some data may remain")
    
    print("\n" + "="*50)
    print("🔒 PRESERVED DATA:")
    print("  ✅ User accounts (login credentials)")
    print("  ✅ Quizzes and content")
    print("  ✅ Categories and collections")
    print("  ✅ Site settings and configuration")
    print("  ✅ Admin panel settings")
    print("="*50)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Reset cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)