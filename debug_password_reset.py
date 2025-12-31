#!/usr/bin/env python3
"""
Debug script to check password reset OTP data directly in database
"""

import asyncio
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db_session
from app.models.user import User

async def check_password_reset_data():
    """Check password reset data for a specific email"""
    
    email = "jaikattimani@9Jai.com"  # Change this to the email you're testing with
    
    # Create async session
    async_session = get_db_session()
    async with async_session() as session:
        try:
            # Get user data
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ No user found with email: {email}")
                return
            
            print(f"📧 User found: {user.email}")
            print(f"🔑 Password reset token: {user.password_reset_token}")
            print(f"⏰ Password reset expires: {user.password_reset_expires}")
            
            if user.password_reset_expires:
                current_time = datetime.utcnow()
                expires_time = user.password_reset_expires
                
                # Handle timezone
                if expires_time.tzinfo is not None:
                    expires_time = expires_time.replace(tzinfo=None)
                
                print(f"🕐 Current time (UTC): {current_time}")
                print(f"⏳ Expiry time: {expires_time}")
                print(f"⚖️  Comparison: expires_time > current_time = {expires_time > current_time}")
                
                if expires_time > current_time:
                    print("✅ Token is still valid (not expired)")
                else:
                    print("❌ Token has expired")
                    time_diff = current_time - expires_time
                    print(f"   Expired {time_diff} ago")
            else:
                print("❌ No password reset expiry time set")
                
        except Exception as e:
            print(f"❌ Error: {e}")

def main():
    """Run the debug check"""
    print("🔍 Password Reset OTP Debug Tool")
    print("=" * 40)
    
    asyncio.run(check_password_reset_data())

if __name__ == "__main__":
    main()
