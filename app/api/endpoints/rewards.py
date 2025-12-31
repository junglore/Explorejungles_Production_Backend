"""
Rewards API endpoints for the Knowledge Engine
"""

from datetime import datetime
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
import structlog

from app.db.database import get_db, get_db_with_retry
from app.core.security import get_current_user
from app.models.user import User
from app.services.currency_service import currency_service, CurrencyTypeEnum, ActivityTypeEnum
from app.services.rewards_service import rewards_service
from app.services.leaderboard_service import leaderboard_service
from app.schemas.rewards import (
    CurrencyBalanceResponse,
    TransactionHistoryResponse, 
    RewardsConfigResponse,
    LeaderboardResponse,
    DailySummaryResponse
)

router = APIRouter()
logger = structlog.get_logger()


@router.get("/currency/balance", response_model=CurrencyBalanceResponse)
async def get_currency_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's current currency balance"""
    
    try:
        balance = await currency_service.get_user_balance(db, current_user.id)
        return CurrencyBalanceResponse(**balance)
        
    except Exception as e:
        logger.error("Error getting currency balance", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving currency balance"
        )


@router.get("/currency/transactions", response_model=TransactionHistoryResponse)
async def get_transaction_history(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    currency_type: Optional[str] = Query(None, description="Filter by currency type (points/credits)"),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's transaction history"""
    
    try:
        # Validate enums
        currency_filter = None
        if currency_type:
            try:
                currency_filter = CurrencyTypeEnum(currency_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid currency type: {currency_type}"
                )
        
        activity_filter = None
        if activity_type:
            try:
                activity_filter = ActivityTypeEnum(activity_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid activity type: {activity_type}"
                )
        
        transactions = await currency_service.get_transaction_history(
            db, current_user.id, limit, offset, currency_filter, activity_filter
        )
        
        return TransactionHistoryResponse(
            transactions=[
                {
                    "id": str(t.id),
                    "transaction_type": t.transaction_type.value,
                    "currency_type": t.currency_type.value,
                    "amount": t.amount,
                    "balance_after": t.balance_after,
                    "activity_type": t.activity_type.value,
                    "activity_reference_id": str(t.activity_reference_id) if t.activity_reference_id else None,
                    "metadata": t.transaction_metadata,
                    "created_at": t.created_at,
                    "processed_at": t.processed_at
                }
                for t in transactions
            ],
            total_count=len(transactions),
            has_more=len(transactions) == limit
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting transaction history", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving transaction history"
        )


@router.get("/rewards/available", response_model=RewardsConfigResponse)
async def get_available_rewards(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available rewards structure for the user"""
    
    try:
        rewards_summary = await rewards_service.get_available_rewards_summary(db, current_user.id)
        return RewardsConfigResponse(**rewards_summary)
        
    except Exception as e:
        logger.error("Error getting rewards config", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving rewards configuration"
        )


@router.get("/daily-summary", response_model=DailySummaryResponse)
async def get_daily_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get today's activity and earnings summary"""
    
    try:
        summary = await currency_service.get_daily_earnings_summary(db, current_user.id)
        return DailySummaryResponse(**summary)
        
    except Exception as e:
        logger.error("Error getting daily summary", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving daily summary"
        )


@router.post("/process-quiz-reward")
async def process_quiz_reward(
    quiz_result_id: UUID,
    quiz_id: UUID,
    score_percentage: int,
    time_taken: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process reward for quiz completion (internal endpoint)"""
    
    try:
        # Validate score percentage
        if not 0 <= score_percentage <= 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score percentage must be between 0 and 100"
            )
        
        # Process reward
        reward_result = await rewards_service.process_quiz_completion_reward(
            db=db,
            user_id=current_user.id,
            quiz_result_id=quiz_result_id,
            quiz_id=quiz_id,
            score_percentage=score_percentage,
            time_taken=time_taken,
            perfect_score_bonus=(score_percentage == 100)
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Quiz reward processed successfully",
            **reward_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error processing quiz reward", 
                    user_id=str(current_user.id), 
                    quiz_id=str(quiz_id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing quiz reward"
        )


@router.post("/process-myths-facts-reward")
async def process_myths_facts_reward(
    game_session_id: UUID,
    score_percentage: int,
    time_taken: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process reward for myths vs facts game completion"""
    
    try:
        # Validate score percentage
        if not 0 <= score_percentage <= 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Score percentage must be between 0 and 100"
            )
        
        # Process reward
        reward_result = await rewards_service.process_myths_facts_reward(
            db=db,
            user_id=current_user.id,
            game_session_id=game_session_id,
            score_percentage=score_percentage,
            time_taken=time_taken,
            perfect_accuracy=(score_percentage == 100)
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Myths vs Facts reward processed successfully",
            **reward_result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Error processing myths facts reward", 
                    user_id=str(current_user.id), 
                    game_session_id=str(game_session_id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing myths vs facts reward"
        )


@router.post("/daily-login")
async def process_daily_login_reward(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Process daily login reward"""
    
    try:
        reward_result = await rewards_service.process_daily_login_reward(db, current_user.id)
        await db.commit()
        
        return {
            "success": True,
            "message": "Daily login reward processed successfully",
            **reward_result
        }
        
    except Exception as e:
        await db.rollback()
        logger.error("Error processing daily login reward", 
                    user_id=str(current_user.id),
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error processing daily login reward"
        )


# Leaderboard endpoints
@router.get("/leaderboard/global-points", response_model=LeaderboardResponse)
async def get_global_points_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get global points leaderboard"""
    
    try:
        leaderboard = await leaderboard_service.get_global_points_leaderboard(
            db, limit, current_user.id
        )
        return LeaderboardResponse(**leaderboard)
        
    except Exception as e:
        logger.error("Error getting global points leaderboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving global points leaderboard"
        )


@router.get("/leaderboard/quiz-performance", response_model=LeaderboardResponse)
async def get_quiz_leaderboard(
    limit: int = Query(50, ge=1, le=100),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get quiz performance leaderboard"""
    
    try:
        leaderboard = await leaderboard_service.get_quiz_leaderboard(
            db, limit, category_id, current_user.id
        )
        return LeaderboardResponse(**leaderboard)
        
    except Exception as e:
        logger.error("Error getting quiz leaderboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving quiz leaderboard"
        )


@router.get("/leaderboard/weekly", response_model=LeaderboardResponse)
async def get_weekly_leaderboard(
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get weekly points leaderboard"""
    
    try:
        leaderboard = await leaderboard_service.get_weekly_leaderboard(
            db, limit, current_user.id
        )
        return LeaderboardResponse(**leaderboard)
        
    except Exception as e:
        logger.error("Error getting weekly leaderboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving weekly leaderboard"
        )


@router.get("/leaderboard/monthly", response_model=LeaderboardResponse)
async def get_monthly_leaderboard(
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get monthly points leaderboard"""
    
    try:
        leaderboard = await leaderboard_service.get_monthly_leaderboard(
            db, limit, current_user.id
        )
        return LeaderboardResponse(**leaderboard)
        
    except Exception as e:
        logger.error("Error getting monthly leaderboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving monthly leaderboard"
        )


@router.get("/leaderboard/category/{category_id}", response_model=LeaderboardResponse)
async def get_category_leaderboard(
    category_id: UUID,
    limit: int = Query(25, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get category-specific leaderboard"""
    
    try:
        leaderboard = await leaderboard_service.get_category_leaderboard(
            db, category_id, limit, current_user.id
        )
        return LeaderboardResponse(**leaderboard)
        
    except Exception as e:
        logger.error("Error getting category leaderboard", category_id=str(category_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving category leaderboard"
        )


@router.get("/leaderboard/user-positions")
async def get_user_leaderboard_positions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's position across all leaderboards"""
    
    try:
        positions = await leaderboard_service.get_user_leaderboard_positions(db, current_user.id)
        return positions
        
    except Exception as e:
        logger.error("Error getting user leaderboard positions", 
                    user_id=str(current_user.id), 
                    error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving leaderboard positions"
        )