#!/usr/bin/env python3
"""
Inspect the database to see the actual OTP data
"""

import asyncio
import sys
import os
from datetime import datetime
import sqlite3

def check_sqlite_otp_data():
    """Check OTP data in SQLite database"""
    
    db_path = "junglore.db"
    email = "kattimanijai@gmail.com"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if user exists and get OTP data
        cursor.execute("""
            SELECT email, password_reset_token, password_reset_expires, 
                   created_at, updated_at
            FROM users 
            WHERE email = ?
        """, (email,))
        
        result = cursor.fetchone()
        
        if result:
            email_db, reset_token, reset_expires, created_at, updated_at = result
            
            print(f"📧 Email: {email_db}")
            print(f"🔑 Password Reset Token: '{reset_token}'")
            print(f"⏰ Password Reset Expires: {reset_expires}")
            print(f"📅 Created: {created_at}")
            print(f"🔄 Updated: {updated_at}")
            
            if reset_expires:
                print(f"\n⏱️  Current time: {datetime.utcnow()}")
                print(f"⏳ Expiry time: {reset_expires}")
                
                # Parse the expiry time
                try:
                    if isinstance(reset_expires, str):
                        # Try different datetime formats
                        for fmt in ['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S']:
                            try:
                                expiry_dt = datetime.strptime(reset_expires, fmt)
                                break
                            except ValueError:
                                continue
                        else:
                            expiry_dt = datetime.fromisoformat(reset_expires.replace('Z', '+00:00')).replace(tzinfo=None)
                    else:
                        expiry_dt = reset_expires
                    
                    current_time = datetime.utcnow()
                    is_valid = expiry_dt > current_time
                    
                    print(f"✅ Token valid: {is_valid}")
                    if not is_valid:
                        time_diff = current_time - expiry_dt
                        print(f"❌ Expired {time_diff} ago")
                    else:
                        time_left = expiry_dt - current_time
                        print(f"⏰ Time remaining: {time_left}")
                        
                except Exception as e:
                    print(f"❌ Error parsing expiry time: {e}")
            else:
                print("❌ No password reset expiry time set")
                
        else:
            print(f"❌ No user found with email: {email}")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

def main():
    """Run the database inspection"""
    print("🔍 Database OTP Inspection Tool")
    print("=" * 40)
    
    check_sqlite_otp_data()

if __name__ == "__main__":
    main()
