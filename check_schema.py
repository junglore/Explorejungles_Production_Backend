#!/usr/bin/env python3
"""
Check database schema
"""

import sqlite3
import os

def check_schema():
    """Check the database schema"""
    
    db_path = "junglore.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table schema
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("📋 Users table schema:")
        for col in columns:
            print(f"   {col[1]} ({col[2]}) - nullable: {not col[3]}")
        
        # Check for any OTP-related columns
        print("\n🔍 Looking for OTP-related columns:")
        for col in columns:
            col_name = col[1].lower()
            if 'reset' in col_name or 'otp' in col_name or 'token' in col_name or 'verification' in col_name:
                print(f"   ✓ {col[1]} ({col[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    check_schema()
