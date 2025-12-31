"""
Conservation API Routes
Handles conservation efforts and initiatives
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, or_
from typing import List, Optional
from uuid import UUID

from app.db.database import get_db
from app.models.conservation import ConservationEffort
from app.models.user import User
from app.core.security import get_current_user, get_current_user_optional

router = APIRouter()

@router.get("/")
async def get_conservation_efforts(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db)
):
    """Get conservation efforts with filtering and pagination"""
    try:
        query = select(ConservationEffort)
        
        # Apply search filter
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    ConservationEffort.title.ilike(search_term),
                    ConservationEffort.description.ilike(search_term)
                )
            )
        
        # Apply status filter
        if status_filter:
            query = query.where(ConservationEffort.status == status_filter)
        
        # Apply pagination and ordering
        query = query.offset(skip).limit(limit).order_by(desc(ConservationEffort.created_at))
        
        result = await db.execute(query)
        efforts = result.scalars().all()
        
        # Convert to response format
        return [
            {
                "id": str(effort.id),
                "title": effort.title,
                "description": effort.description,
                "status": effort.status,
                "location": effort.location,
                "start_date": effort.start_date.isoformat() if effort.start_date else None,
                "end_date": effort.end_date.isoformat() if effort.end_date else None,
                "budget": effort.budget,
                "raised_amount": effort.raised_amount,
                "image_url": effort.image_url,
                "created_at": effort.created_at.isoformat(),
                "updated_at": effort.updated_at.isoformat()
            }
            for effort in efforts
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conservation efforts: {str(e)}"
        )

@router.get("/{effort_id}")
async def get_conservation_effort(
    effort_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get specific conservation effort by ID"""
    try:
        result = await db.execute(
            select(ConservationEffort).where(ConservationEffort.id == effort_id)
        )
        effort = result.scalar_one_or_none()
        
        if not effort:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conservation effort not found"
            )
        
        return {
            "id": str(effort.id),
            "title": effort.title,
            "description": effort.description,
            "status": effort.status,
            "location": effort.location,
            "start_date": effort.start_date.isoformat() if effort.start_date else None,
            "end_date": effort.end_date.isoformat() if effort.end_date else None,
            "budget": effort.budget,
            "raised_amount": effort.raised_amount,
            "image_url": effort.image_url,
            "created_at": effort.created_at.isoformat(),
            "updated_at": effort.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch conservation effort: {str(e)}"
        )

@router.post("/")
async def create_conservation_effort(
    effort_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new conservation effort (Admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create conservation efforts"
        )
    
    try:
        effort = ConservationEffort(
            title=effort_data.get("title"),
            description=effort_data.get("description"),
            status=effort_data.get("status", "PLANNING"),
            location=effort_data.get("location"),
            budget=effort_data.get("budget"),
            image_url=effort_data.get("image_url")
        )
        
        db.add(effort)
        await db.commit()
        await db.refresh(effort)
        
        return {
            "id": str(effort.id),
            "title": effort.title,
            "description": effort.description,
            "status": effort.status,
            "message": "Conservation effort created successfully"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conservation effort: {str(e)}"
        )

@router.get("/featured/active")
async def get_featured_conservation_efforts(
    limit: int = Query(6, ge=1, le=20, description="Number of featured efforts to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get featured active conservation efforts"""
    try:
        result = await db.execute(
            select(ConservationEffort)
            .where(ConservationEffort.status.in_(["ACTIVE", "ONGOING"]))
            .order_by(desc(ConservationEffort.created_at))
            .limit(limit)
        )
        efforts = result.scalars().all()
        
        return [
            {
                "id": str(effort.id),
                "title": effort.title,
                "description": effort.description,
                "status": effort.status,
                "location": effort.location,
                "budget": effort.budget,
                "raised_amount": effort.raised_amount,
                "image_url": effort.image_url,
                "created_at": effort.created_at.isoformat()
            }
            for effort in efforts
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch featured conservation efforts: {str(e)}"
        )