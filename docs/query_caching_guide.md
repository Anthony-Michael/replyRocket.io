# Query Caching Guide

This guide explains how to implement and maintain the query caching system in the ReplyRocket.io application.

## Overview

The query caching system provides a way to store and reuse the results of database queries, significantly improving performance for frequently executed queries. The system is implemented in `app/utils/query_cache.py` and provides several mechanisms for caching query results.

## When to Use Query Caching

Query caching is most effective for:

1. **Frequently accessed data** - Queries that are executed many times
2. **Relatively stable data** - Data that doesn't change frequently
3. **Computationally expensive queries** - Complex queries with joins, aggregations, etc.
4. **Read-heavy operations** - Operations that read data much more often than they write

Caching is less appropriate for:

1. **Rapidly changing data** - Data that updates frequently
2. **Write-heavy operations** - Operations that frequently modify data
3. **User-specific sensitive data** - Unless cache keys incorporate user identifiers
4. **Very large result sets** - These can consume excessive memory

## Caching Mechanisms

The caching system provides several ways to implement caching:

### 1. Decorator-based Caching

The simplest approach is to use the `@cached_query` decorator on service functions:

```python
from app.utils.query_cache import cached_query

@cached_query(ttl=300)  # Cache for 5 minutes
def get_user_stats(db: Session, user_id: str):
    # Database query logic here
    return result
```

### 2. Manual Caching

For more control, you can use the caching functions directly:

```python
from app.utils.query_cache import get_cached_result, set_cached_result

def get_campaign_stats(db: Session, campaign_id: str):
    # Generate a cache key
    cache_key = f"campaign_stats:{campaign_id}"
    
    # Try to get from cache
    cached = get_cached_result(cache_key)
    if cached is not None:
        return cached
    
    # If not in cache, execute query
    result = db.execute(...)
    
    # Store in cache for 10 minutes
    set_cached_result(cache_key, result, ttl=600)
    
    return result
```

### 3. Direct Query Caching

For raw SQL queries, use the `cached_db_query` function:

```python
from app.utils.query_cache import cached_db_query
from sqlalchemy import text

def get_active_campaigns(db: Session):
    query = text("SELECT * FROM campaigns WHERE status = 'active'")
    result = cached_db_query(db, query, ttl=300)
    return result
```

## Cache Invalidation

### Automatic Invalidation

The caching system automatically sets up event listeners to invalidate cache entries when data changes. This is configured in the `setup_cache_invalidation` function.

### Manual Invalidation

You can manually invalidate cache entries in several ways:

1. **Invalidate specific keys**:

```python
from app.utils.query_cache import invalidate_cache

# Invalidate a specific cache entry
invalidate_cache("campaign_stats:123")
```

2. **Invalidate by table**:

```python
from app.utils.query_cache import invalidate_table_cache

# Invalidate all cache entries related to the campaigns table
invalidate_table_cache("campaigns")
```

3. **Invalidate all**:

```python
from app.utils.query_cache import invalidate_cache

# Clear the entire cache
invalidate_cache()
```

## Cache Configuration

The main configuration options for the cache are:

1. **TTL (Time-to-Live)** - How long entries remain valid (in seconds)
2. **Cache Key Generation** - How keys are created for database queries
3. **Cache Invalidation Patterns** - Which tables trigger invalidation

These are set in the caching utility and can be adjusted as needed.

## Best Practices

### Cache Keys

- Ensure cache keys are unique for different query parameters
- Include table names in keys to help with invalidation
- For user-specific data, include the user ID in the key
- Keep keys reasonably short but descriptive

### TTL Settings

- Set TTL based on how frequently the data changes
- Use shorter TTL for frequently changing data
- Consider longer TTL for stable reference data
- Critical data should have shorter TTL to reduce staleness

### Memory Usage

- Monitor cache size to avoid excessive memory usage
- Consider implementing cache size limits
- Prioritize caching smaller result sets over very large ones
- Implement cache eviction policies if memory usage is a concern

### Invalidation Strategy

- Set up automatic invalidation for all tables with cached queries
- Invalidate only what's necessary to avoid cache thrashing
- For complex data models, consider cascading invalidation
- In write-heavy operations, invalidate selectively rather than clearing all

## Implementation Examples

### Caching User Statistics

```python
from app.utils.query_cache import cached_query

@cached_query(ttl=300)  # 5-minute cache
def get_user_dashboard_stats(db: Session, user_id: str):
    """Get dashboard statistics for a specific user."""
    # Complex query with multiple joins and aggregations
    campaigns = db.query(
        Campaign.id,
        Campaign.name,
        func.count(Email.id).label('total_emails'),
        func.sum(case((Email.opened == True, 1), else_=0)).label('opened'),
        func.sum(case((Email.replied == True, 1), else_=0)).label('replied')
    ).join(
        Email, Campaign.id == Email.campaign_id
    ).filter(
        Campaign.user_id == user_id
    ).group_by(
        Campaign.id
    ).all()
    
    return campaigns
```

### Caching Reference Data

```python
from app.utils.query_cache import cached_query

@cached_query(ttl=3600)  # 1-hour cache for stable reference data
def get_email_templates(db: Session):
    """Get all email templates."""
    return db.query(EmailTemplate).all()
```

### Selective Caching Based on Query Complexity

```python
from app.utils.query_cache import cached_db_query
from sqlalchemy import text

def get_campaign_emails(db: Session, campaign_id: str, page: int = 0, limit: int = 100):
    """Get emails for a campaign with pagination."""
    # For simple queries with pagination, don't use cache
    if limit <= 100:
        query = text(
            "SELECT * FROM emails WHERE campaign_id = :campaign_id "
            "ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        )
        return db.execute(
            query, 
            {"campaign_id": campaign_id, "limit": limit, "offset": page * limit}
        ).fetchall()
    
    # For larger queries that might be expensive, use cache
    else:
        query = text(
            "SELECT * FROM emails WHERE campaign_id = :campaign_id "
            "ORDER BY created_at DESC"
        )
        return cached_db_query(
            db, 
            query, 
            params={"campaign_id": campaign_id},
            ttl=300
        )
```

## Monitoring Cache Performance

Use the cache statistics endpoints to monitor performance:

- `/api/v1/db/cache` - Get overall cache statistics
- Cache hit rate - Should be above 70% for optimal performance
- Cache evictions - High eviction rate may indicate need for larger cache or more selective caching

You can also run the performance testing script to evaluate cache effectiveness:

```bash
python scripts/test_db_performance.py --cache
```

## Troubleshooting

### Cache Not Working

1. Verify the cache key is being generated consistently
2. Check if automatic invalidation is clearing the cache too frequently
3. Ensure TTL is appropriate for the data volatility
4. Verify that the cached_query decorator is applied correctly

### High Cache Miss Rate

1. Check if invalidation is happening too frequently
2. Verify that the cache key includes all relevant query parameters
3. Consider if the data is changing too frequently for caching to be effective
4. Ensure cache is warmed up before evaluating performance

### Memory Usage Issues

1. Reduce TTL for large cached result sets
2. Implement more selective caching
3. Consider caching only the most frequent queries
4. Implement cache size limits or LRU eviction

## Advanced Topics

### Distributed Caching

For multi-server deployments, consider implementing Redis or Memcached instead of the in-memory cache:

1. Update the cache implementation to use a distributed cache
2. Ensure consistent cache key generation across servers
3. Configure appropriate cache size and eviction policies
4. Implement connection pooling for the cache service

### Cache Warming

For critical queries, implement cache warming on application startup:

```python
def warm_cache():
    """Pre-populate cache with frequently accessed data."""
    db = SessionLocal()
    try:
        # Warm up common queries
        get_active_campaigns(db)
        get_email_templates(db)
    finally:
        db.close()
```

### Custom Cache Validators

Implement custom validation logic for sensitive cached data:

```python
def validate_cached_user(cached_user, current_user_id):
    """Validate that the cached user data is accessible to the current user."""
    if cached_user.id != current_user_id and not current_user.is_admin:
        return False
    return True
```

## Conclusion

Effective query caching can dramatically improve application performance by reducing database load and response times. By following the best practices outlined in this guide, you can implement caching that balances performance gains with data consistency and resource usage. 