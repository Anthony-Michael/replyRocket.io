# Database Performance Testing Guide

This guide explains how to use the database performance testing script to evaluate and optimize your database queries.

## Overview

The `test_db_performance.py` script in the `scripts` directory allows you to:

1. Measure query execution times with and without caching
2. Identify slow queries
3. View database statistics
4. Evaluate the effectiveness of the query cache

## Prerequisites

Before running the script, ensure:

1. Your database is running and accessible
2. The application environment is properly configured
3. You have all required dependencies installed

## Basic Usage

To run a basic performance test:

```bash
# From the project root directory
python scripts/test_db_performance.py
```

This will:
- Run 5 iterations (default) of 3 queries (default)
- Measure execution time for each query
- Display results in a formatted table

## Command Line Options

The script supports several command line options:

| Option | Description | Default |
|--------|-------------|---------|
| `--iterations N` | Number of iterations for each test | 5 |
| `--queries N` | Number of different queries to test (1-3) | 3 |
| `--cache` | Test with query cache enabled | False |
| `--show-stats` | Display database statistics and slow queries | False |
| `--slow-threshold T` | Threshold for slow queries in seconds | 0.1 |

## Examples

### Testing with Query Cache

To test the performance impact of query caching:

```bash
python scripts/test_db_performance.py --cache
```

This will run each query both with and without caching, allowing you to see the performance improvement.

### Showing Database Statistics

To view database statistics and slow queries:

```bash
python scripts/test_db_performance.py --show-stats
```

### Comprehensive Test

For a comprehensive test:

```bash
python scripts/test_db_performance.py --cache --show-stats --iterations 10 --slow-threshold 0.05
```

## Understanding the Results

The script provides several result sections:

### Query Performance Results

This table shows:
- Average, minimum, and maximum execution times for each query
- If caching is enabled, cached execution times and improvement percentage

### Query Cache Statistics

When caching is enabled, these statistics show:
- Total cache entries
- Cache hits and misses
- Hit rate percentage
- Cache evictions
- Total operations

### Database Statistics

When `--show-stats` is used:
- Active and available connections
- Total queries executed
- Average query execution time
- List of slow queries exceeding the threshold

## Using Results for Optimization

1. **Identify slow queries**: Focus optimization efforts on queries with the highest execution times
2. **Evaluate cache effectiveness**: If the improvement percentage is low, consider adjusting cache settings
3. **Check connection pool**: Ensure the connection pool has sufficient available connections
4. **Monitor query patterns**: Use the slow query list to identify patterns in problematic queries

## Extending the Script

The script can be extended to:
- Add more complex test queries specific to your application
- Include additional performance metrics
- Generate performance reports over time
- Test specific database operations or tables

## Troubleshooting

If you encounter issues:

1. Ensure database connectivity
2. Check import paths and dependencies
3. Verify that the database user has sufficient permissions
4. For import errors, make sure you're running from the project root or scripts directory

For more help, refer to the database best practices document or contact the development team. 