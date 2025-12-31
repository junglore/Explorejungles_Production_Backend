"""
Base HTML templates for admin panel
"""

def create_html_page(title: str, content: str, active_page: str = "") -> str:
    """Create a complete HTML page with admin layout"""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
>
    <title>{title} - Junglore Admin</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <link href="https://cdn.quilljs.com/1.3.6/quill.snow.css" rel="stylesheet">
    <link href="/static/css/admin-file-upload.css" rel="stylesheet">
    <style>
        {get_admin_css()}
    </style>
</head>
<body>
    <div class="admin-layout">
        {get_sidebar(active_page)}
        <main class="main-content">
            {content}
        </main>
    </div>
    
    <script src="https://cdn.quilljs.com/1.3.6/quill.min.js"></script>
    <script src="/static/js/admin-file-upload.js"></script>
    <script>
        {get_admin_js()}
    </script>
</body>
</html>
"""

def get_sidebar(active_page: str = "") -> str:
    """Generate modern sidebar navigation"""
    return f"""
    <button class="mobile-menu-btn" id="mobile-menu-btn">
        <i class="fas fa-bars"></i>
    </button>
    
    <aside class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h2>🌿 Junglore</h2>
        </div>
        <nav class="sidebar-nav">
            <a href="/admin/" class="nav-link {'active' if active_page == 'dashboard' else ''}" data-page="dashboard">
                <i class="fas fa-tachometer-alt"></i>
                <span>Dashboard</span>
            </a>
            
            <div class="nav-group">
                <div class="nav-group-header" data-toggle="content-creation">
                    <i class="fas fa-plus-circle"></i>
                    <span>Content Creation</span>
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <div class="nav-group-content" id="content-creation">
                    <a href="/admin/create/blog" class="nav-link {'active' if active_page == 'blog' else ''}" data-page="blog">
                        <i class="fas fa-blog"></i>
                        <span>Blog Posts</span>
                    </a>
                    <a href="/admin/create/case-study" class="nav-link {'active' if active_page == 'case-study' else ''}" data-page="case-study">
                        <i class="fas fa-microscope"></i>
                        <span>Case Studies</span>
                    </a>
                    <a href="/admin/create/conservation" class="nav-link {'active' if active_page == 'conservation' else ''}" data-page="conservation">
                        <i class="fas fa-leaf"></i>
                        <span>Conservation</span>
                    </a>
                    <a href="/admin/create/daily-update" class="nav-link {'active' if active_page == 'daily-update' else ''}" data-page="daily-update">
                        <i class="fas fa-newspaper"></i>
                        <span>Daily Updates</span>
                    </a>
                    <a href="/admin/myths-facts/create" class="nav-link {'active' if active_page == 'myths-facts' else ''}" data-page="myths-facts">
                        <i class="fas fa-question-circle"></i>
                        <span>Myths vs Facts</span>
                    </a>
                    <a href="/admin/podcasts/create" class="nav-link {'active' if active_page == 'podcasts' else ''}" data-page="podcasts">
                        <i class="fas fa-podcast"></i>
                        <span>Podcasts</span>
                    </a>
                    <a href="/admin/quizzes/create" class="nav-link {'active' if active_page == 'quiz-create' else ''}" data-page="quiz-create">
                        <i class="fas fa-question-circle"></i>
                        <span>Quizzes</span>
                    </a>
                    <a href="/admin/videos" class="nav-link {'active' if active_page == 'videos' else ''}" data-page="videos">
                        <i class="fas fa-video"></i>
                        <span>Videos</span>
                    </a>
                </div>
            </div>
            
            <div class="nav-group">
                <div class="nav-group-header" data-toggle="management">
                    <i class="fas fa-cog"></i>
                    <span>Management</span>
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <div class="nav-group-content" id="management">
                    <a href="/admin/manage/content" class="nav-link {'active' if active_page == 'content' else ''}" data-page="content">
                        <i class="fas fa-list-alt"></i>
                        <span>All Content</span>
                    </a>
                    <a href="/admin/manage/categories" class="nav-link {'active' if active_page == 'categories' else ''}" data-page="categories">
                        <i class="fas fa-tags"></i>
                        <span>Categories</span>
                    </a>
                    <a href="/admin/myths-facts" class="nav-link {'active' if active_page == 'myths-facts' else ''}" data-page="myths-facts">
                        <i class="fas fa-question-circle"></i>
                        <span>Myths vs Facts</span>
                    </a>
                    <a href="/admin/podcasts" class="nav-link {'active' if active_page == 'podcasts' else ''}" data-page="podcasts">
                        <i class="fas fa-podcast"></i>
                        <span>Podcasts</span>
                    </a>
                    <a href="/admin/quizzes" class="nav-link {'active' if active_page == 'quiz-manage' else ''}" data-page="quiz-manage">
                        <i class="fas fa-brain"></i>
                        <span>Quiz Management</span>
                    </a>
                    <a href="/admin/quizzes/analytics" class="nav-link {'active' if active_page == 'quiz-analytics' else ''}" data-page="quiz-analytics">
                        <i class="fas fa-chart-bar"></i>
                        <span>Quiz Analytics</span>
                    </a>
                    <a href="/admin/videos" class="nav-link {'active' if active_page == 'videos' else ''}" data-page="videos">
                        <i class="fas fa-video"></i>
                        <span>Videos</span>
                    </a>
                    <a href="/admin/settings" class="nav-link {'active' if active_page == 'settings' else ''}" data-page="settings">
                        <i class="fas fa-cogs"></i>
                        <span>Site Settings</span>
                    </a>
                </div>
            </div>
            
            <div class="nav-group">
                <div class="nav-group-header" data-toggle="media-management">
                    <i class="fas fa-images"></i>
                    <span>Media Management</span>
                    <i class="fas fa-chevron-down toggle-icon"></i>
                </div>
                <div class="nav-group-content" id="media-management">
                    <a href="/admin/media/" class="nav-link {'active' if active_page == 'media' else ''}" data-page="media">
                        <i class="fas fa-images"></i>
                        <span>Media Dashboard</span>
                    </a>
                    <a href="/admin/media/upload" class="nav-link {'active' if active_page == 'media-upload' else ''}" data-page="media-upload">
                        <i class="fas fa-upload"></i>
                        <span>Upload Media</span>
                    </a>
                    <a href="/admin/media/library" class="nav-link {'active' if active_page == 'media-library' else ''}" data-page="media-library">
                        <i class="fas fa-th-large"></i>
                        <span>Media Library</span>
                    </a>
                    <a href="/admin/media/featured" class="nav-link {'active' if active_page == 'media-featured' else ''}" data-page="media-featured">
                        <i class="fas fa-star"></i>
                        <span>Featured Images</span>
                    </a>
                    <a href="/admin/videos" class="nav-link {'active' if active_page == 'videos' else ''}" data-page="videos">
                        <i class="fas fa-video"></i>
                        <span>Video Library</span>
                    </a>
                </div>
            </div>
            
            <div class="nav-group">
                <div class="nav-group-title">Account</div>
                <a href="/admin/logout" class="nav-link" data-page="logout">
                    <i class="fas fa-sign-out-alt"></i>
                    <span>Logout</span>
                </a>
            </div>
        </nav>
    </aside>
    """

def get_admin_css() -> str:
    """Get modern admin panel CSS inspired by AdminJS and modern admin panels"""
    return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
            background: #f7f9fc;
            color: #2d3748;
            line-height: 1.6;
        }
        
        .admin-layout {
            display: flex;
            min-height: 100vh;
        }
        
        /* Modern Sidebar - Dark Green Jungle Theme */
        .sidebar {
            width: 280px;
            background: linear-gradient(180deg, #1a4b1a 0%, #0f2f0f 100%);
            color: white;
            position: fixed;
            left: 0;
            top: 0;
            height: 100vh;
            overflow-y: auto;
            box-shadow: 4px 0 20px rgba(0, 0, 0, 0.1);
            z-index: 1000;
            transition: transform 0.3s ease;
        }
        
        .sidebar-header {
            padding: 2rem 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            background: rgba(0, 0, 0, 0.2);
            position: relative;
            overflow: hidden;
        }
        
        .sidebar-header::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            animation: shimmer 3s infinite;
        }
        
        @keyframes shimmer {
            0% { left: -100%; }
            100% { left: 100%; }
        }
        
        .sidebar-header h2 {
            color: #ffffff;
            font-size: 1.5rem;
            font-weight: 700;
            text-align: center;
            letter-spacing: -0.025em;
        }
        

        
        .sidebar-nav {
            padding: 1.5rem 0;
        }
        
        .nav-group {
            margin-bottom: 2rem;
        }
        
        .nav-group-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1rem 1.5rem;
            cursor: pointer;
            font-weight: 600;
            color: rgba(255, 255, 255, 0.9);
            transition: all 0.3s ease;
            user-select: none;
            position: relative;
            z-index: 10;
            border-radius: 8px;
            margin: 0.25rem 0;
        }
        
        .nav-group-header:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }
        
        .nav-group-header i {
            margin-right: 0.75rem;
            font-size: 1rem;
        }
        
        .nav-group-header .toggle-icon {
            transition: transform 0.3s ease;
            transform: rotate(0deg);
        }
        
        .nav-group-header.collapsed .toggle-icon {
            transform: rotate(-90deg);
        }
        
        .nav-group-header:hover {
            background: rgba(255, 255, 255, 0.1);
            transform: translateX(2px);
        }
        
        .nav-group-header:active {
            background: rgba(255, 255, 255, 0.2);
            transform: translateX(1px);
        }
        
        .nav-group-header:focus {
            outline: 2px solid rgba(255, 255, 255, 0.5);
            outline-offset: 2px;
        }
        
        .nav-group-content {
            padding: 0 1.5rem;
            max-height: 0;
            overflow: hidden;
            transition: all 0.3s ease;
            opacity: 0;
            transform: translateY(-10px);
            background: rgba(0, 0, 0, 0.1);
            border-radius: 8px;
            margin: 0.25rem 0;
            position: relative;
            z-index: 5;
            min-height: 0;
        }
        
        .nav-group-content.active {
            max-height: 500px !important;
            padding: 0.5rem 1.5rem 1rem 1.5rem !important;
            opacity: 1 !important;
            transform: translateY(0) !important;
            border-left: 2px solid rgba(255, 255, 255, 0.3) !important;
            margin-left: 0.5rem !important;
            background: rgba(0, 0, 0, 0.15) !important;
            display: block !important;
        }
        
        .nav-group-content .nav-link {
            padding: 0.75rem 1rem;
            margin-bottom: 0.25rem;
            border-radius: 8px;
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }
        
        .nav-group-content .nav-link:hover {
            transform: translateX(6px);
            background: rgba(255, 255, 255, 0.15);
        }
        
        .nav-group-title {
            padding: 0.5rem 1.5rem;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            color: rgba(255, 255, 255, 0.7);
            letter-spacing: 0.1em;
            margin-bottom: 0.5rem;
        }
        
        .nav-link {
            display: flex;
            align-items: center;
            padding: 1rem 1.5rem;
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
            transition: all 0.3s ease;
            border-left: 3px solid transparent;
            font-weight: 500;
        }
        
        .nav-link:hover {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            border-left-color: #4ade80;
            transform: translateX(4px);
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .nav-link.active {
            background: rgba(255, 255, 255, 0.15);
            color: white;
            border-left-color: #4ade80;
            font-weight: 600;
        }
        
        .nav-link i {
            width: 20px;
            margin-right: 1rem;
            font-size: 1.1rem;
        }
        
        /* Main Content Area */
        .main-content {
            flex: 1;
            margin-left: 280px;
            padding: 2rem;
            background: #f7f9fc;
            min-height: 100vh;
            transition: margin-left 0.3s ease;
        }
        
        .page-header {
            margin-bottom: 2.5rem;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .page-title {
            font-size: 2.25rem;
            font-weight: 800;
            color: #1a202c;
            margin-bottom: 0.5rem;
            letter-spacing: -0.025em;
        }
        
        .page-subtitle {
            color: #718096;
            font-size: 1.125rem;
            font-weight: 400;
        }
        
        /* Modern Form Container */
        .form-container {
            background: white;
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid #e2e8f0;
        }
        
        .form-section {
            margin-bottom: 2.5rem;
        }
        
        .section-title {
            font-size: 1.375rem;
            font-weight: 700;
            color: #2d3748;
            margin-bottom: 1.5rem;
            padding-bottom: 0.75rem;
            border-bottom: 2px solid #e2e8f0;
            position: relative;
        }
        
        .section-title::after {
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            width: 60px;
            height: 2px;
            background: linear-gradient(90deg, #16a34a, #15803d);
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 1.5rem;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-group label {
            display: block;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 0.75rem;
            font-size: 0.95rem;
        }
        
        .form-control {
            width: 100%;
            padding: 1rem;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            font-size: 1rem;
            transition: all 0.3s ease;
            background: #ffffff;
        }
        
        .form-control:focus {
            outline: none;
            border-color: #16a34a;
            box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.1);
            transform: translateY(-1px);
        }
        
        .form-control:hover {
            border-color: #cbd5e0;
        }
        
        /* Modern Buttons */
        .btn {
            padding: 1rem 2rem;
            border: none;
            border-radius: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 1rem;
            position: relative;
            overflow: hidden;
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }
        
        .btn:hover::before {
            left: 100%;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(22, 163, 74, 0.3);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(22, 163, 74, 0.4);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #a0aec0 0%, #718096 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(160, 174, 192, 0.3);
        }
        
        .btn-secondary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(160, 174, 192, 0.4);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(72, 187, 120, 0.3);
        }
        
        .btn-success:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(72, 187, 120, 0.4);
        }
        
        /* Error and Success Messages */
        .field-error {
            color: #e53e3e;
            font-size: 0.875rem;
            margin-top: 0.5rem;
            font-weight: 500;
        }
        
        .message {
            padding: 1.25rem;
            border-radius: 12px;
            margin-bottom: 1.5rem;
            font-weight: 500;
            border-left: 4px solid;
        }
        
        .message.success {
            background: linear-gradient(135deg, #f0fff4 0%, #c6f6d5 100%);
            color: #22543d;
            border-left-color: #38a169;
        }
        
        .message.error {
            background: linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%);
            color: #742a2a;
            border-left-color: #e53e3e;
        }
        
        /* Modern File Upload */
        .file-upload-area {
            border: 2px dashed #cbd5e0;
            border-radius: 16px;
            padding: 3rem 2rem;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
        }
        
        .file-upload-area:hover {
            border-color: #16a34a;
            background: linear-gradient(135deg, #f0fdf4 0%, #bbf7d0 100%);
            transform: translateY(-2px);
        }
        
        .file-upload-area i {
            font-size: 2.5rem;
            color: #16a34a;
            margin-bottom: 1rem;
        }
        
        .file-upload-area p {
            font-size: 1.125rem;
            font-weight: 600;
            color: #4a5568;
            margin-bottom: 0.5rem;
        }
        
        .file-upload-area small {
            color: #718096;
            font-size: 0.875rem;
        }
        
        .file-input {
            display: none;
        }
        
        /* QuillJS Editor Styling */
        .ql-toolbar {
            border-top: 2px solid #e2e8f0 !important;
            border-left: 2px solid #e2e8f0 !important;
            border-right: 2px solid #e2e8f0 !important;
            border-bottom: none !important;
            border-radius: 12px 12px 0 0 !important;
            background: #f7fafc !important;
        }
        
        .ql-container {
            border-bottom: 2px solid #e2e8f0 !important;
            border-left: 2px solid #e2e8f0 !important;
            border-right: 2px solid #e2e8f0 !important;
            border-top: none !important;
            border-radius: 0 0 12px 12px !important;
        }
        
        .ql-editor {
            min-height: 300px;
            font-size: 1rem;
            line-height: 1.6;
        }
        
        .ql-editor:focus {
            outline: none;
        }
        
        /* Dashboard Cards */
        .dashboard-card {
            background: white;
            border-radius: 16px;
            padding: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            border: 1px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        
        .dashboard-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 25px -3px rgba(0, 0, 0, 0.1);
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        /* Responsive Design */
        @media (max-width: 1024px) {
            .form-row {
                grid-template-columns: 1fr;
            }
        }
        
        @media (max-width: 768px) {
            .sidebar {
                transform: translateX(-100%);
                transition: transform 0.3s ease;
            }
            
            .sidebar.mobile-open {
                transform: translateX(0);
            }
            
            .main-content {
                margin-left: 0;
                padding: 1rem;
            }
            
            .page-title {
                font-size: 1.875rem;
            }
            
            .form-container {
                padding: 1.5rem;
            }
            
            .btn {
                padding: 0.875rem 1.5rem;
                font-size: 0.95rem;
            }
        }
        
        /* Loading States */
        .loading {
            opacity: 0.6;
            pointer-events: none;
        }
        

        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        /* Mobile Menu Button */
        .mobile-menu-btn {
            display: none;
            position: fixed;
            top: 1rem;
            left: 1rem;
            z-index: 1001;
            background: #16a34a;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem;
            cursor: pointer;
        }
        
        @media (max-width: 768px) {
            .mobile-menu-btn {
                display: block;
            }
        }
    """

def get_admin_js() -> str:
    """Get modern admin panel JavaScript with enhanced functionality"""
    return """
        // Global admin functions
        function showMessage(message, type = 'success') {
            const container = document.getElementById('message-container');
            if (container) {
                const messageEl = document.createElement('div');
                messageEl.className = `message ${type}`;
                messageEl.innerHTML = `
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span>${message}</span>
                        <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: inherit; cursor: pointer; font-size: 1.2rem;">&times;</button>
                    </div>
                `;
                container.appendChild(messageEl);
                
                // Auto-remove after 5 seconds
                setTimeout(() => {
                    if (messageEl.parentElement) {
                        messageEl.remove();
                    }
                }, 5000);
            }
        }
        
        function showFieldError(fieldId, message) {
            const errorElement = document.getElementById(fieldId);
            if (errorElement) {
                errorElement.textContent = message;
                errorElement.style.display = 'block';
            }
        }
        
        function clearFieldError(fieldId) {
            const errorElement = document.getElementById(fieldId);
            if (errorElement) {
                errorElement.textContent = '';
                errorElement.style.display = 'none';
            }
        }
        
        function clearAllErrors() {
            const errorElements = document.querySelectorAll('.field-error');
            errorElements.forEach(el => {
                el.textContent = '';
                el.style.display = 'none';
            });
        }
        
        // Mobile menu toggle
        function toggleMobileMenu() {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.toggle('mobile-open');
            }
        }
        
        // Initialize mobile menu button
        function initMobileMenu() {
            const menuBtn = document.getElementById('mobile-menu-btn');
            if (menuBtn) {
                menuBtn.addEventListener('click', toggleMobileMenu);
            }
        }
        
        // File upload handler is defined in editor templates
        
        // Form validation helpers
        function validateRequired(fieldId, fieldName) {
            const field = document.getElementById(fieldId);
            const value = field ? field.value.trim() : '';
            
            if (!value) {
                showFieldError(fieldId + '-error', `${fieldName} is required`);
                return false;
            }
            
            clearFieldError(fieldId + '-error');
            return true;
        }
        
        function validateMinLength(fieldId, fieldName, minLength) {
            const field = document.getElementById(fieldId);
            const value = field ? field.value.trim() : '';
            
            if (value.length < minLength) {
                showFieldError(fieldId + '-error', `${fieldName} must be at least ${minLength} characters long`);
                return false;
            }
            
            clearFieldError(fieldId + '-error');
            return true;
        }
        
        // Loading state management
        function setFormLoading(formId, isLoading) {
            const form = document.getElementById(formId);
            if (!form) return;
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const inputs = form.querySelectorAll('input, textarea, select, button');
            
            if (isLoading) {
                form.classList.add('loading');
                inputs.forEach(input => input.disabled = true);
                
                if (submitBtn) {
                    submitBtn.innerHTML = `
                        <span class="spinner"></span>
                        Creating...
                    `;
                }
            } else {
                form.classList.remove('loading');
                inputs.forEach(input => input.disabled = false);
                
                if (submitBtn) {
                    submitBtn.innerHTML = submitBtn.dataset.originalText || 'Submit';
                }
            }
        }
        
        // Removed duplicate initialization code
        
        // Initialize sidebar dropdown functionality
        function initSidebarDropdowns() {
            // Use a simple flag to prevent multiple initializations
            if (window.sidebarDropdownsInitialized) {
                console.log('Sidebar dropdowns already initialized, skipping...');
                return;
            }
            window.sidebarDropdownsInitialized = true;
            
            console.log('Initializing sidebar dropdowns...');
            
            // Check if elements exist
            const headers = document.querySelectorAll('.nav-group-header');
            const contents = document.querySelectorAll('.nav-group-content');
            
            console.log('Found headers:', headers.length);
            console.log('Found contents:', contents.length);
            
            if (headers.length === 0) {
                console.warn('No nav-group-header elements found!');
                return;
            }
            
            // Add click event listener to document for event delegation
            document.addEventListener('click', function(e) {
                // Check if the clicked element is a sidebar dropdown header
                const header = e.target.closest('.nav-group-header');
                if (header) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const targetId = header.getAttribute('data-toggle');
                    const content = document.getElementById(targetId);
                    
                    if (content) {
                        // Toggle active class
                        content.classList.toggle('active');
                        header.classList.toggle('collapsed');
                        
                        // Add smooth animation
                        if (content.classList.contains('active')) {
                            content.style.maxHeight = content.scrollHeight + 'px';
                        } else {
                            content.style.maxHeight = '0px';
                        }
                        
                        console.log('Sidebar dropdown toggled:', targetId, 'active:', content.classList.contains('active'));
                    }
                }
            });
            
            // Also add direct event listeners for better reliability
            const groupHeaders = document.querySelectorAll('.nav-group-header');
            groupHeaders.forEach(header => {
                header.style.cursor = 'pointer';
                
                // Add click event listener directly
                header.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const targetId = this.getAttribute('data-toggle');
                    const content = document.getElementById(targetId);
                    
                    if (content) {
                        // Toggle active class
                        content.classList.toggle('active');
                        this.classList.toggle('collapsed');
                        
                        // Add smooth animation
                        if (content.classList.contains('active')) {
                            content.style.maxHeight = content.scrollHeight + 'px';
                        } else {
                            content.style.maxHeight = '0px';
                        }
                        
                        console.log('Direct click - Sidebar dropdown toggled:', targetId, 'active:', content.classList.contains('active'));
                    }
                });
            });
            
            // Set initial state - all groups collapsed by default
            const allGroups = document.querySelectorAll('.nav-group-content');
            const allHeaders = document.querySelectorAll('.nav-group-header');
            
            allGroups.forEach((group, index) => {
                group.classList.remove('active');
                group.style.maxHeight = '0px';
            });
            
            allHeaders.forEach((header, index) => {
                header.classList.remove('collapsed');
            });
            
            console.log('All dropdowns set to collapsed state by default');
            
            // Add some debugging
            console.log('Found nav groups:', document.querySelectorAll('.nav-group').length);
            console.log('Found nav group headers:', document.querySelectorAll('.nav-group-header').length);
            console.log('Found nav group content:', document.querySelectorAll('.nav-group-content').length);
            
            console.log('Sidebar dropdowns initialized successfully');
            
            // Make function available globally for debugging
            window.testSidebarDropdowns = function() {
                console.log('Testing sidebar dropdowns...');
                const headers = document.querySelectorAll('.nav-group-header');
                const contents = document.querySelectorAll('.nav-group-content');
                
                console.log('Headers found:', headers.length);
                console.log('Contents found:', contents.length);
                
                headers.forEach((header, index) => {
                    const targetId = header.getAttribute('data-toggle');
                    const content = document.getElementById(targetId);
                    console.log(`Header ${index}:`, {
                        text: header.textContent.trim(),
                        targetId: targetId,
                        contentFound: !!content,
                        contentId: content ? content.id : 'NOT FOUND'
                    });
                });
                
                // Test clicking first header
                if (headers.length > 0) {
                    console.log('Testing click on first header...');
                    headers[0].click();
                }
            };
            
            // Add manual test function
            window.manualTestDropdown = function() {
                console.log('Manual dropdown test...');
                const firstHeader = document.querySelector('.nav-group-header');
                if (firstHeader) {
                    console.log('Clicking first header manually...');
                    firstHeader.click();
                } else {
                    console.log('No headers found!');
                }
            };
            
            // Add form initialization helper - prevent multiple initializations
            window.initForms = function() {
                if (window.formsInitialized) {
                    console.log('Forms already initialized, skipping...');
                    return;
                }
                window.formsInitialized = true;
                
                console.log('Initializing forms...');
                const forms = document.querySelectorAll('form');
                forms.forEach(form => {
                    // Re-bind form events
                    const submitBtn = form.querySelector('button[type="submit"]');
                    if (submitBtn) {
                        submitBtn.addEventListener('click', function(e) {
                            console.log('Form submit button clicked');
                        });
                    }
                    
                    // Re-bind file inputs
                    const fileInputs = form.querySelectorAll('input[type="file"]');
                    fileInputs.forEach(input => {
                        input.addEventListener('change', function(e) {
                            console.log('File input changed:', e.target.files[0]?.name);
                        });
                    });
                });
                console.log('Forms initialized');
            };
            
            // Add Quill debugging helper
            window.debugQuill = function() {
                console.log('=== Quill Debug Info ===');
                console.log('Quill available:', typeof Quill !== 'undefined');
                console.log('Quill version:', typeof Quill !== 'undefined' ? Quill.version : 'N/A');
                
                const containers = document.querySelectorAll('[id*="editor-container"], [id*="content-editor-container"]');
                console.log('Quill containers found:', containers.length);
                
                containers.forEach((container, index) => {
                    console.log(`Container ${index}:`, {
                        id: container.id,
                        hasQuillEditor: !!container.querySelector('.ql-editor'),
                        quillInstance: Quill.find(container)
                    });
                });
                
                console.log('=== End Quill Debug ===');
            };
            
            // Add Quill cleanup helper
            window.cleanupQuill = function() {
                console.log('Cleaning up Quill instances...');
                if (window.quillInstances) {
                    window.quillInstances.forEach((quill, editorId) => {
                        try {
                            if (quill && typeof quill.destroy === 'function') {
                                quill.destroy();
                                console.log('Destroyed Quill instance for:', editorId);
                            }
                        } catch (error) {
                            console.log('Error destroying Quill instance for:', editorId, error);
                        }
                    });
                    window.quillInstances.clear();
                }
                console.log('Quill cleanup completed');
            };
            
            // Add reset function for page changes
            window.resetInitializationFlags = function() {
                console.log('Resetting initialization flags...');
                window.formsInitialized = false;
                window.componentsInitialized = false;
                window.navigationComponentsInitialized = false;
                window.quillInstances = new Map();
                console.log('Initialization flags reset');
            };
            
            // Add case study specific helper
            window.initCaseStudy = function() {
                console.log('Initializing case study page...');
                
                // Check for multiple Quill containers
                const quillContainers = document.querySelectorAll('[id*="editor-container"], [id*="content-editor-container"]');
                console.log('Case study Quill containers found:', quillContainers.length);
                
                if (quillContainers.length > 1) {
                    console.warn('Multiple Quill containers detected! This may cause conflicts.');
                    quillContainers.forEach((container, index) => {
                        console.log(`Container ${index}:`, container.id, container.className);
                    });
                }
                
                // Initialize only once
                if (!window.caseStudyInitialized) {
                    window.caseStudyInitialized = true;
                    console.log('Case study initialization completed');
                } else {
                    console.log('Case study already initialized, skipping...');
                }
            };
        }
        
                // Re-initialize components after content load
        function reinitializeComponents(retryCount = 0) {
            console.log('Re-initializing components...');
            
            // Track Quill instances to prevent multiple initializations
            if (!window.quillInstances) {
                window.quillInstances = new Map();
            }
            
            // Re-initialize Quill editors only if containers exist
            const quillContainers = document.querySelectorAll('[id*="editor-container"], [id*="content-editor-container"]');
            console.log('Found Quill containers:', quillContainers.length);
            
            if (quillContainers.length > 0) {
                quillContainers.forEach(container => {
                    const editorId = container.id;
                    const textareaId = container.querySelector('textarea')?.id || 'content';
                    
                    // Check if this Quill instance is already initialized
                    if (window.quillInstances.has(editorId)) {
                        console.log('Quill instance already exists for:', editorId, 'skipping...');
                        return;
                    }
                    
                    // Check if Quill is available and container exists
                    if (typeof Quill !== 'undefined' && container) {
                        // Initialize new Quill instance
                        try {
                            console.log('Initializing new Quill instance for:', editorId);
                            const quill = new Quill(`#${editorId}`, {
                                theme: 'snow',
                                modules: {
                                    toolbar: [
                                        [{ 'header': [1, 2, 3, false] }],
                                        ['bold', 'italic', 'underline', 'strike'],
                                        [{ 'color': [] }, { 'background': [] }],
                                        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
                                        [{ 'indent': '-1' }, { 'indent': '+1' }],
                                        [{ 'align': [] }],
                                        ['link', 'image', 'video'],
                                        ['blockquote', 'code-block'],
                                        ['clean']
                                    ]
                                }
                            });
                            
                            // Sync content with textarea
                            quill.on('text-change', function() {
                                const textarea = document.getElementById(textareaId);
                                if (textarea) {
                                    textarea.value = quill.root.innerHTML;
                                }
                            });
                            
                            // Store the instance to prevent re-initialization
                            window.quillInstances.set(editorId, quill);
                            console.log('Quill instance created successfully for:', editorId);
                        } catch (error) {
                            console.log('Quill initialization failed for', editorId, ':', error);
                        }
                    } else {
                        console.log('Quill not available or container not found for:', editorId);
                    }
                });
            } else {
                console.log('No Quill containers found, skipping Quill initialization');
            }
            
            // Re-initialize file upload components
            const fileUploadAreas = document.querySelectorAll('[id*="upload-area"], [id*="image-upload-area"]');
            fileUploadAreas.forEach(area => {
                const fileInput = area.querySelector('input[type="file"]');
                if (fileInput) {
                    // Re-bind file input events
                    fileInput.addEventListener('change', function(e) {
                        const file = e.target.files[0];
                        if (file) {
                            // Handle file preview
                            const previewId = area.getAttribute('data-preview') || 'image-preview';
                            const preview = document.getElementById(previewId);
                            if (preview) {
                                const reader = new FileReader();
                                reader.onload = function(e) {
                                    preview.innerHTML = `<img src="${e.target.result}" alt="Preview" style="max-width: 200px; max-height: 200px;">`;
                                };
                                reader.readAsDataURL(file);
                            }
                        }
                    });
                }
            });
            
            // Re-initialize form-specific file upload handlers
            const fileInputs = document.querySelectorAll('input[type="file"]');
            fileInputs.forEach(input => {
                const inputId = input.id;
                const previewId = inputId.replace('_', '-') + '-preview';
                
                // Remove existing event listeners
                const newInput = input.cloneNode(true);
                input.parentNode.replaceChild(newInput, input);
                
                // Add new event listener
                newInput.addEventListener('change', function(e) {
                    if (typeof handleFileUpload === 'function') {
                        handleFileUpload(e, previewId, 'image');
                    }
                });
            });
            
            // Re-initialize upload area click handlers
            const uploadAreas = document.querySelectorAll('[id*="upload-area"]');
            uploadAreas.forEach(area => {
                const areaId = area.id;
                const fileInputId = areaId.replace('-upload-area', '').replace('-', '_');
                const fileInput = document.getElementById(fileInputId);
                
                if (fileInput) {
                    // Remove existing event listeners
                    const newArea = area.cloneNode(true);
                    area.parentNode.replaceChild(newArea, area);
                    
                    // Add new click handler
                    newArea.addEventListener('click', function() {
                        fileInput.click();
                    });
                }
            });
            
            // Re-initialize AdminFileUpload if available
            if (typeof AdminFileUpload !== 'undefined' && document.getElementById('image-upload-area') && document.getElementById('image')) {
                // Destroy existing instance if it exists
                if (window.adminFileUpload) {
                    // Clean up existing instance
                    window.adminFileUpload = null;
                }
                
                // Create new instance
                window.adminFileUpload = new AdminFileUpload({
                    uploadArea: 'image-upload-area',
                    fileInput: 'image',
                    previewContainer: 'image-preview',
                    maxFileSize: 10 * 1024 * 1024, // 10MB
                    allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/avif'],
                    multiple: false
                });
            }
            
            // Re-initialize form validation and submission
            const forms = document.querySelectorAll('.admin-form');
            forms.forEach(form => {
                // Re-bind form submission
                form.addEventListener('submit', function(e) {
                    e.preventDefault();
                    handleFormSubmission(form);
                });
                
                // Re-bind input validation
                const inputs = form.querySelectorAll('input, select, textarea');
                inputs.forEach(input => {
                    input.addEventListener('blur', function() {
                        validateField(input);
                    });
                });
            });
            
            // Call form-specific initialization functions if they exist
            const formInitFunctions = [
                'initFormSubmission',
                'initBlogForm',
                'initCaseStudyForm',
                'initConservationForm',
                'initDailyUpdateForm',
                'initMythsFactsForm'
            ];
            
            formInitFunctions.forEach(funcName => {
                if (typeof window[funcName] === 'function') {
                    try {
                        window[funcName]();
                    } catch (error) {
                        console.log(`Error calling ${funcName}:`, error);
                    }
                }
            });
            
            // Re-initialize save draft buttons
            const saveDraftBtn = document.getElementById('save-draft-btn');
            if (saveDraftBtn && typeof saveDraft === 'function') {
                // Remove existing event listeners
                const newBtn = saveDraftBtn.cloneNode(true);
                saveDraftBtn.parentNode.replaceChild(newBtn, saveDraftBtn);
                
                // Add new event listener
                newBtn.addEventListener('click', saveDraft);
            }
            
            // Re-initialize any other components that need it
            console.log('Components re-initialized after navigation');
            
            // Trigger a custom event to notify other components
            window.dispatchEvent(new CustomEvent('adminContentLoaded', {
                detail: { page: 'current' }
            }));
            
            // Retry mechanism for Quill editor if not available
            if (quillContainers.length > 0 && typeof Quill === 'undefined' && retryCount < 3) {
                console.log('Quill not available, retrying in 500ms... (attempt', retryCount + 1, 'of 3)');
                setTimeout(() => {
                    reinitializeComponents(retryCount + 1);
                }, 500);
                return;
            } else if (quillContainers.length === 0) {
                console.log('No Quill containers found, no retry needed');
            }
            
            // Show refresh button if components might need manual refresh
            const refreshBtn = document.getElementById('refresh-components-btn');
            if (refreshBtn) {
                refreshBtn.style.display = 'block';
                refreshBtn.addEventListener('click', function() {
                    reinitializeComponents();
                    this.style.display = 'none';
                    setTimeout(() => {
                        this.style.display = 'block';
                    }, 2000);
                });
            }
            
            // Initialize forms to prevent refresh issues
            if (typeof window.initForms === 'function') {
                window.initForms();
            }
            
            // Initialize case study specific functionality if available
            if (typeof window.initCaseStudy === 'function') {
                window.initCaseStudy();
            }
        }
        
        // Initialize SPA-like navigation
        function initSPANavigation() {
            const navLinks = document.querySelectorAll('.nav-link[data-page]');
            
            navLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    // Don't intercept external links or logout
                    if (this.getAttribute('target') === '_blank' || 
                        this.getAttribute('data-page') === 'logout') {
                        return;
                    }
                    
                    e.preventDefault();
                    
                    const href = this.getAttribute('href');
                    const page = this.getAttribute('data-page');
                    
                    // Update active state
                    document.querySelectorAll('.nav-link').forEach(navLink => {
                        navLink.classList.remove('active');
                    });
                    this.classList.add('active');
                    
                    // Navigate using fetch for SPA-like experience
                    fetch(href)
                        .then(response => response.text())
                        .then(html => {
                            // Extract the main content from the response
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            const newContent = doc.querySelector('.main-content');
                            
                            if (newContent) {
                                const mainContent = document.querySelector('.main-content');
                                if (mainContent) {
                                    mainContent.innerHTML = newContent.innerHTML;
                                    
                                    // Execute any script tags in the loaded content
                                    const scripts = newContent.querySelectorAll('script');
                                    scripts.forEach(script => {
                                        if (script.src) {
                                            // External script - create new script tag
                                            const newScript = document.createElement('script');
                                            newScript.src = script.src;
                                            document.head.appendChild(newScript);
                                        } else {
                                            // Inline script - execute directly
                                            try {
                                                eval(script.innerHTML);
                                            } catch (error) {
                                                console.log('Error executing inline script:', error);
                                            }
                                        }
                                    });
                                    
                                    // Update browser history
                                    window.history.pushState({ page }, '', href);
                                    
                                    // Re-initialize components after content load - only if not already done
                                    if (!window.navigationComponentsInitialized) {
                                        window.navigationComponentsInitialized = true;
                                        setTimeout(() => {
                                            reinitializeComponents();
                                        }, 50);
                                    }
                                }
                            }
                        })
                        .catch(error => {
                            console.error('Navigation error:', error);
                            // Fallback to regular navigation
                            window.location.href = href;
                        });
                });
            });
            
            // Handle browser back/forward buttons
            window.addEventListener('popstate', function(e) {
                if (e.state && e.state.page) {
                    // Handle back/forward navigation
                    const link = document.querySelector(`[data-page="${e.state.page}"]`);
                    if (link) {
                        link.click();
                    }
                }
            });
        }
        
        // Initialize everything when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM Content Loaded - Initializing admin panel...');
            
            // Reset initialization flags for fresh page load
            window.resetInitializationFlags();
            
            // Initialize mobile menu
            initMobileMenu();
            
            // Initialize SPA-like navigation
            initSPANavigation();
            
            // Initialize sidebar dropdowns
            initSidebarDropdowns();
            
            // Store original button text
            const submitBtns = document.querySelectorAll('button[type="submit"]');
            submitBtns.forEach(btn => {
                btn.dataset.originalText = btn.innerHTML;
            });
            
            // Close mobile menu when clicking outside
            document.addEventListener('click', function(e) {
                const sidebar = document.getElementById('sidebar');
                const menuBtn = document.querySelector('.mobile-menu-btn');
                
                if (sidebar && menuBtn && 
                    !sidebar.contains(e.target) && 
                    !menuBtn.contains(e.target) && 
                    sidebar.classList.contains('mobile-open')) {
                    sidebar.classList.remove('mobile-open');
                }
            });
            
            // Initialize components on first load - only once
            if (!window.componentsInitialized) {
                window.componentsInitialized = true;
                setTimeout(() => {
                    reinitializeComponents();
                }, 100);
            }
            
            // Fallback initialization for sidebar dropdowns
            setTimeout(() => {
                if (!window.sidebarDropdownsInitialized) {
                    console.log('Fallback: Re-initializing sidebar dropdowns...');
                    initSidebarDropdowns();
                }
            }, 500);
        });
        
        // Additional fallback for window load event
        window.addEventListener('load', function() {
            console.log('Window loaded - Checking sidebar dropdowns...');
            if (!window.sidebarDropdownsInitialized) {
                console.log('Window load fallback: Initializing sidebar dropdowns...');
                initSidebarDropdowns();
            }
        });
    """