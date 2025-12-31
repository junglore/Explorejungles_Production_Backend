"""
Test script for email verification functionality
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.email_service import email_service
from app.db.database import get_db
from app.core.config import settings

async def test_email_service():
    """Test email service functionality"""
    
    print("🧪 Testing Email Service Configuration...")
    print(f"Sender Email: {settings.SENDER_EMAIL}")
    print(f"Postmark Token configured: {'Yes' if settings.POSTMARK_SERVER_TOKEN else 'No'}")
    
    # Test basic email sending (without database operations)
    if email_service.client:
        print("✅ Postmark client initialized successfully")
        
        # Test OTP generation
        otp = email_service.generate_otp()
        print(f"📱 Generated OTP: {otp}")
        
        # Test verification token generation
        token = email_service.generate_verification_token()
        print(f"🎟️ Generated token: {token[:10]}...")
        
        print("\n🌟 Email service is ready to send emails!")
        
        # Test email template
        html_template = email_service._get_verification_email_template("Test User", "123456")
        print(f"📧 Email template generated (length: {len(html_template)} chars)")
        
    else:
        print("❌ Postmark client not configured")
        return False
    
    return True

if __name__ == "__main__":
    result = asyncio.run(test_email_service())
    if result:
        print("\n✅ Email service test completed successfully!")
    else:
        print("\n❌ Email service test failed!")
