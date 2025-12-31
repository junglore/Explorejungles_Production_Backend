"""
Quizzes API Routes
Handles wildlife quizzes and user results
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone, time
import logging

from app.db.database import get_db, get_db_with_retry
from app.models.quiz_extended import Quiz, UserQuizResult
from app.models.user import User
from app.models.category import Category
from app.core.security import get_current_user, get_current_user_optional
from app.schemas.quiz import (
    QuizCreateSchema,
    QuizUpdateSchema, 
    QuizResponseSchema,
    QuizListResponseSchema,
    QuizSubmissionSchema,
    QuizResultSchema,
    QuizStatsSchema,
    UserQuizHistorySchema
)
from app.services.rewards_service import rewards_service
from app.services.anti_gaming_service import anti_gaming_service
from app.services.credits_service import CreditsService
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=List[QuizListResponseSchema])
async def get_quizzes(
    skip: int = Query(0, ge=0, description="Number of quizzes to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of quizzes to return"),
    category_id: Optional[UUID] = Query(None, description="Filter by category"),
    difficulty: Optional[int] = Query(None, ge=1, le=3, description="Filter by difficulty level"),
    active_only: bool = Query(True, description="Show only active quizzes"),
    db: AsyncSession = Depends(get_db)
):
    """Get available quizzes with pagination and filtering"""
    
    query = select(Quiz)
    
    # Apply filters
    if active_only:
        query = query.where(Quiz.is_active == True)
    
    if category_id:
        query = query.where(Quiz.category_id == category_id)
        
    if difficulty:
        query = query.where(Quiz.difficulty_level == difficulty)
    
    # Apply pagination and ordering
    query = query.offset(skip).limit(limit).order_by(desc(Quiz.created_at))
    
    result = await db.execute(query)
    quizzes = result.scalars().all()
    
    # Convert to response format with calculated fields
    quiz_responses = []
    for quiz in quizzes:
        total_questions = len(quiz.questions) if quiz.questions else 0
        total_points = sum(q.get('points', 1) for q in quiz.questions) if quiz.questions else 0
        
        quiz_responses.append(QuizListResponseSchema(
            id=quiz.id,
            title=quiz.title,
            description=quiz.description,
            cover_image=f"/uploads/{quiz.cover_image}" if quiz.cover_image else None,
            category_id=quiz.category_id,
            difficulty_level=quiz.difficulty_level,
            time_limit=quiz.time_limit,
            is_active=quiz.is_active,
            created_at=quiz.created_at,
            total_questions=total_questions,
            total_points=total_points
        ))
    
    return quiz_responses


@router.get("/{quiz_id}", response_model=QuizResponseSchema)
async def get_quiz(
    quiz_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get a specific quiz by ID"""
    
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    if not quiz.is_active and (not current_user or not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quiz is not available"
        )
    
    # Calculate additional fields
    total_questions = len(quiz.questions) if quiz.questions else 0
    total_points = sum(q.get('points', 1) for q in quiz.questions) if quiz.questions else 0
    
    return QuizResponseSchema(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        cover_image=f"/uploads/{quiz.cover_image}" if quiz.cover_image else None,
        category_id=quiz.category_id,
        questions=quiz.questions,
        difficulty_level=quiz.difficulty_level,
        time_limit=quiz.time_limit,
        is_active=quiz.is_active,
        created_at=quiz.created_at,
        total_questions=total_questions,
        total_points=total_points
    )


@router.post("/", response_model=QuizResponseSchema)
async def create_quiz(
    quiz_data: QuizCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new quiz (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create quizzes"
        )
    
    # Validate category if provided
    if quiz_data.category_id:
        result = await db.execute(select(Category).where(Category.id == quiz_data.category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    # Create quiz
    quiz = Quiz(
        title=quiz_data.title,
        description=quiz_data.description,
        category_id=quiz_data.category_id,
        questions=[q.dict() for q in quiz_data.questions],
        difficulty_level=quiz_data.difficulty_level,
        time_limit=quiz_data.time_limit,
        is_active=quiz_data.is_active
    )
    
    db.add(quiz)
    await db.commit()
    await db.refresh(quiz)
    
    # Calculate additional fields for response
    total_questions = len(quiz.questions) if quiz.questions else 0
    total_points = sum(q.get('points', 1) for q in quiz.questions) if quiz.questions else 0
    
    return QuizResponseSchema(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        cover_image=quiz.cover_image,
        category_id=quiz.category_id,
        questions=quiz.questions,
        difficulty_level=quiz.difficulty_level,
        time_limit=quiz.time_limit,
        is_active=quiz.is_active,
        created_at=quiz.created_at,
        total_questions=total_questions,
        total_points=total_points
    )


@router.put("/{quiz_id}", response_model=QuizResponseSchema)
async def update_quiz(
    quiz_id: UUID,
    quiz_data: QuizUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a quiz (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update quizzes"
        )
    
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    # Update fields
    update_data = quiz_data.dict(exclude_unset=True)
    
    # Validate category if being updated
    if 'category_id' in update_data and update_data['category_id']:
        result = await db.execute(select(Category).where(Category.id == update_data['category_id']))
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    # Convert questions to dict format if provided
    if 'questions' in update_data:
        update_data['questions'] = [q.dict() for q in update_data['questions']]
    
    for field, value in update_data.items():
        setattr(quiz, field, value)
    
    await db.commit()
    await db.refresh(quiz)
    
    # Calculate additional fields for response
    total_questions = len(quiz.questions) if quiz.questions else 0
    total_points = sum(q.get('points', 1) for q in quiz.questions) if quiz.questions else 0
    
    return QuizResponseSchema(
        id=quiz.id,
        title=quiz.title,
        description=quiz.description,
        cover_image=quiz.cover_image,
        category_id=quiz.category_id,
        questions=quiz.questions,
        difficulty_level=quiz.difficulty_level,
        time_limit=quiz.time_limit,
        is_active=quiz.is_active,
        created_at=quiz.created_at,
        total_questions=total_questions,
        total_points=total_points
    )


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a quiz (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete quizzes"
        )
    
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    await db.delete(quiz)
    await db.commit()
    
    return {"message": "Quiz deleted successfully"}


@router.post("/{quiz_id}/submit", response_model=QuizResultSchema)
async def submit_quiz(
    quiz_id: UUID,
    submission: QuizSubmissionSchema,
    request: Request,
    db: AsyncSession = Depends(get_db_with_retry),  # Use retry for critical submissions
    current_user: User = Depends(get_current_user)
):
    """Submit quiz answers and get results with rewards processing"""
    
    # Get quiz
    result = await db.execute(select(Quiz).where(Quiz.id == quiz_id))
    quiz = result.scalar_one_or_none()
    
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quiz not found"
        )
    
    if not quiz.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Quiz is not active"
        )
    
    # Extract client IP for tracking
    client_ip = request.client.host if request.client else "unknown"
    
    # Get security settings
    from app.services.settings_service import SettingsService
    settings_service = SettingsService(db)
    security_settings = await settings_service.get_security_settings()
    
    # Check daily quiz attempts limit (skip in development mode for testing)
    if settings.ENVIRONMENT != "development":
        max_daily_attempts = security_settings.get('max_quiz_attempts_per_day', 10)
        
        # Count today's quiz attempts (different quizzes completed)
        today = datetime.utcnow().date()
        tomorrow = today + timedelta(days=1)
        
        daily_attempts_result = await db.execute(
            select(func.count(func.distinct(UserQuizResult.quiz_id)))
            .where(
                and_(
                    UserQuizResult.user_id == current_user.id,
                    UserQuizResult.completed_at >= today,
                    UserQuizResult.completed_at < tomorrow
                )
            )
        )
        
        daily_attempts = daily_attempts_result.scalar() or 0
        
        if daily_attempts >= max_daily_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"You have reached the daily quiz limit of {max_daily_attempts} different quizzes. Come back tomorrow!"
            )
    
    # Check 5-minute cooldown between quiz attempts (skip in development mode)
    if settings.ENVIRONMENT != "development":
        min_time_between_attempts = security_settings.get('min_time_between_attempts', 300)  # 5 minutes default
        
        last_attempt_result = await db.execute(
            select(UserQuizResult.completed_at)
            .where(UserQuizResult.user_id == current_user.id)
            .order_by(desc(UserQuizResult.completed_at))
            .limit(1)
        )
        
        last_attempt = last_attempt_result.scalar_one_or_none()
        
        if last_attempt:
            time_since_last_attempt = (datetime.now(timezone.utc) - last_attempt).total_seconds()
            if time_since_last_attempt < min_time_between_attempts:
                remaining_seconds = int(min_time_between_attempts - time_since_last_attempt)
                remaining_minutes = (remaining_seconds + 59) // 60  # Round up to next minute
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"You must wait {remaining_minutes} minute(s) before attempting another quiz."
                )
    
    # Check if user already completed this quiz (skip in development mode for testing)
    if settings.ENVIRONMENT != "development":
        existing_result = await db.execute(
            select(UserQuizResult).where(
                and_(
                    UserQuizResult.user_id == current_user.id,
                    UserQuizResult.quiz_id == quiz_id
                )
            )
        )
        
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already completed this quiz. Come back tomorrow!"
            )
    
    # Validate submission
    if len(submission.answers) > len(quiz.questions):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Too many answers provided"
        )
    
    # Calculate score
    score = 0
    max_score = 0
    answer_results = []
    
    for i, question in enumerate(quiz.questions):
        max_score += question.get('points', 1)
        
        # Find user's answer for this question
        user_answer = next(
            (a for a in submission.answers if a.question_index == i),
            None
        )
        
        if user_answer:
            is_correct = user_answer.selected_answer == question['correct_answer']
            if is_correct:
                score += question.get('points', 1)
            
            answer_results.append({
                "question_index": i,
                "question": question['question'],
                "selected_answer": user_answer.selected_answer,
                "correct_answer": question['correct_answer'],
                "is_correct": is_correct,
                "points_earned": question.get('points', 1) if is_correct else 0,
                "time_taken": user_answer.time_taken,
                "explanation": question.get('explanation')
            })
        else:
            # Question not answered
            answer_results.append({
                "question_index": i,
                "question": question['question'],
                "selected_answer": None,
                "correct_answer": question['correct_answer'],
                "is_correct": False,
                "points_earned": 0,
                "time_taken": None,
                "explanation": question.get('explanation')
            })
    
    percentage = round((score / max_score) * 100) if max_score > 0 else 0
    
    # Save result first
    quiz_result = UserQuizResult(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=score,
        max_score=max_score,
        percentage=percentage,
        answers=answer_results,
        time_taken=submission.total_time_taken,
        completed_at=datetime.now(timezone.utc)
    )
    
    # Initialize reward fields (set as attributes after creation)
    quiz_result.points_earned = 0
    quiz_result.credits_earned = 0
    quiz_result.reward_tier = None
    
    db.add(quiz_result)
    await db.flush()  # Get the ID without committing
    
    # Anti-gaming analysis
    try:
        gaming_analysis = await anti_gaming_service.analyze_quiz_completion(
            db=db,
            user_id=current_user.id,
            quiz_result_id=quiz_result.id,
            time_taken=submission.total_time_taken,
            score_percentage=percentage,
            client_ip=client_ip,
            enable_ip_tracking=security_settings.get('enable_ip_tracking', True),
            enable_behavior_analysis=security_settings.get('enable_behavior_analysis', True)
        )
        
        # Process rewards if not flagged for gaming
        if gaming_analysis.get("allow_rewards", True):
            # Use enhanced rewards service for comprehensive reward calculation
            from app.services.enhanced_rewards_service import EnhancedRewardsService
            enhanced_rewards = EnhancedRewardsService(db)
            
            # Calculate completion time in seconds
            completion_time = submission.total_time_taken if submission.total_time_taken else None
            
            # Use actual score (points from correct answers only) as base points
            base_points = score  # This is already calculated correctly above
            
            # Award enhanced rewards with all bonuses
            reward_calculation = await enhanced_rewards.award_quiz_completion(
                user_id=current_user.id,
                quiz_id=str(quiz_id),
                quiz_percentage=percentage,
                base_points=base_points,  # Use actual earned score, not total possible points
                base_credits=quiz.credits_on_completion or 10,  # Use quiz credits setting
                completion_time=completion_time,
                completed_at=datetime.now(timezone.utc)
            )
            
            # Get final calculated rewards
            points_earned = reward_calculation.get('final_points', score)
            credits_earned = reward_calculation.get('final_credits', 5)
            reward_tier = reward_calculation.get('tier', 'bronze')
            
            # Update quiz result with enhanced reward information
            quiz_result.credits_earned = credits_earned
            quiz_result.points_earned = points_earned
            quiz_result.reward_tier = reward_tier
            
            # Store comprehensive bonus information for display
            if reward_calculation.get('bonuses'):
                quiz_result.bonus_info = {
                    'bonuses': reward_calculation['bonuses'],
                    'multiplier': reward_calculation.get('multiplier', 1.0),
                    'credits_multiplier': reward_calculation.get('credits_multiplier', 1.0),
                    'base_points': score,  # Use actual earned score
                    'base_credits': quiz.credits_on_completion or 10,
                    'message': reward_calculation.get('message', ''),
                    'was_limited': reward_calculation.get('was_limited', False),
                    'tier': reward_calculation.get('tier', 'bronze')
                }
            
            # Update user's total points in their profile
            current_user.total_points_earned = (current_user.total_points_earned or 0) + points_earned
            
            # Update weekly leaderboard cache with enhanced points
            from app.models.weekly_leaderboard_cache import WeeklyLeaderboardCache
            await WeeklyLeaderboardCache.update_user_weekly_stats(
                db,
                user_id=current_user.id,
                credits_earned=0,  # Credits already handled by enhanced rewards
                points_earned=points_earned,
                quiz_completed=False,  # Already marked completed
                is_perfect_score=(percentage == 100),
                score_percentage=percentage
            )
            
            logger.info(
                f"Enhanced quiz rewards: User {current_user.id} earned {points_earned} points "
                f"({reward_calculation.get('multiplier', 1.0)}x multiplier) and {credits_earned} credits. "
                f"Tier: {reward_tier}. Bonuses: {reward_calculation.get('bonuses', [])}"
            )
        else:
            # Log that rewards were blocked due to suspicious activity
            logger.warning(f"Rewards blocked for quiz submission {quiz_result.id} due to gaming detection")
    
    except Exception as e:
        # Log error but don't fail the quiz submission
        logger.error(
            f"Error processing rewards for quiz {quiz_id}: {str(e)} "
            f"(user_id={current_user.id}, quiz_result_id={quiz_result.id})",
            exc_info=True
        )
        # Continue with basic quiz result
    
    await db.commit()
    await db.refresh(quiz_result)
    
    return QuizResultSchema(
        id=quiz_result.id,
        user_id=quiz_result.user_id,
        quiz_id=quiz_result.quiz_id,
        score=quiz_result.score,
        max_score=quiz_result.max_score,
        percentage=quiz_result.percentage,
        answers=quiz_result.answers,
        time_taken=quiz_result.time_taken,
        completed_at=quiz_result.completed_at,
        # Include reward information in response
        points_earned=quiz_result.points_earned,
        credits_earned=quiz_result.credits_earned,
        reward_tier=quiz_result.reward_tier
    )


@router.get("/leaderboard", response_model=list[QuizResultSchema])
async def get_leaderboard(
    quiz_id: Optional[UUID] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Top results leaderboard (overall or per quiz)"""
    query = select(UserQuizResult)
    if quiz_id:
        query = query.where(UserQuizResult.quiz_id == quiz_id)
    # Order by percentage desc, then time ascending, then completed_at desc
    query = query.order_by(desc(UserQuizResult.percentage), UserQuizResult.time_taken.asc().nullsLast(), desc(UserQuizResult.completed_at)).limit(limit)
    result = await db.execute(query)
    rows = result.scalars().all()
    return [
        QuizResultSchema(
            id=r.id,
            user_id=r.user_id,
            quiz_id=r.quiz_id,
            score=r.score,
            max_score=r.max_score,
            percentage=r.percentage,
            answers=r.answers,
            time_taken=r.time_taken,
            completed_at=r.completed_at
        ) for r in rows
    ]


@router.get("/{quiz_id}/results", response_model=List[QuizResultSchema])
async def get_quiz_results(
    quiz_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quiz results (Admin only or own results)"""
    
    if not current_user.is_superuser:
        # Regular users can only see their own results
        query = select(UserQuizResult).where(
            and_(
                UserQuizResult.quiz_id == quiz_id,
                UserQuizResult.user_id == current_user.id
            )
        )
    else:
        # Admins can see all results
        query = select(UserQuizResult).where(UserQuizResult.quiz_id == quiz_id)
    
    query = query.offset(skip).limit(limit).order_by(desc(UserQuizResult.completed_at))
    
    result = await db.execute(query)
    results = result.scalars().all()
    
    return [QuizResultSchema(
        id=r.id,
        user_id=r.user_id,
        quiz_id=r.quiz_id,
        score=r.score,
        max_score=r.max_score,
        percentage=r.percentage,
        answers=r.answers,
        time_taken=r.time_taken,
        completed_at=r.completed_at
    ) for r in results]


@router.get("/{quiz_id}/stats", response_model=QuizStatsSchema)
async def get_quiz_stats(
    quiz_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get quiz statistics (Admin only)"""
    
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view quiz statistics"
        )
    
    # Get all results for this quiz
    result = await db.execute(
        select(UserQuizResult).where(UserQuizResult.quiz_id == quiz_id)
    )
    results = result.scalars().all()
    
    if not results:
        return QuizStatsSchema(
            quiz_id=quiz_id,
            total_attempts=0,
            average_score=0.0,
            average_percentage=0.0,
            average_time=None,
            difficulty_rating=0.0,
            popular_wrong_answers=[]
        )
    
    # Calculate statistics
    total_attempts = len(results)
    average_score = sum(r.score for r in results) / total_attempts
    average_percentage = sum(r.percentage for r in results) / total_attempts
    
    # Calculate average time (excluding None values)
    times = [r.time_taken for r in results if r.time_taken is not None]
    average_time = sum(times) / len(times) if times else None
    
    # Calculate difficulty rating (lower percentage = higher difficulty)
    difficulty_rating = max(0.0, (100.0 - average_percentage) / 20.0)  # Scale 0-5
    
    return QuizStatsSchema(
        quiz_id=quiz_id,
        total_attempts=total_attempts,
        average_score=average_score,
        average_percentage=average_percentage,
        average_time=average_time,
        difficulty_rating=difficulty_rating,
        popular_wrong_answers=[]  # TODO: Implement detailed wrong answer analysis
    )


@router.get("/user/history", response_model=dict)
async def get_user_quiz_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's quiz history and statistics"""
    
    try:
        # Get user's quiz results
        result = await db.execute(
            select(UserQuizResult)
            .where(UserQuizResult.user_id == current_user.id)
            .order_by(desc(UserQuizResult.completed_at))
        )
        quiz_results = result.scalars().all()
        
        # Convert to response format
        results = []
        for r in quiz_results:
            results.append({
                "id": r.id,
                "user_id": r.user_id,
                "quiz_id": r.quiz_id,
                "score": r.score,
                "max_score": r.max_score,
                "percentage": r.percentage,
                "answers": r.answers,
                "time_taken": r.time_taken,
                "completed_at": r.completed_at,
                "points_earned": r.points_earned,
                "credits_earned": r.credits_earned,
                "reward_tier": r.reward_tier
            })
        
        # Calculate statistics
        total_quizzes = len(results)
        total_points = sum(r["points_earned"] for r in results)
        total_credits = sum(r["credits_earned"] for r in results)
        average_percentage = sum(r["percentage"] for r in results) / total_quizzes if total_quizzes > 0 else 0
        
        return {
            "results": results,
            "statistics": {
                "total_quizzes_completed": total_quizzes,
                "total_points_earned": total_points,
                "total_credits_earned": total_credits,
                "average_percentage": round(average_percentage, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching user quiz history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch quiz history"
        )


@router.get("/user/rankings", response_model=dict)
async def get_user_rankings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's rankings across different categories"""
    
    try:
        # Get current week (Monday to Sunday) - use timezone-aware datetimes
        now = datetime.now(timezone.utc)
        today = now.date()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        # Convert to timezone-aware datetime objects for database comparison
        week_start_dt = datetime.combine(week_start, time.min, tzinfo=timezone.utc)
        week_end_dt = datetime.combine(week_end, time.max, tzinfo=timezone.utc)
        
        # Global ranking (all-time total points)
        global_rank_query = text("""
            SELECT rank FROM (
                SELECT user_id, RANK() OVER (ORDER BY COALESCE(total_points_earned, 0) DESC) as rank
                FROM users 
                WHERE COALESCE(total_points_earned, 0) > 0
            ) ranked_users
            WHERE user_id = :user_id
        """)
        
        global_rank_result = await db.execute(global_rank_query, {"user_id": current_user.id})
        global_rank = global_rank_result.scalar_one_or_none() or 0
        
        # Weekly ranking (points earned this week) - use proper datetime comparison
        weekly_rank_query = text("""
            SELECT rank FROM (
                SELECT user_id, RANK() OVER (ORDER BY COALESCE(SUM(points_earned), 0) DESC) as rank
                FROM user_quiz_results 
                WHERE completed_at >= :week_start AND completed_at <= :week_end
                GROUP BY user_id
            ) ranked_users
            WHERE user_id = :user_id
        """)
        
        weekly_rank_result = await db.execute(weekly_rank_query, {
            "user_id": current_user.id,
            "week_start": week_start_dt,
            "week_end": week_end_dt
        })
        weekly_rank = weekly_rank_result.scalar_one_or_none() or 0
        
        return {
            "weekly_rank": weekly_rank,
            "global_rank": global_rank,
            "personal_best": current_user.total_points_earned or 0
        }
        
    except Exception as e:
        logger.error(f"Error calculating user rankings: {e}")
        return {
            "weekly_rank": 0,
            "global_rank": 0,
            "personal_best": current_user.total_points_earned or 0
        }


# Removed - This Quiz Rank not needed for leaderboard display


@router.get("/{quiz_id}/availability", response_model=dict)
async def check_quiz_availability(
    quiz_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if user can take a specific quiz and return availability status"""
    
    try:
        # Get security settings
        from app.services.settings_service import SettingsService
        settings_service = SettingsService(db)
        security_settings = await settings_service.get_security_settings()
        
        # Get today's date range
        today = datetime.now(timezone.utc).date()
        tomorrow = today + timedelta(days=1)
        
        # Check daily quiz limit (skip in development mode for testing)
        if settings.ENVIRONMENT != "development":
            max_daily_attempts = security_settings.get('max_daily_quiz_attempts', 5)
            
            daily_attempts_result = await db.execute(
                select(func.count(func.distinct(UserQuizResult.quiz_id)))
                .where(
                    and_(
                        UserQuizResult.user_id == current_user.id,
                        UserQuizResult.completed_at >= today,
                        UserQuizResult.completed_at < tomorrow
                    )
                )
            )
            
            daily_attempts = daily_attempts_result.scalar() or 0
            
            if daily_attempts >= max_daily_attempts:
                return {
                    "can_take_quiz": False,
                    "reason": "daily_limit_reached",
                    "message": f"You have reached the daily quiz limit of {max_daily_attempts} different quizzes. Come back tomorrow!",
                    "remaining_time": None,
                    "next_available": tomorrow.isoformat()
                }
        
        # Check 5-minute cooldown between quiz attempts (skip in development mode for testing)
        if settings.ENVIRONMENT != "development":
            min_time_between_attempts = security_settings.get('min_time_between_attempts', 300)  # 5 minutes default
            
            last_attempt_result = await db.execute(
                select(UserQuizResult.completed_at)
                .where(UserQuizResult.user_id == current_user.id)
                .order_by(desc(UserQuizResult.completed_at))
                .limit(1)
            )
            
            last_attempt = last_attempt_result.scalar_one_or_none()
            
            if last_attempt:
                time_since_last_attempt = (datetime.now(timezone.utc) - last_attempt).total_seconds()
                if time_since_last_attempt < min_time_between_attempts:
                    remaining_seconds = int(min_time_between_attempts - time_since_last_attempt)
                    remaining_minutes = (remaining_seconds + 59) // 60  # Round up to next minute
                    
                    next_available = last_attempt + timedelta(seconds=min_time_between_attempts)
                    return {
                        "can_take_quiz": False,
                        "reason": "cooldown_active",
                        "message": f"You must wait {remaining_minutes} minute(s) before attempting another quiz.",
                        "remaining_time": remaining_seconds,
                        "next_available": next_available.isoformat()
                    }
        
        # Check if user already completed this specific quiz (skip in development mode for testing)
        if settings.ENVIRONMENT != "development":
            existing_result = await db.execute(
                select(UserQuizResult).where(
                    and_(
                        UserQuizResult.user_id == current_user.id,
                        UserQuizResult.quiz_id == quiz_id
                    )
                )
            )
            
            if existing_result.scalar_one_or_none():
                return {
                    "can_take_quiz": False,
                    "reason": "already_completed",
                    "message": "You have already completed this quiz. Come back tomorrow!",
                    "remaining_time": None,
                    "next_available": tomorrow.isoformat()
                }
        
        # User can take the quiz
        return {
            "can_take_quiz": True,
            "reason": None,
            "message": "Quiz available",
            "remaining_time": None,
            "next_available": None
        }
        
    except Exception as e:
        logger.error(f"Error checking quiz availability: {e}")
        # On error, allow the quiz (fail open)
        return {
            "can_take_quiz": True,
            "reason": "error_checking",
            "message": "Unable to verify quiz availability, proceeding...",
            "remaining_time": None,
            "next_available": None
        }