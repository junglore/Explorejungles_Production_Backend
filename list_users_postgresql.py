#!/usr/bin/env python3
"""
List all users in the PostgreSQL database
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

async def list_users():
    """List all users in the PostgreSQL database"""
    
    # Load environment variables
    load_dotenv()
    
    # Database connection details
    db_host = "localhost"
    db_port = 5432
    db_name = "junglore_KE_db"
    db_user = "postgres"
    db_password = "admin123"
    
    try:
        # Connect to PostgreSQL
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        
        print(f"✅ Connected to PostgreSQL database: {db_name}")
        
        # Check if users table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        
        if not table_exists:
            print("❌ Users table does not exist")
            await conn.close()
            return
        
        # Get all users with their details
        users = await conn.fetch("""
            SELECT 
                id,
                email, 
                username, 
                is_active,
                is_superuser,
                created_at,
                password_reset_token, 
                password_reset_expires 
            FROM users 
            ORDER BY created_at
        """)
        
        if users:
            print(f"📋 Found {len(users)} users in PostgreSQL database:")
            print("=" * 80)
            
            for i, user in enumerate(users, 1):
                print(f"{i}. 👤 {user['username']} ({user['email']})")
                print(f"   🆔 ID: {user['id']}")
                print(f"   ✅ Active: {user['is_active']}")
                print(f"   👑 Superuser: {user['is_superuser']}")
                print(f"   📅 Created: {user['created_at']}")
                
                if user['password_reset_token']:
                    print(f"   🔑 Reset Token: {user['password_reset_token']}")
                    print(f"   ⏰ Token Expires: {user['password_reset_expires']}")
                else:
                    print(f"   🔑 Reset Token: None")
                
                print("-" * 40)
        else:
            print("❌ No users found in PostgreSQL database")
        
        # Also check temporary users table if it exists
        temp_table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'tempuserregistration'
            );
        """)
        
        if temp_table_exists:
            temp_users = await conn.fetch("""
                SELECT email, username, otp, otp_expires, created_at 
                FROM tempuserregistration 
                ORDER BY created_at
            """)
            
            if temp_users:
                print(f"\n🔄 Found {len(temp_users)} temporary users:")
                print("=" * 80)
                
                for i, temp_user in enumerate(temp_users, 1):
                    print(f"{i}. 🕐 {temp_user['username']} ({temp_user['email']})")
                    print(f"   🔢 OTP: {temp_user['otp']}")
                    print(f"   ⏰ OTP Expires: {temp_user['otp_expires']}")
                    print(f"   📅 Created: {temp_user['created_at']}")
                    print("-" * 40)
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    asyncio.run(list_users())
