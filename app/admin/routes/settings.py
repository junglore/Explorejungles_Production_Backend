"""
Admin Settings Management Routes
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import Optional
import structlog

from app.db.database import get_db_session
from app.models.site_setting import SiteSetting
from app.admin.templates.base import create_html_page

logger = structlog.get_logger()
router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings management page"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    try:
        async with get_db_session() as db:
            # Get all settings grouped by category
            result = await db.execute(
                select(SiteSetting).order_by(SiteSetting.category, SiteSetting.key)
            )
            settings = result.scalars().all()
            
            # Group settings by category
            settings_by_category = {}
            for setting in settings:
                if setting.category not in settings_by_category:
                    settings_by_category[setting.category] = []
                settings_by_category[setting.category].append(setting)
            
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        settings_by_category = {}
    
    # Generate settings form HTML
    settings_form = f"""
        <div class="page-header">
            <h1 class="page-title">Site Settings</h1>
            <p class="page-subtitle">Manage global site configuration</p>
        </div>
        
        <div id="message-container"></div>
        
        <div class="form-container">
            <form id="settingsForm" class="admin-form">
                {generate_settings_sections(settings_by_category)}
                
                <!-- Submit Button -->
                <div class="form-section">
                    <div class="form-actions">
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Save Settings
                        </button>
                        <button type="button" class="btn btn-secondary" onclick="resetForm()">
                            <i class="fas fa-undo"></i>
                            Reset
                        </button>
                    </div>
                </div>
            </form>
        </div>
        
        <script>
            // Settings form submission handler
            document.getElementById('settingsForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const submitBtn = document.querySelector('button[type="submit"]');
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
                
                try {{
                    // Collect form data
                    const formData = new FormData();
                    
                    // Get all setting inputs
                    const settingInputs = document.querySelectorAll('[data-setting-key]');
                    settingInputs.forEach(input => {{
                        const key = input.getAttribute('data-setting-key');
                        let value = input.value;
                        
                        // Handle checkboxes
                        if (input.type === 'checkbox') {{
                            value = input.checked ? 'true' : 'false';
                        }}
                        
                        formData.append(key, value);
                    }});
                    
                    const response = await fetch('/admin/settings/update', {{
                        method: 'POST',
                        body: formData
                    }});
                    
                    const result = await response.json();
                    
                    if (response.ok) {{
                        showMessage(result.message || 'Settings updated successfully', 'success');
                    }} else {{
                        showMessage(result.error || 'Failed to update settings', 'error');
                    }}
                    
                }} catch (error) {{
                    showMessage('Network error: ' + error.message, 'error');
                }} finally {{
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-save"></i> Save Settings';
                }}
            }});
            
            function resetForm() {{
                if (confirm('Are you sure you want to reset all changes?')) {{
                    document.getElementById('settingsForm').reset();
                    showMessage('Form reset to original values', 'info');
                }}
            }}
            
            function showMessage(message, type) {{
                const container = document.getElementById('message-container');
                const alertClass = type === 'error' ? 'alert-danger' : 
                                 type === 'success' ? 'alert-success' : 
                                 'alert-info';
                                 
                container.innerHTML = `
                    <div class="alert ${{alertClass}} alert-dismissible fade show" role="alert">
                        ${{message}}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                `;
            }}
        </script>
        
        <style>
            .settings-section {{
                margin-bottom: 2rem;
            }}
            
            .settings-section h3 {{
                color: #2d3748;
                margin-bottom: 1rem;
                font-size: 1.25rem;
                font-weight: 700;
                border-bottom: 2px solid #e2e8f0;
                padding-bottom: 0.5rem;
            }}
            
            .setting-item {{
                margin-bottom: 1.5rem;
                padding: 1rem;
                background: white;
                border-radius: 8px;
                border: 1px solid #e2e8f0;
            }}
            
            .setting-label {{
                font-weight: 600;
                color: #4a5568;
                margin-bottom: 0.5rem;
                display: block;
            }}
            
            .setting-description {{
                font-size: 0.875rem;
                color: #718096;
                margin-top: 0.25rem;
                font-style: italic;
            }}
            
            .checkbox-wrapper {{
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-top: 0.5rem;
            }}
            
            .alert {{
                padding: 0.75rem 1rem;
                border-radius: 8px;
                margin-bottom: 1rem;
            }}
            
            .alert-success {{
                background-color: #d1fae5;
                color: #065f46;
                border: 1px solid #a7f3d0;
            }}
            
            .alert-danger {{
                background-color: #fee2e2;
                color: #7f1d1d;
                border: 1px solid #fca5a5;
            }}
            
            .alert-info {{
                background-color: #dbeafe;
                color: #1e3a8a;
                border: 1px solid #93c5fd;
            }}
        </style>
    """
    
    return HTMLResponse(content=create_html_page("Settings", settings_form, "settings"))


@router.post("/settings/update")
async def update_settings(request: Request):
    """Update multiple settings"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required"}
        )
    
    try:
        # Get form data
        form = await request.form()
        updated_count = 0
        
        async with get_db_session() as db:
            for key, value in form.items():
                # Update each setting
                result = await db.execute(
                    update(SiteSetting)
                    .where(SiteSetting.key == key)
                    .values(value=str(value))
                )
                
                if result.rowcount > 0:
                    updated_count += 1
            
            await db.commit()
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Successfully updated {updated_count} settings",
                "updated_count": updated_count
            }
        )
        
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to update settings"}
        )


def generate_settings_sections(settings_by_category):
    """Generate HTML for settings sections"""
    html = ""
    
    category_titles = {
        'general': 'General Settings',
        'rewards': 'Rewards System',
        'myths_vs_facts': 'Myths vs Facts Game',
        'leaderboard': 'Leaderboard Settings',
        'security': 'Security & Anti-Gaming',
        'appearance': 'Appearance'
    }
    
    for category, settings in settings_by_category.items():
        category_title = category_titles.get(category, category.title())
        
        html += f"""
        <div class="form-section settings-section">
            <h3 class="section-title">{category_title}</h3>
            <div class="settings-grid">
        """
        
        for setting in settings:
            html += generate_setting_input(setting)
        
        html += """
            </div>
        </div>
        """
    
    return html


def generate_setting_input(setting: SiteSetting):
    """Generate HTML input for a single setting"""
    input_html = ""
    
    if setting.data_type == 'bool':
        checked = 'checked' if setting.parsed_value else ''
        input_html = f"""
        <div class="setting-item">
            <label class="setting-label">{setting.label}</label>
            <div class="checkbox-wrapper">
                <input type="checkbox" 
                       id="{setting.key}" 
                       data-setting-key="{setting.key}"
                       {checked}
                       class="form-checkbox">
                <label for="{setting.key}" class="checkbox-label">Enable</label>
            </div>
            {f'<div class="setting-description">{setting.description}</div>' if setting.description else ''}
        </div>
        """
    elif setting.data_type == 'int':
        input_html = f"""
        <div class="setting-item">
            <label class="setting-label" for="{setting.key}">{setting.label}</label>
            <input type="number" 
                   id="{setting.key}" 
                   data-setting-key="{setting.key}"
                   value="{setting.value}"
                   class="form-control"
                   min="0">
            {f'<div class="setting-description">{setting.description}</div>' if setting.description else ''}
        </div>
        """
    else:  # string
        input_html = f"""
        <div class="setting-item">
            <label class="setting-label" for="{setting.key}">{setting.label}</label>
            <input type="text" 
                   id="{setting.key}" 
                   data-setting-key="{setting.key}"
                   value="{setting.value}"
                   class="form-control">
            {f'<div class="setting-description">{setting.description}</div>' if setting.description else ''}
        </div>
        """
    
    return input_html