#!/usr/bin/env python3
"""
Quick test to verify password reset OTP directly
"""

import asyncio
import requests
import json

def test_password_reset_verification():
    """Test the password reset OTP verification with the exact values from the screenshot"""
    
    BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
    
    # From the screenshot
    email = "kattimanijai@gmail.com"
    otp = "394062"
    
    print(f"🧪 Testing Password Reset OTP Verification")
    print(f"📧 Email: {email}")
    print(f"🔢 OTP: {otp}")
    print("=" * 50)
    
    try:
        # Test the verify-reset-otp endpoint
        verify_data = {
            "email": email,
            "otp": otp
        }
        
        print("📡 Sending verification request...")
        print(f"Request data: {json.dumps(verify_data, indent=2)}")
        
        response = requests.post(f"{BASE_URL}/verify-reset-otp", json=verify_data)
        
        print(f"📊 Response status: {response.status_code}")
        print(f"📋 Response headers: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"📄 Response body: {json.dumps(response_data, indent=2)}")
        except:
            print(f"📄 Response body (raw): {response.text}")
        
        if response.status_code == 200:
            print("✅ OTP verification successful!")
        elif response.status_code == 400:
            print("❌ OTP verification failed - Bad Request")
        elif response.status_code == 422:
            print("❌ Validation error - Check request format")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed! Make sure the backend server is running:")
        print("   cd KE_Junglore_Backend_Production-main")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        
    except Exception as e:
        print(f"❌ Error: {e}")

def test_request_new_otp():
    """Request a new OTP for testing"""
    
    BASE_URL = "http://127.0.0.1:8000/api/v1/auth"
    email = "kattimanijai@gmail.com"
    
    print(f"\n🔄 Requesting new password reset OTP for {email}...")
    
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
        else:
            print("❌ Failed to request new OTP")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Password Reset OTP Debug Tool")
    print("This tool tests the exact scenario from your screenshot")
    print()
    
    # First test with current OTP
    test_password_reset_verification()
    
    # Offer to request new OTP
    print("\n" + "=" * 50)
    user_input = input("Would you like to request a new OTP? (y/n): ")
    if user_input.lower() == 'y':
        test_request_new_otp()
        print("\n📧 Check your email for the new OTP, then run this script again!")
