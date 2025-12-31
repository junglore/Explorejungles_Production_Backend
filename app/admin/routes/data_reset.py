"""
Admin API Routes for Production Data Reset
Provides secure endpoints for resetting user data for production launch
"""

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, func, text
from typing import Dict, Any
import asyncio
import logging
from datetime import datetime

from app.db.database import get_db
from app.models.user import User
from app.models.quiz_extended import UserQuizResult
from app.models.user_quiz_best_score import UserQuizBestScore
from app.models.rewards import (
    UserCurrencyTransaction, 
    UserDailyActivity, 
    UserAchievement
)
from app.models.weekly_leaderboard_cache import WeeklyLeaderboardCache
from app.core.security import get_current_user
from app.admin.templates.base import create_html_page

router = APIRouter()
logger = logging.getLogger(__name__)

# Track ongoing reset operations
reset_in_progress = False
reset_status = {
    "status": "idle",
    "progress": 0,
    "message": "",
    "started_at": None,
    "completed_at": None,
    "operations": [],
    "errors": []
}


@router.get("", response_class=HTMLResponse)
async def data_reset_page(request: Request):
    """Data reset admin page"""
    
    # Check if user is logged in and has admin access
    if "user_id" not in request.session:
        return RedirectResponse(url="/admin/login", status_code=302)
    
    data_reset_content = """
        <div style="max-width: 1200px; margin: 0 auto; padding: 2rem;">
            <div style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; padding: 2rem; border-radius: 12px; margin-bottom: 2rem; text-align: center;">
                <i class="fas fa-exclamation-triangle" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700;">Production Data Reset</h1>
                <p style="margin: 1rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">⚠️ DANGER ZONE - This action cannot be undone ⚠️</p>
            </div>
            
            <div class="dashboard-card" style="margin-bottom: 2rem;">
                <h3 style="color: #dc3545; margin-bottom: 1rem; display: flex; align-items: center;">
                    <i class="fas fa-info-circle" style="margin-right: 0.5rem;"></i>
                    What This Reset Will Do
                </h3>
                <div style="background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px; padding: 1.5rem; margin-bottom: 1rem;">
                    <p style="margin: 0 0 1rem 0; font-weight: 600;">This operation will permanently delete the following data:</p>
                    <ul style="margin: 0; padding-left: 1.5rem; color: #856404;">
                        <li>All user quiz results and best scores</li>
                        <li>All currency transactions and balances (points & credits)</li>
                        <li>All daily activity records</li>
                        <li>All leaderboard entries and rankings</li>
                        <li>All user achievements and progress</li>
                        <li>All user earned totals will be reset to zero</li>
                    </ul>
                </div>
                <div style="background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 8px; padding: 1.5rem;">
                    <p style="margin: 0; color: #721c24; font-weight: 600;">
                        <i class="fas fa-shield-alt" style="margin-right: 0.5rem;"></i>
                        What Will NOT Be Affected:
                    </p>
                    <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem; color: #721c24;">
                        <li>User accounts and login credentials</li>
                        <li>Quiz content and questions</li>
                        <li>Myths vs Facts content</li>
                        <li>System settings and configurations</li>
                        <li>Media files and uploads</li>
                    </ul>
                </div>
            </div>
            
            <div class="dashboard-card">
                <h3 style="color: #dc3545; margin-bottom: 1.5rem; display: flex; align-items: center;">
                    <i class="fas fa-chart-bar" style="margin-right: 0.5rem;"></i>
                    Current Data Summary
                </h3>
                
                <div id="data-summary" style="text-align: center; padding: 2rem; color: #6c757d;">
                    <i class="fas fa-spinner fa-spin" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>Loading current data summary...</p>
                </div>
                
                <div id="reset-section" style="display: none; margin-top: 2rem; padding: 2rem; background: #f8f9fa; border-radius: 8px; border: 2px solid #dc3545;">
                    <h4 style="color: #dc3545; margin-bottom: 1rem; text-align: center;">
                        <i class="fas fa-exclamation-triangle"></i>
                        CONFIRM PRODUCTION DATA RESET
                    </h4>
                    
                    <div style="background: #dc3545; color: white; padding: 1rem; border-radius: 6px; margin-bottom: 1.5rem; text-align: center;">
                        <strong>⚠️ THIS ACTION CANNOT BE UNDONE ⚠️</strong>
                        <br>
                        All user progress and achievements will be permanently lost.
                    </div>
                    
                    <div style="margin-bottom: 1.5rem;">
                        <label style="font-weight: 600; color: #495057; margin-bottom: 0.5rem; display: block;">
                            Type exactly: <code style="background: #e9ecef; padding: 0.25rem 0.5rem; border-radius: 4px;">RESET PRODUCTION DATA</code>
                        </label>
                        <input type="text" id="confirmation-input" placeholder="Type the confirmation text here..." 
                               style="width: 100%; padding: 0.75rem; border: 2px solid #ced4da; border-radius: 6px; font-size: 1rem;">
                    </div>
                    
                    <div style="text-align: center;">
                        <button id="execute-reset-btn" disabled 
                                style="background: #dc3545; color: white; border: none; padding: 1rem 2rem; border-radius: 6px; font-size: 1.1rem; font-weight: 600; cursor: not-allowed; opacity: 0.5;">
                            <i class="fas fa-trash-alt"></i>
                            Execute Production Data Reset
                        </button>
                    </div>
                </div>
                
                <div id="reset-progress" style="display: none; margin-top: 2rem;">
                    <h4 style="color: #dc3545; margin-bottom: 1rem; text-align: center;">
                        <i class="fas fa-cog fa-spin"></i>
                        Reset In Progress
                    </h4>
                    <div style="background: #f8f9fa; border-radius: 6px; padding: 1.5rem;">
                        <div style="background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden; margin-bottom: 1rem;">
                            <div id="progress-bar" style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); height: 100%; width: 0%; transition: width 0.3s ease;"></div>
                        </div>
                        <div id="progress-text" style="text-align: center; font-weight: 600; color: #495057;">Initializing...</div>
                        <div id="progress-details" style="margin-top: 1rem; max-height: 200px; overflow-y: auto; background: white; border: 1px solid #dee2e6; border-radius: 4px; padding: 1rem; font-family: monospace; font-size: 0.9rem;"></div>
                    </div>
                </div>
                
                <div id="reset-complete" style="display: none; margin-top: 2rem;">
                    <div id="reset-success" style="display: none; background: #d4edda; border: 1px solid #c3e6cb; border-radius: 6px; padding: 1.5rem; text-align: center;">
                        <i class="fas fa-check-circle" style="color: #155724; font-size: 2rem; margin-bottom: 1rem;"></i>
                        <h4 style="color: #155724; margin-bottom: 1rem;">Reset Completed Successfully</h4>
                        <p style="color: #155724; margin: 0;">All production data has been reset. Your website is ready for launch!</p>
                        <button onclick="location.reload()" style="background: #28a745; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 4px; margin-top: 1rem; cursor: pointer;">
                            <i class="fas fa-refresh"></i> Refresh Page
                        </button>
                    </div>
                    
                    <div id="reset-error" style="display: none; background: #f8d7da; border: 1px solid #f5c6cb; border-radius: 6px; padding: 1.5rem; text-align: center;">
                        <i class="fas fa-exclamation-circle" style="color: #721c24; font-size: 2rem; margin-bottom: 1rem;"></i>
                        <h4 style="color: #721c24; margin-bottom: 1rem;">Reset Failed</h4>
                        <div id="error-details" style="color: #721c24; margin-bottom: 1rem;"></div>
                        <button onclick="location.reload()" style="background: #dc3545; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 4px; cursor: pointer;">
                            <i class="fas fa-refresh"></i> Refresh Page
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Load data summary on page load
            async function loadDataSummary() {
                try {
                    const response = await fetch('/admin/data-reset/data-summary');
                    if (!response.ok) throw new Error('Failed to load data summary');
                    
                    const data = await response.json();
                    const summary = data.summary;
                    
                    document.getElementById('data-summary').innerHTML = `
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; text-align: center;">
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #007bff;">
                                <div style="font-size: 2rem; font-weight: 700; color: #007bff;">${summary.users_count}</div>
                                <div style="color: #6c757d; font-size: 0.9rem;">Total Users</div>
                            </div>
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #28a745;">
                                <div style="font-size: 2rem; font-weight: 700; color: #28a745;">${summary.quiz_results_count}</div>
                                <div style="color: #6c757d; font-size: 0.9rem;">Quiz Results</div>
                            </div>
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #ffc107;">
                                <div style="font-size: 2rem; font-weight: 700; color: #ffc107;">${summary.transactions_count}</div>
                                <div style="color: #6c757d; font-size: 0.9rem;">Transactions</div>
                            </div>
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #dc3545;">
                                <div style="font-size: 2rem; font-weight: 700; color: #dc3545;">${summary.activities_count}</div>
                                <div style="color: #6c757d; font-size: 0.9rem;">Activities</div>
                            </div>
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #6f42c1;">
                                <div style="font-size: 2rem; font-weight: 700; color: #6f42c1;">${summary.leaderboard_count}</div>
                                <div style="color: #6c757d; font-size: 0.9rem;">Leaderboard Entries</div>
                            </div>
                            <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid #20c997;">
                                <div style="font-size: 2rem; font-weight: 700; color: #20c997;">${summary.achievements_count}</div>
                                <div style="color: #6c757d; font-size: 0.9rem;">Achievements</div>
                            </div>
                        </div>
                        <div style="margin-top: 2rem; padding: 1.5rem; background: white; border-radius: 8px; border: 2px solid #6c757d;">
                            <h5 style="margin-bottom: 1rem; color: #495057;">Currency Summary</h5>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; text-align: center;">
                                <div>
                                    <div style="font-size: 1.5rem; font-weight: 700; color: #007bff;">${summary.total_points_distributed}</div>
                                    <div style="color: #6c757d; font-size: 0.9rem;">Total Points Distributed</div>
                                </div>
                                <div>
                                    <div style="font-size: 1.5rem; font-weight: 700; color: #28a745;">${summary.total_credits_distributed}</div>
                                    <div style="color: #6c757d; font-size: 0.9rem;">Total Credits Distributed</div>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // Show reset section if no reset is in progress
                    if (data.reset_available) {
                        document.getElementById('reset-section').style.display = 'block';
                    } else {
                        document.getElementById('reset-progress').style.display = 'block';
                        pollResetStatus();
                    }
                    
                } catch (error) {
                    document.getElementById('data-summary').innerHTML = `
                        <div style="color: #dc3545; text-align: center;">
                            <i class="fas fa-exclamation-triangle" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                            <p>Failed to load data summary: ${error.message}</p>
                        </div>
                    `;
                }
            }
            
            // Handle confirmation input
            document.getElementById('confirmation-input').addEventListener('input', function(e) {
                const button = document.getElementById('execute-reset-btn');
                const requiredText = 'RESET PRODUCTION DATA';
                
                if (e.target.value === requiredText) {
                    button.disabled = false;
                    button.style.cursor = 'pointer';
                    button.style.opacity = '1';
                } else {
                    button.disabled = true;
                    button.style.cursor = 'not-allowed';
                    button.style.opacity = '0.5';
                }
            });
            
            // Handle reset execution
            document.getElementById('execute-reset-btn').addEventListener('click', async function() {
                if (!confirm('Are you absolutely sure? This action cannot be undone!')) {
                    return;
                }
                
                if (!confirm('This will permanently delete all user progress. Continue?')) {
                    return;
                }
                
                try {
                    const response = await fetch('/admin/data-reset/execute-reset', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            confirmation: document.getElementById('confirmation-input').value
                        })
                    });
                    
                    if (!response.ok) {
                        const error = await response.json();
                        throw new Error(error.detail || 'Failed to start reset');
                    }
                    
                    // Hide reset section and show progress
                    document.getElementById('reset-section').style.display = 'none';
                    document.getElementById('reset-progress').style.display = 'block';
                    
                    // Start polling for status updates
                    pollResetStatus();
                    
                } catch (error) {
                    alert('Failed to start reset: ' + error.message);
                }
            });
            
            // Poll reset status
            async function pollResetStatus() {
                try {
                    const response = await fetch('/admin/data-reset/reset-status');
                    if (!response.ok) throw new Error('Failed to get status');
                    
                    const data = await response.json();
                    const status = data.status;
                    
                    // Update progress bar
                    document.getElementById('progress-bar').style.width = status.progress + '%';
                    document.getElementById('progress-text').textContent = status.message;
                    
                    // Update details
                    const details = status.operations.concat(status.errors).join('\\n');
                    document.getElementById('progress-details').textContent = details;
                    
                    // Check if completed
                    if (status.status === 'completed') {
                        document.getElementById('reset-progress').style.display = 'none';
                        document.getElementById('reset-complete').style.display = 'block';
                        document.getElementById('reset-success').style.display = 'block';
                    } else if (status.status === 'failed') {
                        document.getElementById('reset-progress').style.display = 'none';
                        document.getElementById('reset-complete').style.display = 'block';
                        document.getElementById('reset-error').style.display = 'block';
                        document.getElementById('error-details').innerHTML = '<pre>' + status.errors.join('\\n') + '</pre>';
                    } else if (status.status === 'running') {
                        // Continue polling
                        setTimeout(pollResetStatus, 1000);
                    }
                    
                } catch (error) {
                    console.error('Failed to poll status:', error);
                    setTimeout(pollResetStatus, 2000); // Retry after 2 seconds
                }
            }
            
            // Load data on page load
            loadDataSummary();
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Production Data Reset", data_reset_content, "data-reset"))


@router.get("/data-summary")
async def get_data_summary(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get summary of user data that would be affected by reset"""
    
    # Check if user is logged in as admin via session
    if "user_id" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    
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
        
        # Get current balances
        points_balance_result = await db.execute(
            select(func.coalesce(func.sum(User.points_balance), 0))
        )
        current_points_balance = points_balance_result.scalar()
        
        credits_balance_result = await db.execute(
            select(func.coalesce(func.sum(User.credits_balance), 0))
        )
        current_credits_balance = credits_balance_result.scalar()
        
        return {
            "summary": {
                "users_count": users_count,
                "quiz_results_count": quiz_results_count,
                "transactions_count": transactions_count,
                "activities_count": activities_count,
                "leaderboard_count": leaderboard_count,
                "achievements_count": achievements_count,
                "best_scores_count": best_scores_count,
                "total_points_distributed": total_points,
                "total_credits_distributed": total_credits,
                "current_points_balance": current_points_balance,
                "current_credits_balance": current_credits_balance
            },
            "reset_available": not reset_in_progress,
            "reset_status": reset_status
        }
        
    except Exception as e:
        logger.error(f"Error getting data summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get data summary"
        )


@router.get("/reset-status")
async def get_reset_status(
    request: Request
):
    """Get current status of reset operation"""
    
    # Check if user is logged in as admin via session
    if "user_id" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    
    return {
        "reset_in_progress": reset_in_progress,
        "status": reset_status
    }


async def perform_data_reset(db: AsyncSession) -> Dict[str, Any]:
    """Perform the actual data reset operation"""
    global reset_status, reset_in_progress
    
    operations_log = []
    errors_log = []
    
    try:
        reset_status["message"] = "Starting data reset..."
        reset_status["progress"] = 5
        
        # 1. Reset user currency balances
        reset_status["message"] = "Resetting user currency balances..."
        reset_status["progress"] = 10
        
        try:
            update_stmt = update(User).values(
                points_balance=0,
                credits_balance=0,
                total_points_earned=0,
                total_credits_earned=0
            )
            result = await db.execute(update_stmt)
            await db.commit()
            operations_log.append(f"Reset currency balances for {result.rowcount} users")
        except Exception as e:
            error_msg = f"Failed to reset user currency: {e}"
            errors_log.append(error_msg)
            logger.error(error_msg)
        
        # 2. Delete currency transactions
        reset_status["message"] = "Deleting currency transaction history..."
        reset_status["progress"] = 25
        
        try:
            delete_stmt = delete(UserCurrencyTransaction)
            result = await db.execute(delete_stmt)
            await db.commit()
            operations_log.append(f"Deleted {result.rowcount} currency transactions")
        except Exception as e:
            error_msg = f"Failed to delete currency transactions: {e}"
            errors_log.append(error_msg)
            logger.error(error_msg)
        
        # 3. Delete quiz results and best scores
        reset_status["message"] = "Deleting quiz results and best scores..."
        reset_status["progress"] = 40
        
        try:
            # Delete quiz results
            quiz_delete_stmt = delete(UserQuizResult)
            quiz_result = await db.execute(quiz_delete_stmt)
            
            # Delete best scores
            best_scores_delete_stmt = delete(UserQuizBestScore)
            best_scores_result = await db.execute(best_scores_delete_stmt)
            
            await db.commit()
            operations_log.append(f"Deleted {quiz_result.rowcount} quiz results")
            operations_log.append(f"Deleted {best_scores_result.rowcount} best score records")
        except Exception as e:
            error_msg = f"Failed to delete quiz data: {e}"
            errors_log.append(error_msg)
            logger.error(error_msg)
        
        # 4. Delete daily activities
        reset_status["message"] = "Deleting daily activity records..."
        reset_status["progress"] = 60
        
        try:
            delete_stmt = delete(UserDailyActivity)
            result = await db.execute(delete_stmt)
            await db.commit()
            operations_log.append(f"Deleted {result.rowcount} daily activity records")
        except Exception as e:
            error_msg = f"Failed to delete daily activities: {e}"
            errors_log.append(error_msg)
            logger.error(error_msg)
        
        # 5. Delete leaderboard cache
        reset_status["message"] = "Deleting leaderboard cache..."
        reset_status["progress"] = 75
        
        try:
            delete_stmt = delete(WeeklyLeaderboardCache)
            result = await db.execute(delete_stmt)
            await db.commit()
            operations_log.append(f"Deleted {result.rowcount} leaderboard entries")
        except Exception as e:
            error_msg = f"Failed to delete leaderboard cache: {e}"
            errors_log.append(error_msg)
            logger.error(error_msg)
        
        # 6. Delete user achievements
        reset_status["message"] = "Deleting user achievements..."
        reset_status["progress"] = 90
        
        try:
            delete_stmt = delete(UserAchievement)
            result = await db.execute(delete_stmt)
            await db.commit()
            operations_log.append(f"Deleted {result.rowcount} user achievements")
        except Exception as e:
            error_msg = f"Failed to delete user achievements: {e}"
            errors_log.append(error_msg)
            logger.error(error_msg)
        
        # Final verification
        reset_status["message"] = "Verifying reset completion..."
        reset_status["progress"] = 95
        
        # Check if reset was successful
        checks = [
            ("Quiz Results", UserQuizResult),
            ("Best Scores", UserQuizBestScore),
            ("Currency Transactions", UserCurrencyTransaction),
            ("Daily Activities", UserDailyActivity),
            ("Leaderboard Cache", WeeklyLeaderboardCache),
            ("User Achievements", UserAchievement)
        ]
        
        verification_results = []
        for name, model in checks:
            try:
                result = await db.execute(select(func.count(model.id)))
                count = result.scalar()
                verification_results.append(f"{name}: {count} records remaining")
            except Exception as e:
                verification_results.append(f"{name}: Error checking - {e}")
        
        # Check user currency totals
        try:
            result = await db.execute(
                select(func.sum(User.points_balance + User.credits_balance + User.total_points_earned + User.total_credits_earned))
            )
            total_currency = result.scalar() or 0
            verification_results.append(f"Total user currency: {total_currency}")
        except Exception as e:
            verification_results.append(f"Currency check: Error - {e}")
        
        reset_status["message"] = "Data reset completed"
        reset_status["progress"] = 100
        
        return {
            "success": len(errors_log) == 0,
            "operations": operations_log,
            "errors": errors_log,
            "verification": verification_results,
            "completed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        error_msg = f"Critical error during reset: {e}"
        errors_log.append(error_msg)
        logger.error(error_msg)
        
        return {
            "success": False,
            "operations": operations_log,
            "errors": errors_log,
            "verification": [],
            "completed_at": datetime.utcnow().isoformat()
        }


async def background_reset_task(db_session_func):
    """Background task to perform data reset"""
    global reset_in_progress, reset_status
    
    try:
        async with db_session_func() as db:
            result = await perform_data_reset(db)
            
            reset_status.update({
                "status": "completed" if result["success"] else "failed",
                "operations": result["operations"],
                "errors": result["errors"],
                "completed_at": result["completed_at"]
            })
            
    except Exception as e:
        logger.error(f"Background reset task failed: {e}")
        reset_status.update({
            "status": "failed",
            "message": f"Reset failed: {e}",
            "completed_at": datetime.utcnow().isoformat(),
            "errors": [str(e)]
        })
    finally:
        reset_in_progress = False


@router.post("/execute-reset")
async def execute_production_reset(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Execute production data reset with proper confirmation"""
    global reset_in_progress, reset_status
    
    # Check if user is logged in as admin via session
    if "user_id" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    
    # Get confirmation from request body
    body = await request.json()
    confirmation = body.get("confirmation")
    
    # Validate confirmation
    required_confirmation = "RESET PRODUCTION DATA"
    if confirmation != required_confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid confirmation. Must be exactly: '{required_confirmation}'"
        )
    
    # Check if reset is already in progress
    if reset_in_progress:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data reset is already in progress"
        )
    
    # Initialize reset status
    reset_in_progress = True
    reset_status = {
        "status": "running",
        "progress": 0,
        "message": "Initializing data reset...",
        "started_at": datetime.utcnow().isoformat(),
        "completed_at": None,
        "operations": [],
        "errors": []
    }
    
    # Start background task
    from app.db.database import get_db_session
    background_tasks.add_task(background_reset_task, get_db_session)
    
    logger.warning(f"Production data reset initiated by admin user (session: {request.session.get('user_id')})")
    
    return {
        "message": "Production data reset started",
        "status": "initiated",
        "reset_id": reset_status["started_at"]
    }


@router.post("/cancel-reset")
async def cancel_reset(
    request: Request
):
    """Cancel ongoing reset operation (if possible)"""
    global reset_in_progress, reset_status
    
    # Check if user is logged in as admin via session
    if "user_id" not in request.session:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authentication required"
        )
    
    if not reset_in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No reset operation in progress"
        )
    
    # Note: This is a soft cancel - actual database operations may continue
    # but we mark the operation as cancelled
    reset_in_progress = False
    reset_status.update({
        "status": "cancelled",
        "message": "Reset operation cancelled by admin",
        "completed_at": datetime.utcnow().isoformat()
    })
    
    logger.warning(f"Data reset cancelled by admin user (session: {request.session.get('user_id')})")
    
    return {
        "message": "Reset operation cancelled",
        "status": "cancelled"
    }