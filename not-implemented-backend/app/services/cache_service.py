"""
Redis caching service for the Sonnet application.

Provides caching functionality for frequently accessed data including:
- Location hierarchies (rarely change)
- Popular schemes (with TTL)
"""

import json
import functools
from typing import Any, Callable, Optional
import redis
from app.core.config import get_settings


class CacheService:
    """Service for managing Redis cache operations."""
    
    def __init__(self):
        """Initialize Redis connection."""
        settings = get_settings()
        self.redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            db=settings.redis_db,
            password=settings.redis_password,
            decode_responses=True
        )
        self.scheme_ttl = settings.cache_ttl_schemes
        self.location_ttl = settings.cache_ttl_locations
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except (redis.RedisError, json.JSONDecodeError):
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value)
            if ttl:
                self.redis_client.setex(key, ttl, serialized)
            else:
                self.redis_client.set(key, serialized)
            return True
        except (redis.RedisError, TypeError, ValueError):
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.redis_client.delete(key)
            return True
        except redis.RedisError:
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "location:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except redis.RedisError:
            return 0
    
    def clear_all(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.redis_client.flushdb()
            return True
        except redis.RedisError:
            return False
    
    def ping(self) -> bool:
        """
        Check if Redis connection is alive.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            return self.redis_client.ping()
        except redis.RedisError:
            return False
    
    def add_to_set(self, key: str, value: str) -> bool:
        """
        Add a value to a Redis set.
        
        Args:
            key: Set key
            value: Value to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.redis_client.sadd(key, value)
            return True
        except redis.RedisError:
            return False
    
    def get_set_members(self, key: str) -> list:
        """
        Get all members of a Redis set.
        
        Args:
            key: Set key
            
        Returns:
            List of set members, empty list if key doesn't exist or on error
        """
        try:
            members = self.redis_client.smembers(key)
            return list(members) if members else []
        except redis.RedisError:
            return []


# Global cache service instance
_cache_service: Optional[CacheService] = None


def get_cache_service() -> CacheService:
    """Get or create the global cache service instance."""
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService()
    return _cache_service


def cache_result(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None
):
    """
    Decorator to cache function results in Redis.
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds (optional)
        key_builder: Custom function to build cache key from args/kwargs
                    If None, uses default key building from function args
    
    Example:
        @cache_result("location", ttl=3600)
        def get_location(location_id: str):
            # ... fetch from database
            return location
        
        @cache_result("scheme", ttl=1800, key_builder=lambda scheme_id: f"scheme:{scheme_id}")
        def get_scheme(scheme_id: str):
            # ... fetch from database
            return scheme
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache_service()
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building: prefix:arg1:arg2:...
                arg_parts = [str(arg) for arg in args]
                kwarg_parts = [f"{k}={v}" for k, v in sorted(kwargs.items())]
                all_parts = [key_prefix] + arg_parts + kwarg_parts
                cache_key = ":".join(all_parts)
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator
