"""
Authentication schemas for request/response models
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

from app.models.user import GenderEnum
from app.utils.password_validation import validate_password_strength


class UserCreate(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters with uppercase, lowercase, number, and special character")
    username: str = Field(..., min_length=3, max_length=50, description="Username must be 3-50 characters")
    full_name: Optional[str] = Field(None, max_length=100, description="User's full name")
    gender: Optional[GenderEnum] = None
    country: Optional[str] = Field(None, max_length=100, description="User's country")
    recaptcha_token: Optional[str] = Field(None, alias="recaptchaToken")

    class Config:
        populate_by_name = True

    @validator('password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        result = validate_password_strength(v)
        if not result.is_valid:
            raise ValueError('; '.join(result.errors))
        return v


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str
    recaptcha_token: Optional[str] = Field(None, alias="recaptchaToken")

    class Config:
        populate_by_name = True


class GoogleLoginRequest(BaseModel):
    """Schema for Google OAuth login request"""
    credential: str  # JWT token from Google


class FacebookLoginRequest(BaseModel):
    """Schema for Facebook OAuth login request"""
    accessToken: str
    userID: str
    name: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None


class LinkedInLoginRequest(BaseModel):
    """Schema for LinkedIn OAuth login request"""
    code: str  # Authorization code from LinkedIn


class UserResponse(BaseModel):
    """Schema for user response (without sensitive data)"""
    id: str
    email: str
    username: str
    full_name: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    is_admin: bool = False
    is_email_verified: bool = False
    created_at: datetime
    message: Optional[str] = None  # For status messages

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for authentication token response"""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int
    user: Optional[dict] = None


class TokenData(BaseModel):
    """Schema for token payload data"""
    email: Optional[str] = None
    user_id: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    new_password: str = Field(..., min_length=8, description="New password must be at least 8 characters with uppercase, lowercase, number, and special character")

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        result = validate_password_strength(v)
        if not result.is_valid:
            raise ValueError('; '.join(result.errors))
        return v


class VerifyEmailRequest(BaseModel):
    """Schema for email verification request"""
    token: str


class VerifyOTPRequest(BaseModel):
    """Schema for OTP verification request"""
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class ResendVerificationRequest(BaseModel):
    """Schema for resend verification request"""
    email: EmailStr


class ChangePasswordRequest(BaseModel):
    """Schema for change password request"""
    current_password: str
    new_password: str = Field(..., min_length=8, description="New password must be at least 8 characters with uppercase, lowercase, number, and special character")

    @validator('new_password')
    def validate_password_strength(cls, v):
        """Validate password meets security requirements"""
        result = validate_password_strength(v)
        if not result.is_valid:
            raise ValueError('; '.join(result.errors))
        return v