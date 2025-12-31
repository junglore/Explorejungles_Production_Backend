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
        
        # Get all users with their details
        users = await conn.fetch("""
            SELECT 
                email, 
                username, 
                is_active,
                is_superuser,
                password_reset_token, 
                password_reset_expires 
            FROM users 
            ORDER BY created_at
        """)
        
        if users:
            print(f"📋 Found {len(users)} users:")
            for user in users:
                user_type = "👑 Admin" if user['is_superuser'] else "👤 User"
                status = "✅ Active" if user['is_active'] else "❌ Inactive"
                print(f"   📧 {user['email']} ({user['username']}) - {user_type} - {status}")
                if user['password_reset_token']:
                    print(f"      🔑 Reset Token: {user['password_reset_token']}")
                    print(f"      ⏰ Expires: {user['password_reset_expires']}")
        else:
            print("❌ No users found in database")
            
        await conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    asyncio.run(list_users())
