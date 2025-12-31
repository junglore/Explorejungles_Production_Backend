#!/usr/bin/env python3
"""
Request new password reset OTP
"""

import requests
import json

def request_new_otp():
    """Request a new OTP for testing"""
    
    BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
    email = "kattimanijai@gmail.com"
    
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
            print("✅ New OTP requested successfully! Check your email.")
            print("📧 The OTP will be valid for 15 minutes.")
            print("🔢 After receiving the OTP, run the test again with the new code.")
        else:
            print("❌ Failed to request new OTP")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    request_new_otp()
