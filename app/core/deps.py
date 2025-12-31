"""
Dependency functions for FastAPI endpoints
Authentication, authorization, and common dependencies
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from typing import Optional
from uuid import UUID

from app.db.database import get_db
from app.models.user import User
from app.core.config import settings

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    
    Raises 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_identifier: str = payload.get("sub")
        
        if user_identifier is None:
            raise credentials_exception
        
    except JWTError:
        raise credentials_exception
    
    # Get user from database - try UUID first, then email
    try:
        # Try treating as UUID (new format)
        user = await db.get(User, UUID(user_identifier))
    except (ValueError, TypeError):
        # If not a UUID, treat as email (for backwards compatibility and admin tokens)
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.email == user_identifier)
        )
        user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return user


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token is provided, otherwise return None
    
    Used for endpoints that work for both authenticated and anonymous users
    """
    if not token:
        return None
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_identifier: str = payload.get("sub")
        
        if user_identifier is None:
            return None
        
        # Get user from database - try UUID first, then email
        try:
            # Try treating as UUID (new format)
            user = await db.get(User, UUID(user_identifier))
        except (ValueError, TypeError):
            # If not a UUID, treat as email (for backwards compatibility and admin tokens)
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(User.email == user_identifier)
            )
            user = result.scalar_one_or_none()
        
        if user and user.is_active:
            return user
        
    except JWTError:
        return None
    
    return None


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they have admin privileges
    
    Raises 403 if user is not an admin
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    
    return current_user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current user and verify they are active
    
    Raises 403 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    
    return current_user