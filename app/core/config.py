"""
Application configuration using Pydantic Settings
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Database - Railway provides DATABASE_URL automatically
    DATABASE_URL: str = "postgresql+asyncpg://postgres:admin123@localhost:5432/junglore_KE_db"
    TEST_DATABASE_URL: str = "postgresql+asyncpg://postgres:admin123@localhost:5432/junglore_KE_db"
    
    # Redis - Railway provides REDISURL, but we map it to REDIS_URL
    REDIS_URL: str = "redis://localhost:6379/0"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Map Railway's REDISURL to REDIS_URL if available
        if "REDISURL" in os.environ and not os.environ.get("REDIS_URL"):
            self.REDIS_URL = os.environ["REDISURL"]
        
        # Fix DATABASE_URL to use asyncpg driver
        if self.DATABASE_URL and not self.DATABASE_URL.startswith("postgresql+asyncpg"):
            if self.DATABASE_URL.startswith("postgresql://"):
                self.DATABASE_URL = self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Same for test database URL
        if self.TEST_DATABASE_URL and not self.TEST_DATABASE_URL.startswith("postgresql+asyncpg"):
            if self.TEST_DATABASE_URL.startswith("postgresql://"):
                self.TEST_DATABASE_URL = self.TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Security
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Admin Panel
    ADMIN_SECRET_KEY: str = "your-admin-secret-key-change-this"
    ADMIN_USERNAME: str = "admin@junglore.com"
    ADMIN_PASSWORD: str = "admin123"
    
    # File Storage
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_BUCKET_NAME: str = "junglore-media"
    AWS_REGION: str = "us-east-1"
    # Cloudflare R2 Storage
    USE_R2_STORAGE: str = "false"
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    R2_ENDPOINT_URL: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:5173,http://127.0.0.1:8000"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # External APIs
    OPENAI_API_KEY: Optional[str] = None
    
    # Email Configuration (Postmark)
    SENDER_EMAIL: str = "Expedition@junglore.com"
    POSTMARK_SERVER_TOKEN: Optional[str] = None
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    
    # Facebook OAuth Configuration
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None
    
    # LinkedIn OAuth Configuration
    LINKEDIN_CLIENT_ID: Optional[str] = None
    LINKEDIN_CLIENT_SECRET: Optional[str] = None

    # reCAPTCHA
    RECAPTCHA_SECRET_KEY: Optional[str] = None
    
    # Backend URL (for generating upload URLs)
    BACKEND_URL: str = "http://localhost:8000"
    
    # File Upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_FILE_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "video/mp4",
        "video/webm"
    ]
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create settings instance
settings = Settings()


# Validate critical settings
def validate_settings():
    """Validate critical application settings"""
    if settings.SECRET_KEY == "your-super-secret-key-change-this-in-production":
        if settings.ENVIRONMENT == "production":
            raise ValueError("SECRET_KEY must be changed in production")
    
    # Enforce strong admin password in production
    if settings.ADMIN_PASSWORD == "admin123":
        if settings.ENVIRONMENT == "production":
            raise ValueError("ADMIN_PASSWORD must be changed from default value in production. Use a strong password with at least 12 characters.")


# Run validation
validate_settings()
