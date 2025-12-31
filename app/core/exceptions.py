"""
Custom exception classes for content operations and global error handling
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, status


class ContentError(Exception):
    """Base exception for content-related errors"""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ContentNotFoundError(ContentError):
    """Exception raised when content is not found"""
    
    def __init__(self, content_id: str = None, content_type: str = None):
        if content_id and content_type:
            message = f"{content_type.title()} with ID {content_id} not found"
        elif content_type:
            message = f"{content_type.title()} not found"
        else:
            message = "Content not found"
            
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND
        )


class ContentValidationError(ContentError):
    """Exception raised when content validation fails"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)
            
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class ContentPermissionError(ContentError):
    """Exception raised when user lacks permission for content operation"""
    
    def __init__(self, operation: str = "access", content_type: str = "content"):
        message = f"Not authorized to {operation} this {content_type}"
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN
        )


class FileUploadError(ContentError):
    """Exception raised when file upload fails"""
    
    def __init__(self, message: str, filename: str = None, file_type: str = None):
        details = {}
        if filename:
            details["filename"] = filename
        if file_type:
            details["file_type"] = file_type
            
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details
        )


class FileSizeError(FileUploadError):
    """Exception raised when file size exceeds limit"""
    
    def __init__(self, filename: str, size: int, max_size: int):
        message = f"File '{filename}' size ({size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        super().__init__(
            message=message,
            filename=filename,
            file_type="size_limit"
        )


class FileTypeError(FileUploadError):
    """Exception raised when file type is not allowed"""
    
    def __init__(self, filename: str, file_type: str, allowed_types: list = None):
        if allowed_types:
            allowed_str = ", ".join(allowed_types)
            message = f"File type '{file_type}' not allowed for '{filename}'. Allowed types: {allowed_str}"
        else:
            message = f"File type '{file_type}' not allowed for '{filename}'"
            
        super().__init__(
            message=message,
            filename=filename,
            file_type=file_type
        )


class DatabaseError(ContentError):
    """Exception raised when database operation fails"""
    
    def __init__(self, message: str, operation: str = None):
        details = {}
        if operation:
            details["operation"] = operation
            
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details
        )


class CategoryNotFoundError(ContentError):
    """Exception raised when category is not found"""
    
    def __init__(self, category_id: str):
        message = f"Category with ID {category_id} not found"
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class SlugConflictError(ContentError):
    """Exception raised when slug already exists"""
    
    def __init__(self, slug: str, content_type: str = "content"):
        message = f"A {content_type} with slug '{slug}' already exists"
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details={"slug": slug, "content_type": content_type}
        )


class ContentLimitError(ContentError):
    """Exception raised when content limit is exceeded"""
    
    def __init__(self, limit_type: str, current_count: int, max_count: int):
        message = f"Maximum {limit_type} limit reached ({current_count}/{max_count})"
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details={
                "limit_type": limit_type,
                "current_count": current_count,
                "max_count": max_count
            }
        )


def create_error_response(error: ContentError) -> dict:
    """
    Create a standardized error response from ContentError
    
    Args:
        error: ContentError instance
        
    Returns:
        Dictionary with error details in standardized format
    """
    response = {
        "message": error.message,
        "status": False,
        "error_type": error.__class__.__name__
    }
    
    if error.details:
        response["details"] = error.details
        
    return response


def create_http_exception(error: ContentError) -> HTTPException:
    """
    Convert ContentError to HTTPException
    
    Args:
        error: ContentError instance
        
    Returns:
        HTTPException with appropriate status code and detail
    """
    detail = {
        "message": error.message,
        "error_type": error.__class__.__name__
    }
    
    if error.details:
        detail["details"] = error.details
        
    return HTTPException(
        status_code=error.status_code,
        detail=detail
    )