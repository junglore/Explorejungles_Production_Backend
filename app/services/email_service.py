"""
Email service for sending verification emails, OTPs, and password reset emails using Postmark
"""

import random
import string
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from postmarker.core import PostmarkClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.core.config import settings
from app.models.user import User
from app.models.temp_user import TempUserRegistration
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class EmailService:
    """Service for handling email operations"""
    
    def __init__(self):
        """Initialize email service with Postmark client"""
        if not settings.POSTMARK_SERVER_TOKEN:
            logger.warning("POSTMARK_SERVER_TOKEN not configured - email functionality disabled")
            self.client = None
        else:
            self.client = PostmarkClient(server_token=settings.POSTMARK_SERVER_TOKEN)
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP"""
        otp = ''.join(random.choices(string.digits, k=length))
        logger.info(f"Generated OTP: '{otp}' (length: {len(otp)}, type: {type(otp)})")
        return otp
    
    def generate_verification_token(self, length: int = 32) -> str:
        """Generate a random verification token"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    async def send_temp_verification_email(
        self, 
        db: AsyncSession, 
        temp_user: TempUserRegistration
    ) -> bool:
        """Send email verification OTP for temporary user registration"""
        if not self.client:
            logger.error("Email client not configured")
            return False
        
        try:
            # Send email
            response = self.client.emails.send(
                From=settings.SENDER_EMAIL,
                To=temp_user.email,
                Subject="Verify Your Junglore Account",
                HtmlBody=self._get_verification_email_template(
                    temp_user.full_name or temp_user.username, 
                    temp_user.email_verification_token
                ),
                TextBody=f"Hello {temp_user.full_name or temp_user.username},\n\nYour verification code is: {temp_user.email_verification_token}\n\nThis code will expire in 15 minutes.\n\nBest regards,\nJunglore Team"
            )
            
            logger.info(f"Verification email sent to {temp_user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {temp_user.email}: {str(e)}")
            return False
    
    async def verify_temp_user_otp(
        self, 
        db: AsyncSession, 
        user_email: str, 
        otp: str
    ) -> bool:
        """Verify OTP for temporary user registration and create actual user"""
        try:
            # Get temporary user registration
            stmt = select(TempUserRegistration).where(TempUserRegistration.email == user_email)
            result = await db.execute(stmt)
            temp_user = result.scalar_one_or_none()
            
            if not temp_user:
                logger.warning(f"No temporary registration found for {user_email}")
                return False
            
            # Get current time (timezone-naive to match database)
            current_time = datetime.utcnow()
            
            # Debug logging to help troubleshoot timing issues
            logger.info(f"Temp user OTP verification for {user_email}: current_time={current_time}, expires_time={temp_user.email_verification_expires}, otp_match={temp_user.email_verification_token == otp}")
            
            # Check OTP and expiration
            if (temp_user.email_verification_token == otp and 
                temp_user.email_verification_expires > current_time):
                
                # Create actual user from temporary data
                from app.models.user import GenderEnum
                
                # Convert gender string back to enum if needed
                gender_enum = None
                if temp_user.gender:
                    try:
                        gender_enum = GenderEnum(temp_user.gender)
                    except ValueError:
                        gender_enum = None
                
                new_user = User(
                    email=temp_user.email,
                    username=temp_user.username,
                    hashed_password=temp_user.hashed_password,
                    full_name=temp_user.full_name,
                    gender=gender_enum,
                    country=temp_user.country,
                    is_active=True,
                    is_superuser=False,
                    is_email_verified=True  # Verified through OTP
                )
                
                # Add new user and delete temporary registration
                db.add(new_user)
                
                # Delete temporary registration
                delete_stmt = delete(TempUserRegistration).where(TempUserRegistration.email == user_email)
                await db.execute(delete_stmt)
                
                await db.commit()
                
                logger.info(f"User account created successfully for {user_email}")
                return True
            else:
                logger.warning(f"Invalid or expired OTP for {user_email}: OTP={otp}, stored_token={temp_user.email_verification_token}, expired={(temp_user.email_verification_expires <= current_time)}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to verify temp user OTP for {user_email}: {str(e)}")
            await db.rollback()
            return False
    
    async def resend_temp_verification_email(
        self, 
        db: AsyncSession, 
        user_email: str
    ) -> bool:
        """Resend verification email for temporary user registration"""
        try:
            # Get temporary user registration
            stmt = select(TempUserRegistration).where(TempUserRegistration.email == user_email)
            result = await db.execute(stmt)
            temp_user = result.scalar_one_or_none()
            
            if not temp_user:
                logger.warning(f"No temporary registration found for {user_email}")
                return False
            
            # Generate new OTP and update expiration
            new_otp = self.generate_otp()
            new_expires = datetime.utcnow() + timedelta(minutes=15)
            
            # Update temporary user with new OTP
            update_stmt = update(TempUserRegistration).where(
                TempUserRegistration.email == user_email
            ).values(
                email_verification_token=new_otp,
                email_verification_expires=new_expires
            )
            await db.execute(update_stmt)
            
            # Refresh the temp_user object
            await db.refresh(temp_user)
            temp_user.email_verification_token = new_otp
            temp_user.email_verification_expires = new_expires
            
            await db.commit()
            
            # Send new verification email
            return await self.send_temp_verification_email(db, temp_user)
            
        except Exception as e:
            logger.error(f"Failed to resend verification email for {user_email}: {str(e)}")
            await db.rollback()
            return False
    
    async def send_password_reset_email(
        self, 
        db: AsyncSession, 
        user_email: str, 
        user_name: str
    ) -> bool:
        """Send password reset OTP"""
        if not self.client:
            logger.error("Email client not configured")
            return False
        
        try:
            # Generate OTP
            otp = self.generate_otp()
            # Use timezone-aware datetime for consistency with the database
            from datetime import timezone
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)  # OTP expires in 15 minutes
            
            logger.info(f"Password reset for {user_email}: Generated OTP='{otp}', expires_at={expires_at}")
            
            # Update user with reset token
            stmt = update(User).where(User.email == user_email).values(
                password_reset_token=otp,
                password_reset_expires=expires_at
            )
            await db.execute(stmt)
            await db.commit()
            
            logger.info(f"Password reset token stored for {user_email}")
            
            # Send email
            response = self.client.emails.send(
                From=settings.SENDER_EMAIL,
                To=user_email,
                Subject="Reset Your Junglore Password",
                HtmlBody=self._get_password_reset_email_template(user_name, otp),
                TextBody=f"Hello {user_name},\n\nYour password reset code is: {otp}\n\nThis code will expire in 15 minutes.\n\nIf you didn't request this, please ignore this email.\n\nBest regards,\nJunglore Team"
            )
            
            logger.info(f"Password reset email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send password reset email to {user_email}: {str(e)}")
            return False
    
    async def send_verification_email(
        self, 
        db: AsyncSession, 
        user_email: str, 
        user_name: str
    ) -> bool:
        """Send email verification OTP for existing users"""
        if not self.client:
            logger.error("Email client not configured")
            return False
        
        try:
            # Generate OTP
            otp = self.generate_otp()
            expires_at = datetime.utcnow().replace(tzinfo=None) + timedelta(minutes=15)  # OTP expires in 15 minutes
            
            # Update user with verification token
            stmt = update(User).where(User.email == user_email).values(
                email_verification_token=otp,
                email_verification_expires=expires_at
            )
            await db.execute(stmt)
            await db.commit()
            
            # Send email
            response = self.client.emails.send(
                From=settings.SENDER_EMAIL,
                To=user_email,
                Subject="Verify Your Junglore Account",
                HtmlBody=self._get_verification_email_template(user_name, otp),
                TextBody=f"Hello {user_name},\n\nYour verification code is: {otp}\n\nThis code will expire in 15 minutes.\n\nBest regards,\nJunglore Team"
            )
            
            logger.info(f"Verification email sent to {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {user_email}: {str(e)}")
            return False
    
    async def verify_email_otp(
        self, 
        db: AsyncSession, 
        user_email: str, 
        otp: str
    ) -> bool:
        """Verify email OTP and activate existing user"""
        try:
            # Get user
            stmt = select(User).where(User.email == user_email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Get current time (timezone-naive to match database)
            current_time = datetime.utcnow().replace(tzinfo=None)
            
            # Convert expiration to timezone-naive if it's timezone-aware
            expires_time = user.email_verification_expires
            if expires_time and expires_time.tzinfo is not None:
                expires_time = expires_time.replace(tzinfo=None)
            
            # Debug logging to help troubleshoot timing issues
            logger.info(f"Email OTP verification for {user_email}: current_time={current_time}, expires_time={expires_time}, otp_match={user.email_verification_token == otp}")
            
            # Check OTP and expiration
            if (user.email_verification_token == otp and 
                expires_time and 
                expires_time > current_time):
                
                # Verify user and clear tokens
                stmt = update(User).where(User.email == user_email).values(
                    is_email_verified=True,
                    email_verification_token=None,
                    email_verification_expires=None
                )
                await db.execute(stmt)
                await db.commit()
                
                logger.info(f"Email verified successfully for {user_email}")
                return True
            
            logger.warning(f"Email OTP verification failed for {user_email}: OTP={otp}, stored_token={user.email_verification_token}, expired={(expires_time <= current_time) if expires_time else 'No expiry set'}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify email OTP for {user_email}: {str(e)}")
            return False
    
    async def verify_password_reset_otp(
        self, 
        db: AsyncSession, 
        user_email: str, 
        otp: str
    ) -> bool:
        """Verify password reset OTP"""
        try:
            # Get user
            stmt = select(User).where(User.email == user_email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"No user found for email: {user_email}")
                return False
            
            logger.info(f"Found user for {user_email}: password_reset_token={user.password_reset_token}, expires={user.password_reset_expires}")
            
            # Normalize OTP strings (strip whitespace, ensure string type)
            provided_otp = str(otp).strip()
            stored_otp = str(user.password_reset_token).strip() if user.password_reset_token else None
            
            # Get current time - use timezone-aware for consistency  
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
            
            # Ensure expires_time is timezone-aware
            expires_time = user.password_reset_expires
            if expires_time and expires_time.tzinfo is None:
                # If stored as naive, assume it's UTC
                expires_time = expires_time.replace(tzinfo=timezone.utc)
            
            # Debug logging to help troubleshoot timing issues
            logger.info(f"Password reset OTP verification for {user_email}: current_time={current_time}, expires_time={expires_time}")
            logger.info(f"OTP comparison: provided='{provided_otp}' (len={len(provided_otp)}), stored='{stored_otp}' (len={len(stored_otp) if stored_otp else 0}), exact_match={provided_otp == stored_otp}")
            
            # Check OTP and expiration
            if (stored_otp and provided_otp == stored_otp and 
                expires_time and 
                expires_time > current_time):
                
                logger.info(f"Password reset OTP verified for {user_email}")
                return True
            
            logger.warning(f"Password reset OTP verification failed for {user_email}: provided_otp='{provided_otp}', stored_otp='{stored_otp}', expired={(expires_time <= current_time) if expires_time else 'No expiry set'}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to verify password reset OTP for {user_email}: {str(e)}")
            return False
    
    async def resend_verification_email(
        self, 
        db: AsyncSession, 
        user_email: str
    ) -> bool:
        """Resend verification email for existing users"""
        try:
            # Get user
            stmt = select(User).where(User.email == user_email)
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            if user.is_email_verified:
                logger.info(f"User {user_email} is already verified")
                return False
            
            return await self.send_verification_email(db, user_email, user.full_name or user.username)
            
        except Exception as e:
            logger.error(f"Failed to resend verification email for {user_email}: {str(e)}")
            return False
    
    def _get_password_reset_email_template(self, user_name: str, otp: str) -> str:
        """Get HTML template for password reset email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reset Your Junglore Password</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #f57c00, #ff9800); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background: #fff; border: 2px solid #ff9800; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #f57c00; letter-spacing: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 14px; }}
                .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔐 Password Reset Request</h1>
                    <p>Junglore Account Security</p>
                </div>
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    <p>We received a request to reset your Junglore account password. Use the verification code below to proceed with resetting your password:</p>
                    
                    <div class="otp-box">
                        <p>Your password reset code is:</p>
                        <div class="otp-code">{otp}</div>
                        <p><small>This code will expire in 15 minutes</small></p>
                    </div>
                    
                    <div class="warning">
                        <p><strong>Security Notice:</strong> If you didn't request this password reset, please ignore this email. Your account remains secure.</p>
                    </div>
                    
                    <p>Enter this code in the password reset screen to create a new password for your account.</p>
                </div>
                <div class="footer">
                    <p>Best regards,<br>The Junglore Security Team</p>
                    <p><small>This is an automated email. Please do not reply to this message.</small></p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_verification_email_template(self, user_name: str, otp: str) -> str:
        """Get HTML template for verification email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Verify Your Junglore Account</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #2e7d32, #4caf50); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ background: #fff; border: 2px solid #4caf50; border-radius: 8px; padding: 20px; text-align: center; margin: 20px 0; }}
                .otp-code {{ font-size: 32px; font-weight: bold; color: #2e7d32; letter-spacing: 5px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 14px; }}
                .button {{ background: #4caf50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌿 Welcome to Junglore!</h1>
                    <p>Discover and protect wildlife with us</p>
                </div>
                <div class="content">
                    <h2>Hello {user_name}!</h2>
                    <p>Thank you for joining the Junglore community! To complete your registration and start exploring our wildlife conservation platform, please verify your email address using the code below:</p>
                    
                    <div class="otp-box">
                        <p>Your verification code is:</p>
                        <div class="otp-code">{otp}</div>
                        <p><small>This code will expire in 15 minutes</small></p>
                    </div>
                    
                    <p>Enter this code in the verification screen to activate your account and start your journey with Junglore!</p>
                    
                    <p>If you didn't create this account, please ignore this email.</p>
                </div>
                <div class="footer">
                    <p>Best regards,<br>The Junglore Team</p>
                    <p><small>This is an automated email. Please do not reply to this message.</small></p>
                </div>
            </div>
        </body>
        </html>
        """


# Create email service instance
email_service = EmailService()
