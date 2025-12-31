"""
Temporary user registration model for storing user data before email verification
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

from app.db.database import Base
from app.models.user import GenderEnum


class TempUserRegistration(Base):
    """Temporary storage for user registration data before email verification"""
    __tablename__ = "temp_user_registrations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    
    # OTP verification fields
    email_verification_token = Column(String(10), nullable=False)
    email_verification_expires = Column(DateTime, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    is_expired = Column(Boolean, default=False)
    
    def is_verification_expired(self) -> bool:
        """Check if verification has expired"""
        return datetime.utcnow() > self.email_verification_expires
    
    def to_user_dict(self) -> dict:
        """Convert temp registration to user creation dict"""
        return {
            "email": self.email,
            "username": self.username,
            "hashed_password": self.hashed_password,
            "full_name": self.full_name,
            "gender": self.gender,
            "country": self.country,
            "is_active": True,
            "is_superuser": False,
            "is_email_verified": True  # Will be verified after OTP
        }
