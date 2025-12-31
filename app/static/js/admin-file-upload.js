/**
 * Enhanced File Upload Component for Admin Panel
 * Supports drag-and-drop, image preview, and validation
 */

class AdminFileUpload {
    constructor(options = {}) {
        this.options = {
            maxFileSize: 10 * 1024 * 1024, // 10MB default
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/avif'],
            previewContainer: null,
            uploadArea: null,
            fileInput: null,
            multiple: false,
            ...options
        };

        this.files = [];
        this.init();
    }

    init() {
        this.setupElements();
        this.bindEvents();
    }

    setupElements() {
        // Get elements
        this.uploadArea = document.getElementById(this.options.uploadArea);
        this.fileInput = document.getElementById(this.options.fileInput);
        this.previewContainer = document.getElementById(this.options.previewContainer);

        if (!this.uploadArea || !this.fileInput) {
            console.error('Required elements not found for file upload');
            return;
        }

        // Add drag-and-drop classes
        this.uploadArea.classList.add('file-upload-dropzone');

        // Create preview container if it doesn't exist
        if (!this.previewContainer) {
            this.previewContainer = document.createElement('div');
            this.previewContainer.id = this.options.previewContainer;
            this.previewContainer.className = 'file-preview-container';
            this.uploadArea.parentNode.insertBefore(this.previewContainer, this.uploadArea.nextSibling);
        }
    }

    bindEvents() {
        if (!this.uploadArea || !this.fileInput) return;

        // File input change
        this.fileInput.addEventListener('change', (e) => {
            this.handleFiles(e.target.files);
        });

        // Upload area click
        this.uploadArea.addEventListener('click', (e) => {
            e.preventDefault();
            this.fileInput.click();
        });

        // Drag and drop events
        this.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.add('dragover');
        });

        this.uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.remove('dragover');
        });

        this.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.uploadArea.classList.remove('dragover');

            const files = e.dataTransfer.files;
            this.handleFiles(files);
        });

        // Prevent default drag behaviors on document
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
    }

    handleFiles(fileList) {
        const files = Array.from(fileList);

        if (!this.options.multiple && files.length > 1) {
            this.showError('Please select only one file');
            return;
        }

        // Clear previous files if not multiple
        if (!this.options.multiple) {
            this.files = [];
            this.clearPreviews();
        }

        files.forEach(file => {
            if (this.validateFile(file)) {
                this.files.push(file);
                this.createPreview(file);
            }
        });

        // Update file input
        this.updateFileInput();
    }

    validateFile(file) {
        // Check file type
        if (!this.options.allowedTypes.includes(file.type)) {
            this.showError(`Invalid file type. Allowed types: ${this.options.allowedTypes.join(', ')}`);
            return false;
        }

        // Check file size
        if (file.size > this.options.maxFileSize) {
            const maxSizeMB = (this.options.maxFileSize / (1024 * 1024)).toFixed(1);
            this.showError(`File size too large. Maximum size: ${maxSizeMB}MB`);
            return false;
        }

        return true;
    }

    createPreview(file) {
        const previewItem = document.createElement('div');
        previewItem.className = 'file-preview-item';
        previewItem.dataset.fileName = file.name;

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                previewItem.innerHTML = `
                    <div class="image-preview">
                        <img src="${e.target.result}" alt="${file.name}">
                        <div class="image-overlay">
                            <button type="button" class="remove-file-btn" onclick="adminFileUpload.removeFile('${file.name}')">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                    </div>
                `;
            };
            reader.readAsDataURL(file);
        } else {
            previewItem.innerHTML = `
                <div class="file-preview">
                    <div class="file-icon">
                        <i class="fas fa-file"></i>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${file.name}</div>
                        <div class="file-size">${this.formatFileSize(file.size)}</div>
                    </div>
                    <button type="button" class="remove-file-btn" onclick="adminFileUpload.removeFile('${file.name}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
        }

        this.previewContainer.appendChild(previewItem);
    }

    removeFile(fileName) {
        // Remove from files array
        this.files = this.files.filter(file => file.name !== fileName);

        // Remove preview
        const previewItem = this.previewContainer.querySelector(`[data-file-name="${fileName}"]`);
        if (previewItem) {
            previewItem.remove();
        }

        // Update file input
        this.updateFileInput();
    }

    clearPreviews() {
        if (this.previewContainer) {
            this.previewContainer.innerHTML = '';
        }
    }

    updateFileInput() {
        // Create new FileList from our files array
        const dt = new DataTransfer();
        this.files.forEach(file => dt.items.add(file));
        this.fileInput.files = dt.files;

        // Don't trigger change event to avoid infinite loop
        // The UI is already updated through the preview system
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    showError(message) {
        // Use existing showMessage function if available, otherwise alert
        if (typeof showMessage === 'function') {
            showMessage(message, 'error');
        } else {
            alert(message);
        }
    }

    getFiles() {
        return this.files;
    }

    reset() {
        this.files = [];
        this.clearPreviews();
        this.fileInput.value = '';
    }
}

// Enhanced CSS for drag-and-drop functionality
const uploadStyles = `
<style>
.file-upload-dropzone {
    position: relative;
    transition: all 0.3s ease;
}

.file-upload-dropzone.dragover {
    border-color: #16a34a !important;
    background: linear-gradient(135deg, #f0fdf4 0%, #bbf7d0 100%) !important;
    transform: scale(1.02);
    box-shadow: 0 8px 25px rgba(22, 163, 74, 0.2);
}

.file-preview-container {
    margin-top: 1rem;
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
}

.file-preview-item {
    position: relative;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    overflow: hidden;
    background: white;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: all 0.3s ease;
}

.file-preview-item:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
}

.image-preview {
    position: relative;
    width: 100%;
    height: 150px;
    overflow: hidden;
}

.image-preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
}

.image-preview:hover img {
    transform: scale(1.05);
}

.image-overlay {
    position: absolute;
    top: 0;
    right: 0;
    left: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.3s ease;
}

.image-preview:hover .image-overlay {
    opacity: 1;
}

.remove-file-btn {
    background: #e53e3e;
    color: white;
    border: none;
    border-radius: 50%;
    width: 32px;
    height: 32px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
}

.remove-file-btn:hover {
    background: #c53030;
    transform: scale(1.1);
}

.file-info {
    padding: 1rem;
}

.file-name {
    font-weight: 600;
    color: #2d3748;
    margin-bottom: 0.25rem;
    word-break: break-word;
}

.file-size {
    font-size: 0.875rem;
    color: #718096;
}

.file-preview {
    display: flex;
    align-items: center;
    padding: 1rem;
    gap: 1rem;
}

.file-icon {
    font-size: 2rem;
    color: #16a34a;
}

.file-preview .file-info {
    flex: 1;
    padding: 0;
}

.file-preview .remove-file-btn {
    position: static;
    margin-left: auto;
}

/* Upload area enhancements */
.file-upload-area {
    position: relative;
    overflow: hidden;
}

.file-upload-area::before {
    content: '';
    position: absolute;
    top: -2px;
    left: -2px;
    right: -2px;
    bottom: -2px;
    background: linear-gradient(45deg, #16a34a, #15803d, #16a34a);
    border-radius: inherit;
    opacity: 0;
    transition: opacity 0.3s ease;
    z-index: -1;
}

.file-upload-area:hover::before {
    opacity: 0.1;
}

.file-upload-area.dragover::before {
    opacity: 0.2;
}

/* Responsive design */
@media (max-width: 768px) {
    .file-preview-container {
        grid-template-columns: 1fr;
    }
    
    .file-preview-item {
        max-width: 100%;
    }
}

/* Animation for new items */
@keyframes slideInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.file-preview-item {
    animation: slideInUp 0.3s ease;
}
</style>
`;

// Inject styles into document head
if (typeof document !== 'undefined') {
    document.head.insertAdjacentHTML('beforeend', uploadStyles);
}

// Global instance for easy access
let adminFileUpload = null;

// Initialize file upload when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    // Initialize for image upload if elements exist
    if (document.getElementById('image-upload-area') && document.getElementById('image')) {
        adminFileUpload = new AdminFileUpload({
            uploadArea: 'image-upload-area',
            fileInput: 'image',
            previewContainer: 'image-preview',
            maxFileSize: 10 * 1024 * 1024, // 10MB
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp', 'image/avif'],
            multiple: false
        });
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AdminFileUpload;
}