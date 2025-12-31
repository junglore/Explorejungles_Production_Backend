"""
Caching system with Redis and in-memory fallback
"""

import json
import pickle
import asyncio
from typing import Any, Optional, Union, Dict
from datetime import timedelta
import redis.asyncio as redis
from app.core.config import settings
import structlog

logger = structlog.get_logger()

class CacheManager:
    """Unified cache manager with Redis and in-memory fallback"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.memory_cache: Dict[str, Dict[str, Any]] = {}
        self.memory_cache_ttl: Dict[str, float] = {}
        self.use_redis = False
        
    async def initialize(self):
        """Initialize Redis connection - required but with fallback"""
        try:
            # Redis is required, but we'll fallback to memory if connection fails
            if not settings.REDIS_URL:
                logger.error("Redis URL not provided! Using memory cache as fallback.")
                self.use_redis = False
                return
                
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,
                socket_connect_timeout=10,
                socket_timeout=10,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            self.use_redis = True
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.error(f"Redis connection failed! Using memory cache fallback: {e}")
            self.use_redis = False
            self.redis_client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        try:
            if self.use_redis and self.redis_client:
                value = await self.redis_client.get(key)
                if value:
                    return pickle.loads(value)
            else:
                # Use memory cache
                if key in self.memory_cache:
                    import time
                    if key in self.memory_cache_ttl and time.time() > self.memory_cache_ttl[key]:
                        # Expired
                        del self.memory_cache[key]
                        del self.memory_cache_ttl[key]
                        return None
                    return self.memory_cache[key]
            
            return None
            
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL"""
        try:
            if self.use_redis and self.redis_client:
                serialized_value = pickle.dumps(value)
                await self.redis_client.setex(key, ttl, serialized_value)
                return True
            else:
                # Use memory cache
                import time
                self.memory_cache[key] = value
                self.memory_cache_ttl[key] = time.time() + ttl
                return True
                
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            if self.use_redis and self.redis_client:
                await self.redis_client.delete(key)
            else:
                # Use memory cache
                if key in self.memory_cache:
                    del self.memory_cache[key]
                if key in self.memory_cache_ttl:
                    del self.memory_cache_ttl[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> bool:
        """Clear all keys matching pattern"""
        try:
            if self.use_redis and self.redis_client:
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            else:
                # Use memory cache
                keys_to_delete = [key for key in self.memory_cache.keys() if pattern.replace("*", "") in key]
                for key in keys_to_delete:
                    if key in self.memory_cache:
                        del self.memory_cache[key]
                    if key in self.memory_cache_ttl:
                        del self.memory_cache_ttl[key]
            
            return True
            
        except Exception as e:
            logger.error(f"Cache clear pattern error for {pattern}: {e}")
            return False
    
    async def cleanup_memory_cache(self):
        """Clean up expired entries from memory cache"""
        if not self.use_redis:
            import time
            current_time = time.time()
            expired_keys = [
                key for key, ttl in self.memory_cache_ttl.items()
                if current_time > ttl
            ]
            
            for key in expired_keys:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                if key in self.memory_cache_ttl:
                    del self.memory_cache_ttl[key]

# Global cache instance
cache_manager = CacheManager()

# Cache decorators
def cache_result(ttl: int = 300, key_prefix: str = ""):
    """Decorator to cache function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cached_result = await cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await cache_manager.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

# Cache keys constants
class CacheKeys:
    """Cache key constants"""
    MEDIA_LIST = "media:list"
    MEDIA_FEATURED = "media:featured"
    MEDIA_STATS = "media:stats"
    CONTENT_LIST = "content:list"
    CONTENT_FEATURED = "content:featured"
    CATEGORIES = "categories:all"
    USER_PROFILE = "user:profile"
    
    @staticmethod
    def media_by_type(media_type: str) -> str:
        return f"media:type:{media_type}"
    
    @staticmethod
    def content_by_category(category_id: str) -> str:
        return f"content:category:{category_id}"
    
    @staticmethod
    def user_by_id(user_id: str) -> str:
        return f"user:id:{user_id}"