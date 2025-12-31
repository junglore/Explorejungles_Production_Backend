
"""
Category API Routes
Handles wildlife categories for community organization
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    skip: int = Query(0, ge=0, description="Number of categories to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of categories to return"),
    search: Optional[str] = Query(None, description="Search categories by name or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    mvf_enabled: Optional[bool] = Query(None, description="Filter by MVF enabled status"),
    has_cards: Optional[bool] = Query(None, description="Filter categories that have myth-fact cards"),
    db: AsyncSession = Depends(get_db)
):
    """Get all categories with optional filtering"""
    try:
        from app.models.myth_fact import MythFact
        
        # Join with myth_fact table to get card counts
        query = select(
            Category,
            func.count(MythFact.id).label('card_count')
        ).outerjoin(
            MythFact, Category.id == MythFact.category_id
        ).group_by(Category.id)
        
        # Apply filters
        if is_active is not None:
            query = query.where(Category.is_active == is_active)
        
        if mvf_enabled is not None:
            query = query.where(Category.mvf_enabled == mvf_enabled)
        
        # Filter categories that have cards
        if has_cards is True:
            query = query.having(func.count(MythFact.id) > 0)
        elif has_cards is False:
            query = query.having(func.count(MythFact.id) == 0)
        
        if search:
            search_term = f"%{search}%"
            query = query.where(
                Category.name.ilike(search_term) | 
                Category.description.ilike(search_term)
            )
        
        # Apply pagination and ordering (featured categories first)
        query = query.offset(skip).limit(limit).order_by(Category.is_featured.desc(), Category.name)
        
        result = await db.execute(query)
        categories_with_counts = result.all()
        
        # Extract just the categories from the result
        categories = [row[0] for row in categories_with_counts]
        
        return categories
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch categories: {str(e)}"
        )

@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category_by_id(
    category_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific category by ID"""
    try:
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch category: {str(e)}"
        )

@router.post("/", response_model=CategoryResponse)
async def create_category(
    category_data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new category (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create categories"
        )
    
    try:
        # Check if category with same name exists
        existing_result = await db.execute(
            select(Category).where(Category.name == category_data.name)
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )
        
        # Create slug from name if not provided
        from slugify import slugify
        slug = category_data.slug or slugify(category_data.name)
        
        # Check if slug exists
        slug_result = await db.execute(
            select(Category).where(Category.slug == slug)
        )
        if slug_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this slug already exists"
            )
        
        category = Category(
            name=category_data.name,
            slug=slug,
            description=category_data.description,
            is_active=category_data.is_active
        )
        
        db.add(category)
        await db.commit()
        await db.refresh(category)
        
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create category: {str(e)}"
        )

@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    category_data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update category (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can update categories"
        )
    
    try:
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Update fields
        update_data = category_data.dict(exclude_unset=True)
        
        # Handle slug update
        if 'name' in update_data and 'slug' not in update_data:
            from slugify import slugify
            update_data['slug'] = slugify(update_data['name'])
        
        # Check for conflicts
        if 'name' in update_data:
            existing_result = await db.execute(
                select(Category).where(
                    Category.name == update_data['name'],
                    Category.id != category_id
                )
            )
            if existing_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this name already exists"
                )
        
        if 'slug' in update_data:
            slug_result = await db.execute(
                select(Category).where(
                    Category.slug == update_data['slug'],
                    Category.id != category_id
                )
            )
            if slug_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Category with this slug already exists"
                )
        
        for field, value in update_data.items():
            setattr(category, field, value)
        
        await db.commit()
        await db.refresh(category)
        
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update category: {str(e)}"
        )

@router.delete("/{category_id}")
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete category (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete categories"
        )
    
    try:
        result = await db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        # Check if category has associated content
        from app.models.content import Content
        content_result = await db.execute(
            select(func.count(Content.id)).where(Content.category_id == category_id)
        )
        content_count = content_result.scalar()
        
        if content_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete category with {content_count} associated content items"
            )
        
        await db.delete(category)
        await db.commit()
        
        return {"message": "Category deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete category: {str(e)}"
        )

@router.get("/slug/{slug}", response_model=CategoryResponse)
async def get_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get category by slug"""
    try:
        result = await db.execute(
            select(Category).where(Category.slug == slug)
        )
        category = result.scalar_one_or_none()
        
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        return category
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch category: {str(e)}"
        )