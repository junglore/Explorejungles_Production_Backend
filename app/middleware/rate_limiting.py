"""
Rate limiting middleware for API protection
"""

import time
from typing import Dict, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import asyncio
from collections import defaultdict, deque
import ipaddress

class RateLimiter:
    """In-memory rate limiter with sliding window"""
    
    def __init__(self):
        # Store request timestamps for each IP
        self.requests: Dict[str, deque] = defaultdict(lambda: deque())
        # Store blocked IPs with unblock time
        self.blocked_ips: Dict[str, float] = {}
        
    def is_allowed(self, ip: str, limit: int, window: int) -> Tuple[bool, int]:
        """
        Check if request is allowed based on rate limit
        Returns (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        
        # Check if IP is currently blocked
        if ip in self.blocked_ips:
            if current_time < self.blocked_ips[ip]:
                retry_after = int(self.blocked_ips[ip] - current_time)
                return False, retry_after
            else:
                # Unblock IP
                del self.blocked_ips[ip]
        
        # Clean old requests outside the window
        requests = self.requests[ip]
        while requests and requests[0] < current_time - window:
            requests.popleft()
        
        # Check if limit exceeded
        if len(requests) >= limit:
            # Block IP for the window duration
            self.blocked_ips[ip] = current_time + window
            return False, window
        
        # Add current request
        requests.append(current_time)
        return True, 0
    
    def cleanup_old_entries(self):
        """Clean up old entries to prevent memory leaks"""
        current_time = time.time()
        
        # Clean up old request records (older than 1 hour)
        for ip in list(self.requests.keys()):
            requests = self.requests[ip]
            while requests and requests[0] < current_time - 3600:
                requests.popleft()
            if not requests:
                del self.requests[ip]
        
        # Clean up expired blocked IPs
        for ip in list(self.blocked_ips.keys()):
            if current_time >= self.blocked_ips[ip]:
                del self.blocked_ips[ip]

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with different limits for different endpoints"""
    
    def __init__(self, app, default_limit: int = 100, default_window: int = 60):
        super().__init__(app)
        self.rate_limiter = RateLimiter()
        self.default_limit = default_limit
        self.default_window = default_window
        
        # Different rate limits for different endpoint patterns
        self.endpoint_limits = {
            "/api/v1/auth/login": (5, 300),  # 5 requests per 5 minutes
            "/api/v1/auth/register": (3, 300),  # 3 requests per 5 minutes
            "/api/v1/media/upload": (10, 60),  # 10 uploads per minute
            "/admin/login": (5, 300),  # 5 admin login attempts per 5 minutes
        }
        
        # Whitelist for internal IPs
        self.whitelist = [
            ipaddress.ip_network("127.0.0.0/8"),  # Localhost
            ipaddress.ip_network("10.0.0.0/8"),   # Private network
            ipaddress.ip_network("172.16.0.0/12"), # Private network
            ipaddress.ip_network("192.168.0.0/16"), # Private network
        ]
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_task())
    
    def get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct connection
        return request.client.host if request.client else "unknown"
    
    def is_whitelisted(self, ip: str) -> bool:
        """Check if IP is in whitelist"""
        try:
            client_ip = ipaddress.ip_address(ip)
            return any(client_ip in network for network in self.whitelist)
        except ValueError:
            return False
    
    def get_rate_limit(self, path: str) -> Tuple[int, int]:
        """Get rate limit for specific endpoint"""
        for pattern, (limit, window) in self.endpoint_limits.items():
            if path.startswith(pattern):
                return limit, window
        return self.default_limit, self.default_window
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting"""
        client_ip = self.get_client_ip(request)
        
        # Skip rate limiting for whitelisted IPs
        if self.is_whitelisted(client_ip):
            return await call_next(request)
        
        # Get rate limit for this endpoint
        limit, window = self.get_rate_limit(request.url.path)
        
        # Check rate limit
        is_allowed, retry_after = self.rate_limiter.is_allowed(client_ip, limit, window)
        
        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)}
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        
        # Get current request count
        current_requests = len(self.rate_limiter.requests[client_ip])
        remaining = max(0, limit - current_requests)
        
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))
        
        return response
    
    async def _cleanup_task(self):
        """Background task to clean up old entries"""
        while True:
            await asyncio.sleep(300)  # Clean up every 5 minutes
            self.rate_limiter.cleanup_old_entries()