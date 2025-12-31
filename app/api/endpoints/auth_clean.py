"""
Authentication endpoints for login, signup, token management with email verification
"""

from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Body, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import secrets

from app.core.config import settings
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.api.deps import get_current_user, oauth2_scheme
from app.core.logging_config import get_logger
from app.db.database import get_db
from app.models.user import User
from app.models.temp_user import TempUserRegistration
from app.services.email_service import email_service
from app.schemas.auth import (
    Token, UserCreate, UserResponse, ForgotPasswordRequest, 
    ResetPasswordRequest, VerifyEmailRequest, ResendVerificationRequest,
    ChangePasswordRequest, TokenData, LoginRequest, VerifyOTPRequest
)

logger = get_logger(__name__)
router = APIRouter()

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# JSON-based login endpoint for frontend
@router.post("/login", response_model=Token)
async def login_json(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with JSON payload and return access token"""
    
    # Get user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if email is verified
    if not user.is_email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email address before logging in",
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "gender": user.gender.value if user.gender else None,
            "country": user.country,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "is_admin": user.is_superuser,
            "is_email_verified": user.is_email_verified
        }
    }


# Form-based login endpoint (OAuth2 compatible)
@router.post("/login-form", response_model=Token)
async def login_form(
    user_credentials: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """Authenticate user with form data and return access token"""
    
    # Get user by email (OAuth2PasswordRequestForm uses 'username' field for email)
    result = await db.execute(
        select(User).where(User.email == user_credentials.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email},
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "gender": user.gender.value if user.gender else None,
            "country": user.country,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "is_admin": user.is_superuser,
            "is_email_verified": user.is_email_verified
        }
    }


@router.post("/signup", response_model=UserResponse)
async def signup(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """Register new user account and send verification email - data stored temporarily until verification"""
    
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if username is taken
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Check if temporary registration already exists
    result = await db.execute(
        select(TempUserRegistration).where(TempUserRegistration.email == user_data.email)
    )
    existing_temp = result.scalar_one_or_none()
    
    if existing_temp:
        # Delete existing temporary registration
        await db.delete(existing_temp)
        await db.commit()
    
    # Create temporary user registration
    hashed_password = get_password_hash(user_data.password)
    otp = email_service.generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    temp_user = TempUserRegistration(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        gender=user_data.gender.value if user_data.gender else None,
        country=user_data.country,
        email_verification_token=otp,
        email_verification_expires=expires_at
    )
    
    db.add(temp_user)
    await db.commit()
    await db.refresh(temp_user)
    
    # Send verification email
    email_sent = await email_service.send_temp_verification_email(db, temp_user)
    
    if not email_sent:
        # If email fails, clean up temporary registration
        await db.delete(temp_user)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again."
        )
    
    return UserResponse(
        id=str(temp_user.id),
        email=temp_user.email,
        username=temp_user.username,
        full_name=temp_user.full_name,
        gender=temp_user.gender,
        country=temp_user.country,
        is_active=False,  # Not active until verified
        is_admin=False,
        is_email_verified=False,
        created_at=temp_user.created_at,
        message="Account registration initiated! Please check your email for verification code."
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token using refresh token"""
    
    try:
        from app.core.security import verify_token
        payload = verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Get user
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id), "email": user.email},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout():
    """Logout user (client-side token removal)"""
    return {"message": "Successfully logged out"}


@router.get("/profile", response_model=UserResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user profile"""
    
    # Get the current user ID to avoid session conflicts
    user_id = current_user.id
    
    # Fetch the user from the database to ensure it's attached to the current session
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        gender=user.gender.value if user.gender else None,
        country=user.country,
        bio=user.bio,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_admin=user.is_superuser,
        is_email_verified=user.is_email_verified,
        created_at=user.created_at
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    profile_data: dict = Body(...),
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """Update user profile"""
    
    try:
        # Log the incoming profile data for debugging
        logger.info(f"Profile update request data: {profile_data}")
        
        # Verify token and get user ID directly
        from app.core.security import verify_token
        
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        try:
            payload = verify_token(token)
            user_id: str = payload.get("sub")
            if user_id is None:
                raise credentials_exception
        except Exception:
            raise credentials_exception
        
        # Fetch the user from the database using the current session
        result = await db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update allowed fields
        if 'username' in profile_data and profile_data['username']:
            # Check if username is already taken by another user
            result = await db.execute(
                select(User).where(
                    User.username == profile_data['username'], 
                    User.id != user.id
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            user.username = profile_data['username']
        
        # Update email if provided
        if 'email' in profile_data and profile_data['email']:
            # Check if email is already taken by another user
            result = await db.execute(
                select(User).where(
                    User.email == profile_data['email'], 
                    User.id != user.id
                )
            )
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already taken"
                )
            user.email = profile_data['email']
        
        # Update other profile fields
        if 'full_name' in profile_data:
            user.full_name = profile_data['full_name']
        
        if 'gender' in profile_data:
            if profile_data['gender']:
                # Convert string to enum
                from app.models.user import GenderEnum
                try:
                    user.gender = GenderEnum(profile_data['gender'])
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid gender value"
                    )
            else:
                user.gender = None
        
        if 'country' in profile_data:
            user.country = profile_data['country']
        
        if 'bio' in profile_data:
            user.bio = profile_data['bio']
        
        if 'avatar_url' in profile_data:
            user.avatar_url = profile_data['avatar_url']
        
        # Update timestamp
        user.updated_at = datetime.utcnow()
        
        # Prepare response data before committing
        response_data = UserResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            gender=user.gender.value if user.gender else None,
            country=user.country,
            bio=user.bio,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_admin=user.is_superuser,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at
        )
        
        # Commit changes
        await db.commit()
        
        return response_data
    
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Profile update failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.post("/upload-avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Upload user avatar image"""
    
    try:
        from app.services.file_upload import file_upload_service
        from app.core.exceptions import (
            FileUploadError, FileSizeError, FileTypeError, 
            create_http_exception
        )
        
        # Validate file type - only images allowed for avatar
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only image files are allowed for avatar upload"
            )
        
        # Upload file using enhanced service with avatar category
        upload_result = await file_upload_service.upload_file(
            file=file,
            file_category="images",
            validate_content=True
        )
        
        # Create avatar URL path
        avatar_url = f"/uploads/{upload_result['file_url']}"
        
        # Get the current user ID to avoid session conflicts
        user_id = current_user.id
        
        # Fetch the user from the database to ensure it's attached to the current session
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete old avatar file if it exists
        if user.avatar_url:
            try:
                from pathlib import Path
                old_file_path = Path("uploads") / user.avatar_url.replace("/uploads/", "")
                if old_file_path.exists():
                    old_file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete old avatar: {e}")
        
        # Update user avatar URL
        user.avatar_url = avatar_url
        user.updated_at = datetime.utcnow()
        
        # Commit changes
        await db.commit()
        
        return {
            "message": "Avatar uploaded successfully",
            "avatar_url": avatar_url,
            "file_info": {
                "filename": upload_result["filename"],
                "file_size": upload_result["file_size"],
                "mime_type": upload_result["mime_type"]
            }
        }
        
    except (FileUploadError, FileSizeError, FileTypeError) as e:
        raise create_http_exception(e)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Avatar upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Avatar upload failed: {str(e)}"
        )


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    
    try:
        # Get the current user ID to avoid session conflicts
        user_id = current_user.id
        
        # Verify current password
        if not verify_password(request.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )
        
        # Fetch the user from the database to ensure it's attached to the current session
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update password
        user.hashed_password = get_password_hash(request.new_password)
        user.updated_at = datetime.utcnow()
        await db.commit()
        
        return {"message": "Password changed successfully"}
    
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password"
        )


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send password reset OTP"""
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Don't reveal if email exists for security
        return {"message": "If the email exists, a reset code has been sent"}
    
    # Send password reset email
    email_sent = await email_service.send_password_reset_email(
        db, user.email, user.full_name or user.username
    )
    
    return {"message": "If the email exists, a reset code has been sent"}


@router.post("/verify-reset-otp")
async def verify_reset_otp(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify password reset OTP"""
    
    success = await email_service.verify_password_reset_otp(db, request.email, request.otp)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )
    
    return {"message": "Reset code verified successfully. You can now set a new password."}


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Reset password using verified OTP"""
    
    # First verify the OTP is still valid
    success = await email_service.verify_password_reset_otp(db, request.email, request.otp)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )
    
    # Find user and update password
    result = await db.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    # Update password and clear reset tokens
    user.hashed_password = get_password_hash(request.new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    user.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Password reset successfully. Please login with your new password."}


@router.post("/verify-email")
async def verify_email(
    request: VerifyOTPRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify email address using OTP and create user account"""
    
    # First try to verify temporary user registration
    success = await email_service.verify_temp_user_otp(db, request.email, request.otp)
    
    if success:
        return {"message": "Email verified successfully! Your account has been created. You can now login."}
    
    # If no temporary registration found, check existing users
    success = await email_service.verify_email_otp(db, request.email, request.otp)
    
    if success:
        return {"message": "Email verified successfully! You can now login."}
    
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired verification code"
    )


@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resend email verification OTP"""
    
    # First try to resend for temporary user registration
    success = await email_service.resend_temp_verification_email(db, request.email)
    
    if success:
        return {"message": "Verification code sent successfully! Please check your email."}
    
    # If no temporary registration found, check existing users
    success = await email_service.resend_verification_email(db, request.email)
    
    if success:
        return {"message": "Verification code sent successfully! Please check your email."}
    
    return {"message": "If the email exists and is not verified, a new verification code has been sent"}
