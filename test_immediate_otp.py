#!/usr/bin/env python3
"""
Request a fresh OTP and test it immediately
"""

import requests
import json
import time

def test_immediate_otp():
    """Request fresh OTP and test immediately"""
    
    BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
    email = "kattimanijai@gmail.com"
    
    print(f"🔄 Step 1: Requesting fresh OTP for {email}...")
    
    try:
        # Request new OTP
        reset_data = {"email": email}
        response = requests.post(f"{BASE_URL}/forgot-password", json=reset_data)
        
        print(f"📊 Request status: {response.status_code}")
        
        if response.status_code != 200:
            print("❌ Failed to request OTP")
            return False
        
        print("✅ OTP requested successfully!")
        
        # Wait a moment for processing
        print("⏳ Waiting 2 seconds for processing...")
        time.sleep(2)
        
        # Now let's check the backend logs for the generated OTP
        # Since we can't read logs directly, let's try some common patterns
        print("\n🔍 Step 2: Testing verification immediately...")
        print("Since we can't see backend logs, please check your server console for the generated OTP")
        print("Look for a log message like: 'Generated OTP: xxxxxx'")
        
        # Ask user for the OTP from logs
        otp = input("\nEnter the OTP from backend logs (or press Enter to skip): ").strip()
        
        if not otp:
            print("Skipping verification test - no OTP provided")
            return False
        
        # Test verification
        verify_data = {
            "email": email,
            "otp": otp
        }
        
        print(f"📡 Testing OTP: {otp}")
        response = requests.post(f"{BASE_URL}/verify-reset-otp", json=verify_data)
        
        print(f"📊 Verification status: {response.status_code}")
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
    print("🧪 Immediate OTP Test")
    print("This will request a fresh OTP and test it immediately")
    print("=" * 60)
    
    success = test_immediate_otp()
    
    if success:
        print("\n🎉 SUCCESS! Password reset OTP verification is working!")
    else:
        print("\n💡 Next steps:")
        print("1. Check backend server logs for the generated OTP")
        print("2. Look for timezone-related debug messages")
        print("3. Verify the email exists in PostgreSQL database")
