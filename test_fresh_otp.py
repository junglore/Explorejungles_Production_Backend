#!/usr/bin/env python3
"""
Test the current OTP verification with the fresh token
"""

import requests
import json

def test_fresh_otp():
    """Test the fresh OTP we just generated"""
    
    BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
    email = "kattimanijai@gmail.com"
    otp = "426246"  # Fresh OTP from the database
    
    print(f"🧪 Testing Fresh OTP Verification")
    print(f"📧 Email: {email}")
    print(f"🔢 OTP: {otp}")
    print("=" * 50)
    
    try:
        verify_data = {
            "email": email,
            "otp": otp
        }
        
        print("📡 Sending verification request...")
        response = requests.post(f"{BASE_URL}/verify-reset-otp", json=verify_data)
        
        print(f"📊 Response status: {response.status_code}")
        try:
            response_data = response.json()
            print(f"📄 Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"📄 Response (raw): {response.text}")
        
        if response.status_code == 200:
            print("✅ OTP verification successful!")
            return True
        else:
            print("❌ OTP verification failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_fresh_otp()
    
    if success:
        print("\n🎉 PASSWORD RESET OTP VERIFICATION IS WORKING!")
        print("The timezone fix resolved the issue.")
    else:
        print("\n⚠️  Still investigating the issue...")
        print("Check backend logs for detailed debug information.")
