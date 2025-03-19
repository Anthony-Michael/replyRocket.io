"""
Query caching utility.

This module provides functionality to cache query results
for improved performance on frequently executed queries.
"""

import functools
import hashlib
import json
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
import threading

from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# In-memory cache dictionary
# Key: cache_key, Value: (result, timestamp, ttl)
_query_cache: Dict[str, Tuple[Any, float, float]] = {}

# Lock for thread-safe cache access
_cache_lock = threading.Lock()

# Cache statistics
_cache_stats = {
    "hits": 0,
    "misses": 0,
    "evictions": 0,
    "sets": 0,
    "errors": 0
}


def generate_cache_key(query: str, params: Dict[str, Any] = None) -> str:
    """
    Generate a cache key from a query and parameters.
    
    Args:
        query: SQL query string
        params: Dictionary of query parameters
        
    Returns:
        Cache key string
    """
    # Normalize whitespace in query
    normalized_query = " ".join(query.split())
    
    # Hash query and parameters together
    hasher = hashlib.md5()
    hasher.update(normalized_query.encode('utf-8'))
    
    if params:
        # Sort params to ensure consistent order
        sorted_params = {k: params[k] for k in sorted(params.keys())}
        param_str = json.dumps(sorted_params, sort_keys=True, default=str)
        hasher.update(param_str.encode('utf-8'))
    
    return hasher.hexdigest()


def get_cached_result(cache_key: str) -> Optional[Any]:
    """
    Get a result from the cache if it exists and hasn't expired.
    
    Args:
        cache_key: Cache key string
        
    Returns:
        Cached result or None if not found or expired
    """
    with _cache_lock:
        if cache_key in _query_cache:
            result, timestamp, ttl = _query_cache[cache_key]
            
            # Check if the result has expired
            if ttl > 0 and time.time() - timestamp > ttl:
                # Expired, remove from cache
                del _query_cache[cache_key]
                _cache_stats["evictions"] += 1
                return None
            
            # Cache hit
            _cache_stats["hits"] += 1
            return result
        
        # Cache miss
        _cache_stats["misses"] += 1
        return None


def set_cached_result(cache_key: str, result: Any, ttl: float = 300.0) -> None:
    """
    Store a result in the cache with a TTL.
    
    Args:
        cache_key: Cache key string
        result: Result data to cache
        ttl: Time-to-live in seconds (default: 300s / 5min)
    """
    with _cache_lock:
        _query_cache[cache_key] = (result, time.time(), ttl)
        _cache_stats["sets"] += 1
        
        # Log cache size if it's getting large
        if len(_query_cache) % 100 == 0:
            logger.info(f"Query cache size: {len(_query_cache)} entries")


def invalidate_cache(cache_key: Optional[str] = None) -> int:
    """
    Invalidate entries in the cache.
    
    Args:
        cache_key: Specific cache key to invalidate, or None to invalidate all
        
    Returns:
        Number of entries invalidated
    """
    with _cache_lock:
        if cache_key:
            if cache_key in _query_cache:
                del _query_cache[cache_key]
                return 1
            return 0
        else:
            count = len(_query_cache)
            _query_cache.clear()
            return count


def invalidate_by_prefix(prefix: str) -> int:
    """
    Invalidate cache entries with keys starting with a prefix.
    
    This can be used to invalidate all queries related to a specific table
    or operation when data changes.
    
    Args:
        prefix: Cache key prefix to match
        
    Returns:
        Number of entries invalidated
    """
    with _cache_lock:
        keys_to_remove = [k for k in _query_cache.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            del _query_cache[key]
        return len(keys_to_remove)


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about the query cache.
    
    Returns:
        Dictionary with cache statistics
    """
    with _cache_lock:
        total_requests = _cache_stats["hits"] + _cache_stats["misses"]
        hit_rate = _cache_stats["hits"] / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(_query_cache),
            "hits": _cache_stats["hits"],
            "misses": _cache_stats["misses"],
            "hit_rate": hit_rate,
            "sets": _cache_stats["sets"],
            "evictions": _cache_stats["evictions"],
            "errors": _cache_stats["errors"]
        }


def cached_query(ttl: float = 300.0, prefix: Optional[str] = None):
    """
    Decorator to cache the results of a query function.
    
    Args:
        ttl: Time-to-live in seconds (default: 300s / 5min)
        prefix: Optional cache key prefix to use
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a cache key
            func_name = func.__name__
            module_name = func.__module__
            
            # Include the function path in the key
            key_base = f"{module_name}.{func_name}"
            if prefix:
                key_base = f"{prefix}:{key_base}"
            
            # Add arguments to the key
            args_str = json.dumps([str(arg) for arg in args], sort_keys=True)
            kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
            
            cache_key = hashlib.md5(f"{key_base}:{args_str}:{kwargs_str}".encode('utf-8')).hexdigest()
            
            # Try to get from cache
            cached_result = get_cached_result(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute the function
            result = func(*args, **kwargs)
            
            # Store in cache
            set_cached_result(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    return decorator


def cached_db_query(db: Session, query: str, params: Dict[str, Any] = None, ttl: float = 300.0) -> Any:
    """
    Execute a database query with caching.
    
    Args:
        db: SQLAlchemy session
        query: SQL query string
        params: Query parameters
        ttl: Time-to-live in seconds
        
    Returns:
        Query results (either from cache or from database)
    """
    cache_key = generate_cache_key(query, params)
    
    # Try to get from cache
    cached_result = get_cached_result(cache_key)
    if cached_result is not None:
        return cached_result
    
    # Execute the query
    try:
        start_time = time.time()
        if params:
            result = db.execute(text(query), params).fetchall()
        else:
            result = db.execute(text(query)).fetchall()
        
        execution_time = time.time() - start_time
        
        # Only cache if query takes a significant amount of time
        # This prevents caching trivial queries
        if execution_time > 0.01:  # 10ms threshold
            set_cached_result(cache_key, result, ttl)
        
        return result
    except Exception as e:
        logger.error(f"Error executing cached query: {str(e)}")
        with _cache_lock:
            _cache_stats["errors"] += 1
        raise


def invalidate_table_cache(table_name: str) -> int:
    """
    Invalidate all cache entries related to a specific table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        Number of entries invalidated
    """
    # Use a table prefix scheme in cache keys
    prefix = f"table:{table_name}:"
    return invalidate_by_prefix(prefix)


def setup_automatic_invalidation(db: Session) -> None:
    """
    Set up event listeners to automatically invalidate cache on data changes.
    
    Args:
        db: SQLAlchemy session
    """
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # Check if this is a write operation
        is_write = (
            statement.strip().upper().startswith(("INSERT", "UPDATE", "DELETE")) or
            "INSERT INTO" in statement.upper() or
            "UPDATE " in statement.upper() or
            "DELETE FROM" in statement.upper()
        )
        
        if is_write:
            # Extract table name
            table_name = None
            if "INSERT INTO" in statement.upper():
                match = re.search(r"INSERT INTO (\w+)", statement, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
            elif "UPDATE " in statement.upper():
                match = re.search(r"UPDATE (\w+)", statement, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
            elif "DELETE FROM" in statement.upper():
                match = re.search(r"DELETE FROM (\w+)", statement, re.IGNORECASE)
                if match:
                    table_name = match.group(1)
            
            if table_name:
                invalidation_count = invalidate_table_cache(table_name)
                if invalidation_count > 0:
                    logger.debug(f"Invalidated {invalidation_count} cache entries for table {table_name}")
                
                # Also invalidate related tables if we know about them
                # For example, if updating 'users', also invalidate cache for 'user_profiles'
                related_tables = {
                    "users": ["user_profiles", "sessions"],
                    "email_campaigns": ["emails", "campaign_stats"],
                    # Add more relationships as needed
                }
                
                for related in related_tables.get(table_name, []):
                    invalidate_table_cache(related) 