"""
Middleware for handling large file uploads
"""

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import logging

logger = logging.getLogger(__name__)

class LargeUploadMiddleware(BaseHTTPMiddleware):
    """Middleware to handle large file uploads"""
    
    def __init__(self, app, max_size: int = 50 * 1024 * 1024):  # 50MB default
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        # Set large request size limit
        request.scope["max_content_size"] = self.max_size
        
        # Patch the multipart parser if this is a multipart request
        if request.headers.get("content-type", "").startswith("multipart/form-data"):
            # Set environment variables for the multipart parser
            os.environ["MAX_CONTENT_LENGTH"] = str(self.max_size)
            
            # Aggressively patch the multipart parser
            try:
                import multipart
                
                # Patch the FormParser DEFAULT_CONFIG
                multipart.FormParser.DEFAULT_CONFIG['MAX_MEMORY_FILE_SIZE'] = self.max_size
                multipart.FormParser.DEFAULT_CONFIG['MAX_BODY_SIZE'] = self.max_size
                
                # Patch the internal parser limits
                if hasattr(multipart, 'FormParser'):
                    # Patch the internal field size limit
                    original_init = multipart.FormParser.__init__
                    def patched_init(self, headers, stream, max_files=1000, max_fields=1000, max_part_size=self.max_size):
                        # Force the max_part_size to be our limit
                        return original_init(self, headers, stream, max_files, max_fields, self.max_size)
                    multipart.FormParser.__init__ = patched_init
                
                # Patch any other internal limits
                if hasattr(multipart, 'parse_options_header'):
                    original_parse = multipart.parse_options_header
                    def patched_parse(headers, stream, max_size=None):
                        if max_size is None or max_size < self.max_size:
                            max_size = self.max_size
                        return original_parse(headers, stream, max_size)
                    multipart.parse_options_header = patched_parse
                
                logger.info(f"Patched multipart library for request with max_size: {self.max_size}")
                
            except (ImportError, AttributeError) as e:
                logger.warning(f"Could not patch multipart library: {e}")
            

        
        return await call_next(request)
