"""
QuillJS Editor utilities for admin forms
"""

def get_quill_editor_html(editor_id: str, textarea_id: str, height: str = "400px") -> str:
    """Generate QuillJS editor HTML"""
    return f"""
    <div id="{editor_id}" style="height: {height}; border: 1px solid #d1d5db; border-radius: 8px;"></div>
    <textarea id="{textarea_id}" name="{textarea_id}" style="display: none;" required></textarea>
    """

def get_quill_editor_js(editor_id: str, textarea_id: str, variable_name: str) -> str:
    """Generate QuillJS editor JavaScript initialization"""
    return f"""
    // Initialize Quill editor when DOM is ready - avoid redeclaration
    function init{variable_name}() {{
        if (typeof Quill === 'undefined') {{
            return;
        }}
        
        const editorElement = document.getElementById('{editor_id}');
        if (!editorElement) {{
            return;
        }}
        
        // Check if already initialized to avoid redeclaration
        if (typeof window.{variable_name} !== 'undefined' && window.{variable_name}) {{
            return;
        }}
        
        try {{
            window.{variable_name} = new Quill('#{editor_id}', {{
                theme: 'snow',
                modules: {{
                    toolbar: [
                        [{{ 'header': [1, 2, 3, false] }}],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{{ 'color': [] }}, {{ 'background': [] }}],
                        [{{ 'list': 'ordered' }}, {{ 'list': 'bullet' }}],
                        [{{ 'indent': '-1' }}, {{ 'indent': '+1' }}],
                        [{{ 'align': [] }}],
                        ['link', 'image', 'video'],
                        ['blockquote', 'code-block'],
                        ['clean']
                    ]
                }}
            }});
            
            // Sync content with textarea
            window.{variable_name}.on('text-change', function() {{
                const textarea = document.getElementById('{textarea_id}');
                if (textarea) {{
                    textarea.value = window.{variable_name}.root.innerHTML;
                }}
            }});
            
        }} catch (error) {{
            // Quill initialization failed
        }}
    }}
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', init{variable_name});
    }} else {{
        init{variable_name}();
    }}
    """

def get_upload_handlers_js() -> str:
    """Generate upload handler JavaScript functions"""
    return """
    // Enhanced file upload handler with preview
    function handleFileUpload(event, previewId, type) {
        const file = event.target.files[0];
        const preview = document.getElementById(previewId);
        
        if (!file || !preview) return;
        
        // Clear previous preview
        preview.innerHTML = '';
        
        if (type === 'image') {
            // Validate image file - support all five extensions including AVIF
            const allowedTypes = [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/avif'
            ];
            
            if (!allowedTypes.includes(file.type)) {
                showMessage('Please select a valid image file (JPEG, PNG, GIF, WebP, or AVIF)', 'error');
                event.target.value = '';
                return;
            }
            
            // Check file size (50MB limit for better compatibility)
            if (file.size > 50 * 1024 * 1024) {
                showMessage('Image file size must be less than 50MB', 'error');
                event.target.value = '';
                return;
            }
            
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.innerHTML = `
                    <div style="margin-top: 1rem; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 8px; background: #f7fafc;">
                        <img src="${e.target.result}" style="max-width: 200px; max-height: 200px; border-radius: 8px; display: block; margin: 0 auto;">
                        <p style="text-align: center; margin-top: 0.5rem; font-size: 0.875rem; color: #718096;">${file.name}</p>
                        <p style="text-align: center; font-size: 0.75rem; color: #a0aec0;">${(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                `;
            };
            reader.readAsDataURL(file);
            
        } else if (type === 'video') {
            // Validate video file
            const allowedVideoTypes = [
                'video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/webm', 'video/mkv', 'video/flv'
            ];
            
            if (!allowedVideoTypes.includes(file.type)) {
                showMessage('Please select a valid video file (MP4, AVI, MOV, WMV, WebM, MKV, or FLV)', 'error');
                event.target.value = '';
                return;
            }
            
            // Check file size (200MB limit)
            if (file.size > 200 * 1024 * 1024) {
                showMessage('Video file size must be less than 200MB', 'error');
                event.target.value = '';
                return;
            }
            
            preview.innerHTML = `
                <div style="margin-top: 1rem; padding: 1rem; border: 1px solid #e2e8f0; border-radius: 8px; background: #f7fafc;">
                    <div style="text-align: center;">
                        <i class="fas fa-video" style="font-size: 2rem; color: #16a34a; margin-bottom: 0.5rem;"></i>
                        <p style="font-weight: 600; color: #4a5568;">${file.name}</p>
                        <p style="font-size: 0.875rem; color: #718096;">${(file.size / (1024 * 1024)).toFixed(2)} MB</p>
                    </div>
                </div>
            `;
        }
    }
    
    // Function to remove current image
    function removeCurrentImage(fieldName, currentImageId) {
        const currentImageDiv = document.getElementById(currentImageId);
        if (currentImageDiv) {
            currentImageDiv.style.display = 'none';
        }
        
        // Add hidden input to indicate removal
        const form = document.querySelector('form');
        if (form) {
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'remove_' + fieldName;
            hiddenInput.value = 'true';
            form.appendChild(hiddenInput);
        }
        
        // Clear the file input if it exists
        const fileInput = document.getElementById(fieldName);
        if (fileInput) {
            fileInput.value = '';
        }
    }
    """