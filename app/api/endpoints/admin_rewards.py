"""
Admin endpoints for monitoring and managing the rewards system
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta

from app.db.database import get_db
from app.models.user import User
from app.models.site_setting import SiteSetting
from app.models.rewards import (
    UserCurrencyTransaction,
    AntiGamingTracking,
    UserDailyActivity,
    LeaderboardEntry,
    UserAchievement,
    RewardsConfiguration
)
from app.core.security import get_current_user
from app.services.anti_gaming_service import anti_gaming_service
from app.services.currency_service import currency_service
from app.services.leaderboard_service import leaderboard_service

router = APIRouter()


@router.get("/dashboard")
async def get_rewards_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get rewards system dashboard data (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get key metrics
        today = datetime.now(timezone.utc).date()
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Total transactions
        total_transactions = await db.execute(
            select(func.count(UserCurrencyTransaction.id))
        )
        
        # Transactions today
        transactions_today = await db.execute(
            select(func.count(UserCurrencyTransaction.id))
            .where(func.date(UserCurrencyTransaction.created_at) == today)
        )
        
        # Total points distributed
        total_points = await db.execute(
            select(func.sum(UserCurrencyTransaction.amount))
            .where(and_(
                UserCurrencyTransaction.transaction_type == "EARN",
                UserCurrencyTransaction.currency_type == "POINTS"
            ))
        )
        
        # Total credits distributed
        total_credits = await db.execute(
            select(func.sum(UserCurrencyTransaction.amount))
            .where(and_(
                UserCurrencyTransaction.transaction_type == "EARN",
                UserCurrencyTransaction.currency_type == "CREDITS"
            ))
        )
        
        # Flagged activities
        flagged_activities = await db.execute(
            select(func.count(AntiGamingTracking.id))
            .where(and_(
                AntiGamingTracking.is_flagged == True,
                AntiGamingTracking.created_at >= week_ago
            ))
        )
        
        # Active users (last 7 days)
        active_users = await db.execute(
            select(func.count(func.distinct(UserDailyActivity.user_id)))
            .where(UserDailyActivity.activity_date >= week_ago.date())
        )
        
        return {
            "total_transactions": total_transactions.scalar() or 0,
            "transactions_today": transactions_today.scalar() or 0,
            "total_points_distributed": total_points.scalar() or 0,
            "total_credits_distributed": total_credits.scalar() or 0,
            "flagged_activities_week": flagged_activities.scalar() or 0,
            "active_users_week": active_users.scalar() or 0,
            "dashboard_updated": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching dashboard data: {str(e)}"
        )


@router.get("/flagged-activities")
async def get_flagged_activities(
    limit: int = Query(20, ge=1, le=100),
    admin_reviewed: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get flagged activities for review (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    flagged_activities = await anti_gaming_service.get_flagged_activities(
        db=db,
        limit=limit,
        admin_reviewed=admin_reviewed
    )
    
    return {
        "flagged_activities": [
            {
                "id": str(activity.id),
                "user_id": str(activity.user_id),
                "activity_type": activity.activity_type.value,
                "risk_score": activity.risk_score,
                "suspicious_patterns": activity.suspicious_patterns,
                "completion_time_seconds": activity.completion_time_seconds,
                "score_percentage": activity.score_percentage,
                "created_at": activity.created_at,
                "admin_reviewed": activity.admin_reviewed
            }
            for activity in flagged_activities
        ]
    }


@router.post("/review-flagged/{tracking_id}")
async def review_flagged_activity(
    tracking_id: UUID,
    review_data: dict,  # action: str, notes: Optional[str]
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Review a flagged activity (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    action = review_data.get("action")
    notes = review_data.get("notes")
    
    if action not in ["approve", "penalize", "warn"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be one of: approve, penalize, warn"
        )
    
    result = await anti_gaming_service.review_flagged_activity(
        db=db,
        tracking_id=tracking_id,
        admin_id=current_user.id,
        action=action,
        notes=notes
    )
    
    return {
        "message": f"Activity {action}d successfully",
        "result": result
    }


@router.get("/user/{user_id}/currency")
async def get_user_currency_details(
    user_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user currency details and transaction history (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    # Get user
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get transactions
    result = await db.execute(
        select(UserCurrencyTransaction)
        .where(UserCurrencyTransaction.user_id == user_id)
        .order_by(desc(UserCurrencyTransaction.created_at))
        .limit(limit)
    )
    transactions = result.scalars().all()
    
    # Get risk summary
    risk_summary = await anti_gaming_service.get_user_risk_summary(db, user_id)
    
    return {
        "user_id": str(user_id),
        "email": user.email,
        "current_balances": {
            "points": user.points_balance or 0,
            "credits": user.credits_balance or 0,
            "total_earned_points": user.total_points_earned or 0,
            "total_earned_credits": user.total_credits_earned or 0
        },
        "risk_summary": risk_summary,
        "recent_transactions": [
            {
                "id": str(t.id),
                "currency_type": t.currency_type.value,
                "transaction_type": t.transaction_type.value,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "activity_type": t.activity_type.value if t.activity_type else None,
                "reason": t.reason,
                "created_at": t.created_at
            }
            for t in transactions
        ]
    }


@router.get("/leaderboard/refresh")
async def refresh_leaderboards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually refresh leaderboards (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Refresh all leaderboard types
        await leaderboard_service.update_global_points_leaderboard(db)
        await leaderboard_service.update_quiz_performance_leaderboard(db)
        await leaderboard_service.update_weekly_leaderboard(db)
        await leaderboard_service.update_monthly_leaderboard(db)
        
        return {
            "message": "All leaderboards refreshed successfully",
            "refreshed_at": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing leaderboards: {str(e)}"
        )


@router.get("/transactions")
async def get_recent_transactions(
    limit: int = Query(100, ge=1, le=500),
    currency_type: Optional[str] = Query(None),
    transaction_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get recent transactions across all users (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    query = select(UserCurrencyTransaction)
    
    # Apply filters
    filters = []
    if currency_type:
        filters.append(UserCurrencyTransaction.currency_type == currency_type.upper())
    if transaction_type:
        filters.append(UserCurrencyTransaction.transaction_type == transaction_type.upper())
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(desc(UserCurrencyTransaction.created_at)).limit(limit)
    
    result = await db.execute(query)
    transactions = result.scalars().all()
    
    return {
        "transactions": [
            {
                "id": str(t.id),
                "user_id": str(t.user_id),
                "currency_type": t.currency_type.value,
                "transaction_type": t.transaction_type.value,
                "amount": t.amount,
                "balance_after": t.balance_after,
                "activity_type": t.activity_type.value if t.activity_type else None,
                "reason": t.reason,
                "created_at": t.created_at
            }
            for t in transactions
        ]
    }


@router.post("/manual-reward/{user_id}")
async def grant_manual_reward(
    user_id: UUID,
    reward_data: dict,  # currency_type, amount, reason
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Manually grant rewards to a user (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    currency_type = reward_data.get("currency_type", "").upper()
    amount = reward_data.get("amount", 0)
    reason = reward_data.get("reason", "Manual admin reward")
    
    if currency_type not in ["POINTS", "CREDITS"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Currency type must be POINTS or CREDITS"
        )
    
    if amount <= 0 or amount > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be between 1 and 1000"
        )
    
    # Check if user exists
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Grant reward
    from app.services.currency_service import CurrencyTypeEnum
    currency_enum = CurrencyTypeEnum.POINTS if currency_type == "POINTS" else CurrencyTypeEnum.CREDITS
    
    transaction = await currency_service.add_currency(
        db=db,
        user_id=user_id,
        currency_type=currency_enum,
        amount=amount,
        activity_type=None,
        reason=f"Manual admin reward: {reason}",
        admin_id=current_user.id
    )
    
    return {
        "message": f"Successfully granted {amount} {currency_type.lower()} to user",
        "transaction_id": str(transaction.id),
        "user_id": str(user_id),
        "amount": amount,
        "currency_type": currency_type
    }


@router.get("/settings")
async def get_system_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current system settings for admin panel (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        # Get all reward-related settings
        result = await db.execute(
            select(SiteSetting).where(SiteSetting.category == 'rewards')
        )
        settings = result.scalars().all()
        
        # Convert to admin panel format
        admin_settings = {}
        for setting in settings:
            admin_settings[setting.key] = setting.parsed_value
        
        # Map to admin panel expected format
        return {
            "rewards": {
                "quiz_base_points": admin_settings.get("quiz_base_credits", 10),
                "quiz_difficulty_multiplier_easy": 1.0,
                "quiz_difficulty_multiplier_medium": 1.2, 
                "quiz_difficulty_multiplier_hard": 1.5,
                "myths_facts_points": 5,
                "streak_bonus_threshold": admin_settings.get("streak_bonus_threshold", 3),
                "streak_bonus_multiplier": admin_settings.get("streak_bonus_multiplier", 1.1),
                "daily_limit_points": admin_settings.get("daily_points_limit", 500),
                "daily_limit_credits": admin_settings.get("daily_credit_cap_quizzes", 200),
                "pure_scoring_mode": admin_settings.get("pure_scoring_mode", False)
            },
            "antiGaming": {
                "max_attempts_per_quiz_per_day": admin_settings.get("max_quiz_attempts_per_day", 10),
                "min_time_between_attempts": admin_settings.get("min_time_between_attempts", 300),
                "suspicious_score_threshold": admin_settings.get("suspicious_score_threshold", 0.95),
                "rapid_completion_threshold": admin_settings.get("rapid_completion_threshold", 30),
                "enable_ip_tracking": admin_settings.get("enable_ip_tracking", True),
                "enable_behavior_analysis": admin_settings.get("enable_behavior_analysis", True)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching system settings: {str(e)}"
        )


@router.post("/settings")
async def update_system_settings(
    settings_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update system settings (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    try:
        rewards_settings = settings_data.get("rewards", {})
        anti_gaming_settings = settings_data.get("antiGaming", {})
        
        # Settings mapping: frontend field -> database key
        settings_mapping = {
            # Rewards settings
            "daily_limit_points": "daily_points_limit",
            "daily_limit_credits": "daily_credit_cap_quizzes", 
            "pure_scoring_mode": "pure_scoring_mode",
            "streak_bonus_threshold": "streak_bonus_threshold",
            "streak_bonus_multiplier": "streak_bonus_multiplier",
            
            # Anti-gaming settings  
            "max_attempts_per_quiz_per_day": "max_quiz_attempts_per_day",
            "min_time_between_attempts": "min_time_between_attempts",
            "suspicious_score_threshold": "suspicious_score_threshold",
            "rapid_completion_threshold": "rapid_completion_threshold",
            "enable_ip_tracking": "enable_ip_tracking",
            "enable_behavior_analysis": "enable_behavior_analysis"
        }
        
        updated_settings = []
        
        # Update rewards settings
        for frontend_key, db_key in settings_mapping.items():
            if frontend_key in rewards_settings:
                value = rewards_settings[frontend_key]
                
                # Get existing setting
                result = await db.execute(
                    select(SiteSetting).where(SiteSetting.key == db_key)
                )
                setting = result.scalar_one_or_none()
                
                if setting:
                    setting.set_value(value)
                    updated_settings.append(f"{db_key}: {value}")
        
        # Update anti-gaming settings
        for frontend_key, db_key in settings_mapping.items():
            if frontend_key in anti_gaming_settings:
                value = anti_gaming_settings[frontend_key]
                
                # Get existing setting
                result = await db.execute(
                    select(SiteSetting).where(SiteSetting.key == db_key)
                )
                setting = result.scalar_one_or_none()
                
                if setting:
                    setting.set_value(value)
                    updated_settings.append(f"{db_key}: {value}")
        
        await db.commit()
        
        return {
            "message": "System settings updated successfully",
            "updated_settings": updated_settings,
            "updated_by": current_user.email,
            "updated_at": datetime.now(timezone.utc)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating system settings: {str(e)}"
        )