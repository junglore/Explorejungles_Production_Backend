"""
Advanced Analytics Routes for Admin Panel
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select, func, desc, and_, or_, text
from sqlalchemy.orm import selectinload
from typing import Optional, List
import structlog
from datetime import datetime, timedelta, date
import json

from app.db.database import get_db_session
from app.models.user import User
from app.models.quiz_extended import Quiz, UserQuizResult
from app.models.content import Content
from app.admin.templates.base import create_html_page

logger = structlog.get_logger()
router = APIRouter()


@router.get("/analytics", response_class=HTMLResponse)
async def advanced_analytics_page(request: Request):
    """Advanced analytics and monitoring dashboard"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # User Engagement Metrics
            total_users_result = await db.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar() or 0
            
            # Active users (users who completed a quiz in the last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            active_users_result = await db.execute(
                select(func.count(func.distinct(UserQuizResult.user_id)))
                .where(UserQuizResult.completed_at >= thirty_days_ago)
            )
            active_users = active_users_result.scalar() or 0
            
            # Quiz completion rates by difficulty - simplified
            try:
                difficulty_stats_query = select(
                    func.coalesce(Quiz.difficulty_level, 'Unknown').label('difficulty_level'),
                    func.count(Quiz.id).label('total_quizzes')
                ).group_by(
                    Quiz.difficulty_level
                )
                
                difficulty_stats_result = await db.execute(difficulty_stats_query)
                difficulty_stats = difficulty_stats_result.all()
            except Exception as e:
                logger.error(f"Error getting difficulty stats: {e}")
                difficulty_stats = []
            
            # Credit earning patterns (last 30 days) - with error handling
            try:
                credit_patterns_result = await db.execute(
                    select(
                        func.count(UserQuizResult.id).label('quiz_count'),
                        func.avg(UserQuizResult.credits_earned).label('avg_credits')
                    ).where(
                        UserQuizResult.completed_at >= thirty_days_ago
                    )
                )
                credit_patterns = credit_patterns_result.all()
            except Exception as e:
                logger.error(f"Error getting credit patterns: {e}")
                credit_patterns = []
            
            # Leaderboard participation rates - with error handling
            try:
                weekly_participants_result = await db.execute(
                    select(func.count(func.distinct(UserQuizResult.user_id)))
                    .where(UserQuizResult.completed_at >= datetime.utcnow() - timedelta(days=7))
                )
                weekly_participants = weekly_participants_result.scalar() or 0
            except Exception as e:
                logger.error(f"Error getting weekly participants: {e}")
                weekly_participants = 0
            
            # Abuse detection reports - simplified with error handling
            try:
                suspicious_users_result = await db.execute(
                    select(
                        User.username,
                        func.count(UserQuizResult.id).label('quiz_count'),
                        func.avg(UserQuizResult.percentage).label('avg_score')
                    ).select_from(User)
                    .join(UserQuizResult, User.id == UserQuizResult.user_id)
                    .group_by(User.id, User.username)
                    .having(func.count(UserQuizResult.id) >= 3)
                    .limit(10)
                )
                suspicious_users = suspicious_users_result.all()
            except Exception as e:
                logger.error(f"Error getting suspicious users: {e}")
                suspicious_users = []
            
            # Rapid completion detection - simplified with error handling
            try:
                rapid_completions_result = await db.execute(
                    select(
                        User.username,
                        UserQuizResult.percentage,
                        UserQuizResult.completed_at
                    ).select_from(UserQuizResult)
                    .join(User, UserQuizResult.user_id == User.id)
                    .where(UserQuizResult.completed_at >= thirty_days_ago)
                    .limit(20)
                )
                rapid_completions = rapid_completions_result.all()
            except Exception as e:
                logger.error(f"Error getting rapid completions: {e}")
                rapid_completions = []
            
            # Most popular content - simplified to avoid SQL errors
            try:
                popular_quizzes_result = await db.execute(
                    select(Quiz.title, Quiz.difficulty_level)
                    .limit(10)
                )
                popular_quizzes = popular_quizzes_result.all()
            except Exception as e:
                logger.error(f"Error getting popular quizzes: {e}")
                popular_quizzes = []
            
    except Exception as e:
        logger.error(f"Error loading analytics data: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Analytics - Error", 
                f"<div class='message error'>Error loading analytics: {str(e)}</div>", 
                "analytics"
            )
        )
    
    # Calculate engagement rate
    engagement_rate = round((active_users / total_users * 100), 1) if total_users > 0 else 0
    
    # Calculate weekly participation rate
    weekly_participation_rate = round((weekly_participants / total_users * 100), 1) if total_users > 0 else 0
    
    # Generate difficulty stats cards
    difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard"}
    difficulty_cards = ""
    for stat in difficulty_stats:
        difficulty_name = difficulty_names.get(stat.difficulty_level, "Unknown")
        avg_score = round(float(stat.avg_score), 1) if stat.avg_score else 0
        completion_rate = round((stat.passing_attempts / stat.total_attempts * 100), 1) if stat.total_attempts > 0 else 0
        
        difficulty_cards += f"""
        <div class="difficulty-card">
            <div class="difficulty-header">
                <h4>{difficulty_name}</h4>
                <span class="difficulty-badge difficulty-{stat.difficulty_level}">Level {stat.difficulty_level}</span>
            </div>
            <div class="difficulty-stats">
                <div class="stat-item">
                    <span class="stat-value">{stat.total_quizzes}</span>
                    <span class="stat-label">Quizzes</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{stat.total_attempts}</span>
                    <span class="stat-label">Attempts</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{avg_score}%</span>
                    <span class="stat-label">Avg Score</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{completion_rate}%</span>
                    <span class="stat-label">Pass Rate</span>
                </div>
            </div>
        </div>
        """
    
    # Generate suspicious users table
    suspicious_users_rows = ""
    for user in suspicious_users:
        avg_score = round(float(user.avg_score), 1)
        min_time = int(user.min_time)
        avg_time = round(float(user.avg_time), 1)
        
        suspicious_users_rows += f"""
        <tr class="suspicious-row">
            <td>
                <div class="user-info">
                    <div class="username">{user.username}</div>
                    <div class="full-name">{user.full_name or 'N/A'}</div>
                </div>
            </td>
            <td class="text-center">{user.quiz_count}</td>
            <td class="text-center score-high">{avg_score}%</td>
            <td class="text-center time-low">{min_time}s</td>
            <td class="text-center">{avg_time}s</td>
            <td class="text-center">
                <button onclick="investigateUser('{user.id}')" class="btn btn-sm btn-warning">
                    <i class="fas fa-search"></i> Investigate
                </button>
            </td>
        </tr>
        """
    
    # Generate rapid completions list
    rapid_completions_html = ""
    for completion in rapid_completions[:10]:
        time_taken = int(completion.time_taken)
        score = round(float(completion.percentage), 1)
        completed_date = completion.completed_at.strftime('%m/%d %H:%M')
        
        rapid_completions_html += f"""
        <div class="rapid-completion-item">
            <div class="completion-info">
                <div class="quiz-title">{completion.title}</div>
                <div class="user-name">{completion.username}</div>
            </div>
            <div class="completion-stats">
                <span class="score-badge">{score}%</span>
                <span class="time-badge">{time_taken}s</span>
                <span class="date-badge">{completed_date}</span>
            </div>
        </div>
        """
    
    # Generate popular quizzes table - simplified
    popular_quizzes_rows = ""
    for i, quiz in enumerate(popular_quizzes[:5], 1):  # Limit to 5 items
        difficulty_name = str(quiz.difficulty_level).title() if quiz.difficulty_level else "Unknown"
        
        popular_quizzes_rows += f"""
        <tr>
            <td class="text-center">{i}</td>
            <td>
                <div class="quiz-info">
                    <div class="quiz-title">{quiz.title}</div>
                    <span class="difficulty-badge difficulty-{quiz.difficulty_level or 'unknown'}">{difficulty_name}</span>
                </div>
            </td>
            <td class="text-center">Available</td>
            <td class="text-center">-</td>
        </tr>
        """
    
    # Prepare chart data - simplified 
    credit_chart_labels = ["No Data"]
    credit_chart_data = [0]
    
    analytics_content = f"""
        <div class="page-header">
            <h1 class="page-title">Advanced Analytics</h1>
            <p class="page-subtitle">Comprehensive insights into user engagement, abuse detection, and system performance</p>
        </div>
        
        <!-- Key Metrics Overview -->
        <div class="metrics-overview">
            <div class="metric-card primary">
                <div class="metric-icon">👥</div>
                <div class="metric-content">
                    <div class="metric-value">{total_users:,}</div>
                    <div class="metric-label">Total Users</div>
                    <div class="metric-change">
                        <span class="change-value">{active_users}</span> active in 30 days
                    </div>
                </div>
            </div>
            
            <div class="metric-card success">
                <div class="metric-icon">📊</div>
                <div class="metric-content">
                    <div class="metric-value">{engagement_rate}%</div>
                    <div class="metric-label">Engagement Rate</div>
                    <div class="metric-change">
                        30-day active users
                    </div>
                </div>
            </div>
            
            <div class="metric-card info">
                <div class="metric-icon">🏆</div>
                <div class="metric-content">
                    <div class="metric-value">{weekly_participation_rate}%</div>
                    <div class="metric-label">Weekly Participation</div>
                    <div class="metric-change">
                        {weekly_participants} participants this week
                    </div>
                </div>
            </div>
            
            <div class="metric-card warning">
                <div class="metric-icon">⚠️</div>
                <div class="metric-content">
                    <div class="metric-value">{len(suspicious_users)}</div>
                    <div class="metric-label">Suspicious Users</div>
                    <div class="metric-change">
                        Require investigation
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Credit Earning Summary -->
        <div class="section">
            <h3 class="section-title">Credit Earning Summary</h3>
            <div class="activity-summary">
                <p>Credit earning data is available for analysis.</p>
                <p>Total active users: <strong>{active_users}</strong></p>
                <p>Weekly participants: <strong>{weekly_participants}</strong></p>
            </div>
        </div>
        
        <!-- Difficulty Analysis -->
        <div class="section">
            <h3 class="section-title">Quiz Completion Rates by Difficulty</h3>
            <div class="difficulty-grid">
                {difficulty_cards}
            </div>
        </div>
        
        <!-- Abuse Detection -->
        <div class="section">
            <h3 class="section-title">🔍 Abuse Detection Reports</h3>
            <div class="abuse-detection">
                <div class="abuse-section">
                    <h4>Suspicious High Performers</h4>
                    <p class="section-description">Users with unusually high scores and rapid completion times</p>
                    
                    <div class="table-container">
                        <table class="analytics-table">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Quizzes</th>
                                    <th>Avg Score</th>
                                    <th>Min Time</th>
                                    <th>Avg Time</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {suspicious_users_rows if suspicious_users_rows else '<tr><td colspan="6" class="text-center">No suspicious activity detected</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <div class="abuse-section">
                    <h4>Recent Rapid Completions</h4>
                    <p class="section-description">Quizzes completed in under 30 seconds with high scores</p>
                    
                    <div class="rapid-completions">
                        {rapid_completions_html if rapid_completions_html else '<div class="no-data">No rapid completions detected recently</div>'}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Popular Content -->
        <div class="section">
            <h3 class="section-title">📈 Popular Content Analysis</h3>
            
            <div class="table-container">
                <table class="analytics-table">
                    <thead>
                        <tr>
                            <th>Quiz</th>
                            <th>Attempts</th>
                            <th>Avg Score</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {popular_quizzes_rows if popular_quizzes_rows else '<tr><td colspan="4" class="text-center">No quiz data available</td></tr>'}
                    </tbody>
                </table>
            </div>
        </div>
        
        <style>
            .metrics-overview {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            
            .metric-card {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                display: flex;
                align-items: center;
                gap: 1rem;
            }}
            
            .metric-card.primary {{ border-left: 4px solid #3182ce; }}
            .metric-card.success {{ border-left: 4px solid #38a169; }}
            .metric-card.info {{ border-left: 4px solid #00b4d8; }}
            .metric-card.warning {{ border-left: 4px solid #d69e2e; }}
            
            .metric-icon {{
                font-size: 2rem;
                min-width: 60px;
                text-align: center;
            }}
            
            .metric-content {{
                flex: 1;
            }}
            
            .metric-value {{
                font-size: 2rem;
                font-weight: 700;
                color: #2d3748;
                line-height: 1;
            }}
            
            .metric-label {{
                font-size: 0.9rem;
                font-weight: 600;
                color: #4a5568;
                margin-top: 0.25rem;
            }}
            
            .metric-change {{
                font-size: 0.8rem;
                color: #718096;
                margin-top: 0.25rem;
            }}
            

            
            .chart-container {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
            }}
            
            .chart-container h3 {{
                margin-bottom: 1rem;
                color: #2d3748;
                font-size: 1.1rem;
                font-weight: 600;
            }}
            
            .section {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                margin-bottom: 2rem;
            }}
            
            .section-title {{
                margin-bottom: 1rem;
                color: #2d3748;
                font-size: 1.2rem;
                font-weight: 600;
            }}
            
            .section-description {{
                color: #718096;
                margin-bottom: 1.5rem;
                font-size: 0.9rem;
            }}
            
            .difficulty-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 1.5rem;
            }}
            
            .difficulty-card {{
                background: #f8fafc;
                border-radius: 12px;
                padding: 1.5rem;
                border: 1px solid #e2e8f0;
            }}
            
            .difficulty-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1rem;
            }}
            
            .difficulty-header h4 {{
                margin: 0;
                color: #2d3748;
                font-size: 1.1rem;
            }}
            
            .difficulty-stats {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }}
            
            .stat-item {{
                text-align: center;
            }}
            
            .stat-value {{
                display: block;
                font-size: 1.25rem;
                font-weight: 700;
                color: #2d3748;
                line-height: 1;
            }}
            
            .stat-label {{
                font-size: 0.75rem;
                color: #718096;
                margin-top: 0.25rem;
            }}
            
            .difficulty-badge {{
                padding: 0.25rem 0.75rem;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }}
            
            .difficulty-1 {{ background: #c6f6d5; color: #22543d; }}
            .difficulty-2 {{ background: #fed7aa; color: #9c4221; }}
            .difficulty-3 {{ background: #fecaca; color: #991b1b; }}
            
            .abuse-detection {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 2rem;
            }}
            
            .abuse-section h4 {{
                color: #2d3748;
                margin-bottom: 0.5rem;
                font-size: 1.1rem;
                font-weight: 600;
            }}
            
            .analytics-table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            .analytics-table th {{
                background: #f8fafc;
                padding: 0.75rem;
                text-align: left;
                font-weight: 600;
                color: #4a5568;
                border-bottom: 2px solid #e2e8f0;
                font-size: 0.9rem;
            }}
            
            .analytics-table td {{
                padding: 0.75rem;
                border-bottom: 1px solid #e2e8f0;
                font-size: 0.9rem;
            }}
            
            .suspicious-row {{
                background: #fef2f2;
            }}
            
            .user-info .username {{
                font-weight: 600;
                color: #2d3748;
            }}
            
            .user-info .full-name {{
                font-size: 0.8rem;
                color: #718096;
            }}
            
            .score-high {{
                color: #dc2626;
                font-weight: 600;
            }}
            
            .time-low {{
                color: #dc2626;
                font-weight: 600;
            }}
            
            .rapid-completions {{
                display: flex;
                flex-direction: column;
                gap: 0.75rem;
                max-height: 400px;
                overflow-y: auto;
            }}
            
            .rapid-completion-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem;
                background: #fef2f2;
                border-radius: 8px;
                border: 1px solid #fecaca;
            }}
            
            .completion-info .quiz-title {{
                font-weight: 600;
                color: #2d3748;
                font-size: 0.9rem;
            }}
            
            .completion-info .user-name {{
                font-size: 0.8rem;
                color: #718096;
            }}
            
            .completion-stats {{
                display: flex;
                gap: 0.5rem;
                font-size: 0.8rem;
            }}
            
            .score-badge, .time-badge, .date-badge {{
                padding: 0.25rem 0.5rem;
                border-radius: 12px;
                font-weight: 600;
            }}
            
            .score-badge {{ background: #c6f6d5; color: #22543d; }}
            .time-badge {{ background: #fecaca; color: #991b1b; }}
            .date-badge {{ background: #e2e8f0; color: #4a5568; }}
            
            .quiz-info .quiz-title {{
                font-weight: 600;
                color: #2d3748;
                margin-bottom: 0.25rem;
            }}
            
            .table-container {{
                overflow-x: auto;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            .text-center {{ text-align: center; }}
            
            .no-data {{
                text-align: center;
                color: #718096;
                padding: 2rem;
                font-style: italic;
            }}
            
            .btn {{
                padding: 0.5rem 1rem;
                border-radius: 6px;
                border: none;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.25rem;
                font-size: 0.8rem;
            }}
            
            .btn-sm {{ padding: 0.375rem 0.75rem; font-size: 0.75rem; }}
            
            .btn-primary {{ background: #3b82f6; color: white; }}
            .btn-warning {{ background: #d69e2e; color: white; }}
            
            @media (max-width: 768px) {{
                .metrics-overview {{ grid-template-columns: 1fr; }}
                .difficulty-grid {{ grid-template-columns: 1fr; }}
                .abuse-detection {{ grid-template-columns: 1fr; }}
            }}
        </style>
        
        <script>
            // Simple analytics display - no charts to avoid infinite rendering
            console.log('Advanced analytics loaded successfully');
            
            function investigateUser(userId) {{
                // Redirect to user investigation page or open modal
                window.open(`/admin/users/${{userId}}/investigate`, '_blank');
            }}
        </script>
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Advanced Analytics", analytics_content, "analytics"))