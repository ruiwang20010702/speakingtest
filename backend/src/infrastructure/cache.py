"""
Redis Cache Utility

Provides simple caching for expensive database queries.
Falls back gracefully when Redis is unavailable.

Usage:
    from src.infrastructure.cache import cache_get, cache_set

    # Try to get from cache first
    cached = await cache_get("stats:overview")
    if cached:
        return cached
    
    # Compute expensive result
    result = await compute_expensive_stats()
    
    # Cache for 5 minutes
    await cache_set("stats:overview", result, ttl=300)
    return result
"""
import json
import logging
from typing import Any, Optional

from src.infrastructure.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Global Redis client (lazy initialized)
_redis_client = None
_redis_available = None


async def _get_redis():
    """Get or create Redis client with connection pooling."""
    global _redis_client, _redis_available
    
    if _redis_available is False:
        return None
    
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # Test connection
            await _redis_client.ping()
            _redis_available = True
            logger.info("Redis cache enabled")
        except Exception as e:
            logger.warning(f"Redis unavailable for caching: {e}")
            _redis_available = False
            _redis_client = None
            return None
    
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """
    Get a value from cache.
    
    Args:
        key: Cache key (will be prefixed with 'cache:')
        
    Returns:
        Cached value (deserialized from JSON) or None if not found/error
    """
    redis = await _get_redis()
    if not redis:
        return None
    
    try:
        full_key = f"cache:{key}"
        value = await redis.get(full_key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.warning(f"Cache get error for {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300) -> bool:
    """
    Set a value in cache.
    
    Args:
        key: Cache key (will be prefixed with 'cache:')
        value: Value to cache (will be serialized to JSON)
        ttl: Time to live in seconds (default: 5 minutes)
        
    Returns:
        True if successful, False otherwise
    """
    redis = await _get_redis()
    if not redis:
        return False
    
    try:
        full_key = f"cache:{key}"
        await redis.setex(full_key, ttl, json.dumps(value))
        return True
    except Exception as e:
        logger.warning(f"Cache set error for {key}: {e}")
        return False


async def cache_delete(key: str) -> bool:
    """
    Delete a value from cache.
    
    Args:
        key: Cache key (will be prefixed with 'cache:')
        
    Returns:
        True if successful, False otherwise
    """
    redis = await _get_redis()
    if not redis:
        return False
    
    try:
        full_key = f"cache:{key}"
        await redis.delete(full_key)
        return True
    except Exception as e:
        logger.warning(f"Cache delete error for {key}: {e}")
        return False


async def cache_delete_pattern(pattern: str) -> int:
    """
    Delete all keys matching a pattern.
    
    Args:
        pattern: Pattern to match (e.g., 'stats:*')
        
    Returns:
        Number of keys deleted, or 0 on error
    """
    redis = await _get_redis()
    if not redis:
        return 0
    
    try:
        full_pattern = f"cache:{pattern}"
        keys = []
        async for key in redis.scan_iter(match=full_pattern):
            keys.append(key)
        
        if keys:
            return await redis.delete(*keys)
        return 0
    except Exception as e:
        logger.warning(f"Cache delete pattern error for {pattern}: {e}")
        return 0
