"""
Quiz and Myths vs Facts Configuration admin routes
Provides comprehensive system configuration overview and settings management
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Dict, Any
import logging
import json

from app.models.site_setting import SiteSetting
from app.models.site_setting import SiteSetting
from app.models.user import User
from app.admin.templates.base import create_html_page
from app.db.database import get_db_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/quiz-mvf-config", response_class=HTMLResponse)
async def quiz_mvf_config_dashboard(request: Request):
    """Quiz and Myths vs Facts configuration dashboard"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)

    try:
        async with get_db_session() as db:
            # Get current system settings
            settings_query = select(SiteSetting)
            result = await db.execute(settings_query)
            settings = result.scalars().all()
            
            # Convert to dict for easier access
            settings_dict = {}
            for setting in settings:
                settings_dict[setting.key] = {
                    'value': setting.parsed_value,
                    'description': setting.description,
                    'category': setting.category
                }
            
            # Get mythsVsFacts_config from database
            mvf_setting = settings_dict.get('mythsVsFacts_config', {}).get('value', {})
            
            # Get individual MVF settings (these take priority over JSON config)
            mvf_individual_settings = {
                'mvf_base_points_per_card': settings_dict.get('mvf_base_points_per_card', {}).get('value', 5),
                'mvf_base_credits_per_game': settings_dict.get('mvf_base_credits_per_game', {}).get('value', 3),
                'mvf_cards_per_game': settings_dict.get('mvf_cards_per_game', {}).get('value', 10),
                'mvf_max_games_per_day': settings_dict.get('mvf_max_games_per_day', {}).get('value', 20)
            }

    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        settings_dict = {}
        mvf_setting = {}

    # Extract base values from individual settings (priority) or JSON config (fallback)
    quiz_base_credits = settings_dict.get('quiz_base_credits', {}).get('value', 50)
    mvf_base_points = mvf_individual_settings.get('mvf_base_points_per_card', mvf_setting.get('basePointsPerCard', 5) if mvf_setting else 5)
    mvf_base_credits = mvf_individual_settings.get('mvf_base_credits_per_game', mvf_setting.get('baseCreditsPerGame', 3) if mvf_setting else 3)
    mvf_cards_per_game = mvf_individual_settings.get('mvf_cards_per_game', mvf_setting.get('gameParameters', {}).get('cardsPerGame', 10) if mvf_setting else 10)
    mvf_max_games_per_day = mvf_individual_settings.get('mvf_max_games_per_day', mvf_setting.get('dailyLimits', {}).get('maxGamesPerDay', 20) if mvf_setting else 20)
    mvf_daily_limits = mvf_setting.get('dailyLimits', {}) if mvf_setting else {}

    # Configuration values (now reading from database)
    default_config = {
        'quiz': {
            'basePointsPerQuestion': 5,
            'baseCreditsPerQuiz': quiz_base_credits,
            'maxTriesPerQuiz': 3,
            'maxQuizzesPerDay': 10,
            'dailyPointsLimit': settings_dict.get('daily_points_limit', {}).get('value', 500),
            'dailyCreditsLimit': settings_dict.get('daily_credit_cap_quizzes', {}).get('value', 200),
            'timeLimit': 30,
            'categories': ['Wildlife', 'Marine Life', 'Conservation', 'Climate']
        },
        'mythsVsFacts': {
            'basePointsPerCard': mvf_base_points,
            'baseCreditsPerGame': mvf_base_credits,
            'cardsPerGame': mvf_cards_per_game,
            'maxGamesPerDay': mvf_max_games_per_day,
            'dailyPointsLimit': mvf_daily_limits.get('maxPointsPerDay', 500),
            'dailyCreditsLimit': mvf_daily_limits.get('maxCreditsPerDay', 200),
            'timeLimit': mvf_setting.get('gameParameters', {}).get('timePerCard', 30) if mvf_setting else 30,
            'collections': ['Wildlife Conservation', 'Marine Myths', 'Forest Facts']
        },
        'performanceTiers': {
            'bronze': {'scoreRange': '60-74%', 'multiplier': 1.0, 'description': 'Basic Performance'},
            'silver': {'scoreRange': '75-84%', 'multiplier': 1.3, 'description': 'Good Performance'},
            'gold': {'scoreRange': '85-94%', 'multiplier': 1.6, 'description': 'Excellent Performance'},
            'platinum': {'scoreRange': '95-100%', 'multiplier': 2.0, 'description': 'Perfect Performance'}
        },
        'userTiers': {
            'bronze': {'range': '0-99 points', 'bonusMultiplier': 1.0, 'description': 'New Explorer'},
            'silver': {'range': '100-499 points', 'bonusMultiplier': 1.1, 'description': 'Wildlife Enthusiast'},
            'gold': {'range': '500-999 points', 'bonusMultiplier': 1.2, 'description': 'Conservation Advocate'},
            'platinum': {'range': '1000+ points', 'bonusMultiplier': 1.3, 'description': 'Expert Naturalist'}
        }
    }

    content = f"""
    <div style="max-width: 1200px; margin: 0 auto; padding: 2rem;">
        <div style="margin-bottom: 2rem;">
            <h1 style="color: #2d3748; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 1rem;">
                <span style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1rem; border-radius: 12px;">
                    <i class="fas fa-cogs" style="color: white; font-size: 1.5rem;"></i>
                </span>
                Quiz & Myths vs Facts Configuration
            </h1>
            <p style="color: #718096;">Comprehensive system configuration overview and settings management</p>
            <a href="/admin" style="color: #007bff; text-decoration: none;">← Back to Dashboard</a>
        </div>

        <!-- Important Notice -->
        <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-left: 4px solid #2196f3; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 2rem;">
            <h3 style="color: #1976d2; margin: 0 0 0.5rem 0;">📋 Configuration Information Panel</h3>
            <p style="color: #1976d2; margin: 0;">This panel shows current system configuration for scoring, tiers, and limits. To modify these settings, use the Settings Management section.</p>
        </div>

        <!-- Configuration Status -->
        <div style="background: {'linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%)' if settings_dict else 'linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%)'}; border-left: 4px solid {'#28a745' if settings_dict else '#ffc107'}; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 2rem;">
            <h3 style="color: {'#155724' if settings_dict else '#856404'}; margin: 0 0 0.5rem 0; display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-{'database' if settings_dict else 'exclamation-triangle'}"></i>
                Configuration Source Status
            </h3>
            <div style="color: {'#155724' if settings_dict else '#856404'};">
                <p style="margin: 0 0 0.5rem 0;"><strong>Individual MVF Settings:</strong> {'✅ Available (Takes Priority)' if 'mvf_base_points_per_card' in settings_dict else '⚠️ Not Found'}</p>
                <p style="margin: 0 0 0.5rem 0;"><strong>JSON Config:</strong> {'✅ Available (Fallback)' if mvf_setting else '⚠️ Using Defaults'}</p>
                <p style="margin: 0 0 0.5rem 0;"><strong>Database Connection:</strong> {'✅ Connected' if settings_dict else '❌ Error'}</p>
                <p style="margin: 0;"><strong>Current Values:</strong> MVF Points = {mvf_base_points} | MVF Credits = {mvf_base_credits} | Quiz Credits = {quiz_base_credits}</p>
            </div>
        </div>

        <!-- Quiz System Configuration -->
        <div style="background: white; border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 2rem; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); padding: 1.5rem;">
                <h2 style="color: white; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-question-circle"></i>
                    Quiz System Configuration
                </h2>
            </div>
            <div style="padding: 2rem;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                    <!-- Scoring System -->
                    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem;">
                        <h3 style="color: #2d3748; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                            📊 Scoring System
                        </h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Base Points per Question</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['quiz']['basePointsPerQuestion']} points</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Base Credits per Quiz</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['quiz']['baseCreditsPerQuiz']} credits</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Time Limit per Question</td>
                                <td style="padding: 0.5rem 0; color: #dc3545;">{default_config['quiz']['timeLimit']} seconds</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.5rem 0; font-weight: 600;">Max Tries per Quiz</td>
                                <td style="padding: 0.5rem 0; color: #ffc107;">{default_config['quiz']['maxTriesPerQuiz']} attempts</td>
                            </tr>
                        </table>
                    </div>

                    <!-- Daily Limits -->
                    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem;">
                        <h3 style="color: #2d3748; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                            ⏰ Daily Limits
                        </h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Max Quizzes per Day</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['quiz']['maxQuizzesPerDay']} quizzes</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Daily Points Limit</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['quiz']['dailyPointsLimit']} points</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.5rem 0; font-weight: 600;">Daily Credits Limit</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['quiz']['dailyCreditsLimit']} credits</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Myths vs Facts Configuration -->
        <div style="background: white; border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 2rem; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); padding: 1.5rem;">
                <h2 style="color: white; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-brain"></i>
                    Myths vs Facts Configuration
                </h2>
            </div>
            <div style="padding: 2rem;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                    <!-- Game System -->
                    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem;">
                        <h3 style="color: #2d3748; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                            🎮 Game System
                        </h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Base Points per Card</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['mythsVsFacts']['basePointsPerCard']} points</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Base Credits per Game</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['mythsVsFacts']['baseCreditsPerGame']} credits</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Cards per Game</td>
                                <td style="padding: 0.5rem 0; color: #17a2b8;">{default_config['mythsVsFacts']['cardsPerGame']} cards</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.5rem 0; font-weight: 600;">Time Limit per Game</td>
                                <td style="padding: 0.5rem 0; color: #dc3545;">{default_config['mythsVsFacts']['timeLimit']} seconds</td>
                            </tr>
                        </table>
                    </div>

                    <!-- Daily Limits -->
                    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem;">
                        <h3 style="color: #2d3748; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                            📅 Daily Limits
                        </h3>
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Max Games per Day</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['mythsVsFacts']['maxGamesPerDay']} games</td>
                            </tr>
                            <tr style="border-bottom: 1px solid #dee2e6;">
                                <td style="padding: 0.5rem 0; font-weight: 600;">Daily Points Limit</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['mythsVsFacts']['dailyPointsLimit']} points</td>
                            </tr>
                            <tr>
                                <td style="padding: 0.5rem 0; font-weight: 600;">Daily Credits Limit</td>
                                <td style="padding: 0.5rem 0; color: #28a745;">{default_config['mythsVsFacts']['dailyCreditsLimit']} credits</td>
                            </tr>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Performance Tiers -->
        <div style="background: white; border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 2rem; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem;">
                <h2 style="color: white; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-trophy"></i>
                    Performance Tier System
                </h2>
            </div>
            <div style="padding: 2rem;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
                    <div style="background: linear-gradient(135deg, #cd7f32 0%, #a0522d 100%); color: white; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">🥉 Bronze</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['performanceTiers']['bronze']['multiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">{default_config['performanceTiers']['bronze']['scoreRange']}</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #c0c0c0 0%, #808080 100%); color: white; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">🥈 Silver</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['performanceTiers']['silver']['multiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">{default_config['performanceTiers']['silver']['scoreRange']}</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #ffd700 0%, #daa520 100%); color: white; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">🥇 Gold</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['performanceTiers']['gold']['multiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">{default_config['performanceTiers']['gold']['scoreRange']}</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #e5e4e2 0%, #b8b8b8 100%); color: #333; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">💎 Platinum</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['performanceTiers']['platinum']['multiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.8;">{default_config['performanceTiers']['platinum']['scoreRange']}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- User Tier System -->
        <div style="background: white; border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 2rem; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); padding: 1.5rem;">
                <h2 style="color: white; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-users"></i>
                    User Tier System
                </h2>
            </div>
            <div style="padding: 2rem;">
                <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
                    <div style="background: linear-gradient(135deg, #cd7f32 0%, #a0522d 100%); color: white; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">🌱 Bronze User</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['userTiers']['bronze']['bonusMultiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">{default_config['userTiers']['bronze']['range']}</div>
                        <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 0.5rem;">{default_config['userTiers']['bronze']['description']}</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #c0c0c0 0%, #808080 100%); color: white; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">🦋 Silver User</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['userTiers']['silver']['bonusMultiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">{default_config['userTiers']['silver']['range']}</div>
                        <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 0.5rem;">{default_config['userTiers']['silver']['description']}</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #ffd700 0%, #daa520 100%); color: white; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">🦅 Gold User</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['userTiers']['gold']['bonusMultiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.9;">{default_config['userTiers']['gold']['range']}</div>
                        <div style="font-size: 0.75rem; opacity: 0.8; margin-top: 0.5rem;">{default_config['userTiers']['gold']['description']}</div>
                    </div>
                    <div style="background: linear-gradient(135deg, #e5e4e2 0%, #b8b8b8 100%); color: #333; padding: 1.5rem; border-radius: 0.5rem; text-align: center;">
                        <h3 style="margin: 0 0 0.5rem 0;">🦁 Platinum User</h3>
                        <div style="font-size: 1.5rem; font-weight: bold; margin-bottom: 0.5rem;">{default_config['userTiers']['platinum']['bonusMultiplier']}x</div>
                        <div style="font-size: 0.875rem; opacity: 0.8;">{default_config['userTiers']['platinum']['range']}</div>
                        <div style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.5rem;">{default_config['userTiers']['platinum']['description']}</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Scoring Examples -->
        <div style="background: white; border-radius: 0.75rem; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 2rem; overflow: hidden;">
            <div style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); padding: 1.5rem;">
                <h2 style="color: white; margin: 0; display: flex; align-items: center; gap: 0.5rem;">
                    <i class="fas fa-calculator"></i>
                    Scoring Examples
                </h2>
            </div>
            <div style="padding: 2rem;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem;">
                    <!-- Quiz Example -->
                    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem;">
                        <h3 style="color: #2d3748; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                            🎯 Quiz Example
                        </h3>
                        <div style="font-size: 0.875rem; margin-bottom: 1rem; color: #6c757d;">
                            5-question quiz, 80% score (Silver tier), Bronze user tier:
                        </div>
                        <div style="background: #e9ecef; padding: 1rem; border-radius: 0.25rem; font-family: monospace; font-size: 0.875rem;">
                            • Base Points: 5 questions × 5 = <strong>25 points</strong><br/>
                            • Performance Bonus: 25 × 1.3 (Silver) = <strong>32.5 points</strong><br/>
                            • User Tier Bonus: 32.5 × 1.0 (Bronze) = <strong>32.5 points</strong><br/><br/>
                            • Base Credits: <strong>2 credits</strong><br/>
                            • Final Credits: 2 × 1.0 = <strong>2 credits</strong>
                        </div>
                    </div>

                    <!-- Myths vs Facts Example -->
                    <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 0.5rem;">
                        <h3 style="color: #2d3748; margin: 0 0 1rem 0; display: flex; align-items: center; gap: 0.5rem;">
                            🧠 Myths vs Facts Example
                        </h3>
                        <div style="font-size: 0.875rem; margin-bottom: 1rem; color: #6c757d;">
                            7-card game, 100% score (Platinum tier), Gold user tier:
                        </div>
                        <div style="background: #e9ecef; padding: 1rem; border-radius: 0.25rem; font-family: monospace; font-size: 0.875rem;">
                            • Base Points: 7 cards × 5 = <strong>35 points</strong><br/>
                            • Performance Bonus: 35 × 2.0 (Platinum) = <strong>70 points</strong><br/>
                            • User Tier Bonus: 70 × 1.2 (Gold) = <strong>84 points</strong><br/><br/>
                            • Base Credits: <strong>3 credits</strong><br/>
                            • Final Credits: 3 × 1.2 = <strong>3.6 credits</strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div style="display: flex; gap: 1rem; justify-content: center; margin-top: 2rem;">
            <a href="/admin/settings" style="background: #007bff; color: white; padding: 1rem 2rem; border-radius: 0.5rem; text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-edit"></i>
                Edit Settings
            </a>
            <a href="/admin/collections" style="background: #28a745; color: white; padding: 1rem 2rem; border-radius: 0.5rem; text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-layer-group"></i>
                Manage Collections
            </a>
            <a href="/admin/analytics" style="background: #17a2b8; color: white; padding: 1rem 2rem; border-radius: 0.5rem; text-decoration: none; font-weight: 600; display: flex; align-items: center; gap: 0.5rem;">
                <i class="fas fa-chart-line"></i>
                View Analytics
            </a>
        </div>
    </div>
    """

    return create_html_page("Quiz & MVF Configuration", content)


@router.post("/quiz-mvf-config/update", response_class=JSONResponse)
async def update_mvf_config(
    request: Request,
    base_points_per_card: int = Form(...),
    base_credits_per_game: int = Form(...),
    cards_per_game: int = Form(...),
    max_games_per_day: int = Form(...),
    max_points_per_day: int = Form(...),
    max_credits_per_day: int = Form(...),
    time_per_card: int = Form(...),
    passing_score: int = Form(...)
):
    """Update Myths vs Facts configuration"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"success": False, "message": "Authentication required"}
        )
    
    try:
        async with get_db_session() as db:
            # Get existing configuration
            result = await db.execute(
                select(SiteSetting).where(SiteSetting.key == 'mythsVsFacts_config')
            )
            setting = result.scalar_one_or_none()
            
            # Build updated configuration
            updated_config = {
                "basePointsPerCard": base_points_per_card,
                "baseCreditsPerGame": base_credits_per_game,
                "performanceTiers": {
                    "bronze": {"multiplier": 1.0, "threshold": 50},
                    "silver": {"multiplier": 1.2, "threshold": 70},
                    "gold": {"multiplier": 1.5, "threshold": 85},
                    "platinum": {"multiplier": 2.0, "threshold": 95}
                },
                "userTiers": {
                    "bronze": {"bonusMultiplier": 1.0, "maxLevel": 10},
                    "silver": {"bonusMultiplier": 1.1, "maxLevel": 25},
                    "gold": {"bonusMultiplier": 1.3, "maxLevel": 50},
                    "platinum": {"bonusMultiplier": 1.5, "maxLevel": 100}
                },
                "dailyLimits": {
                    "maxGamesPerDay": max_games_per_day,
                    "maxPointsPerDay": max_points_per_day,
                    "maxCreditsPerDay": max_credits_per_day
                },
                "gameParameters": {
                    "cardsPerGame": cards_per_game,
                    "timePerCard": time_per_card,
                    "passingScore": passing_score
                }
            }
            
            if setting:
                # Update existing setting
                setting.set_value(updated_config)
            else:
                # Create new setting
                setting = SiteSetting(
                    key='mythsVsFacts_config',
                    data_type='json',
                    category='mythsVsFacts',
                    label='Myths vs Facts Configuration',
                    description='Complete configuration for the Myths vs Facts game system',
                    is_public=False
                )
                setting.set_value(updated_config)
                db.add(setting)
            
            await db.commit()
            
            return JSONResponse(content={
                "success": True,
                "message": "Myths vs Facts configuration updated successfully!",
                "config": updated_config
            })
            
    except Exception as e:
        logger.error(f"Error updating MVF configuration: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error updating configuration: {str(e)}"}
        )


@router.get("/quiz-mvf-config/api", response_class=JSONResponse)
async def get_mvf_config_api(request: Request):
    """Get current Myths vs Facts configuration as JSON"""
    
    try:
        async with get_db_session() as db:
            # Get mythsVsFacts_config from database
            result = await db.execute(
                select(SiteSetting).where(SiteSetting.key == 'mythsVsFacts_config')
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                config = setting.parsed_value
                return JSONResponse(content={
                    "success": True,
                    "config": config,
                    "source": "database"
                })
            else:
                # Return default configuration
                default_config = {
                    "basePointsPerCard": 5,
                    "baseCreditsPerGame": 3,
                    "performanceTiers": {
                        "bronze": {"multiplier": 1.0, "threshold": 50},
                        "silver": {"multiplier": 1.2, "threshold": 70},
                        "gold": {"multiplier": 1.5, "threshold": 85},
                        "platinum": {"multiplier": 2.0, "threshold": 95}
                    },
                    "userTiers": {
                        "bronze": {"bonusMultiplier": 1.0, "maxLevel": 10},
                        "silver": {"bonusMultiplier": 1.1, "maxLevel": 25},
                        "gold": {"bonusMultiplier": 1.3, "maxLevel": 50},
                        "platinum": {"bonusMultiplier": 1.5, "maxLevel": 100}
                    },
                    "dailyLimits": {
                        "maxGamesPerDay": 20,
                        "maxPointsPerDay": 500,
                        "maxCreditsPerDay": 200
                    },
                    "gameParameters": {
                        "cardsPerGame": 10,
                        "timePerCard": 30,
                        "passingScore": 60
                    }
                }
                return JSONResponse(content={
                    "success": True,
                    "config": default_config,
                    "source": "default"
                })
                
    except Exception as e:
        logger.error(f"Error fetching MVF configuration: {e}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "message": f"Error fetching configuration: {str(e)}"}
        )