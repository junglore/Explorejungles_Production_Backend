#!/usr/bin/env python3
"""
Junglore Backend Production Server
=================================

This is the ONLY server startup file for the Junglore Backend.
It configures the server with proper large upload limits (50MB) and
multipart library patches for handling large file uploads.

HOW TO START THE SERVER:
=======================

1. Make sure you're in the Junglore_Backend_Production directory
2. Activate your virtual environment: source venv/bin/activate
3. Install dependencies: pip install -r requirements.txt
4. Start the server: python3 start_with_large_limits.py

The server will be available at:
- Main API: http://127.0.0.1:8000
- Admin Panel: http://127.0.0.1:8000/admin
- API Docs: http://127.0.0.1:8000/api/docs

FEATURES:
=========
- 50MB file upload limit for images and videos
- Proper multipart library configuration
- Admin panel with authentication
- CORS configured for frontend
- Static file serving for uploads
- Database connection management
"""

import os
import sys
import uvicorn

# Set environment variables for large requests
os.environ["MAX_CONTENT_LENGTH"] = str(50 * 1024 * 1024)  # 50MB
os.environ["UVICORN_MAX_CONTENT_SIZE"] = str(50 * 1024 * 1024)  # 50MB

# Patch multipart library BEFORE importing anything else
try:
    import multipart
    
    # Patch the FormParser DEFAULT_CONFIG
    multipart.FormParser.DEFAULT_CONFIG['MAX_MEMORY_FILE_SIZE'] = 50 * 1024 * 1024  # 50MB
    multipart.FormParser.DEFAULT_CONFIG['MAX_BODY_SIZE'] = 50 * 1024 * 1024  # 50MB
    
    # Also patch the internal parser limits
    if hasattr(multipart, 'FormParser'):
        # Patch the internal field size limit
        original_init = multipart.FormParser.__init__
        def patched_init(self, headers, stream, max_files=1000, max_fields=1000, max_part_size=50*1024*1024):
            # Force the max_part_size to be 50MB
            return original_init(self, headers, stream, max_files, max_fields, 50*1024*1024)
        multipart.FormParser.__init__ = patched_init
    
    # Patch any other internal limits
    if hasattr(multipart, 'parse_options_header'):
        original_parse = multipart.parse_options_header
        def patched_parse(headers, stream, max_size=None):
            if max_size is None or max_size < 50*1024*1024:
                max_size = 50 * 1024 * 1024
            return original_parse(headers, stream, max_size)
        multipart.parse_options_header = patched_parse
    
    print("✅ Patched multipart.FormParser.DEFAULT_CONFIG")
    print(f"   MAX_MEMORY_FILE_SIZE: {multipart.FormParser.DEFAULT_CONFIG['MAX_MEMORY_FILE_SIZE']} bytes")
    print(f"   MAX_BODY_SIZE: {multipart.FormParser.DEFAULT_CONFIG['MAX_BODY_SIZE']} bytes")
    print("✅ Patched multipart.FormParser.__init__ to force 50MB limit")
    print("✅ Patched multipart.parse_options_header to use 50MB limit")
    
except Exception as e:
    print(f"❌ Failed to patch multipart: {e}")
    sys.exit(1)



# Now import the app
from app.main import app

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 JUNGLORE BACKEND PRODUCTION SERVER")
    print("=" * 60)
    print("📏 Max upload size: 50MB")
    
    # Get port from environment (Railway sets PORT env var)
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0" if os.environ.get("RAILWAY_ENVIRONMENT") else "127.0.0.1"
    
    print(f"🌐 Server will be available at: http://{host}:{port}")
    print(f"🎨 Admin Panel: http://{host}:{port}/admin")
    print(f"📚 API Documentation: http://{host}:{port}/api/docs")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    print("")
    
    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            # Custom configuration for large requests
            limit_max_requests=1000,
            limit_concurrency=1000,
            timeout_keep_alive=75
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)
