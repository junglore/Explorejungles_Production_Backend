#!/usr/bin/env python3
"""
Request password reset for admin user
"""

import requests
import json

def request_admin_otp():
    """Request a new OTP for admin user"""
    
    BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
    email = "admin@junglore.com"
    
    print(f"🔄 Requesting new password reset OTP for {email}...")
    
    try:
        reset_data = {"email": email}
        response = requests.post(f"{BASE_URL}/forgot-password", json=reset_data)
        
        print(f"📊 Response status: {response.status_code}")
        try:
            response_data = response.json()
            print(f"📄 Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"📄 Response (raw): {response.text}")
            
        if response.status_code == 200:
            print("✅ New OTP requested successfully!")
            print("📧 Check the backend logs for the OTP (since admin email might not be configured for actual sending)")
        else:
            print("❌ Failed to request new OTP")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    request_admin_otp()
