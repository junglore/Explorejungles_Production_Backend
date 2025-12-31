"""
Content formatting utilities for standardized API responses
"""

from typing import List, Optional
from app.models.content import Content, ContentStatusEnum
from app.schemas.content import StandardContentItem, StandardPaginationResponse, StandardAPIResponse
from app.core.exceptions import create_error_response, ContentError
from app.core.config import settings


def format_content_item(content: Content, include_full_content: bool = False) -> StandardContentItem:
    """
    Format a Content model instance to StandardContentItem
    
    Args:
        content: Content model instance
        include_full_content: Whether to include full content text (for single item responses)
    
    Returns:
        StandardContentItem formatted according to junglore.com pattern
    """
    # Construct full image URLs for frontend
    def build_image_url(image_path):
        if not image_path:
            return None
        # If it's already a full URL, return as is
        if image_path.startswith(('http://', 'https://')):
            return image_path
        # If it's a relative path, construct full URL
        if image_path.startswith('/'):
            return f"{settings.BACKEND_URL}{image_path}"
        else:
            return f"{settings.BACKEND_URL}/uploads/{image_path}"
    
    return StandardContentItem(
        id=str(content.id),
        title=content.title,
        slug=content.slug,
        category_id=str(content.category_id) if content.category_id else None,
        banner=build_image_url(content.banner),
        image=build_image_url(content.featured_image),  # Map featured_image to image
        video=build_image_url(content.video),
        description=content.excerpt,  # Map excerpt to description
        content=content.content if include_full_content else None,
        featured=content.featured or False,
        feature_place=content.feature_place or 0,
        status=content.status == ContentStatusEnum.PUBLISHED,
        type=content.type.value if content.type else None,
        author_name=content.author_name,  # Include author_name from content
        createdAt=content.created_at.isoformat(),
        updatedAt=content.updated_at.isoformat()
    )


def format_content_list(
    content_list: List[Content], 
    page: int, 
    limit: int, 
    total_items: int
) -> StandardPaginationResponse:
    """
    Format a list of Content models to StandardPaginationResponse
    
    Args:
        content_list: List of Content model instances
        page: Current page number
        limit: Items per page
        total_items: Total number of items
    
    Returns:
        StandardPaginationResponse with formatted content items
    """
    formatted_items = [format_content_item(content) for content in content_list]
    total_pages = (total_items + limit - 1) // limit
    
    return StandardPaginationResponse(
        result=formatted_items,
        totalPages=total_pages,
        currentPage=page,
        limit=len(formatted_items)
    )


def create_success_response(
    data: StandardPaginationResponse | StandardContentItem | dict,
    message: str
) -> StandardAPIResponse:
    """
    Create a standardized success response
    
    Args:
        data: Response data (pagination, single item, or dict)
        message: Success message
    
    Returns:
        StandardAPIResponse with success status
    """
    return StandardAPIResponse(
        message=message,
        data=data,
        status=True
    )


def create_error_response_dict(message: str, status_code: int = 400) -> dict:
    """
    Create a standardized error response dictionary
    
    Args:
        message: Error message
        status_code: HTTP status code
    
    Returns:
        Dictionary with error details
    """
    return {
        "message": message,
        "status": False,
        "status_code": status_code
    }