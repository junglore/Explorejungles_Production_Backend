"""
Leaderboard Administration Routes
"""

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional
import structlog
from datetime import datetime, timedelta

from app.db.database import get_db_session
from app.models.user import User
from app.models.quiz import UserQuizResult
from app.models.site_setting import SiteSetting
from app.admin.templates.base import create_html_page
from app.api.leaderboards import get_current_week_start, get_current_month_start

logger = structlog.get_logger()
router = APIRouter()


@router.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_admin_page(request: Request):
    """Leaderboard administration page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Get leaderboard statistics
            current_week_start = get_current_week_start()
            current_month_start = get_current_month_start()
            
            # Weekly stats
            weekly_participants_result = await db.execute(
                select(func.count(func.distinct(UserQuizResult.user_id)))
                .where(UserQuizResult.completed_at >= current_week_start)
            )
            weekly_participants = weekly_participants_result.scalar() or 0
            
            weekly_attempts_result = await db.execute(
                select(func.count(UserQuizResult.id))
                .where(UserQuizResult.completed_at >= current_week_start)
            )
            weekly_attempts = weekly_attempts_result.scalar() or 0
            
            # Monthly stats
            monthly_participants_result = await db.execute(
                select(func.count(func.distinct(UserQuizResult.user_id)))
                .where(UserQuizResult.completed_at >= current_month_start)
            )
            monthly_participants = monthly_participants_result.scalar() or 0
            
            monthly_attempts_result = await db.execute(
                select(func.count(UserQuizResult.id))
                .where(UserQuizResult.completed_at >= current_month_start)
            )
            monthly_attempts = monthly_attempts_result.scalar() or 0
            
            # All-time stats
            total_participants_result = await db.execute(
                select(func.count(func.distinct(UserQuizResult.user_id)))
            )
            total_participants = total_participants_result.scalar() or 0
            
            total_attempts_result = await db.execute(
                select(func.count(UserQuizResult.id))
            )
            total_attempts = total_attempts_result.scalar() or 0
            
            # Get leaderboard settings
            settings_result = await db.execute(
                select(SiteSetting).where(SiteSetting.category == 'leaderboard')
            )
            settings = {setting.key: setting for setting in settings_result.scalars().all()}
            
    except Exception as e:
        logger.error(f"Error loading leaderboard admin data: {e}")
        return HTMLResponse(
            content=create_html_page(
                "Error", 
                f"<div class='message error'>Error loading leaderboard data: {str(e)}</div>", 
                "leaderboard"
            )
        )
    
    # Generate settings form
    public_enabled = settings.get('leaderboard_public_enabled')
    public_checked = "checked" if (public_enabled and public_enabled.parsed_value) else ""
    
    show_names = settings.get('leaderboard_show_real_names')
    names_checked = "checked" if (show_names and show_names.parsed_value) else ""
    
    anonymous_mode = settings.get('leaderboard_anonymous_mode')
    anonymous_checked = "checked" if (anonymous_mode and anonymous_mode.parsed_value) else ""
    
    max_entries = settings.get('leaderboard_max_entries')
    max_entries_value = max_entries.parsed_value if max_entries else 100
    
    reset_weekly = settings.get('leaderboard_reset_weekly')
    weekly_checked = "checked" if (reset_weekly and reset_weekly.parsed_value) else ""
    
    reset_monthly = settings.get('leaderboard_reset_monthly')
    monthly_checked = "checked" if (reset_monthly and reset_monthly.parsed_value) else ""
    
    settings_form = f"""
        <div class="form-group">
            <label for="leaderboard_public_enabled">Public Leaderboards</label>
            <div class="checkbox-wrapper">
                <input type="checkbox" id="leaderboard_public_enabled" name="leaderboard_public_enabled" 
                       {public_checked} class="form-checkbox">
                <label for="leaderboard_public_enabled" class="checkbox-label">Enable public leaderboards</label>
            </div>
            <small class="field-help">Allow non-authenticated users to view leaderboards</small>
        </div>
        
        <div class="form-group">
            <label for="leaderboard_show_real_names">Show Real Names</label>
            <div class="checkbox-wrapper">
                <input type="checkbox" id="leaderboard_show_real_names" name="leaderboard_show_real_names" 
                       {names_checked} class="form-checkbox">
                <label for="leaderboard_show_real_names" class="checkbox-label">Display full names instead of usernames</label>
            </div>
            <small class="field-help">Show users' real names on public leaderboards</small>
        </div>
        
        <div class="form-group">
            <label for="leaderboard_anonymous_mode">Anonymous Mode</label>
            <div class="checkbox-wrapper">
                <input type="checkbox" id="leaderboard_anonymous_mode" name="leaderboard_anonymous_mode" 
                       {anonymous_checked} class="form-checkbox">
                <label for="leaderboard_anonymous_mode" class="checkbox-label">Allow anonymous participation</label>
            </div>
            <small class="field-help">Users can choose to appear anonymously on leaderboards</small>
        </div>
        
        <div class="form-group">
            <label for="leaderboard_max_entries">Maximum Entries</label>
            <input type="number" id="leaderboard_max_entries" name="leaderboard_max_entries" 
                   value="{max_entries_value}"
                   min="10" max="500" class="form-control">
            <small class="field-help">Maximum number of entries to display on leaderboards</small>
        </div>
        
        <div class="form-group">
            <label for="leaderboard_reset_weekly">Auto-Reset Weekly</label>
            <div class="checkbox-wrapper">
                <input type="checkbox" id="leaderboard_reset_weekly" name="leaderboard_reset_weekly" 
                       {weekly_checked} class="form-checkbox">
                <label for="leaderboard_reset_weekly" class="checkbox-label">Automatically reset weekly leaderboards</label>
            </div>
            <small class="field-help">Reset weekly leaderboards every Monday at midnight</small>
        </div>
        
        <div class="form-group">
            <label for="leaderboard_reset_monthly">Auto-Reset Monthly</label>
            <div class="checkbox-wrapper">
                <input type="checkbox" id="leaderboard_reset_monthly" name="leaderboard_reset_monthly" 
                       {monthly_checked} class="form-checkbox">
                <label for="leaderboard_reset_monthly" class="checkbox-label">Automatically reset monthly leaderboards</label>
            </div>
            <small class="field-help">Reset monthly leaderboards on the 1st of each month</small>
        </div>
    """
    
    leaderboard_content = f"""
        <div class="page-header">
            <h1 class="page-title">Leaderboard Administration</h1>
            <p class="page-subtitle">Manage leaderboard settings, rankings, and reset schedules</p>
        </div>
        
        <div id="message-container"></div>
        
        <!-- Statistics Overview -->
        <div class="stats-section">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-icon">📅</div>
                    <div class="stat-content">
                        <div class="stat-value">{weekly_participants}</div>
                        <div class="stat-label">Weekly Participants</div>
                        <div class="stat-sublabel">{weekly_attempts} attempts</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">🗓️</div>
                    <div class="stat-content">
                        <div class="stat-value">{monthly_participants}</div>
                        <div class="stat-label">Monthly Participants</div>
                        <div class="stat-sublabel">{monthly_attempts} attempts</div>
                    </div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-icon">🏆</div>
                    <div class="stat-content">
                        <div class="stat-value">{total_participants}</div>
                        <div class="stat-label">All-Time Participants</div>
                        <div class="stat-sublabel">{total_attempts} total attempts</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Manual Reset Controls -->
        <div class="form-container">
            <div class="form-section">
                <h3 class="section-title">Manual Reset Controls</h3>
                <p class="section-description">Use these controls to manually reset leaderboards. This action cannot be undone.</p>
                
                <div class="reset-controls">
                    <div class="reset-option">
                        <div class="reset-info">
                            <h4>Weekly Leaderboard</h4>
                            <p>Reset current week's rankings and start fresh</p>
                        </div>
                        <button onclick="confirmReset('weekly')" class="btn btn-warning">
                            <i class="fas fa-refresh"></i> Reset Weekly
                        </button>
                    </div>
                    
                    <div class="reset-option">
                        <div class="reset-info">
                            <h4>Monthly Leaderboard</h4>
                            <p>Reset current month's rankings and start fresh</p>
                        </div>
                        <button onclick="confirmReset('monthly')" class="btn btn-warning">
                            <i class="fas fa-refresh"></i> Reset Monthly
                        </button>
                    </div>
                    
                    <div class="reset-option">
                        <div class="reset-info">
                            <h4>All-Time Leaderboard</h4>
                            <p><strong>⚠️ DANGER:</strong> This will permanently delete all quiz results and rankings</p>
                        </div>
                        <button onclick="confirmReset('alltime')" class="btn btn-danger">
                            <i class="fas fa-exclamation-triangle"></i> Reset All-Time
                        </button>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Leaderboard Settings -->
        <div class="form-container">
            <form id="leaderboardSettingsForm" class="admin-form">
                <div class="form-section">
                    <h3 class="section-title">Leaderboard Settings</h3>
                    <p class="section-description">Configure leaderboard visibility, privacy, and behavior</p>
                    
                    {settings_form}
                    
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i> Save Settings
                        </button>
                    </div>
                </div>
            </form>
        </div>
        
        <!-- Reset Confirmation Modal -->
        <div id="resetModal" class="modal" style="display: none;">
            <div class="modal-content">
                <h3>Confirm Leaderboard Reset</h3>
                <p id="resetMessage"></p>
                <p class="text-danger"><strong>⚠️ This action cannot be undone!</strong></p>
                <div class="modal-actions">
                    <button onclick="closeResetModal()" class="btn btn-secondary">Cancel</button>
                    <button onclick="executeReset()" class="btn btn-danger">Confirm Reset</button>
                </div>
            </div>
        </div>
        
        <style>
            .stats-section {{
                margin-bottom: 2rem;
            }}
            
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
            }}
            
            .stat-card {{
                background: white;
                border-radius: 16px;
                padding: 1.5rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                display: flex;
                align-items: center;
                gap: 1rem;
            }}
            
            .stat-icon {{
                font-size: 2rem;
                min-width: 60px;
                text-align: center;
            }}
            
            .stat-content {{
                flex: 1;
            }}
            
            .stat-value {{
                font-size: 2rem;
                font-weight: 700;
                color: #2d3748;
                line-height: 1;
            }}
            
            .stat-label {{
                font-size: 0.9rem;
                font-weight: 600;
                color: #4a5568;
                margin-top: 0.25rem;
            }}
            
            .stat-sublabel {{
                font-size: 0.8rem;
                color: #718096;
                margin-top: 0.25rem;
            }}
            
            .form-container {{
                background: white;
                border-radius: 16px;
                padding: 2rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                border: 1px solid #e2e8f0;
                margin-bottom: 2rem;
            }}
            
            .form-section {{
                margin-bottom: 1.5rem;
            }}
            
            .section-title {{
                color: #2d3748;
                margin-bottom: 0.5rem;
                font-size: 1.25rem;
                font-weight: 700;
            }}
            
            .section-description {{
                color: #718096;
                margin-bottom: 1.5rem;
                font-size: 0.95rem;
            }}
            
            .reset-controls {{
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }}
            
            .reset-option {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1.5rem;
                background: #f8fafc;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
            }}
            
            .reset-info h4 {{
                margin: 0 0 0.5rem 0;
                color: #2d3748;
                font-size: 1.1rem;
                font-weight: 600;
            }}
            
            .reset-info p {{
                margin: 0;
                color: #718096;
                font-size: 0.9rem;
            }}
            
            .form-group {{
                margin-bottom: 1.5rem;
            }}
            
            .form-group label {{
                display: block;
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.5rem;
            }}
            
            .form-control {{
                width: 100%;
                padding: 0.75rem;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                font-size: 0.95rem;
                transition: border-color 0.2s, box-shadow 0.2s;
            }}
            
            .form-control:focus {{
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }}
            
            .checkbox-wrapper {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                margin-top: 0.5rem;
            }}
            
            .checkbox-label {{
                font-weight: 500;
                color: #4a5568;
                cursor: pointer;
                margin-bottom: 0;
            }}
            
            .form-checkbox {{
                width: 18px;
                height: 18px;
                margin: 0;
            }}
            
            .field-help {{
                display: block;
                color: #718096;
                font-size: 0.875rem;
                margin-top: 0.5rem;
                font-style: italic;
            }}
            
            .form-actions {{
                display: flex;
                gap: 1rem;
                justify-content: flex-start;
                margin-top: 2rem;
            }}
            
            .btn {{
                padding: 0.75rem 1.5rem;
                border-radius: 8px;
                border: none;
                font-weight: 600;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 0.5rem;
                transition: all 0.2s;
            }}
            
            .btn-primary {{
                background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                color: white;
            }}
            
            .btn-primary:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            }}
            
            .btn-warning {{
                background: linear-gradient(135deg, #d69e2e 0%, #b7791f 100%);
                color: white;
            }}
            
            .btn-warning:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(214, 158, 46, 0.3);
            }}
            
            .btn-danger {{
                background: linear-gradient(135deg, #e53e3e 0%, #c53030 100%);
                color: white;
            }}
            
            .btn-danger:hover {{
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(229, 62, 62, 0.3);
            }}
            
            .btn-secondary {{
                background: #e2e8f0;
                color: #4a5568;
            }}
            
            .btn-secondary:hover {{
                background: #cbd5e0;
            }}
            
            .modal {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.5);
                display: flex;
                justify-content: center;
                align-items: center;
                z-index: 1000;
            }}
            
            .modal-content {{
                background: white;
                padding: 2rem;
                border-radius: 16px;
                max-width: 400px;
                width: 90%;
                box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            }}
            
            .modal-actions {{
                display: flex;
                gap: 1rem;
                justify-content: flex-end;
                margin-top: 1.5rem;
            }}
            
            .text-danger {{
                color: #e53e3e;
            }}
            
            .message {{
                padding: 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
                border: 1px solid;
            }}
            
            .message.success {{
                background: #f0fff4;
                color: #22543d;
                border-color: #9ae6b4;
            }}
            
            .message.error {{
                background: #fed7d7;
                color: #742a2a;
                border-color: #feb2b2;
            }}
        </style>
        
        <script>
            let resetType = null;
            
            function confirmReset(type) {{
                resetType = type;
                const modal = document.getElementById('resetModal');
                const message = document.getElementById('resetMessage');
                
                let messageText = '';
                switch(type) {{
                    case 'weekly':
                        messageText = 'Are you sure you want to reset the weekly leaderboard? This will clear all current week rankings.';
                        break;
                    case 'monthly':
                        messageText = 'Are you sure you want to reset the monthly leaderboard? This will clear all current month rankings.';
                        break;
                    case 'alltime':
                        messageText = 'Are you sure you want to reset the all-time leaderboard? This will permanently delete ALL quiz results and rankings from the system. This action is irreversible!';
                        break;
                }}
                
                message.textContent = messageText;
                modal.style.display = 'flex';
            }}
            
            function closeResetModal() {{
                resetType = null;
                document.getElementById('resetModal').style.display = 'none';
            }}
            
            async function executeReset() {{
                if (!resetType) return;
                
                try {{
                    const response = await fetch(`/admin/leaderboard/reset/${{resetType}}`, {{
                        method: 'POST',
                        credentials: 'same-origin'
                    }});
                    
                    const result = await response.json();
                    
                    if (response.ok) {{
                        showMessage(result.message, 'success');
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 2000);
                    }} else {{
                        showMessage(result.error || 'Failed to reset leaderboard', 'error');
                    }}
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
                }} finally {{
                    closeResetModal();
                }}
            }}
            
            // Settings form submission
            document.getElementById('leaderboardSettingsForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const formData = new FormData(this);
                
                try {{
                    const response = await fetch('/admin/leaderboard/settings', {{
                        method: 'POST',
                        body: formData,
                        credentials: 'same-origin'
                    }});
                    
                    const result = await response.json();
                    
                    if (response.ok) {{
                        showMessage(result.message, 'success');
                    }} else {{
                        showMessage(result.error || 'Failed to save settings', 'error');
                    }}
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
                }}
            }});
            
            function showMessage(message, type) {{
                const container = document.getElementById('message-container');
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${{type}}`;
                messageDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span>${{message}}</span>
                        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; cursor: pointer;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
                container.appendChild(messageDiv);
                
                setTimeout(() => {{
                    if (messageDiv.parentElement) {{
                        messageDiv.remove();
                    }}
                }}, 5000);
            }}
            
            // Close modal when clicking outside
            document.getElementById('resetModal').addEventListener('click', function(e) {{
                if (e.target === this) {{
                    closeResetModal();
                }}
            }});
        </script>
    """
    
    return HTMLResponse(content=create_html_page("Leaderboard Administration", leaderboard_content, "leaderboard"))


@router.post("/leaderboard/reset/{reset_type}")
async def reset_leaderboard(request: Request, reset_type: str):
    """Reset leaderboard data"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )
    
    if reset_type not in ['weekly', 'monthly', 'alltime']:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid reset type"}
        )
    
    try:
        async with get_db_session() as db:
            if reset_type == 'weekly':
                # Delete current week's results
                current_week_start = get_current_week_start()
                await db.execute(
                    delete(UserQuizResult).where(
                        UserQuizResult.completed_at >= current_week_start
                    )
                )
                message = "Weekly leaderboard reset successfully"
                
            elif reset_type == 'monthly':
                # Delete current month's results
                current_month_start = get_current_month_start()
                await db.execute(
                    delete(UserQuizResult).where(
                        UserQuizResult.completed_at >= current_month_start
                    )
                )
                message = "Monthly leaderboard reset successfully"
                
            elif reset_type == 'alltime':
                # Delete ALL quiz results - DANGER!
                await db.execute(delete(UserQuizResult))
                message = "All-time leaderboard reset successfully - all quiz results deleted"
            
            await db.commit()
            
            return JSONResponse(
                status_code=200,
                content={"message": message}
            )
            
    except Exception as e:
        logger.error(f"Error resetting leaderboard {reset_type}: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to reset leaderboard: {str(e)}"}
        )


@router.post("/leaderboard/settings")
async def update_leaderboard_settings(request: Request):
    """Update leaderboard settings"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )
    
    try:
        form_data = await request.form()
        
        # Define setting mappings
        setting_mappings = {
            'leaderboard_public_enabled': 'bool',
            'leaderboard_show_real_names': 'bool',
            'leaderboard_anonymous_mode': 'bool',
            'leaderboard_max_entries': 'int',
            'leaderboard_reset_weekly': 'bool',
            'leaderboard_reset_monthly': 'bool'
        }
        
        async with get_db_session() as db:
            updated_count = 0
            
            for key, data_type in setting_mappings.items():
                value = form_data.get(key)
                
                if data_type == 'bool':
                    # Checkbox values - if present, it's checked (true), if not present, it's false
                    value = 'true' if value else 'false'
                elif data_type == 'int':
                    value = str(value) if value else '0'
                else:
                    value = str(value) if value else ''
                
                # Update or create setting
                result = await db.execute(
                    update(SiteSetting)
                    .where(SiteSetting.key == key)
                    .values(value=value)
                )
                
                if result.rowcount > 0:
                    updated_count += 1
                else:
                    # Create new setting if it doesn't exist
                    new_setting = SiteSetting(
                        key=key,
                        value=value,
                        data_type=data_type,
                        category='leaderboard',
                        label=key.replace('_', ' ').title(),
                        description=f'Leaderboard setting: {key}'
                    )
                    db.add(new_setting)
                    updated_count += 1
            
            await db.commit()
            
            return JSONResponse(
                status_code=200,
                content={
                    "message": f"Successfully updated {updated_count} leaderboard settings",
                    "updated_count": updated_count
                }
            )
            
    except Exception as e:
        logger.error(f"Error updating leaderboard settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update settings: {str(e)}"}
        )