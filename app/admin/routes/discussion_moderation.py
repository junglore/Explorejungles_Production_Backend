"""
Admin routes for discussion moderation
Handles approval workflow, reports, badges, statistics
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.db.database import get_db
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.services import ModerationService, BadgeService, DiscussionService
from app.admin.templates.base import create_html_page
from app.schemas.discussion import (
    DiscussionListItem,
    DiscussionDetail,
    AdminApprovalRequest,
    ReportResponse,
    BadgeCreate,
    BadgeUpdate,
    BadgeResponse,
    BadgeAssignmentCreate,
    PaginationParams,
    PaginatedResponse,
    AuthorSummary,
    CategorySummary
)

router = APIRouter()


# ============================================================================
# ADMIN UI ENDPOINTS
# ============================================================================

@router.get("", response_class=HTMLResponse)
@router.get("/", response_class=HTMLResponse)
async def discussions_management_page(request: Request):
    """Inline discussions management page matching admin panel design"""
    
    # Check authentication
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/admin/login", status_code=302)
    
    content = """
    <div class="page-header" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
        <div>
            <h1 class="page-title">Discussions Management</h1>
            <p class="page-subtitle">Manage community discussions, categories, and national parks</p>
        </div>
        <button id="create-discussion-btn" class="btn btn-primary" onclick="openCreateModal()">
            <i class="fas fa-plus"></i> Create Discussion
        </button>
    </div>

    <!-- Statistics Cards -->
    <div class="dashboard-grid" style="margin-bottom: 2rem;">
        <div class="dashboard-card">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="background: linear-gradient(135deg, #ffa726 0%, #fb8c00 100%); padding: 1rem; border-radius: 12px;">
                    <i class="fas fa-clock" style="color: white; font-size: 1.5rem;"></i>
                </div>
                <div>
                    <h4 id="pending-count" style="font-size: 1.5rem; font-weight: 700; margin: 0;">0</h4>
                    <p style="margin: 0; color: #718096;">Pending Approval</p>
                </div>
            </div>
        </div>
        <div class="dashboard-card">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="background: linear-gradient(135deg, #66bb6a 0%, #43a047 100%); padding: 1rem; border-radius: 12px;">
                    <i class="fas fa-check-circle" style="color: white; font-size: 1.5rem;"></i>
                </div>
                <div>
                    <h4 id="approved-count" style="font-size: 1.5rem; font-weight: 700; margin: 0;">0</h4>
                    <p style="margin: 0; color: #718096;">Approved</p>
                </div>
            </div>
        </div>
        <div class="dashboard-card">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="background: linear-gradient(135deg, #ef5350 0%, #e53935 100%); padding: 1rem; border-radius: 12px;">
                    <i class="fas fa-times-circle" style="color: white; font-size: 1.5rem;"></i>
                </div>
                <div>
                    <h4 id="rejected-count" style="font-size: 1.5rem; font-weight: 700; margin: 0;">0</h4>
                    <p style="margin: 0; color: #718096;">Rejected</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Tabs -->
    <div class="tabs-container" style="margin-bottom: 2rem;">
        <div class="tabs" style="display: flex; gap: 0.5rem; border-bottom: 2px solid #e2e8f0; flex-wrap: wrap;">
            <button class="tab-btn active" onclick="switchTab('pending')" data-tab="pending">
                <i class="fas fa-clock"></i> Pending
            </button>
            <button class="tab-btn" onclick="switchTab('approved')" data-tab="approved">
                <i class="fas fa-check-circle"></i> Approved
            </button>
            <button class="tab-btn" onclick="switchTab('rejected')" data-tab="rejected">
                <i class="fas fa-times-circle"></i> Rejected
            </button>
            <button class="tab-btn" onclick="switchTab('categories')" data-tab="categories">
                <i class="fas fa-folder"></i> Categories
            </button>
            <button class="tab-btn" onclick="switchTab('parks')" data-tab="parks">
                <i class="fas fa-tree"></i> National Parks
            </button>
        </div>
    </div>

    <!-- Search and Filter -->
    <div class="form-container" style="margin-bottom: 2rem; padding: 1.5rem;">
        <div class="form-row">
            <div class="form-group" style="flex: 2;">
                <input type="text" id="search-input" class="form-control" placeholder="Search discussions..." onkeyup="searchDiscussions()">
            </div>
            <div class="form-group">
                <select id="category-filter" class="form-control" onchange="filterDiscussions()">
                    <option value="">All Categories</option>
                </select>
            </div>
            <div class="form-group">
                <select id="type-filter" class="form-control" onchange="filterDiscussions()">
                    <option value="">All Types</option>
                    <option value="thread">Thread</option>
                    <option value="national_park">National Park</option>
                </select>
            </div>
        </div>
    </div>

    <!-- Content Area -->
    <div id="content-area" class="form-container">
        <div id="discussions-list" style="min-height: 400px;">
            <div style="text-align: center; padding: 3rem; color: #a0aec0;">
                <i class="fas fa-spinner fa-spin" style="font-size: 2rem;"></i>
                <p style="margin-top: 1rem;">Loading discussions...</p>
            </div>
        </div>
    </div>

    <!-- Pagination -->
    <div id="pagination-container" style="margin-top: 2rem; display: flex; justify-content: center; gap: 0.5rem; flex-wrap: wrap;">
    </div>

    <!-- Create/Edit Discussion Modal -->
    <div id="discussion-modal" class="modal" style="display: none;">
        <div class="modal-content" style="max-width: 800px; max-height: 90vh; overflow-y: auto;">
            <div class="modal-header">
                <h2 id="modal-title">Create Discussion</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <form id="discussion-form">
                    <input type="hidden" id="discussion-id">
                    
                    <div class="form-group">
                        <label>Discussion Type</label>
                        <select id="discussion-type" class="form-control" onchange="toggleTypeFields()" required>
                            <option value="thread">General Thread</option>
                            <option value="national_park">National Park</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Title *</label>
                        <input type="text" id="discussion-title" class="form-control" required minlength="10" maxlength="500">
                        <small style="color: #718096;">Minimum 10 characters</small>
                    </div>

                    <div id="thread-fields">
                        <div class="form-group">
                            <label>Category</label>
                            <select id="discussion-category" class="form-control">
                                <option value="">Select category (optional)</option>
                            </select>
                        </div>
                    </div>

                    <div id="park-fields" style="display: none;">
                        <div class="form-group">
                            <label>National Park *</label>
                            <select id="discussion-park" class="form-control">
                                <option value="">Select national park</option>
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Location *</label>
                            <input type="text" id="discussion-location" class="form-control" placeholder="e.g., Maharashtra, India">
                        </div>

                        <div class="form-group">
                            <label>Banner Image *</label>
                            <div class="file-upload-area" onclick="document.getElementById('banner-image').click()">
                                <i class="fas fa-cloud-upload-alt"></i>
                                <p>Click to upload banner image</p>
                                <small>PNG, JPG up to 10MB</small>
                            </div>
                            <input type="file" id="banner-image" class="file-input" accept="image/*" onchange="previewImage(this, 'banner-preview')">
                            <div id="banner-preview" style="margin-top: 1rem;"></div>
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Content *</label>
                        <textarea id="discussion-content" class="form-control" rows="6" required minlength="50" maxlength="10000"></textarea>
                        <small style="color: #718096;">Minimum 50 characters for thread, max 2000 for national park</small>
                    </div>

                    <div class="form-group">
                        <label>Tags (optional)</label>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem;" id="tags-container"></div>
                        <div style="display: flex; gap: 0.5rem;">
                            <input type="text" id="tag-input" class="form-control" placeholder="Add a tag" onkeypress="handleTagInput(event)">
                            <button type="button" class="btn btn-secondary" onclick="addTag()">Add</button>
                        </div>
                        <small style="color: #718096;">Maximum 5 tags</small>
                    </div>

                    <div class="form-group" id="media-upload-field">
                        <label>Media (optional)</label>
                        <div class="file-upload-area" onclick="document.getElementById('discussion-media').click()">
                            <i class="fas fa-image"></i>
                            <p>Click to upload image or video</p>
                            <small>PNG, JPG, MP4 up to 10MB</small>
                        </div>
                        <input type="file" id="discussion-media" class="file-input" accept="image/*,video/*" onchange="previewImage(this, 'media-preview')">
                        <div id="media-preview" style="margin-top: 1rem;"></div>
                    </div>

                    <div class="form-group">
                        <label style="display: flex; align-items: center; gap: 0.5rem; cursor: pointer;">
                            <input type="checkbox" id="auto-approve" checked>
                            <span>Auto-approve (admin)</span>
                        </label>
                    </div>

                    <div style="display: flex; gap: 1rem; justify-content: flex-end; margin-top: 2rem;">
                        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-save"></i> Save Discussion
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <style>
        .tabs-container {
            width: 100%;
        }

        .tabs {
            display: flex;
            gap: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }

        .tab-btn {
            padding: 0.875rem 1.5rem;
            border: none;
            background: none;
            color: #718096;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            border-bottom: 3px solid transparent;
            white-space: nowrap;
            font-size: 0.95rem;
        }

        .tab-btn:hover {
            color: #16a34a;
            background: rgba(22, 163, 74, 0.05);
        }

        .tab-btn.active {
            color: #16a34a;
            border-bottom-color: #16a34a;
            background: rgba(22, 163, 74, 0.1);
        }

        .modal {
            display: none;
            position: fixed;
            z-index: 10000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            overflow: auto;
            background-color: rgba(0, 0, 0, 0.5);
            animation: fadeIn 0.3s ease;
        }

        .modal.show {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        .modal-content {
            background-color: #fefefe;
            margin: auto;
            padding: 0;
            border: 1px solid #888;
            width: 90%;
            max-width: 800px;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
            from {
                transform: translateY(50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        .modal-header {
            padding: 1.5rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .modal-header h2 {
            margin: 0;
            font-size: 1.5rem;
            color: #2d3748;
        }

        .modal-close {
            background: none;
            border: none;
            font-size: 2rem;
            color: #a0aec0;
            cursor: pointer;
            transition: color 0.3s ease;
            line-height: 1;
            padding: 0;
            width: 32px;
            height: 32px;
        }

        .modal-close:hover {
            color: #e53e3e;
        }

        .modal-body {
            padding: 2rem;
        }

        .discussion-item {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            transition: all 0.3s ease;
        }

        .discussion-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
            border-color: #16a34a;
        }

        .discussion-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
            gap: 1rem;
            flex-wrap: wrap;
        }

        .discussion-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }

        .discussion-meta {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
            font-size: 0.875rem;
            color: #718096;
        }

        .discussion-content {
            color: #4a5568;
            margin: 1rem 0;
            line-height: 1.6;
        }

        .discussion-actions {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }

        .badge-success {
            background: linear-gradient(135deg, #66bb6a 0%, #43a047 100%);
            color: white;
        }

        .badge-warning {
            background: linear-gradient(135deg, #ffa726 0%, #fb8c00 100%);
            color: white;
        }

        .badge-danger {
            background: linear-gradient(135deg, #ef5350 0%, #e53935 100%);
            color: white;
        }

        .badge-info {
            background: linear-gradient(135deg, #42a5f5 0%, #1e88e5 100%);
            color: white;
        }

        .btn-sm {
            padding: 0.5rem 1rem;
            font-size: 0.875rem;
        }

        .pagination {
            display: flex;
            gap: 0.5rem;
            justify-content: center;
            flex-wrap: wrap;
        }

        .pagination button {
            padding: 0.5rem 1rem;
            border: 1px solid #e2e8f0;
            background: white;
            color: #4a5568;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
        }

        .pagination button:hover:not(:disabled) {
            background: #16a34a;
            color: white;
            border-color: #16a34a;
        }

        .pagination button.active {
            background: #16a34a;
            color: white;
            border-color: #16a34a;
        }

        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Mobile Responsive Styles */
        @media (max-width: 768px) {
            .page-header {
                flex-direction: column;
                align-items: flex-start !important;
            }

            .dashboard-grid {
                grid-template-columns: 1fr !important;
            }

            .form-row {
                grid-template-columns: 1fr !important;
            }

            .tabs {
                flex-wrap: nowrap;
                overflow-x: auto;
            }

            .tab-btn {
                padding: 0.75rem 1rem;
                font-size: 0.85rem;
            }

            .discussion-header {
                flex-direction: column;
            }

            .discussion-actions {
                width: 100%;
            }

            .discussion-actions .btn {
                flex: 1;
                justify-content: center;
            }

            .modal-content {
                width: 95%;
                margin: 1rem;
            }

            .modal-body {
                padding: 1rem;
            }

            .modal-header {
                padding: 1rem;
            }
        }

        @media (max-width: 480px) {
            .page-title {
                font-size: 1.5rem;
            }

            .page-subtitle {
                font-size: 0.95rem;
            }

            .discussion-title {
                font-size: 1.1rem;
            }

            .btn {
                font-size: 0.875rem;
                padding: 0.75rem 1rem;
            }

            .discussion-meta {
                font-size: 0.8rem;
            }
        }
    </style>

    <script>
        const API_BASE = '/api/v1';
        let token = '';
        let currentTab = 'pending';
        let currentPage = 1;
        let discussionTags = [];
        let categoriesData = [];
        let parksData = [];

        // ============================================
        // TAB SWITCHING AND NAVIGATION
        // ============================================
        
        // Switch tab
        function switchTab(tab) {
            // Update active tab
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            document.querySelector(`[data-tab="${tab}"]`).classList.add('active');
            
            currentTab = tab;
            
            // Show different content based on tab
            if (tab === 'categories') {
                showCategoriesManagement();
            } else if (tab === 'parks') {
                showParksManagement();
            } else {
                // Show discussions for pending/approved/rejected
                document.getElementById('content-area').innerHTML = '<div id="discussions-list" style="min-height: 400px;"></div>';
                loadDiscussions(tab, 1);
            }
        }

        // ============================================
        // CATEGORIES MANAGEMENT
        // ============================================
        
        async function showCategoriesManagement() {
            const contentArea = document.getElementById('content-area');
            contentArea.innerHTML = \`
                <div style="margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center;">
                    <h3><i class="fas fa-folder"></i> Categories Management</h3>
                    <button class="btn btn-primary" onclick="openCategoryModal()">
                        <i class="fas fa-plus"></i> Add New Category
                    </button>
                </div>
                <div id="categories-list" style="min-height: 300px;">
                    <div style="text-align: center; padding: 2rem;">
                        <i class="fas fa-spinner fa-spin" style="font-size: 2rem;"></i>
                    </div>
                </div>
            \`;
            loadCategoriesManagement();
        }

        async function loadCategoriesManagement() {
            try {
                const response = await fetch('/api/v1/categories/');
                const categories = await response.json();
                
                const listEl = document.getElementById('categories-list');
                if (categories.length === 0) {
                    listEl.innerHTML = \`
                        <div style="text-align: center; padding: 3rem; color: #a0aec0;">
                            <i class="fas fa-folder-open" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                            <p>No categories yet. Create your first category!</p>
                        </div>
                    \`;
                    return;
                }
                
                listEl.innerHTML = \`
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                                <th style="padding: 1rem; text-align: left;">Name</th>
                                <th style="padding: 1rem; text-align: left;">Slug</th>
                                <th style="padding: 1rem; text-align: center;">Status</th>
                                <th style="padding: 1rem; text-align: center;">Viewers</th>
                                <th style="padding: 1rem; text-align: center;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            \${categories.map(cat => \`
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="padding: 1rem;">
                                        <strong>\${cat.name}</strong>
                                        \${cat.description ? \`<br><small style="color: #718096;">\${cat.description}</small>\` : ''}
                                    </td>
                                    <td style="padding: 1rem; color: #718096;">\${cat.slug}</td>
                                    <td style="padding: 1rem; text-align: center;">
                                        <span class="badge \${cat.is_active ? 'badge-success' : 'badge-secondary'}">
                                            \${cat.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td style="padding: 1rem; text-align: center;">\${cat.viewer_count || 0}</td>
                                    <td style="padding: 1rem; text-align: center;">
                                        <button class="btn btn-sm btn-primary" onclick="editCategory('\${cat.id}')" title="Edit">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                        <button class="btn btn-sm \${cat.is_active ? 'btn-warning' : 'btn-success'}" 
                                                onclick="toggleCategoryStatus('\${cat.id}', \${!cat.is_active})" 
                                                title="\${cat.is_active ? 'Deactivate' : 'Activate'}">
                                            <i class="fas fa-\${cat.is_active ? 'toggle-on' : 'toggle-off'}"></i>
                                        </button>
                                        <button class="btn btn-sm btn-danger" onclick="deleteCategory('\${cat.id}')" title="Delete">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            \`).join('')}
                        </tbody>
                    </table>
                \`;
            } catch (error) {
                showMessage('Error loading categories: ' + error.message, 'error');
            }
        }

        async function openCategoryModal(categoryId = null) {
            showMessage('Category modal - to be implemented with full form', 'info');
        }

        async function editCategory(id) {
            showMessage('Edit category: ' + id, 'info');
        }

        async function toggleCategoryStatus(id, isActive) {
            try {
                const response = await fetch(\`/api/v1/categories/\${id}\`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: isActive })
                });
                if (response.ok) {
                    showMessage('Category status updated', 'success');
                    loadCategoriesManagement();
                }
            } catch (error) {
                showMessage('Error updating category: ' + error.message, 'error');
            }
        }

        async function deleteCategory(id) {
            if (!confirm('Are you sure you want to delete this category?')) return;
            try {
                const response = await fetch(\`/api/v1/categories/\${id}\`, { method: 'DELETE' });
                if (response.ok) {
                    showMessage('Category deleted', 'success');
                    loadCategoriesManagement();
                } else {
                    showMessage('Error deleting category', 'error');
                }
            } catch (error) {
                showMessage('Error deleting category: ' + error.message, 'error');
            }
        }

        // ============================================
        // NATIONAL PARKS MANAGEMENT
        // ============================================
        
        async function showParksManagement() {
            const contentArea = document.getElementById('content-area');
            contentArea.innerHTML = \`
                <div style="margin-bottom: 2rem; display: flex; justify-content: space-between; align-items: center;">
                    <h3><i class="fas fa-tree"></i> National Parks Management</h3>
                    <button class="btn btn-primary" onclick="openParkModal()">
                        <i class="fas fa-plus"></i> Add New Park
                    </button>
                </div>
                <div id="parks-list" style="min-height: 300px;">
                    <div style="text-align: center; padding: 2rem;">
                        <i class="fas fa-spinner fa-spin" style="font-size: 2rem;"></i>
                    </div>
                </div>
            \`;
            loadParksManagement();
        }

        async function loadParksManagement() {
            try {
                const response = await fetch('/api/v1/national-parks/');
                const parks = await response.json();
                
                const listEl = document.getElementById('parks-list');
                if (parks.length === 0) {
                    listEl.innerHTML = \`
                        <div style="text-align: center; padding: 3rem; color: #a0aec0;">
                            <i class="fas fa-tree" style="font-size: 3rem; margin-bottom: 1rem;"></i>
                            <p>No national parks yet. Create your first park!</p>
                        </div>
                    \`;
                    return;
                }
                
                listEl.innerHTML = \`
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                                <th style="padding: 1rem; text-align: left;">Name</th>
                                <th style="padding: 1rem; text-align: left;">State</th>
                                <th style="padding: 1rem; text-align: center;">Status</th>
                                <th style="padding: 1rem; text-align: center;">Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            \${parks.map(park => \`
                                <tr style="border-bottom: 1px solid #e2e8f0;">
                                    <td style="padding: 1rem;">
                                        <strong>\${park.name}</strong>
                                        \${park.description ? \`<br><small style="color: #718096;">\${park.description}</small>\` : ''}
                                    </td>
                                    <td style="padding: 1rem; color: #718096;">\${park.state || 'N/A'}</td>
                                    <td style="padding: 1rem; text-align: center;">
                                        <span class="badge \${park.is_active ? 'badge-success' : 'badge-secondary'}">
                                            \${park.is_active ? 'Active' : 'Inactive'}
                                        </span>
                                    </td>
                                    <td style="padding: 1rem; text-align: center;">
                                        <button class="btn btn-sm btn-primary" onclick="editPark('\${park.id}')" title="Edit">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                        <button class="btn btn-sm \${park.is_active ? 'btn-warning' : 'btn-success'}" 
                                                onclick="toggleParkStatus('\${park.id}', \${!park.is_active})" 
                                                title="\${park.is_active ? 'Deactivate' : 'Activate'}">
                                            <i class="fas fa-\${park.is_active ? 'toggle-on' : 'toggle-off'}"></i>
                                        </button>
                                        <button class="btn btn-sm btn-danger" onclick="deletePark('\${park.id}')" title="Delete">
                                            <i class="fas fa-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            \`).join('')}
                        </tbody>
                    </table>
                \`;
            } catch (error) {
                showMessage('Error loading parks: ' + error.message, 'error');
            }
        }

        async function openParkModal(parkId = null) {
            const isEdit = parkId !== null;
            
            // Create modal HTML
            const modalHTML = \`
                <div id="park-modal" style="position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000;">
                    <div style="background: white; border-radius: 8px; padding: 2rem; max-width: 500px; width: 90%;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                            <h3 style="margin: 0;">\${isEdit ? 'Edit' : 'Add'} National Park</h3>
                            <button onclick="closeParkModal()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">&times;</button>
                        </div>
                        <form id="park-form" onsubmit="savePark(event); return false;">
                            <input type="hidden" id="park-id" value="\${parkId || ''}">
                            <div style="margin-bottom: 1rem;">
                                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Park Name *</label>
                                <input type="text" id="park-name" required 
                                       style="width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                            </div>
                            <div style="margin-bottom: 1rem;">
                                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">State</label>
                                <input type="text" id="park-state" 
                                       style="width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                            </div>
                            <div style="margin-bottom: 1rem;">
                                <label style="display: block; margin-bottom: 0.5rem; font-weight: 600;">Description</label>
                                <textarea id="park-description" rows="3"
                                          style="width: 100%; padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 4px;"></textarea>
                            </div>
                            <div style="margin-bottom: 1.5rem;">
                                <label style="display: flex; align-items: center; cursor: pointer;">
                                    <input type="checkbox" id="park-is-active" checked style="margin-right: 0.5rem;">
                                    Active
                                </label>
                            </div>
                            <div style="display: flex; justify-content: flex-end; gap: 1rem;">
                                <button type="button" onclick="closeParkModal()" class="btn btn-secondary">Cancel</button>
                                <button type="submit" class="btn btn-primary">Save</button>
                            </div>
                        </form>
                    </div>
                </div>
            \`;
            
            // Add modal to page
            document.body.insertAdjacentHTML('beforeend', modalHTML);
            
            // If editing, load park data
            if (isEdit) {
                try {
                    const response = await fetch(\`/api/v1/national-parks/\${parkId}\`);
                    const park = await response.json();
                    document.getElementById('park-name').value = park.name;
                    document.getElementById('park-state').value = park.state || '';
                    document.getElementById('park-description').value = park.description || '';
                    document.getElementById('park-is-active').checked = park.is_active;
                } catch (error) {
                    showMessage('Error loading park data', 'error');
                }
            }
        }

        function closeParkModal() {
            const modal = document.getElementById('park-modal');
            if (modal) {
                modal.remove();
            }
        }

        async function savePark(event) {
            event.preventDefault();
            
            const parkId = document.getElementById('park-id').value;
            const isEdit = parkId !== '';
            
            const parkData = {
                name: document.getElementById('park-name').value,
                state: document.getElementById('park-state').value || null,
                description: document.getElementById('park-description').value || null,
                is_active: document.getElementById('park-is-active').checked
            };
            
            try {
                const url = isEdit ? \`/api/v1/national-parks/\${parkId}\` : '/api/v1/national-parks/';
                const method = isEdit ? 'PUT' : 'POST';
                
                const response = await fetch(url, {
                    method: method,
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': \`Bearer \${token}\`
                    },
                    body: JSON.stringify(parkData)
                });
                
                if (!response.ok) {
                    let errorMessage = 'Failed to save park';
                    
                    try {
                        const errorData = await response.json();
                        console.log('API Error Response:', errorData);
                        
                        // Check for specific error messages
                        if (errorData.detail) {
                            const detail = errorData.detail;
                            console.log('Error detail:', detail);
                            
                            // Check if it's a duplicate park error
                            if (detail.toLowerCase().includes('already exists')) {
                                errorMessage = \`Park "\${parkData.name}" already exists!\`;
                            } else {
                                errorMessage = detail;
                            }
                        }
                    } catch (parseError) {
                        console.error('Failed to parse error response:', parseError);
                    }
                    
                    throw new Error(errorMessage);
                }
                
                showMessage(\`Park \${isEdit ? 'updated' : 'created'} successfully!\`, 'success');
                closeParkModal();
                loadParksManagement();
            } catch (error) {
                console.error('Error saving park:', error);
                showMessage(error.message, 'error');
            }
        }

        async function editPark(id) {
            openParkModal(id);
        }

        async function toggleParkStatus(id, isActive) {
            try {
                const response = await fetch(\`/api/v1/national-parks/\${id}/toggle-active\`, {
                    method: 'PATCH',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': \`Bearer \${token}\`
                    }
                });
                if (response.ok) {
                    showMessage('Park status updated', 'success');
                    loadParksManagement();
                } else {
                    const errorData = await response.json();
                    showMessage(errorData.detail || 'Error updating park status', 'error');
                }
            } catch (error) {
                showMessage('Error updating park: ' + error.message, 'error');
            }
        }

        async function deletePark(id) {
            if (!confirm('Are you sure you want to delete this park?')) return;
            try {
                const response = await fetch(\`/api/v1/national-parks/\${id}\`, {
                    method: 'DELETE',
                    headers: {
                        'Authorization': \`Bearer \${token}\`
                    }
                });
                if (response.ok) {
                    showMessage('Park deleted', 'success');
                    loadParksManagement();
                } else {
                    const errorData = await response.json();
                    showMessage(errorData.detail || 'Error deleting park', 'error');
                }
            } catch (error) {
                showMessage('Error deleting park: ' + error.message, 'error');
            }
        }

        // ============================================
        // INITIAL DATA LOADING
        // ============================================

        // Get admin token
        async function getAdminToken() {
            try {
                const response = await fetch('/admin/token');
                if (!response.ok) throw new Error('Failed to get token');
                const data = await response.json();
                token = data.access_token;
                console.log('Token obtained successfully');
                
                // Load initial data
                await Promise.all([
                    loadStats(),
                    loadCategories(),
                    loadParks(),
                    loadDiscussions(currentTab)
                ]);
            } catch (error) {
                console.error('Error getting token:', error);
                showMessage('Authentication failed. Please refresh the page.', 'error');
            }
        }

        // Load statistics
        async function loadStats() {
            try {
                const [pending, approved, rejected] = await Promise.all([
                    fetch(`${API_BASE}/discussions?status=pending&page_size=1`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }).then(r => r.json()),
                    fetch(`${API_BASE}/discussions?status=approved&page_size=1`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }).then(r => r.json()),
                    fetch(`${API_BASE}/discussions?status=rejected&page_size=1`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                    }).then(r => r.json())
                ]);

                document.getElementById('pending-count').textContent = pending.total || 0;
                document.getElementById('approved-count').textContent = approved.total || 0;
                document.getElementById('rejected-count').textContent = rejected.total || 0;
            } catch (error) {
                console.error('Error loading stats:', error);
            }
        }

        // Load categories
        async function loadCategories() {
            try {
                const response = await fetch(`${API_BASE}/discussions/categories`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await response.json();
                categoriesData = data.items || [];
                
                // Populate category filter
                const categoryFilter = document.getElementById('category-filter');
                const categorySelect = document.getElementById('discussion-category');
                
                categoriesData.forEach(cat => {
                    const option1 = document.createElement('option');
                    option1.value = cat.id;
                    option1.textContent = cat.name;
                    categoryFilter.appendChild(option1);
                    
                    const option2 = document.createElement('option');
                    option2.value = cat.id;
                    option2.textContent = cat.name;
                    categorySelect.appendChild(option2);
                });
            } catch (error) {
                console.error('Error loading categories:', error);
            }
        }

        // Load national parks
        async function loadParks() {
            try {
                const response = await fetch(`${API_BASE}/national-parks?is_active=true&limit=200`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await response.json();
                parksData = data || [];
                
                // Populate park select - show and store only the park name
                const parkSelect = document.getElementById('discussion-park');
                parksData.forEach(park => {
                    const option = document.createElement('option');
                    option.value = park.name;  // Save the exact park name
                    option.textContent = park.name;  // Display the exact park name
                    parkSelect.appendChild(option);
                });
            } catch (error) {
                console.error('Error loading parks:', error);
            }
        }

        // Load discussions
        async function loadDiscussions(tab, page = 1) {
            currentTab = tab;
            currentPage = page;
            
            const listEl = document.getElementById('discussions-list');
            listEl.innerHTML = '<div style="text-align: center; padding: 3rem;"><i class="fas fa-spinner fa-spin" style="font-size: 2rem;"></i><p style="margin-top: 1rem;">Loading...</p></div>';

            try {
                const status = tab === 'pending' ? 'pending' : tab === 'approved' ? 'approved' : 'rejected';
                const categoryFilter = document.getElementById('category-filter').value;
                const typeFilter = document.getElementById('type-filter').value;
                const searchQuery = document.getElementById('search-input').value;

                const params = new URLSearchParams({
                    status: status,
                    page: page,
                    page_size: 10,
                    sort_by: 'recent'
                });

                if (categoryFilter) params.append('category_id', categoryFilter);
                if (typeFilter) params.append('type', typeFilter);
                if (searchQuery) params.append('search', searchQuery);

                const response = await fetch(`${API_BASE}/discussions?${params}`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) throw new Error('Failed to load discussions');

                const data = await response.json();
                renderDiscussions(data.items || []);
                renderPagination(data.page, data.total_pages, data.total);
            } catch (error) {
                console.error('Error loading discussions:', error);
                listEl.innerHTML = '<div style="text-align: center; padding: 3rem; color: #e53e3e;"><i class="fas fa-exclamation-triangle" style="font-size: 2rem;"></i><p style="margin-top: 1rem;">Error loading discussions</p></div>';
            }
        }

        // Render discussions
        function renderDiscussions(discussions) {
            const listEl = document.getElementById('discussions-list');
            
            if (discussions.length === 0) {
                listEl.innerHTML = '<div style="text-align: center; padding: 3rem; color: #a0aec0;"><i class="fas fa-inbox" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i><p style="font-size: 1.125rem; font-weight: 500;">No discussions found</p></div>';
                return;
            }

            listEl.innerHTML = discussions.map(discussion => {
                const statusBadge = discussion.status === 'approved' ? 'badge-success' : discussion.status === 'pending' ? 'badge-warning' : 'badge-danger';
                const typeBadge = discussion.type === 'national_park' ? '<span class="badge badge-info">National Park</span>' : '<span class="badge" style="background: #667eea; color: white;">Thread</span>';
                
                return `
                    <div class="discussion-item">
                        <div class="discussion-header">
                            <div style="flex: 1;">
                                <div class="discussion-title">${discussion.title}</div>
                                <div class="discussion-meta">
                                    <span><i class="fas fa-user"></i> ${discussion.author?.full_name || discussion.author?.username || 'Unknown'}</span>
                                    <span><i class="fas fa-clock"></i> ${formatDate(discussion.created_at)}</span>
                                    <span><i class="fas fa-eye"></i> ${discussion.view_count || 0} views</span>
                                    <span><i class="fas fa-comment"></i> ${discussion.comment_count || 0} comments</span>
                                </div>
                            </div>
                            <div style="display: flex; gap: 0.5rem; align-items: flex-start;">
                                ${typeBadge}
                                <span class="badge ${statusBadge}">${discussion.status}</span>
                            </div>
                        </div>
                        <div class="discussion-content">
                            ${discussion.excerpt || discussion.content?.substring(0, 200) + '...' || 'No content'}
                        </div>
                        <div class="discussion-actions">
                            <a href="/community/discussions/${discussion.id}" target="_blank" class="btn btn-sm btn-secondary">
                                <i class="fas fa-eye"></i> View
                            </a>
                            ${discussion.status === 'pending' ? `
                                <button class="btn btn-sm btn-success" onclick="approveDiscussion('${discussion.id}')">
                                    <i class="fas fa-check"></i> Approve
                                </button>
                                <button class="btn btn-sm btn-danger" onclick="rejectDiscussion('${discussion.id}')">
                                    <i class="fas fa-times"></i> Reject
                                </button>
                            ` : ''}
                            <button class="btn btn-sm btn-primary" onclick="editDiscussion('${discussion.id}')">
                                <i class="fas fa-edit"></i> Edit
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteDiscussion('${discussion.id}')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Render pagination
        function renderPagination(page, totalPages, total) {
            const container = document.getElementById('pagination-container');
            
            if (totalPages <= 1) {
                container.innerHTML = '';
                return;
            }

            let html = '<div class="pagination">';
            
            // Previous button
            html += `<button onclick="loadDiscussions('${currentTab}', ${page - 1})" ${page <= 1 ? 'disabled' : ''}>
                <i class="fas fa-chevron-left"></i> Previous
            </button>`;

            // Page numbers
            const maxPages = 5;
            let startPage = Math.max(1, page - Math.floor(maxPages / 2));
            let endPage = Math.min(totalPages, startPage + maxPages - 1);
            
            if (endPage - startPage < maxPages - 1) {
                startPage = Math.max(1, endPage - maxPages + 1);
            }

            for (let i = startPage; i <= endPage; i++) {
                html += `<button onclick="loadDiscussions('${currentTab}', ${i})" class="${i === page ? 'active' : ''}">${i}</button>`;
            }

            // Next button
            html += `<button onclick="loadDiscussions('${currentTab}', ${page + 1})" ${page >= totalPages ? 'disabled' : ''}>
                Next <i class="fas fa-chevron-right"></i>
            </button>`;

            html += '</div>';
            container.innerHTML = html;
        }

        // Search and filter
        let searchTimeout;
        function searchDiscussions() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                loadDiscussions(currentTab, 1);
            }, 500);
        }

        function filterDiscussions() {
            loadDiscussions(currentTab, 1);
        }

        // Modal functions
        function openCreateModal() {
            document.getElementById('modal-title').textContent = 'Create Discussion';
            document.getElementById('discussion-form').reset();
            document.getElementById('discussion-id').value = '';
            discussionTags = [];
            renderTags();
            document.getElementById('discussion-modal').classList.add('show');
            document.getElementById('discussion-modal').style.display = 'flex';
        }

        function closeModal() {
            document.getElementById('discussion-modal').classList.remove('show');
            document.getElementById('discussion-modal').style.display = 'none';
        }

        function toggleTypeFields() {
            const type = document.getElementById('discussion-type').value;
            const threadFields = document.getElementById('thread-fields');
            const parkFields = document.getElementById('park-fields');
            const mediaField = document.getElementById('media-upload-field');

            if (type === 'national_park') {
                threadFields.style.display = 'none';
                parkFields.style.display = 'block';
                mediaField.style.display = 'none';
            } else {
                threadFields.style.display = 'block';
                parkFields.style.display = 'none';
                mediaField.style.display = 'block';
            }
        }

        // Tag management
        function addTag() {
            const input = document.getElementById('tag-input');
            const tag = input.value.trim().replace(/^#/, '');
            
            if (tag && discussionTags.length < 5 && !discussionTags.includes(tag)) {
                discussionTags.push(tag);
                renderTags();
                input.value = '';
            }
        }

        function removeTag(tag) {
            discussionTags = discussionTags.filter(t => t !== tag);
            renderTags();
        }

        function renderTags() {
            const container = document.getElementById('tags-container');
            container.innerHTML = discussionTags.map(tag => `
                <span class="badge badge-info" style="display: flex; align-items: center; gap: 0.5rem;">
                    #${tag}
                    <button type="button" onclick="removeTag('${tag}')" style="background: none; border: none; color: white; cursor: pointer; font-size: 1.2rem; line-height: 1; padding: 0;">&times;</button>
                </span>
            `).join('');
        }

        function handleTagInput(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                addTag();
            }
        }

        // File preview
        function previewImage(input, previewId) {
            const preview = document.getElementById(previewId);
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    preview.innerHTML = `<img src="${e.target.result}" style="max-width: 100%; max-height: 200px; border-radius: 8px;">`;
                };
                reader.readAsDataURL(input.files[0]);
            }
        }

        // Form submission
        document.getElementById('discussion-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = e.target.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';

            try {
                const type = document.getElementById('discussion-type').value;
                let payload = {
                    type: type,
                    title: document.getElementById('discussion-title').value,
                    content: document.getElementById('discussion-content').value,
                    tags: discussionTags
                };

                if (type === 'thread') {
                    const categoryId = document.getElementById('discussion-category').value;
                    if (categoryId) payload.category_id = categoryId;

                    // Handle media upload
                    const mediaFile = document.getElementById('discussion-media').files[0];
                    if (mediaFile) {
                        const mediaFormData = new FormData();
                        mediaFormData.append('file', mediaFile);
                        
                        const uploadRes = await fetch('/admin/upload/image', {
                            method: 'POST',
                            headers: { 'Authorization': `Bearer ${token}` },
                            body: mediaFormData
                        });
                        
                        if (uploadRes.ok) {
                            const uploadData = await uploadRes.json();
                            if (uploadData.success) {
                                payload.media_url = uploadData.url;
                            }
                        }
                    }
                } else {
                    payload.park_name = document.getElementById('discussion-park').value;
                    payload.location = document.getElementById('discussion-location').value || 'India';
                    
                    // Upload banner (required)
                    const bannerFile = document.getElementById('banner-image').files[0];
                    if (!bannerFile) {
                        throw new Error('Banner image is required for national park discussions');
                    }

                    const bannerFormData = new FormData();
                    bannerFormData.append('file', bannerFile);
                    
                    const uploadRes = await fetch('/admin/upload/image', {
                        method: 'POST',
                        headers: { 'Authorization': `Bearer ${token}` },
                        body: bannerFormData
                    });
                    
                    if (uploadRes.ok) {
                        const uploadData = await uploadRes.json();
                        if (uploadData.success) {
                            payload.banner_image = uploadData.url;
                        } else {
                            throw new Error('Failed to upload banner image');
                        }
                    }
                }

                console.log('Creating discussion:', payload);

                const response = await fetch(`${API_BASE}/discussions/`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Failed to create discussion');
                }

                showMessage('Discussion created successfully!', 'success');
                closeModal();
                await loadStats();
                await loadDiscussions(currentTab);
            } catch (error) {
                console.error('Error saving discussion:', error);
                showMessage(error.message || 'Failed to save discussion', 'error');
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-save"></i> Save Discussion';
            }
        });

        // Approve discussion
        async function approveDiscussion(id) {
            if (!confirm('Approve this discussion?')) return;

            try {
                const response = await fetch(`${API_BASE}/admin/discussions/${id}/approve`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ reason: 'Approved by admin' })
                });

                if (!response.ok) throw new Error('Failed to approve');

                showMessage('Discussion approved!', 'success');
                await loadStats();
                await loadDiscussions(currentTab);
            } catch (error) {
                console.error('Error approving:', error);
                showMessage('Failed to approve discussion', 'error');
            }
        }

        // Reject discussion
        async function rejectDiscussion(id) {
            const reason = prompt('Reason for rejection (optional):');
            if (reason === null) return;

            try {
                const response = await fetch(`${API_BASE}/admin/discussions/${id}/reject`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ reason: reason || 'Rejected by admin' })
                });

                if (!response.ok) throw new Error('Failed to reject');

                showMessage('Discussion rejected!', 'success');
                await loadStats();
                await loadDiscussions(currentTab);
            } catch (error) {
                console.error('Error rejecting:', error);
                showMessage('Failed to reject discussion', 'error');
            }
        }

        // Delete discussion
        async function deleteDiscussion(id) {
            if (!confirm('Are you sure you want to delete this discussion? This cannot be undone.')) return;

            try {
                const response = await fetch(`${API_BASE}/discussions/${id}`, {
                    method: 'DELETE',
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (!response.ok) throw new Error('Failed to delete');

                showMessage('Discussion deleted!', 'success');
                await loadStats();
                await loadDiscussions(currentTab);
            } catch (error) {
                console.error('Error deleting:', error);
                showMessage('Failed to delete discussion', 'error');
            }
        }

        // Edit discussion (simplified - just open view for now)
        function editDiscussion(id) {
            window.open(`/community/discussions/${id}`, '_blank');
        }

        // Utility functions
        function formatDate(dateString) {
            const date = new Date(dateString);
            const now = new Date();
            const diff = Math.floor((now - date) / 1000);

            if (diff < 60) return 'just now';
            if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
            if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
            if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
            return date.toLocaleDateString();
        }

        function showMessage(message, type = 'success') {
            const toast = document.createElement('div');
            toast.className = `message ${type}`;
            toast.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 10001; min-width: 300px; animation: slideInRight 0.3s ease;';
            toast.innerHTML = `
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <span>${message}</span>
                    <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; cursor: pointer; font-size: 1.2rem; margin-left: 1rem;">&times;</button>
                </div>
            `;
            document.body.appendChild(toast);

            setTimeout(() => toast.remove(), 5000);
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            getAdminToken();
        });

        // Close modal on outside click
        window.onclick = function(event) {
            const modal = document.getElementById('discussion-modal');
            if (event.target === modal) {
                closeModal();
            }
        };
    </script>
    """
    
    return HTMLResponse(content=create_html_page("Discussions Management", content, "discussions"))


# ============================================================================
# MODERATION ENDPOINTS
# ============================================================================

@router.get("/pending", response_model=PaginatedResponse[DiscussionListItem])
async def get_pending_discussions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get all pending discussions awaiting approval
    
    Admin only
    """
    pagination = PaginationParams(page=page, page_size=page_size)
    
    discussions, total = await ModerationService.get_pending_discussions(db, pagination)
    
    # Build response items
    items = []
    for discussion in discussions:
        author_summary = await DiscussionService.get_author_summary(db, discussion.author)
        
        category_summary = None
        if discussion.category:
            category_summary = CategorySummary(
                id=discussion.category.id,
                name=discussion.category.name,
                slug=discussion.category.slug
            )
        
        engagement = await DiscussionService.get_user_engagement(db, discussion.id, None)
        
        item = DiscussionListItem(
            id=discussion.id,
            type=discussion.type,
            title=discussion.title,
            slug=discussion.slug,
            excerpt=discussion.excerpt,
            author=author_summary,
            category=category_summary,
            tags=discussion.tags or [],
            status=discussion.status,
            is_pinned=discussion.is_pinned,
            is_locked=discussion.is_locked,
            view_count=discussion.view_count,
            like_count=discussion.like_count,
            comment_count=discussion.comment_count,
            reply_count=discussion.reply_count,
            is_liked_by_user=engagement['is_liked'],
            is_saved_by_user=engagement['is_saved'],
            created_at=discussion.created_at,
            last_activity_at=discussion.last_activity_at
        )
        items.append(item)
    
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=page < total_pages,
        has_previous=page > 1,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/{discussion_id}/view")
async def view_discussion_simple(
    discussion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Simple endpoint for admin to view discussion details
    Returns flat structure with just the essential fields
    """
    from sqlalchemy import select
    from app.models.discussion import Discussion
    from app.models.user import User as UserModel
    
    # Simple query with explicit join
    query = (
        select(
            Discussion.id,
            Discussion.type,
            Discussion.title,
            Discussion.content,
            Discussion.media_url,
            Discussion.banner_image,
            Discussion.park_name,
            Discussion.location,
            Discussion.tags,
            Discussion.status,
            Discussion.created_at,
            UserModel.username.label('author_username'),
            UserModel.full_name.label('author_fullname')
        )
        .outerjoin(UserModel, Discussion.author_id == UserModel.id)
        .where(Discussion.id == discussion_id)
    )
    
    result = await db.execute(query)
    row = result.first()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    # Return flat dictionary
    return {
        "id": str(row.id),
        "type": row.type,
        "title": row.title,
        "content": row.content,
        "media_url": row.media_url,
        "banner_image": row.banner_image,
        "park_name": row.park_name,
        "location": row.location,
        "tags": row.tags or [],
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "author_name": row.author_username or row.author_fullname or "Unknown User"
    }


@router.post("/{discussion_id}/approve", response_model=DiscussionDetail)
async def approve_discussion(
    discussion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Approve a pending discussion
    
    Admin only. Sets status to approved and publishes immediately.
    """
    discussion = await ModerationService.approve_discussion(
        db, discussion_id, current_admin.id
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found or not in pending status"
        )
    
    # Build response
    discussion = await DiscussionService.get_discussion_by_id(db, discussion_id)
    author_summary = await DiscussionService.get_author_summary(db, discussion.author)
    
    category_summary = None
    if discussion.category:
        category_summary = CategorySummary(
            id=discussion.category.id,
            name=discussion.category.name,
            slug=discussion.category.slug
        )
    
    engagement = await DiscussionService.get_user_engagement(db, discussion.id, current_admin.id)
    
    return DiscussionDetail(
        id=discussion.id,
        type=discussion.type,
        title=discussion.title,
        slug=discussion.slug,
        content=discussion.content,
        excerpt=discussion.excerpt,
        author=author_summary,
        category=category_summary,
        tags=discussion.tags or [],
        media_url=discussion.media_url,
        park_name=discussion.park_name,
        location=discussion.location,
        banner_image=discussion.banner_image,
        status=discussion.status,
        is_pinned=discussion.is_pinned,
        is_locked=discussion.is_locked,
        view_count=discussion.view_count,
        like_count=discussion.like_count,
        comment_count=discussion.comment_count,
        reply_count=discussion.reply_count,
        is_liked_by_user=engagement['is_liked'],
        is_saved_by_user=engagement['is_saved'],
        published_at=discussion.published_at,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        last_activity_at=discussion.last_activity_at
    )


@router.post("/{discussion_id}/reject", response_model=DiscussionDetail)
async def reject_discussion(
    discussion_id: UUID,
    rejection_data: AdminApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Reject a pending discussion
    
    Admin only. Provide rejection reason.
    """
    discussion = await ModerationService.reject_discussion(
        db, discussion_id, current_admin.id, rejection_data
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found or not in pending status"
        )
    
    # Build response
    discussion = await DiscussionService.get_discussion_by_id(db, discussion_id)
    author_summary = await DiscussionService.get_author_summary(db, discussion.author)
    
    category_summary = None
    if discussion.category:
        category_summary = CategorySummary(
            id=discussion.category.id,
            name=discussion.category.name,
            slug=discussion.category.slug
        )
    
    engagement = await DiscussionService.get_user_engagement(db, discussion.id, current_admin.id)
    
    return DiscussionDetail(
        id=discussion.id,
        type=discussion.type,
        title=discussion.title,
        slug=discussion.slug,
        content=discussion.content,
        excerpt=discussion.excerpt,
        author=author_summary,
        category=category_summary,
        tags=discussion.tags or [],
        media_url=discussion.media_url,
        park_name=discussion.park_name,
        location=discussion.location,
        banner_image=discussion.banner_image,
        status=discussion.status,
        is_pinned=discussion.is_pinned,
        is_locked=discussion.is_locked,
        view_count=discussion.view_count,
        like_count=discussion.like_count,
        comment_count=discussion.comment_count,
        reply_count=discussion.reply_count,
        is_liked_by_user=engagement['is_liked'],
        is_saved_by_user=engagement['is_saved'],
        published_at=discussion.published_at,
        created_at=discussion.created_at,
        updated_at=discussion.updated_at,
        last_activity_at=discussion.last_activity_at
    )


@router.post("/{discussion_id}/pin")
async def pin_discussion(
    discussion_id: UUID,
    pin: bool = Query(True, description="Pin (true) or unpin (false)"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Pin or unpin a discussion
    
    Pinned discussions appear at the top of listings
    """
    discussion = await ModerationService.pin_discussion(
        db, discussion_id, current_admin.id, pin
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    return {
        "message": f"Discussion {'pinned' if pin else 'unpinned'} successfully",
        "is_pinned": discussion.is_pinned
    }


@router.post("/{discussion_id}/lock")
async def lock_discussion(
    discussion_id: UUID,
    lock: bool = Query(True, description="Lock (true) or unlock (false)"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Lock or unlock a discussion
    
    Locked discussions prevent new comments
    """
    discussion = await ModerationService.lock_discussion(
        db, discussion_id, current_admin.id, lock
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    return {
        "message": f"Discussion {'locked' if lock else 'unlocked'} successfully",
        "is_locked": discussion.is_locked
    }


@router.post("/{discussion_id}/archive")
async def archive_discussion(
    discussion_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Archive a discussion
    
    Archived discussions are hidden from public view
    """
    discussion = await ModerationService.archive_discussion(
        db, discussion_id, current_admin.id
    )
    
    if not discussion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Discussion not found"
        )
    
    return {
        "message": "Discussion archived successfully",
        "status": discussion.status
    }


@router.post("/bulk-approve")
async def bulk_approve_discussions(
    discussion_ids: List[UUID],
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Bulk approve multiple discussions
    
    Admin only
    """
    count = await ModerationService.bulk_approve_discussions(
        db, discussion_ids, current_admin.id
    )
    
    return {
        "message": f"Approved {count} discussions",
        "count": count
    }


@router.post("/bulk-reject")
async def bulk_reject_discussions(
    discussion_ids: List[UUID],
    rejection_data: AdminApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Bulk reject multiple discussions
    
    Admin only. Same rejection reason applied to all.
    """
    count = await ModerationService.bulk_reject_discussions(
        db, discussion_ids, current_admin.id, rejection_data
    )
    
    return {
        "message": f"Rejected {count} discussions",
        "count": count
    }


# ============================================================================
# REPORT MANAGEMENT
# ============================================================================

@router.get("/reports")
async def get_reports(
    status: Optional[str] = Query(None, description="Filter by status: pending, reviewed, resolved, dismissed"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get all reports
    
    Admin only. Filter by status.
    """
    pagination = PaginationParams(page=page, page_size=page_size)
    
    reports, total = await ModerationService.get_reports(db, status, pagination)
    
    # Build response
    items = []
    for report in reports:
        reporter_summary = await DiscussionService.get_author_summary(db, report.reporter)
        
        item = {
            "id": report.id,
            "discussion_id": report.discussion_id,
            "discussion_title": report.discussion.title if report.discussion else None,
            "reporter": reporter_summary,
            "report_type": report.report_type,
            "reason": report.reason,
            "status": report.status,
            "admin_notes": report.admin_notes,
            "created_at": report.created_at,
            "reviewed_at": report.reviewed_at
        }
        items.append(item)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: UUID,
    resolution: str = Query(..., description="Resolution: resolved or dismissed"),
    admin_notes: Optional[str] = Query(None, description="Admin notes about the resolution"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Resolve a report
    
    Admin only. Mark as resolved or dismissed with optional notes.
    """
    if resolution not in ['resolved', 'dismissed']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolution must be 'resolved' or 'dismissed'"
        )
    
    report = await ModerationService.resolve_report(
        db, report_id, current_admin.id, resolution, admin_notes
    )
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found or not in pending status"
        )
    
    return {
        "message": f"Report {resolution}",
        "report_id": report.id,
        "status": report.status
    }


@router.get("/comments/flagged")
async def get_flagged_comments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get all flagged comments for review
    
    Admin only
    """
    pagination = PaginationParams(page=page, page_size=page_size)
    
    comments, total = await ModerationService.get_flagged_comments(db, pagination)
    
    # Build response
    items = []
    for comment in comments:
        author_summary = await DiscussionService.get_author_summary(db, comment.author)
        
        item = {
            "id": comment.id,
            "discussion_id": comment.discussion_id,
            "discussion_title": comment.discussion.title if comment.discussion else None,
            "author": author_summary,
            "content": comment.content,
            "like_count": comment.like_count,
            "dislike_count": comment.dislike_count,
            "is_flagged": comment.is_flagged,
            "status": comment.status,
            "created_at": comment.created_at
        }
        items.append(item)
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.post("/comments/{comment_id}/hide")
async def hide_comment(
    comment_id: UUID,
    hide: bool = Query(True, description="Hide (true) or unhide (false)"),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Hide or unhide a comment
    
    Admin only. Hidden comments are not shown to users.
    """
    comment = await ModerationService.hide_comment(
        db, comment_id, current_admin.id, hide
    )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found"
        )
    
    return {
        "message": f"Comment {'hidden' if hide else 'unhidden'} successfully",
        "status": comment.status
    }


@router.get("/stats")
async def get_moderation_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get moderation statistics for admin dashboard
    
    Returns counts for pending items, reports, flagged comments
    """
    stats = await ModerationService.get_moderation_stats(db)
    
    return stats


# ============================================================================
# BADGE MANAGEMENT
# ============================================================================

@router.get("/badges", response_model=List[BadgeResponse])
async def list_badges(
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    List all badges
    
    Admin only
    """
    badges = await BadgeService.list_badges(db)
    
    return [
        BadgeResponse(
            id=badge.id,
            name=badge.name,
            slug=badge.slug,
            description=badge.description,
            icon=badge.icon,
            color=badge.color,
            created_at=badge.created_at
        )
        for badge in badges
    ]


@router.post("/badges", response_model=BadgeResponse, status_code=status.HTTP_201_CREATED)
async def create_badge(
    badge_data: BadgeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Create a new badge
    
    Admin only
    """
    badge = await BadgeService.create_badge(db, badge_data)
    
    return BadgeResponse(
        id=badge.id,
        name=badge.name,
        slug=badge.slug,
        description=badge.description,
        icon=badge.icon,
        color=badge.color,
        created_at=badge.created_at
    )


@router.put("/badges/{badge_id}", response_model=BadgeResponse)
async def update_badge(
    badge_id: UUID,
    update_data: BadgeUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Update a badge
    
    Admin only
    """
    badge = await BadgeService.update_badge(db, badge_id, update_data)
    
    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not found"
        )
    
    return BadgeResponse(
        id=badge.id,
        name=badge.name,
        slug=badge.slug,
        description=badge.description,
        icon=badge.icon,
        color=badge.color,
        created_at=badge.created_at
    )


@router.delete("/badges/{badge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_badge(
    badge_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Delete a badge
    
    Admin only
    """
    deleted = await BadgeService.delete_badge(db, badge_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge not found"
        )
    
    return None


@router.post("/users/{user_id}/badges")
async def assign_badge_to_user(
    user_id: UUID,
    assignment_data: BadgeAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Assign a badge to a user
    
    Admin only
    """
    assignment = await BadgeService.assign_badge_to_user(
        db,
        assignment_data.user_id,
        assignment_data.badge_id,
        current_admin.id,
        assignment_data.note
    )
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User or badge not found, or badge already assigned"
        )
    
    return {
        "message": "Badge assigned successfully",
        "assignment_id": assignment.id
    }


@router.delete("/users/{user_id}/badges/{badge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_badge_from_user(
    user_id: UUID,
    badge_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Remove a badge from a user
    
    Admin only
    """
    removed = await BadgeService.remove_badge_from_user(db, user_id, badge_id)
    
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Badge assignment not found"
        )
    
    return None


@router.get("/users/{user_id}/badges", response_model=List[BadgeResponse])
async def get_user_badges(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get all badges for a user
    
    Admin only
    """
    badges = await BadgeService.get_user_badges(db, user_id)
    
    return badges