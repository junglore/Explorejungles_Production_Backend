/**
 * Reusable File Upload Component for Admin Forms
 * Provides drag-and-drop functionality, image previews, and progress indicators
 */

class FileUploadComponent {
    constructor(options = {}) {
        this.options = {
            maxFileSize: options.maxFileSize || 10 * 1024 * 1024, // 10MB default
            allowedTypes: options.allowedTypes || ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: options.multiple || false,
            showProgress: options.showProgress || true,
            dragAndDrop: options.dragAndDrop || true,
            ...options
        };

        this.uploadedFiles = [];
        this.callbacks = {
            onFileSelect: options.onFileSelect || (() => { }),
            onFileRemove: options.onFileRemove || (() => { }),
            onError: options.onError || ((error) => console.error(error)),
            onProgress: options.onProgress || (() => { })
        };
    }

    /**
     * Initialize file upload component for a specific input
     */
    init(inputId, previewId) {
        const input = document.getElementById(inputId);
        const preview = document.getElementById(previewId);

        if (!input || !preview) {
            console.error('File upload component: Input or preview element not found');
            return;
        }

        // Set up file input event listener
        input.addEventListener('change', (e) => {
            this.handleFileSelect(e, preview);
        });

        // Set up drag and drop if enabled
        if (this.options.dragAndDrop) {
            this.setupDragAndDrop(input, preview);
        }

        return this;
    }

    /**
     * Handle file selection
     */
    handleFileSelect(event, preview) {
        const files = Array.from(event.target.files);

        if (!this.options.multiple && files.length > 1) {
            this.callbacks.onError('Multiple files not allowed');
            return;
        }

        files.forEach((file, index) => {
            if (this.validateFile(file)) {
                this.processFile(file, preview, index);
            }
        });
    }

    /**
     * Validate file against constraints
     */
    validateFile(file) {
        // Check file size
        if (file.size > this.options.maxFileSize) {
            const maxSizeMB = Math.round(this.options.maxFileSize / (1024 * 1024));
            this.callbacks.onError(`File "${file.name}" is too large. Maximum size: ${maxSizeMB}MB`);
            return false;
        }

        // Check file type
        if (!this.options.allowedTypes.includes(file.type)) {
            this.callbacks.onError(`File type "${file.type}" not allowed. Allowed types: ${this.options.allowedTypes.join(', ')}`);
            return false;
        }

        return true;
    }

    /**
     * Process and preview file
     */
    processFile(file, preview, index) {
        const fileId = `file_${Date.now()}_${index}`;

        // Add to uploaded files array
        this.uploadedFiles.push({
            id: fileId,
            file: file,
            name: file.name,
            size: file.size,
            type: file.type
        });

        // Create preview
        this.createPreview(file, preview, fileId);

        // Callback
        this.callbacks.onFileSelect(file, fileId);
    }

    /**
     * Create file preview element
     */
    createPreview(file, preview, fileId) {
        preview.classList.add('active');

        const previewItem = document.createElement('div');
        previewItem.className = 'file-preview-item';
        previewItem.dataset.fileId = fileId;

        // Create preview content based on file type
        if (file.type.startsWith('image/')) {
            this.createImagePreview(file, previewItem, fileId);
        } else if (file.type.startsWith('video/')) {
            this.createVideoPreview(file, previewItem, fileId);
        } else {
            this.createGenericPreview(file, previewItem, fileId);
        }

        preview.appendChild(previewItem);
    }

    /**
     * Create image preview
     */
    createImagePreview(file, container, fileId) {
        const reader = new FileReader();
        reader.onload = (e) => {
            container.innerHTML = `
                <div class="preview-content">
                    <img src="${e.target.result}" class="preview-image" alt="Preview">
                    <div class="preview-info">
                        <div class="preview-name">${file.name}</div>
                        <div class="preview-size">${this.formatFileSize(file.size)}</div>
                        <div class="preview-type">${file.type}</div>
                    </div>
                    <div class="preview-actions">
                        <button type="button" class="preview-remove" onclick="fileUpload.removeFile('${fileId}')">
                            <i class="fas fa-times"></i> Remove
                        </button>
                    </div>
                </div>
                ${this.options.showProgress ? '<div class="upload-progress"><div class="progress-bar"></div></div>' : ''}
            `;
        };
        reader.readAsDataURL(file);
    }

    /**
     * Create video preview
     */
    createVideoPreview(file, container, fileId) {
        container.innerHTML = `
            <div class="preview-content">
                <div class="preview-icon">
                    <i class="fas fa-video"></i>
                </div>
                <div class="preview-info">
                    <div class="preview-name">${file.name}</div>
                    <div class="preview-size">${this.formatFileSize(file.size)}</div>
                    <div class="preview-type">${file.type}</div>
                </div>
                <div class="preview-actions">
                    <button type="button" class="preview-remove" onclick="fileUpload.removeFile('${fileId}')">
                        <i class="fas fa-times"></i> Remove
                    </button>
                </div>
            </div>
            ${this.options.showProgress ? '<div class="upload-progress"><div class="progress-bar"></div></div>' : ''}
        `;
    }

    /**
     * Create generic file preview
     */
    createGenericPreview(file, container, fileId) {
        const iconClass = this.getFileIcon(file.type);

        container.innerHTML = `
            <div class="preview-content">
                <div class="preview-icon">
                    <i class="${iconClass}"></i>
                </div>
                <div class="preview-info">
                    <div class="preview-name">${file.name}</div>
                    <div class="preview-size">${this.formatFileSize(file.size)}</div>
                    <div class="preview-type">${file.type}</div>
                </div>
                <div class="preview-actions">
                    <button type="button" class="preview-remove" onclick="fileUpload.removeFile('${fileId}')">
                        <i class="fas fa-times"></i> Remove
                    </button>
                </div>
            </div>
            ${this.options.showProgress ? '<div class="upload-progress"><div class="progress-bar"></div></div>' : ''}
        `;
    }

    /**
     * Get appropriate icon for file type
     */
    getFileIcon(mimeType) {
        if (mimeType.startsWith('image/')) return 'fas fa-image';
        if (mimeType.startsWith('video/')) return 'fas fa-video';
        if (mimeType.startsWith('audio/')) return 'fas fa-music';
        if (mimeType.includes('pdf')) return 'fas fa-file-pdf';
        if (mimeType.includes('word')) return 'fas fa-file-word';
        if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'fas fa-file-excel';
        if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'fas fa-file-powerpoint';
        return 'fas fa-file';
    }

    /**
     * Remove file from upload
     */
    removeFile(fileId) {
        // Remove from uploaded files array
        this.uploadedFiles = this.uploadedFiles.filter(f => f.id !== fileId);

        // Remove preview element
        const previewItem = document.querySelector(`[data-file-id="${fileId}"]`);
        if (previewItem) {
            previewItem.remove();
        }

        // Hide preview container if no files left
        const preview = previewItem?.parentElement;
        if (preview && !preview.querySelector('.file-preview-item')) {
            preview.classList.remove('active');
        }

        // Callback
        this.callbacks.onFileRemove(fileId);
    }

    /**
     * Setup drag and drop functionality
     */
    setupDragAndDrop(input, preview) {
        const dropZone = preview.closest('.file-upload-container') || preview;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, this.preventDefaults, false);
        });

        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            }, false);
        });

        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            input.files = files;
            this.handleFileSelect({ target: { files } }, preview);
        }, false);
    }

    /**
     * Prevent default drag behaviors
     */
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * Simulate upload progress
     */
    simulateProgress(fileId, callback) {
        const previewItem = document.querySelector(`[data-file-id="${fileId}"]`);
        const progressBar = previewItem?.querySelector('.progress-bar');

        if (!progressBar) return;

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                if (callback) callback();
            }

            progressBar.style.width = progress + '%';
            this.callbacks.onProgress(progress, fileId);
        }, 100);
    }

    /**
     * Get all uploaded files
     */
    getFiles() {
        return this.uploadedFiles;
    }

    /**
     * Clear all files
     */
    clearFiles() {
        this.uploadedFiles.forEach(file => {
            this.removeFile(file.id);
        });
        this.uploadedFiles = [];
    }
}

// CSS Styles for file upload component
const fileUploadStyles = `
    .file-upload-container {
        position: relative;
        margin-bottom: 1rem;
    }
    
    .file-upload-area {
        border: 2px dashed #d1d5db;
        border-radius: 8px;
        padding: 2rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        background: #fafafa;
    }
    
    .file-upload-area:hover,
    .file-upload-area.drag-over {
        border-color: #3b82f6;
        background: #f0f9ff;
    }
    
    .file-upload-area i {
        font-size: 2rem;
        color: #6b7280;
        margin-bottom: 0.5rem;
        display: block;
    }
    
    .file-upload-area p {
        margin: 0.5rem 0 0.25rem 0;
        color: #374151;
        font-weight: 500;
    }
    
    .file-upload-area small {
        color: #6b7280;
        font-size: 0.75rem;
    }
    
    .file-preview {
        margin-top: 1rem;
        display: none;
    }
    
    .file-preview.active {
        display: block;
    }
    
    .file-preview-item {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        overflow: hidden;
    }
    
    .preview-content {
        display: flex;
        align-items: center;
        padding: 1rem;
        gap: 1rem;
    }
    
    .preview-image {
        width: 60px;
        height: 60px;
        object-fit: cover;
        border-radius: 6px;
        flex-shrink: 0;
    }
    
    .preview-icon {
        width: 60px;
        height: 60px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: #f3f4f6;
        border-radius: 6px;
        flex-shrink: 0;
    }
    
    .preview-icon i {
        font-size: 1.5rem;
        color: #6b7280;
    }
    
    .preview-info {
        flex: 1;
        min-width: 0;
    }
    
    .preview-name {
        font-weight: 500;
        color: #1f2937;
        margin-bottom: 0.25rem;
        word-break: break-word;
    }
    
    .preview-size,
    .preview-type {
        font-size: 0.75rem;
        color: #6b7280;
    }
    
    .preview-actions {
        flex-shrink: 0;
    }
    
    .preview-remove {
        background: #ef4444;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 0.5rem 0.75rem;
        font-size: 0.75rem;
        cursor: pointer;
        transition: background 0.2s;
        display: flex;
        align-items: center;
        gap: 0.25rem;
    }
    
    .preview-remove:hover {
        background: #dc2626;
    }
    
    .upload-progress {
        height: 4px;
        background: #f3f4f6;
        overflow: hidden;
    }
    
    .progress-bar {
        height: 100%;
        background: linear-gradient(90deg, #3b82f6, #1d4ed8);
        width: 0%;
        transition: width 0.3s ease;
    }
    
    .file-input {
        display: none;
    }
`;

// Inject styles if not already present
if (!document.getElementById('file-upload-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'file-upload-styles';
    styleSheet.textContent = fileUploadStyles;
    document.head.appendChild(styleSheet);
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FileUploadComponent;
} else {
    window.FileUploadComponent = FileUploadComponent;
}