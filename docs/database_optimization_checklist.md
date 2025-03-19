# Database Optimization Checklist

Use this checklist to identify and resolve common database performance issues in the ReplyRocket.io application.

## Quick Assessment

- [ ] Run `python scripts/test_db_performance.py --cache --show-stats` to get baseline performance
- [ ] Check if query cache hit rate is below 70%
- [ ] Identify queries taking longer than 100ms
- [ ] Look for connection pool issues (low available connections)
- [ ] Check database monitoring dashboard for recent performance trends

## Query Optimization

### Indexing
- [ ] Verify indexes exist on all columns used in WHERE clauses
- [ ] Check for indexes on JOIN columns
- [ ] Confirm indexes on sorting columns (ORDER BY)
- [ ] Ensure foreign keys have appropriate indexes
- [ ] Check if any unused indexes can be removed
- [ ] Consider composite indexes for multi-column filters

### Query Structure
- [ ] Replace `SELECT *` with specific column selections
- [ ] Verify JOINs are necessary and efficient
- [ ] Look for unnecessary subqueries that could be simplified
- [ ] Check if any LIKE '%...%' wildcards can be avoided
- [ ] Ensure aggregate functions use appropriate GROUP BY clauses
- [ ] Consider LIMIT clauses for large result sets

### Caching
- [ ] Identify frequently accessed, rarely changing data for caching
- [ ] Set appropriate TTL values based on data volatility
- [ ] Check if any services should use the @cached_query decorator
- [ ] Verify cache invalidation is triggered on data updates
- [ ] Consider using selective cache invalidation by table

## Connection Management

- [ ] Verify database sessions are properly closed after use
- [ ] Check for potential session leaks in background tasks
- [ ] Confirm appropriate error handling with session rollbacks
- [ ] Adjust connection pool size based on application load
- [ ] Set connection timeout and recycling parameters appropriately
- [ ] Monitor for connection pool saturation during peak load

## Transaction Management

- [ ] Ensure transactions are as short as possible
- [ ] Verify READ operations don't unnecessarily use transactions
- [ ] Check for nested transactions that could be simplified
- [ ] Confirm ACID requirements are met for critical operations
- [ ] Look for potential deadlocks in complex transactions
- [ ] Consider using explicit savepoints for complex operations

## Schema Optimization

- [ ] Analyze table sizes and growth patterns
- [ ] Check for opportunities to denormalize specific tables
- [ ] Consider partitioning for very large tables
- [ ] Evaluate column data types for size optimization
- [ ] Look for unused or redundant columns
- [ ] Consider materialized views for complex reporting queries

## System Configuration

- [ ] Verify PostgreSQL is using optimal configuration for hardware
- [ ] Check if shared_buffers setting is appropriate
- [ ] Verify work_mem is set properly for complex queries
- [ ] Adjust maintenance_work_mem for background operations
- [ ] Configure autovacuum settings for optimal performance
- [ ] Set appropriate WAL (Write-Ahead Log) configuration

## Ongoing Monitoring

- [ ] Set up alerts for slow query frequency increases
- [ ] Monitor cache hit rate on a regular basis
- [ ] Track connection pool utilization
- [ ] Watch for growing table sizes and index bloat
- [ ] Check for increasing query times over time
- [ ] Review database statistics weekly

## Resolving Common Issues

### Slow Queries
1. Run EXPLAIN ANALYZE on the query
2. Use `/api/v1/db/analyze-query` endpoint with the slow query
3. Implement suggested indexes from the analysis
4. Consider rewriting the query based on execution plan
5. Apply caching if appropriate

### Connection Pool Saturation
1. Check for connection leaks in code
2. Verify sessions are being closed properly
3. Increase pool size if hardware allows
4. Implement connection recycling
5. Consider implementing connection timeouts

### Cache Performance Issues
1. Verify cache key generation is efficient
2. Check TTL settings match data volatility
3. Ensure invalidation is working correctly
4. Monitor cache size to prevent memory issues
5. Consider more selective cache invalidation strategies

### ORM Performance Problems
1. Use eager loading (joinedload) for related objects when needed
2. Consider using bulk operations for multiple updates
3. Replace complex ORM queries with raw SQL when necessary
4. Use hybrid properties for computed values
5. Implement custom loading strategies for complex object graphs

## Tools Available

- **Query Analysis**: `/api/v1/db/analyze-query`
- **Index Suggestions**: `/api/v1/db/optimize-query`
- **Table Statistics**: `/api/v1/db/table-stats/{table_name}`
- **Performance Monitoring**: `/api/v1/db/performance`
- **Slow Query Log**: `/api/v1/db/slow-queries`
- **Cache Statistics**: `/api/v1/db/cache`

## Further Resources

- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)
- [SQLAlchemy Performance Guide](https://docs.sqlalchemy.org/en/14/faq/performance.html)
- [Database Best Practices](docs/database_best_practices.md)
- [Database Performance Testing](docs/database_performance_testing.md) 