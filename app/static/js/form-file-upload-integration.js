/**
 * Integration script for file upload components in admin forms
 * Provides easy setup and configuration for different form types
 */

class FormFileUploadIntegration {
    constructor() {
        this.uploadComponents = new Map();
        this.formValidation = {
            errors: new Map(),
            isValid: true
        };
    }

    /**
     * Initialize file upload components for a specific form
     */
    initializeForForm(formType) {
        switch (formType) {
            case 'blog':
                this.setupBlogFormUploads();
                break;
            case 'case-study':
                this.setupCaseStudyFormUploads();
                break;
            case 'conservation':
                this.setupConservationFormUploads();
                break;
            case 'daily-update':
                this.setupDailyUpdateFormUploads();
                break;
            default:
                console.warn('Unknown form type:', formType);
        }
    }

    /**
     * Setup file uploads for blog forms
     */
    setupBlogFormUploads() {
        // Featured image upload
        const featuredImageUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024, // 10MB
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: false,
            onFileSelect: (file, fileId) => {
                this.clearFieldError('featured-image-error');
                console.log('Featured image selected:', file.name);
            },
            onError: (error) => {
                this.showFieldError('featured-image-error', error);
            }
        });

        featuredImageUpload.init('featured_image', 'featured-image-preview');
        this.uploadComponents.set('featured_image', featuredImageUpload);

        // Banner image upload
        const bannerUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024, // 10MB
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: false,
            onFileSelect: (file, fileId) => {
                this.clearFieldError('banner-error');
                console.log('Banner image selected:', file.name);
            },
            onError: (error) => {
                this.showFieldError('banner-error', error);
            }
        });

        bannerUpload.init('banner', 'banner-preview');
        this.uploadComponents.set('banner', bannerUpload);

        // Video upload
        const videoUpload = new FileUploadComponent({
            maxFileSize: 100 * 1024 * 1024, // 100MB
            allowedTypes: ['video/mp4', 'video/webm', 'video/mov', 'video/avi'],
            multiple: false,
            onFileSelect: (file, fileId) => {
                this.clearFieldError('video-error');
                console.log('Video selected:', file.name);
            },
            onError: (error) => {
                this.showFieldError('video-error', error);
            }
        });

        videoUpload.init('video', 'video-preview');
        this.uploadComponents.set('video', videoUpload);
    }

    /**
     * Setup file uploads for case study forms
     */
    setupCaseStudyFormUploads() {
        // Featured image upload
        const featuredImageUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: false,
            onError: (error) => this.showFieldError('featured-image-error', error)
        });

        featuredImageUpload.init('featured_image', 'featured-image-preview');
        this.uploadComponents.set('featured_image', featuredImageUpload);

        // Banner upload
        const bannerUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: false,
            onError: (error) => this.showFieldError('banner-error', error)
        });

        bannerUpload.init('banner', 'banner-preview');
        this.uploadComponents.set('banner', bannerUpload);

        // Research images (multiple)
        const researchImagesUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: true,
            onError: (error) => this.showFieldError('research-images-error', error)
        });

        researchImagesUpload.init('research_images', 'research-images-preview');
        this.uploadComponents.set('research_images', researchImagesUpload);
    }

    /**
     * Setup file uploads for conservation effort forms
     */
    setupConservationFormUploads() {
        // Featured image upload
        const featuredImageUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: false,
            onError: (error) => this.showFieldError('featured-image-error', error)
        });

        featuredImageUpload.init('featured_image', 'featured-image-preview');
        this.uploadComponents.set('featured_image', featuredImageUpload);

        // Banner upload
        const bannerUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: false,
            onError: (error) => this.showFieldError('banner-error', error)
        });

        bannerUpload.init('banner', 'banner-preview');
        this.uploadComponents.set('banner', bannerUpload);

        // Project media (multiple, mixed)
        const projectMediaUpload = new FileUploadComponent({
            maxFileSize: 50 * 1024 * 1024, // 50MB for mixed media
            allowedTypes: [
                'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp',
                'video/mp4', 'video/webm', 'video/mov'
            ],
            multiple: true,
            onError: (error) => this.showFieldError('project-media-error', error)
        });

        projectMediaUpload.init('project_media', 'project-media-preview');
        this.uploadComponents.set('project_media', projectMediaUpload);
    }

    /**
     * Setup file uploads for daily update forms
     */
    setupDailyUpdateFormUploads() {
        // Featured image upload (required)
        const featuredImageUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: false,
            onFileSelect: (file, fileId) => {
                this.clearFieldError('featured-image-error');
                this.markFieldAsValid('featured_image');
            },
            onError: (error) => {
                this.showFieldError('featured-image-error', error);
                this.markFieldAsInvalid('featured_image');
            }
        });

        featuredImageUpload.init('featured_image', 'featured-image-preview');
        this.uploadComponents.set('featured_image', featuredImageUpload);

        // Additional images (multiple)
        const additionalImagesUpload = new FileUploadComponent({
            maxFileSize: 10 * 1024 * 1024,
            allowedTypes: ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp'],
            multiple: true,
            onError: (error) => this.showFieldError('additional-images-error', error)
        });

        additionalImagesUpload.init('additional_images', 'additional-images-preview');
        this.uploadComponents.set('additional_images', additionalImagesUpload);
    }

    /**
     * Validate all file uploads in the form
     */
    validateFileUploads(formType) {
        let isValid = true;
        const errors = [];

        // Form-specific validation rules
        switch (formType) {
            case 'daily-update':
                // Featured image is required for daily updates
                const featuredImageUpload = this.uploadComponents.get('featured_image');
                if (!featuredImageUpload || featuredImageUpload.getFiles().length === 0) {
                    this.showFieldError('featured-image-error', 'Featured image is required for news articles');
                    isValid = false;
                }
                break;

            case 'blog':
                // No required files for blogs, but validate if present
                break;

            case 'case-study':
                // No required files for case studies
                break;

            case 'conservation':
                // No required files for conservation efforts
                break;
        }

        // Validate file sizes and types for all uploads
        this.uploadComponents.forEach((upload, fieldName) => {
            const files = upload.getFiles();
            files.forEach(fileInfo => {
                if (!this.validateIndividualFile(fileInfo.file, fieldName)) {
                    isValid = false;
                }
            });
        });

        return isValid;
    }

    /**
     * Validate individual file
     */
    validateIndividualFile(file, fieldName) {
        const upload = this.uploadComponents.get(fieldName);
        if (!upload) return true;

        return upload.validateFile(file);
    }

    /**
     * Get all uploaded files for form submission
     */
    getAllUploadedFiles() {
        const allFiles = {};

        this.uploadComponents.forEach((upload, fieldName) => {
            const files = upload.getFiles();
            if (files.length > 0) {
                allFiles[fieldName] = files.map(f => f.file);
            }
        });

        return allFiles;
    }

    /**
     * Clear all uploaded files
     */
    clearAllFiles() {
        this.uploadComponents.forEach(upload => {
            upload.clearFiles();
        });
    }

    /**
     * Show field error
     */
    showFieldError(errorId, message) {
        const errorElement = document.getElementById(errorId);
        if (errorElement) {
            errorElement.textContent = message;
            errorElement.classList.add('active');
            errorElement.style.display = 'block';
        }

        this.formValidation.errors.set(errorId, message);
        this.formValidation.isValid = false;
    }

    /**
     * Clear field error
     */
    clearFieldError(errorId) {
        const errorElement = document.getElementById(errorId);
        if (errorElement) {
            errorElement.textContent = '';
            errorElement.classList.remove('active');
            errorElement.style.display = 'none';
        }

        this.formValidation.errors.delete(errorId);
        this.updateFormValidationStatus();
    }

    /**
     * Mark field as valid
     */
    markFieldAsValid(fieldName) {
        const field = document.getElementById(fieldName);
        if (field) {
            field.classList.remove('error');
            field.classList.add('valid');
        }
    }

    /**
     * Mark field as invalid
     */
    markFieldAsInvalid(fieldName) {
        const field = document.getElementById(fieldName);
        if (field) {
            field.classList.remove('valid');
            field.classList.add('error');
        }
    }

    /**
     * Update overall form validation status
     */
    updateFormValidationStatus() {
        this.formValidation.isValid = this.formValidation.errors.size === 0;
    }

    /**
     * Get form validation status
     */
    isFormValid() {
        return this.formValidation.isValid;
    }

    /**
     * Get all validation errors
     */
    getValidationErrors() {
        return Array.from(this.formValidation.errors.entries());
    }

    /**
     * Setup drag and drop for entire form
     */
    setupFormDragAndDrop() {
        const form = document.querySelector('.admin-form');
        if (!form) return;

        // Prevent default drag behaviors on the form
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            form.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        // Add visual feedback for drag over form
        form.addEventListener('dragenter', () => {
            form.classList.add('drag-active');
        });

        form.addEventListener('dragleave', (e) => {
            // Only remove class if leaving the form entirely
            if (!form.contains(e.relatedTarget)) {
                form.classList.remove('drag-active');
            }
        });

        form.addEventListener('drop', () => {
            form.classList.remove('drag-active');
        });
    }

    /**
     * Initialize progress tracking for uploads
     */
    initializeProgressTracking() {
        this.uploadComponents.forEach((upload, fieldName) => {
            upload.callbacks.onProgress = (progress, fileId) => {
                console.log(`Upload progress for ${fieldName}: ${progress}%`);

                // Update UI progress indicators
                const progressElement = document.querySelector(`[data-file-id="${fileId}"] .progress-bar`);
                if (progressElement) {
                    progressElement.style.width = `${progress}%`;
                }
            };
        });
    }
}

// Global instance for easy access
window.formFileUpload = new FormFileUploadIntegration();

// Auto-initialize based on form type if data attribute is present
document.addEventListener('DOMContentLoaded', () => {
    const form = document.querySelector('.admin-form');
    if (form) {
        const formType = form.dataset.formType;
        if (formType) {
            window.formFileUpload.initializeForForm(formType);
            window.formFileUpload.setupFormDragAndDrop();
            window.formFileUpload.initializeProgressTracking();
        }
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FormFileUploadIntegration;
}