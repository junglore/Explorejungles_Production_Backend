"""
Security middleware for HTTPS and security headers
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, RedirectResponse
from starlette.types import ASGIApp
import secrets

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    def __init__(self, app: ASGIApp, force_https: bool = False):
        super().__init__(app)
        self.force_https = force_https
        self.nonce = secrets.token_urlsafe(16)
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response"""
        
        # Force HTTPS redirect in production
        if self.force_https and request.url.scheme != "https":
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        response = await call_next(request)
        
        # Security headers
        security_headers = {
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Content Security Policy
            "Content-Security-Policy": (
                f"default-src 'self'; "
                f"script-src 'self' 'unsafe-inline' 'unsafe-eval' 'nonce-{self.nonce}' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://cdn.quilljs.com; "
                f"style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com https://cdn.quilljs.com; "
                f"font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
                f"img-src 'self' data: https: blob:; "
                f"media-src 'self' https:; "
                f"connect-src 'self' https:; "
                f"frame-ancestors 'none'; "
                f"base-uri 'self'; "
                f"form-action 'self'"
            ),
            
            # Permissions policy
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "speaker=()"
            ),
        }
        
        # Add HTTPS-specific headers
        if request.url.scheme == "https" or self.force_https:
            security_headers.update({
                # HSTS (HTTP Strict Transport Security)
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                
                # Expect-CT (Certificate Transparency)
                "Expect-CT": "max-age=86400, enforce",
            })
        
        # Add all security headers
        for header, value in security_headers.items():
            response.headers[header] = value
        
        # Add nonce to response for CSP
        response.headers["X-CSP-Nonce"] = self.nonce
        
        return response

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP to HTTPS in production"""
    
    def __init__(self, app: ASGIApp, force_https: bool = False):
        super().__init__(app)
        self.force_https = force_https
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Redirect HTTP to HTTPS if enabled"""
        
        if self.force_https and request.url.scheme != "https":
            # Check if it's a health check or internal request
            if request.url.path in ["/health", "/metrics"]:
                return await call_next(request)
            
            # Redirect to HTTPS
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=301)
        
        return await call_next(request)