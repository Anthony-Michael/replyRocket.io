# Database Best Practices for ReplyRocket.io

This document outlines the best practices for database usage in the ReplyRocket.io application. Following these guidelines will help ensure optimal performance, security, and maintainability.

## Table of Contents

1. [Database Session Management](#database-session-management)
2. [Connection Pooling](#connection-pooling)
3. [Query Optimization](#query-optimization)
4. [Caching Strategies](#caching-strategies)
5. [Error Handling](#error-handling)
6. [Transaction Management](#transaction-management)
7. [Monitoring and Debugging](#monitoring-and-debugging)
8. [Schema Design](#schema-design)

## Database Session Management

### Using `Depends(get_db)` in FastAPI Endpoints

Always use FastAPI's dependency injection system to manage database sessions in API endpoints:

```python
@router.get("/items")
def read_items(db: Session = Depends(get_db)):
    # Use db session here
    items = db.query(Item).all()
    return items
```

Benefits:
- Sessions are automatically closed after the request completes
- Sessions are properly rolled back if an exception occurs
- Makes testing easier through dependency overrides

### Avoiding Session Leaks

For non-endpoint contexts (background tasks, scripts), use context managers:

```python
# For background tasks
from app.db.session import get_db_context

with get_db_context() as db:
    # Use db session here
    db.query(User).all()
    # Session is automatically closed at the end of the block
```

### Accessing DB Outside Request Context

For scheduled tasks or command-line scripts, create a session using SessionManager:

```python
from app.db.session import SessionManager

with SessionManager(context="scheduled_task") as db:
    # Use db session here
    users = db.query(User).filter(User.is_active).all()
    # Session is automatically closed when the with block exits
```

## Connection Pooling

Our application uses SQLAlchemy's QueuePool to manage database connections. The configuration is in `app/db/session.py`.

### Default Configuration

```python
pool_size=settings.DB_POOL_SIZE,           # Default: 5 in prod, 2 in dev
max_overflow=settings.DB_MAX_OVERFLOW,     # Default: 10 in prod, 5 in dev
pool_timeout=settings.DB_POOL_TIMEOUT,     # Default: 30 seconds
pool_recycle=settings.DB_POOL_RECYCLE,     # Default: 1800 seconds (30 minutes)
```

### Tuning Guidelines

- **High Traffic**: Increase `DB_POOL_SIZE` for high-concurrency scenarios
- **Spiky Traffic**: Increase `DB_MAX_OVERFLOW` to handle spikes
- **Long Running Tasks**: Consider using a separate session with a longer `pool_timeout`
- **Database Stability**: Database connections are recycled after 30 minutes by default to avoid stale connections

## Query Optimization

### Using Efficient Queries

1. **Select Only What You Need**
   ```python
   # BAD: Selects all columns
   users = db.query(User).all()
   
   # GOOD: Select only needed columns
   users = db.query(User.id, User.email).all()
   ```

2. **Use JOINs Efficiently**
   ```python
   # BAD: Multiple queries (N+1 problem)
   campaigns = db.query(Campaign).filter(Campaign.user_id == user_id).all()
   for campaign in campaigns:
       emails = db.query(Email).filter(Email.campaign_id == campaign.id).all()
   
   # GOOD: Single query with JOIN
   results = db.query(Campaign, Email).\
       join(Email, Campaign.id == Email.campaign_id).\
       filter(Campaign.user_id == user_id).all()
   ```

3. **Use Query Options for Relationships**
   ```python
   # Load relationships eagerly when needed
   campaigns = db.query(Campaign).\
       options(selectinload(Campaign.emails)).\
       filter(Campaign.user_id == user_id).all()
   ```

4. **Add LIMIT Clauses**
   ```python
   # Always limit results, especially in lists
   users = db.query(User).limit(100).offset(0).all()
   ```

5. **Add Appropriate Indexes**
   Use the DB Monitor endpoints to suggest indexes:
   - `/db-monitor/optimize-query` - Suggest indexes based on a specific query
   - `/db-monitor/table-stats/{table_name}` - View current indexes and table statistics

### ORM vs. Raw SQL

Use the ORM for most queries, but consider raw SQL for complex queries:

```python
# Complex aggregation with raw SQL
result = db.execute(text("""
    SELECT date_trunc('day', sent_at) as day, COUNT(*) as count
    FROM emails
    WHERE campaign_id = :campaign_id
    GROUP BY date_trunc('day', sent_at)
    ORDER BY day DESC
"""), {"campaign_id": campaign_id}).fetchall()
```

## Caching Strategies

ReplyRocket.io implements a query cache system to improve performance. Use it for frequently executed, slow-changing data.

### Cached Query Decorator

```python
from app.utils.query_cache import cached_query

@cached_query(ttl=300)  # Cache for 5 minutes
def get_user_statistics(db: Session, user_id: UUID):
    # Complex query here
    return result
```

### Direct Caching for Raw Queries

```python
from app.utils.query_cache import cached_db_query

def get_campaign_summary(db: Session, campaign_id: UUID):
    query = """
        SELECT COUNT(*) as total, 
               SUM(CASE WHEN is_opened THEN 1 ELSE 0 END) as opened,
               SUM(CASE WHEN is_replied THEN 1 ELSE 0 END) as replied
        FROM emails
        WHERE campaign_id = :campaign_id
    """
    result = cached_db_query(db, query, {"campaign_id": str(campaign_id)}, ttl=600)
    return result
```

### Cache Invalidation

Invalidate caches when data changes:

```python
from app.utils.query_cache import invalidate_table_cache

def update_user(db: Session, user_id: UUID, user_data: dict):
    # Update user
    db.query(User).filter(User.id == user_id).update(user_data)
    db.commit()
    
    # Invalidate related caches
    invalidate_table_cache("users")
```

The system automatically invalidates caches for INSERT/UPDATE/DELETE operations, but you can manually invalidate for more control.

## Error Handling

### Transaction Management

Use transactions to ensure data integrity:

```python
def create_campaign_with_emails(db: Session, campaign_data: dict, emails_data: list):
    try:
        # Create campaign
        campaign = Campaign(**campaign_data)
        db.add(campaign)
        db.flush()  # Flush to get ID but don't commit yet
        
        # Create emails
        for email_data in emails_data:
            email = Email(campaign_id=campaign.id, **email_data)
            db.add(email)
        
        # Commit transaction if everything succeeded
        db.commit()
        return campaign
    except Exception as e:
        # Roll back on any error
        db.rollback()
        logger.error(f"Failed to create campaign: {str(e)}")
        raise
```

### Exception Handling

Use the appropriate exception classes to handle database errors:

```python
from app.core.exception_handlers import DatabaseError, EntityNotFoundError

def get_user(db: Session, user_id: UUID):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise EntityNotFoundError(f"User with ID {user_id} not found")
        return user
    except SQLAlchemyError as e:
        # Log and convert to application-specific exception
        logger.error(f"Database error retrieving user {user_id}: {str(e)}")
        raise DatabaseError(f"Error retrieving user: {str(e)}")
```

## Monitoring and Debugging

Use the monitoring tools provided:

1. **Performance Dashboard**
   - `/db-monitor/performance` - Overall database performance

2. **Slow Query Analysis**
   - `/db-monitor/slow-queries` - Find and analyze slow queries

3. **Query Optimization**
   - `/db-monitor/analyze-query` - Get optimization recommendations

4. **Query Cache**
   - `/db-monitor/cache` - Monitor cache hit rates and size

5. **Health Check**
   - `/health/db` - Database health and connection pool status

## Schema Design

### Indexes

Create appropriate indexes for frequently queried columns:

- Primary keys are automatically indexed
- Foreign keys should generally be indexed
- Columns used in WHERE clauses should be indexed
- Columns used in JOIN conditions should be indexed
- Columns used in ORDER BY should be indexed if the table is large

Use the `CreateIndex` operation in Alembic migrations:

```python
from sqlalchemy import Column, Integer, String, ForeignKey, Index
from alembic import op

# In a migration file
def upgrade():
    op.create_index(
        'idx_emails_campaign_id_created_at',
        'emails',
        ['campaign_id', 'created_at'],
        unique=False
    )
```

### Partitioning

For very large tables (millions of rows), consider using PostgreSQL table partitioning:

```sql
CREATE TABLE emails (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL,
    -- other columns
) PARTITION BY RANGE (created_at);

CREATE TABLE emails_y2022 PARTITION OF emails 
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');

CREATE TABLE emails_y2023 PARTITION OF emails 
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
```

## Additional Resources

- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/20/)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [FastAPI Database Dependencies](https://fastapi.tiangolo.com/tutorial/sql-databases/)
- [ReplyRocket Database Monitoring Dashboard](/api/docs#/database) 