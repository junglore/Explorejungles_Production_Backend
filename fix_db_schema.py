#!/usr/bin/env python3
"""
Manually add the missing password reset columns to SQLite database
"""

import sqlite3
import os

def add_password_reset_columns():
    """Add password reset columns to the users table"""
    
    db_path = "junglore.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔧 Adding password reset columns to users table...")
        
        # Add password_reset_token column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(100)")
            print("✅ Added password_reset_token column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  password_reset_token column already exists")
            else:
                print(f"❌ Error adding password_reset_token: {e}")
        
        # Add password_reset_expires column
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_expires DATETIME")
            print("✅ Added password_reset_expires column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  password_reset_expires column already exists")
            else:
                print(f"❌ Error adding password_reset_expires: {e}")
        
        # Add email verification columns as well
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verification_token VARCHAR(100)")
            print("✅ Added email_verification_token column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  email_verification_token column already exists")
            else:
                print(f"❌ Error adding email_verification_token: {e}")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN email_verification_expires DATETIME")
            print("✅ Added email_verification_expires column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  email_verification_expires column already exists")
            else:
                print(f"❌ Error adding email_verification_expires: {e}")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_email_verified BOOLEAN DEFAULT 0")
            print("✅ Added is_email_verified column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  is_email_verified column already exists")
            else:
                print(f"❌ Error adding is_email_verified: {e}")
        
        # Add other profile columns
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN full_name VARCHAR(100)")
            print("✅ Added full_name column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  full_name column already exists")
        
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
            print("✅ Added last_login column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print("ℹ️  last_login column already exists")
        
        conn.commit()
        print("\n✅ Database schema updated successfully!")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        print("\n📋 Updated Users table schema:")
        for col in columns:
            col_name = col[1].lower()
            if 'reset' in col_name or 'verification' in col_name:
                print(f"   ✓ {col[1]} ({col[2]}) - nullable: {not col[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    print("🔧 Database Schema Fix Tool")
    print("Adding missing password reset columns...")
    print("=" * 50)
    
    add_password_reset_columns()
