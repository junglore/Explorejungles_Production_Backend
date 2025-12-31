"""
Custom multipart parser for handling large requests
"""

import os
from typing import Dict, List, Optional, Tuple
from fastapi import Request, Form, File, UploadFile
from starlette.formparsers import MultiPartParser
import logging

logger = logging.getLogger(__name__)

class LargeMultiPartParser(MultiPartParser):
    """Custom multipart parser with increased size limits"""
    
    def __init__(self, headers, stream):
        # Set large limits
        max_files = 1000
        max_fields = 1000
        max_part_size = 50 * 1024 * 1024  # 50MB
        
        super().__init__(headers, stream, max_files=max_files, max_fields=max_fields, max_part_size=max_part_size)

async def parse_large_form_data(request: Request) -> Tuple[Dict, List[UploadFile]]:
    """
    Parse form data with large size limits using standard FastAPI approach
    """
    try:
        # Use the standard form parsing but with increased limits
        # Set the request scope for large content
        request.scope["max_content_size"] = 50 * 1024 * 1024  # 50MB
        
        # Parse form data using standard FastAPI method
        form_data = await request.form()
        
        # Extract fields and files
        fields = {}
        files = []
        
        for key, value in form_data.items():
            if hasattr(value, 'filename'):  # It's a file
                files.append(value)
            else:
                fields[key] = value
        
        return fields, files
        
    except Exception as e:
        logger.error(f"Error parsing large form data: {e}")
        raise

def patch_multipart_globally():
    """
    Patch the multipart library globally to handle large uploads
    """
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
        
        logger.info("Successfully patched multipart library globally")
        return True
        
    except Exception as e:
        logger.error(f"Failed to patch multipart library: {e}")
        return False
