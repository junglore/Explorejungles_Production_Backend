/**
 * Enhanced Form Interactions for Admin Panel
 * Includes real-time validation, AJAX submissions, and user feedback
 */

class AdminFormHandler {
    constructor(options = {}) {
        this.options = {
            formSelector: 'form',
            enableRealTimeValidation: true,
            enableAutoSave: false,
            autoSaveInterval: 30000, // 30 seconds
            showLoadingStates: true,
            ...options
        };

        this.forms = new Map();
        this.validationRules = new Map();
        this.autoSaveTimers = new Map();

        this.init();
    }

    init() {
        this.setupForms();
        this.bindGlobalEvents();
        this.initializeValidation();
    }

    setupForms() {
        const forms = document.querySelectorAll(this.options.formSelector);

        forms.forEach(form => {
            const formId = form.id || `form_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            if (!form.id) form.id = formId;

            this.forms.set(formId, {
                element: form,
                isValid: false,
                isDirty: false,
                originalData: new FormData(form),
                validationErrors: new Map()
            });

            this.bindFormEvents(form);
        });
    }

    bindFormEvents(form) {
        const formId = form.id;

        // Form submission
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleFormSubmission(formId);
        });

        // Input changes for real-time validation
        if (this.options.enableRealTimeValidation) {
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('blur', () => {
                    this.validateField(formId, input);
                });

                input.addEventListener('input', () => {
                    this.markFormDirty(formId);
                    this.clearFieldError(input);

                    // Debounced validation
                    clearTimeout(input.validationTimeout);
                    input.validationTimeout = setTimeout(() => {
                        this.validateField(formId, input);
                    }, 500);
                });
            });
        }

        // Auto-save functionality
        if (this.options.enableAutoSave) {
            this.setupAutoSave(formId);
        }
    }

    bindGlobalEvents() {
        // Prevent accidental navigation when form is dirty
        window.addEventListener('beforeunload', (e) => {
            const dirtyForms = Array.from(this.forms.values()).filter(form => form.isDirty);
            if (dirtyForms.length > 0) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
                return e.returnValue;
            }
        });

        // Handle browser back/forward buttons
        window.addEventListener('popstate', (e) => {
            const dirtyForms = Array.from(this.forms.values()).filter(form => form.isDirty);
            if (dirtyForms.length > 0) {
                const confirmLeave = confirm('You have unsaved changes. Are you sure you want to leave?');
                if (!confirmLeave) {
                    history.pushState(null, null, window.location.href);
                }
            }
        });
    }

    initializeValidation() {
        // Set up common validation rules
        this.addValidationRule('required', (value, element) => {
            const trimmedValue = typeof value === 'string' ? value.trim() : value;
            return trimmedValue !== '' && trimmedValue !== null && trimmedValue !== undefined;
        }, 'This field is required');

        this.addValidationRule('minLength', (value, element, params) => {
            const minLength = params.minLength || 0;
            return value.length >= minLength;
        }, (params) => `Must be at least ${params.minLength} characters long`);

        this.addValidationRule('maxLength', (value, element, params) => {
            const maxLength = params.maxLength || Infinity;
            return value.length <= maxLength;
        }, (params) => `Must be no more than ${params.maxLength} characters long`);

        this.addValidationRule('email', (value, element) => {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return emailRegex.test(value);
        }, 'Please enter a valid email address');

        this.addValidationRule('url', (value, element) => {
            try {
                new URL(value);
                return true;
            } catch {
                return false;
            }
        }, 'Please enter a valid URL');

        this.addValidationRule('fileSize', (value, element, params) => {
            if (!element.files || element.files.length === 0) return true;
            const maxSize = params.maxSize || Infinity;
            return Array.from(element.files).every(file => file.size <= maxSize);
        }, (params) => `File size must be less than ${this.formatFileSize(params.maxSize)}`);

        this.addValidationRule('fileType', (value, element, params) => {
            if (!element.files || element.files.length === 0) return true;
            const allowedTypes = params.allowedTypes || [];
            return Array.from(element.files).every(file => allowedTypes.includes(file.type));
        }, (params) => `Allowed file types: ${params.allowedTypes.join(', ')}`);
    }

    addValidationRule(name, validator, errorMessage) {
        this.validationRules.set(name, {
            validator,
            errorMessage
        });
    }

    validateField(formId, field) {
        const form = this.forms.get(formId);
        if (!form) return true;

        const fieldName = field.name || field.id;
        const value = field.type === 'checkbox' ? field.checked : field.value;
        let isValid = true;
        let errorMessage = '';

        // Check required validation
        if (field.hasAttribute('required')) {
            const rule = this.validationRules.get('required');
            if (!rule.validator(value, field)) {
                isValid = false;
                errorMessage = rule.errorMessage;
            }
        }

        // Check other validation attributes
        if (isValid && value) {
            // Min length
            const minLength = field.getAttribute('minlength') || field.dataset.minLength;
            if (minLength) {
                const rule = this.validationRules.get('minLength');
                if (!rule.validator(value, field, { minLength: parseInt(minLength) })) {
                    isValid = false;
                    errorMessage = typeof rule.errorMessage === 'function'
                        ? rule.errorMessage({ minLength: parseInt(minLength) })
                        : rule.errorMessage;
                }
            }

            // Max length
            const maxLength = field.getAttribute('maxlength') || field.dataset.maxLength;
            if (maxLength) {
                const rule = this.validationRules.get('maxLength');
                if (!rule.validator(value, field, { maxLength: parseInt(maxLength) })) {
                    isValid = false;
                    errorMessage = typeof rule.errorMessage === 'function'
                        ? rule.errorMessage({ maxLength: parseInt(maxLength) })
                        : rule.errorMessage;
                }
            }

            // Email validation
            if (field.type === 'email') {
                const rule = this.validationRules.get('email');
                if (!rule.validator(value, field)) {
                    isValid = false;
                    errorMessage = rule.errorMessage;
                }
            }

            // URL validation
            if (field.type === 'url') {
                const rule = this.validationRules.get('url');
                if (!rule.validator(value, field)) {
                    isValid = false;
                    errorMessage = rule.errorMessage;
                }
            }

            // File validation
            if (field.type === 'file') {
                // File size validation
                const maxSize = field.dataset.maxSize;
                if (maxSize) {
                    const rule = this.validationRules.get('fileSize');
                    if (!rule.validator(value, field, { maxSize: parseInt(maxSize) })) {
                        isValid = false;
                        errorMessage = typeof rule.errorMessage === 'function'
                            ? rule.errorMessage({ maxSize: parseInt(maxSize) })
                            : rule.errorMessage;
                    }
                }

                // File type validation
                const allowedTypes = field.dataset.allowedTypes;
                if (allowedTypes) {
                    const types = allowedTypes.split(',').map(t => t.trim());
                    const rule = this.validationRules.get('fileType');
                    if (!rule.validator(value, field, { allowedTypes: types })) {
                        isValid = false;
                        errorMessage = typeof rule.errorMessage === 'function'
                            ? rule.errorMessage({ allowedTypes: types })
                            : rule.errorMessage;
                    }
                }
            }
        }

        // Update validation state
        if (isValid) {
            form.validationErrors.delete(fieldName);
            this.clearFieldError(field);
        } else {
            form.validationErrors.set(fieldName, errorMessage);
            this.showFieldError(field, errorMessage);
        }

        // Update form validity
        form.isValid = form.validationErrors.size === 0;

        return isValid;
    }

    validateForm(formId) {
        const form = this.forms.get(formId);
        if (!form) return false;

        const inputs = form.element.querySelectorAll('input, textarea, select');
        let isValid = true;

        inputs.forEach(input => {
            if (!this.validateField(formId, input)) {
                isValid = false;
            }
        });

        return isValid;
    }

    showFieldError(field, message) {
        const fieldName = field.name || field.id;
        const errorElement = document.getElementById(`${fieldName}-error`) ||
            document.getElementById(`${field.id}-error`);

        if (errorElement) {
            errorElement.textContent = message;
            errorElement.style.display = 'block';
            errorElement.classList.add('field-error-active');
        }

        // Add error styling to field
        field.classList.add('field-error-input');
        field.setAttribute('aria-invalid', 'true');
        field.setAttribute('aria-describedby', errorElement?.id || '');
    }

    clearFieldError(field) {
        const fieldName = field.name || field.id;
        const errorElement = document.getElementById(`${fieldName}-error`) ||
            document.getElementById(`${field.id}-error`);

        if (errorElement) {
            errorElement.textContent = '';
            errorElement.style.display = 'none';
            errorElement.classList.remove('field-error-active');
        }

        // Remove error styling from field
        field.classList.remove('field-error-input');
        field.removeAttribute('aria-invalid');
        field.removeAttribute('aria-describedby');
    }

    clearAllErrors(formId) {
        const form = this.forms.get(formId);
        if (!form) return;

        const errorElements = form.element.querySelectorAll('.field-error');
        errorElements.forEach(el => {
            el.textContent = '';
            el.style.display = 'none';
            el.classList.remove('field-error-active');
        });

        const inputs = form.element.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.classList.remove('field-error-input');
            input.removeAttribute('aria-invalid');
            input.removeAttribute('aria-describedby');
        });

        form.validationErrors.clear();
    }

    markFormDirty(formId) {
        const form = this.forms.get(formId);
        if (form) {
            form.isDirty = true;
        }
    }

    markFormClean(formId) {
        const form = this.forms.get(formId);
        if (form) {
            form.isDirty = false;
        }
    }

    setFormLoading(formId, isLoading) {
        const form = this.forms.get(formId);
        if (!form) return;

        const formElement = form.element;
        const submitBtn = formElement.querySelector('button[type="submit"]');
        const inputs = formElement.querySelectorAll('input, textarea, select, button');

        if (isLoading) {
            formElement.classList.add('loading');
            inputs.forEach(input => input.disabled = true);

            if (submitBtn) {
                const originalText = submitBtn.dataset.originalText || submitBtn.innerHTML;
                submitBtn.dataset.originalText = originalText;
                submitBtn.innerHTML = `
                    <span class="spinner"></span>
                    ${this.getLoadingText(formElement)}
                `;
            }
        } else {
            formElement.classList.remove('loading');
            inputs.forEach(input => input.disabled = false);

            if (submitBtn && submitBtn.dataset.originalText) {
                submitBtn.innerHTML = submitBtn.dataset.originalText;
            }
        }
    }

    getLoadingText(form) {
        const action = form.dataset.action || 'Processing';
        return `${action}...`;
    }

    async handleFormSubmission(formId) {
        const form = this.forms.get(formId);
        if (!form) return;

        // Clear previous errors
        this.clearAllErrors(formId);

        // Validate form
        if (!this.validateForm(formId)) {
            this.showMessage('Please fix the validation errors above', 'error');
            return;
        }

        // Set loading state
        this.setFormLoading(formId, true);

        try {
            const formData = new FormData(form.element);
            const action = form.element.action || window.location.href;
            const method = form.element.method || 'POST';

            const response = await fetch(action, {
                method: method.toUpperCase(),
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            await this.handleFormResponse(formId, response);

        } catch (error) {
            this.showMessage('Network error: ' + error.message, 'error');
        } finally {
            this.setFormLoading(formId, false);
        }
    }

    async handleFormResponse(formId, response) {
        const form = this.forms.get(formId);
        if (!form) return;

        if (response.ok) {
            // Success
            const successMessage = form.element.dataset.successMessage || 'Form submitted successfully!';
            this.showMessage(successMessage, 'success');

            // Mark form as clean
            this.markFormClean(formId);

            // Handle redirect
            const redirectUrl = form.element.dataset.redirectUrl;
            if (redirectUrl) {
                setTimeout(() => {
                    window.location.href = redirectUrl;
                }, 1500);
            }

        } else {
            // Error
            try {
                const errorData = await response.json();

                if (errorData.detail && typeof errorData.detail === 'object') {
                    // Handle field-specific validation errors
                    Object.keys(errorData.detail).forEach(fieldName => {
                        const field = form.element.querySelector(`[name="${fieldName}"]`) ||
                            form.element.querySelector(`#${fieldName}`);
                        if (field) {
                            this.showFieldError(field, errorData.detail[fieldName]);
                        }
                    });
                    this.showMessage('Please fix the validation errors', 'error');
                } else {
                    // General error message
                    const errorMessage = errorData.detail || errorData.message || 'An error occurred';
                    this.showMessage(errorMessage, 'error');
                }
            } catch {
                // Fallback for non-JSON responses
                this.showMessage(`Error: ${response.status} ${response.statusText}`, 'error');
            }
        }
    }

    setupAutoSave(formId) {
        const form = this.forms.get(formId);
        if (!form) return;

        const autoSaveTimer = setInterval(() => {
            if (form.isDirty && form.isValid) {
                this.autoSaveForm(formId);
            }
        }, this.options.autoSaveInterval);

        this.autoSaveTimers.set(formId, autoSaveTimer);
    }

    async autoSaveForm(formId) {
        const form = this.forms.get(formId);
        if (!form) return;

        try {
            const formData = new FormData(form.element);
            formData.append('auto_save', 'true');

            const response = await fetch(form.element.action || window.location.href, {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                this.showMessage('Draft saved automatically', 'info', 2000);
                this.markFormClean(formId);
            }
        } catch (error) {
            console.warn('Auto-save failed:', error);
        }
    }

    showMessage(message, type = 'success', duration = 5000) {
        // Use existing showMessage function if available
        if (typeof showMessage === 'function') {
            showMessage(message, type);
            return;
        }

        // Fallback message display
        const container = document.getElementById('message-container') || document.body;
        const messageEl = document.createElement('div');
        messageEl.className = `message ${type}`;
        messageEl.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: space-between;">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" 
                        style="background: none; border: none; color: inherit; cursor: pointer; font-size: 1.2rem;">&times;</button>
            </div>
        `;

        if (container === document.body) {
            messageEl.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
                padding: 1rem;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            `;
        }

        container.appendChild(messageEl);

        // Auto-remove
        if (duration > 0) {
            setTimeout(() => {
                if (messageEl.parentElement) {
                    messageEl.remove();
                }
            }, duration);
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';

        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));

        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    destroy() {
        // Clear auto-save timers
        this.autoSaveTimers.forEach(timer => clearInterval(timer));
        this.autoSaveTimers.clear();

        // Clear forms
        this.forms.clear();
        this.validationRules.clear();
    }
}

// Delete confirmation functionality
class DeleteConfirmation {
    constructor() {
        this.init();
    }

    init() {
        this.createModal();
        this.bindEvents();
    }

    createModal() {
        if (document.getElementById('deleteConfirmModal')) return;

        const modal = document.createElement('div');
        modal.id = 'deleteConfirmModal';
        modal.className = 'modal';
        modal.style.display = 'none';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>Confirm Delete</h3>
                <p>Are you sure you want to delete "<span id="deleteItemTitle"></span>"?</p>
                <p class="text-danger">This action cannot be undone.</p>
                <div class="modal-actions">
                    <button type="button" id="cancelDelete" class="btn btn-secondary">Cancel</button>
                    <button type="button" id="confirmDelete" class="btn btn-danger">Delete</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    }

    bindEvents() {
        const modal = document.getElementById('deleteConfirmModal');
        const cancelBtn = document.getElementById('cancelDelete');
        const confirmBtn = document.getElementById('confirmDelete');

        // Cancel button
        cancelBtn?.addEventListener('click', () => this.hide());

        // Click outside to close
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.hide();
            }
        });

        // Escape key to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal?.style.display === 'flex') {
                this.hide();
            }
        });
    }

    show(title, onConfirm) {
        const modal = document.getElementById('deleteConfirmModal');
        const titleElement = document.getElementById('deleteItemTitle');
        const confirmBtn = document.getElementById('confirmDelete');

        if (!modal || !titleElement || !confirmBtn) return;

        titleElement.textContent = title;
        modal.style.display = 'flex';

        // Remove previous event listeners
        const newConfirmBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

        // Add new event listener
        newConfirmBtn.addEventListener('click', () => {
            this.hide();
            if (typeof onConfirm === 'function') {
                onConfirm();
            }
        });

        // Focus on cancel button for accessibility
        document.getElementById('cancelDelete')?.focus();
    }

    hide() {
        const modal = document.getElementById('deleteConfirmModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
}

// Global instances
let adminFormHandler = null;
let deleteConfirmation = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    // Initialize form handler
    adminFormHandler = new AdminFormHandler({
        enableRealTimeValidation: true,
        enableAutoSave: false, // Can be enabled per form
        showLoadingStates: true
    });

    // Initialize delete confirmation
    deleteConfirmation = new DeleteConfirmation();
});

// Global helper functions for backward compatibility
function confirmDelete(id, title, deleteUrl) {
    if (!deleteConfirmation) {
        deleteConfirmation = new DeleteConfirmation();
    }

    deleteConfirmation.show(title, async () => {
        try {
            const response = await fetch(deleteUrl || `/admin/myths-facts/delete/${id}`, {
                method: 'DELETE',
                credentials: 'same-origin',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (response.ok) {
                if (typeof showMessage === 'function') {
                    showMessage('Item deleted successfully!', 'success');
                }
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                if (typeof showMessage === 'function') {
                    showMessage('Error deleting item: ' + response.status, 'error');
                }
            }
        } catch (error) {
            if (typeof showMessage === 'function') {
                showMessage('Network error: ' + error.message, 'error');
            }
        }
    });
}

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AdminFormHandler, DeleteConfirmation };
}