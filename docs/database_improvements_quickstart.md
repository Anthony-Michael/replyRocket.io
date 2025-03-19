# Database Improvements Quickstart Guide

This quickstart guide helps you get started with the newly implemented database performance features in ReplyRocket.io.

## Setup

1. Make sure your application is up-to-date with the latest changes:

```bash
git pull
pip install -r requirements.txt
```

2. Update your database schema if needed:

```bash
alembic upgrade head
```

## Key Features

### 1. Query Caching

To use query caching in your service functions:

```python
from app.utils.query_cache import cached_query

@cached_query(ttl=300)  # Cache for 5 minutes
def get_user_data(db: Session, user_id: str):
    # Database query logic
    return result
```

For more details, see the [Query Caching Guide](query_caching_guide.md).

### 2. Database Monitoring

Access the database monitoring dashboard at:

```
http://localhost:8000/api/v1/db/performance
```

Key endpoints include:
- `/api/v1/db/slow-queries` - View slow queries
- `/api/v1/db/table-stats/{table_name}` - View table statistics 
- `/api/v1/db/cache` - View cache statistics

### 3. Query Optimization

To get optimization suggestions for a query:

```bash
curl -X POST "http://localhost:8000/api/v1/db/optimize-query" \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT * FROM users WHERE email LIKE '%example.com'"}'
```

Or use the Python client:

```python
from app.utils.db_optimization import optimize_query

def improve_query(db: Session, query: str):
    suggestions = optimize_query(db, query)
    print(f"Optimization suggestions: {suggestions}")
```

### 4. Performance Testing

Run the database performance testing script:

```bash
# Basic test
python scripts/test_db_performance.py

# Test with caching enabled
python scripts/test_db_performance.py --cache

# Full test with statistics
python scripts/test_db_performance.py --cache --show-stats --iterations 10
```

## Common Tasks

### Identifying Slow Queries

1. Check the slow query log:

```bash
curl "http://localhost:8000/api/v1/db/slow-queries?threshold=0.1"
```

2. Add missing indexes:

```bash
curl -X POST "http://localhost:8000/api/v1/db/optimize-query" \
  -H "Content-Type: application/json" \
  -d '{"query": "YOUR_SLOW_QUERY_HERE"}'
```

3. Apply suggested indexes using the generated DDL.

### Optimizing Connection Pool

Update your environment variables or settings:

```
# For moderate traffic (default)
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# For high traffic
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_TIMEOUT=60
DB_POOL_RECYCLE=3600
```

### Managing Cache

1. View cache statistics:

```bash
curl "http://localhost:8000/api/v1/db/cache"
```

2. Invalidate specific cache entries:

```bash
curl -X POST "http://localhost:8000/api/v1/db/cache/invalidate" \
  -H "Content-Type: application/json" \
  -d '{"table": "campaigns"}'
```

3. Clear entire cache:

```bash
curl -X POST "http://localhost:8000/api/v1/db/cache/invalidate"
```

## Troubleshooting

### Database Connection Issues

1. Check connection pool status:

```bash
curl "http://localhost:8000/api/v1/db/performance"
```

2. Look for connection pool saturation (low available connections)

3. Update connection pool settings as needed

### Query Performance Issues

1. Identify slow queries using monitoring tools

2. Run the optimization endpoint for suggestions

3. Verify that proper indexes exist on commonly queried columns

4. Consider adding caching for frequently accessed data

### Cache Not Working as Expected

1. Check cache hit rate:

```bash
curl "http://localhost:8000/api/v1/db/cache"
```

2. Verify that cache invalidation is working properly when data changes

3. Adjust TTL settings to match data volatility

4. Ensure cache keys are generated consistently

## Guides for Further Reference

- [Database Optimization Checklist](database_optimization_checklist.md) - Step-by-step checklist for optimization
- [Database Performance Testing](database_performance_testing.md) - Detailed guide for performance testing
- [Query Caching Guide](query_caching_guide.md) - Complete guide for implementing caching
- [Database Best Practices](database_best_practices.md) - Comprehensive best practices document

## Getting Help

If you encounter issues or need assistance with the database improvements:

1. Review the complete documentation in the `docs/` directory
2. Check the database monitoring endpoints for insights
3. Refer to the common troubleshooting steps in this guide
4. For more complex issues, reach out to the database team 