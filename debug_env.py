#!/usr/bin/env python3
"""
Debug Environment Variables for Railway
"""

import os
from app.core.config import settings

def debug_env():
    """Debug environment variables"""
    print("🔍 ENVIRONMENT VARIABLE DEBUG")
    print("=" * 50)
    
    # Check critical environment variables
    critical_vars = [
        "DATABASE_URL",
        "REDIS_URL", 
        "REDISURL",
        "SECRET_KEY",
        "ENVIRONMENT",
        "PORT"
    ]
    
    print("📋 Environment Variables:")
    for var in critical_vars:
        value = os.environ.get(var, "NOT SET")
        if "password" in var.lower() or "secret" in var.lower():
            # Mask sensitive values
            if value != "NOT SET":
                value = value[:10] + "..." if len(value) > 10 else "***"
        print(f"  {var}: {value}")
    
    print("\n📋 Settings Object:")
    print(f"  DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    print(f"  REDIS_URL: {settings.REDIS_URL}")
    print(f"  ENVIRONMENT: {settings.ENVIRONMENT}")
    
    print("\n🔍 Railway Detection:")
    print(f"  RAILWAY_ENVIRONMENT: {os.environ.get('RAILWAY_ENVIRONMENT', 'NOT SET')}")
    print(f"  PORT: {os.environ.get('PORT', 'NOT SET')}")

if __name__ == "__main__":
    debug_env()