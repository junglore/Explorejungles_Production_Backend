#!/usr/bin/env python3
"""
Check PostgreSQL database for OTP data
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text
from app.models.user import User
from app.core.config import settings

async def check_postgresql_otp_data():
    """Check OTP data in PostgreSQL database"""
    
    email = "kattimanijai@gmail.com"
    
    try:
        # Create async engine and session
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as session:
            # Check if user exists and get OTP data
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                print(f"📧 Email: {user.email}")
                print(f"👤 Username: {user.username}")
                print(f"🔑 Password Reset Token: '{user.password_reset_token}'")
                print(f"⏰ Password Reset Expires: {user.password_reset_expires}")
                print(f"✅ Is Active: {user.is_active}")
                print(f"📧 Email Verified: {user.is_email_verified}")
                print(f"📅 Created: {user.created_at}")
                print(f"🔄 Updated: {user.updated_at}")
                
                if user.password_reset_expires:
                    current_time = datetime.utcnow()
                    expires_time = user.password_reset_expires
                    
                    # Handle timezone
                    if expires_time.tzinfo is not None:
                        expires_time = expires_time.replace(tzinfo=None)
                    
                    print(f"\n⏱️  Current time (UTC): {current_time}")
                    print(f"⏳ Expiry time: {expires_time}")
                    print(f"⚖️  Valid: {expires_time > current_time}")
                    
                    if expires_time > current_time:
                        time_left = expires_time - current_time
                        print(f"⏰ Time remaining: {time_left}")
                    else:
                        time_diff = current_time - expires_time
                        print(f"❌ Expired {time_diff} ago")
                else:
                    print("❌ No password reset token set")
            else:
                print(f"❌ No user found with email: {email}")
                
            # Also list all users
            print(f"\n📋 All users in database:")
            stmt = select(User.email, User.username, User.password_reset_token, User.password_reset_expires)
            result = await session.execute(stmt)
            users = result.fetchall()
            
            for user_data in users:
                email_db, username, reset_token, reset_expires = user_data
                print(f"   📧 {email_db} ({username})")
                if reset_token:
                    print(f"      🔑 Token: {reset_token}")
                    print(f"      ⏰ Expires: {reset_expires}")
                    
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run the PostgreSQL database check"""
    print("🔍 PostgreSQL OTP Inspection Tool")
    print("=" * 50)
    
    asyncio.run(check_postgresql_otp_data())

if __name__ == "__main__":
    main()
