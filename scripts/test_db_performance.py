#!/usr/bin/env python3
"""
Database Performance Test Script

This script tests database performance and demonstrates the query caching system.
It runs a series of queries with and without caching to measure performance improvements.
"""

import os
import sys
import time
import argparse
import statistics
from typing import List, Dict, Any, Tuple

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.db.session import SessionLocal
    from app.utils.query_cache import cached_db_query, invalidate_cache, get_cache_stats
    from app.utils.db_monitoring import get_slow_queries, get_db_stats
    from sqlalchemy import text
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running this script from the project root or scripts directory")
    sys.exit(1)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Test database performance with and without query cache')
    parser.add_argument('--iterations', type=int, default=5, help='Number of iterations for each test')
    parser.add_argument('--queries', type=int, default=3, help='Number of different queries to test')
    parser.add_argument('--cache', action='store_true', help='Use query cache')
    parser.add_argument('--show-stats', action='store_true', help='Show database statistics')
    parser.add_argument('--slow-threshold', type=float, default=0.1, help='Threshold for slow queries in seconds')
    
    return parser.parse_args()

def generate_test_queries(num_queries: int) -> List[str]:
    """Generate test queries of varying complexity."""
    queries = []
    
    # Simple count query
    queries.append("SELECT COUNT(*) FROM users")
    
    if num_queries >= 2:
        # Join query
        queries.append("""
            SELECT u.email, COUNT(c.id) 
            FROM users u 
            LEFT JOIN campaigns c ON u.id = c.user_id 
            GROUP BY u.email
        """)
    
    if num_queries >= 3:
        # Complex query with subquery
        queries.append("""
            SELECT 
                c.name, 
                c.total_emails,
                (SELECT COUNT(*) FROM emails e WHERE e.campaign_id = c.id AND e.opened = true) as opened,
                (SELECT COUNT(*) FROM emails e WHERE e.campaign_id = c.id AND e.replied = true) as replied
            FROM campaigns c
            WHERE c.created_at > current_date - interval '30 days'
            ORDER BY c.created_at DESC
        """)
    
    return queries[:num_queries]

def run_query(query: str, use_cache: bool = False) -> Tuple[Any, float]:
    """Run a query and measure execution time."""
    db = SessionLocal()
    try:
        start_time = time.time()
        
        if use_cache:
            result = cached_db_query(db, text(query), ttl=60)
        else:
            result = db.execute(text(query))
            result = result.fetchall()
            
        execution_time = time.time() - start_time
        return result, execution_time
    finally:
        db.close()

def run_tests(queries: List[str], iterations: int, use_cache: bool) -> Dict[str, List[float]]:
    """Run a series of test queries and record execution times."""
    results = {query: [] for query in queries}
    
    print(f"\nRunning tests {'with' if use_cache else 'without'} query cache...")
    
    for i in range(iterations):
        print(f"  Iteration {i+1}/{iterations}")
        
        for query in queries:
            # Clear cache between iterations if testing with cache
            if use_cache and i > 0:
                invalidate_cache()
                
            # First execution to warm up
            if i == 0:
                _, _ = run_query(query, use_cache)
                
            # Test execution
            _, execution_time = run_query(query, use_cache)
            results[query].append(execution_time)
            
    return results

def print_results(no_cache_results: Dict[str, List[float]], cache_results: Dict[str, List[float]] = None):
    """Print test results in a formatted table."""
    print("\n=== Database Query Performance Results ===\n")
    
    headers = ["Query", "Avg Time (ms)", "Min (ms)", "Max (ms)"]
    if cache_results:
        headers.extend(["Cached Avg (ms)", "Improvement"])
    
    # Print headers
    print(f"{headers[0]:<50} {headers[1]:<15} {headers[2]:<10} {headers[3]:<10}", end="")
    if cache_results:
        print(f" {headers[4]:<15} {headers[5]:<10}")
    else:
        print()
        
    print("-" * (85 + (25 if cache_results else 0)))
    
    # Print results for each query
    for i, (query, times) in enumerate(no_cache_results.items()):
        query_short = query.strip().split("\n")[0][:47] + "..." if len(query.strip()) > 50 else query.strip()
        
        avg_time = statistics.mean(times) * 1000  # Convert to ms
        min_time = min(times) * 1000
        max_time = max(times) * 1000
        
        print(f"{query_short:<50} {avg_time:>12.2f}ms {min_time:>8.2f}ms {max_time:>8.2f}ms", end="")
        
        if cache_results and query in cache_results:
            cache_times = cache_results[query]
            cache_avg_time = statistics.mean(cache_times) * 1000
            improvement = ((avg_time - cache_avg_time) / avg_time) * 100 if avg_time > 0 else 0
            print(f" {cache_avg_time:>12.2f}ms {improvement:>8.1f}%")
        else:
            print()

def print_cache_stats():
    """Print cache statistics."""
    stats = get_cache_stats()
    
    print("\n=== Query Cache Statistics ===\n")
    print(f"Total cache entries: {stats['size']}")
    print(f"Cache hits: {stats['hits']}")
    print(f"Cache misses: {stats['misses']}")
    print(f"Hit rate: {stats['hit_rate']:.2f}%")
    print(f"Evictions: {stats['evictions']}")
    print(f"Total operations: {stats['total_operations']}")

def print_db_stats(slow_threshold: float):
    """Print database statistics and slow queries."""
    try:
        db = SessionLocal()
        db_stats = get_db_stats(db)
        slow_queries = get_slow_queries(db, threshold=slow_threshold)
        db.close()
        
        print("\n=== Database Statistics ===\n")
        print(f"Active connections: {db_stats['active_connections']}")
        print(f"Available connections: {db_stats['available_connections']}")
        print(f"Total queries: {db_stats['total_queries']}")
        print(f"Avg query time: {db_stats['avg_query_time']:.4f}s")
        
        if slow_queries:
            print("\n=== Slow Queries ===\n")
            for i, query in enumerate(slow_queries):
                print(f"{i+1}. [{query['execution_time']:.4f}s] {query['query_text']}")
        else:
            print("\nNo slow queries detected.")
    except Exception as e:
        print(f"Error retrieving database statistics: {e}")

def main():
    args = parse_args()
    
    print("\n=== Database Performance Test ===")
    print(f"Running {args.iterations} iterations of {args.queries} queries")
    
    # Generate test queries
    queries = generate_test_queries(args.queries)
    
    # Run tests without cache
    no_cache_results = run_tests(queries, args.iterations, False)
    
    # Run tests with cache if requested
    cache_results = None
    if args.cache:
        cache_results = run_tests(queries, args.iterations, True)
        
    # Print results
    print_results(no_cache_results, cache_results)
    
    # Print cache stats if cache was used
    if args.cache:
        print_cache_stats()
        
    # Print database stats if requested
    if args.show_stats:
        print_db_stats(args.slow_threshold)
        
    print("\nTest completed.")

if __name__ == "__main__":
    main() 