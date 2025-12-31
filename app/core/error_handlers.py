"""
Global error handlers for FastAPI application
"""

import structlog
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError

from app.core.exceptions import ContentError, create_error_response

logger = structlog.get_logger()


async def content_error_handler(request: Request, exc: ContentError) -> JSONResponse:
    """
    Handle custom ContentError exceptions
    
    Args:
        request: FastAPI request object
        exc: ContentError exception
        
    Returns:
        JSONResponse with error details
    """
    logger.warning(
        "Content error occurred",
        error_type=exc.__class__.__name__,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(exc)
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handle HTTPException with standardized response format
    
    Args:
        request: FastAPI request object
        exc: HTTPException
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    
    # If detail is already a dict (from our custom exceptions), use it directly
    if isinstance(exc.detail, dict):
        content = {
            "status": False,
            **exc.detail
        }
    else:
        content = {
            "message": str(exc.detail),
            "status": False,
            "error_type": "HTTPException"
        }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle Pydantic validation errors
    
    Args:
        request: FastAPI request object
        exc: RequestValidationError
        
    Returns:
        JSONResponse with validation error details
    """
    logger.warning(
        "Validation error occurred",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method
    )
    
    # Format validation errors for better readability
    formatted_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        formatted_errors.append({
            "field": field_path,
            "message": error["msg"],
            "type": error["type"]
        })
    
    content = {
        "message": "Validation error occurred",
        "status": False,
        "error_type": "ValidationError",
        "details": {
            "validation_errors": formatted_errors
        }
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=content
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle SQLAlchemy database errors
    
    Args:
        request: FastAPI request object
        exc: SQLAlchemyError
        
    Returns:
        JSONResponse with database error details
    """
    logger.error(
        "Database error occurred",
        error_type=exc.__class__.__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method
    )
    
    # Handle specific database errors
    if isinstance(exc, IntegrityError):
        # Check for common integrity constraint violations
        error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
        
        if "UNIQUE constraint failed" in error_msg or "duplicate key" in error_msg.lower():
            content = {
                "message": "A record with this information already exists",
                "status": False,
                "error_type": "DuplicateError",
                "details": {
                    "constraint_violation": "unique_constraint"
                }
            }
            status_code = status.HTTP_409_CONFLICT
        elif "FOREIGN KEY constraint failed" in error_msg or "foreign key" in error_msg.lower():
            content = {
                "message": "Referenced record does not exist",
                "status": False,
                "error_type": "ForeignKeyError",
                "details": {
                    "constraint_violation": "foreign_key_constraint"
                }
            }
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            content = {
                "message": "Database integrity constraint violation",
                "status": False,
                "error_type": "IntegrityError"
            }
            status_code = status.HTTP_400_BAD_REQUEST
    else:
        content = {
            "message": "Database operation failed",
            "status": False,
            "error_type": "DatabaseError"
        }
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return JSONResponse(
        status_code=status_code,
        content=content
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions
    
    Args:
        request: FastAPI request object
        exc: Exception
        
    Returns:
        JSONResponse with generic error message
    """
    logger.error(
        "Unexpected error occurred",
        error_type=exc.__class__.__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True
    )
    
    content = {
        "message": "An unexpected error occurred. Please try again later.",
        "status": False,
        "error_type": "InternalServerError"
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=content
    )


def register_error_handlers(app):
    """
    Register all error handlers with the FastAPI application
    
    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(ContentError, content_error_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)