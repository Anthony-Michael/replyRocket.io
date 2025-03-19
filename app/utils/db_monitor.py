"""
Database monitoring utility for tracking query performance.

This module provides tools for monitoring database performance, 
tracking slow queries, and logging execution times.
"""

import logging
import time
import functools
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
import threading
import re

from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlalchemy.orm

from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)

# Thread-local storage for query timing information
thread_local = threading.local()

# Global query statistics
query_stats = {
    "total_queries": 0,
    "slow_queries": 0,
    "query_times": {},  # normalized_query -> [min, max, total, count]
    "slow_queries_detail": [],  # list of slow query details
    "top_queries": [],  # list of most frequent queries
}

# Lock for modifying query_stats
stats_lock = threading.Lock()

# Slow query threshold in seconds
SLOW_QUERY_THRESHOLD = getattr(settings, "SLOW_QUERY_THRESHOLD", 0.5)

# Maximum number of slow queries to store
MAX_SLOW_QUERIES = getattr(settings, "MAX_SLOW_QUERIES", 50)

# Maximum number of top queries to track
MAX_TOP_QUERIES = getattr(settings, "MAX_TOP_QUERIES", 20)


def normalize_query(query: str) -> str:
    """
    Normalize a SQL query to group similar queries.
    
    Args:
        query: The SQL query to normalize
        
    Returns:
        Normalized query string with literals replaced
    """
    # Replace literals with placeholders
    normalized = re.sub(r"'[^']*'", "'?'", query)
    normalized = re.sub(r"\d+", "?", normalized)
    # Remove extra whitespace
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def setup_query_timing():
    """Set up event listeners for tracking query execution time."""
    
    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # Store the start time in thread local storage
        thread_local.query_start_time = time.time()
        thread_local.query_statement = statement
        thread_local.query_parameters = parameters
    
    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        # Calculate execution time
        if not hasattr(thread_local, "query_start_time"):
            return
        
        execution_time = time.time() - thread_local.query_start_time
        
        # Update statistics
        with stats_lock:
            query_stats["total_queries"] += 1
            
            # Normalize the query for aggregation
            normalized_query = normalize_query(statement)
            
            # Update query time statistics
            if normalized_query not in query_stats["query_times"]:
                query_stats["query_times"][normalized_query] = [execution_time, execution_time, execution_time, 1]
            else:
                stats = query_stats["query_times"][normalized_query]
                stats[0] = min(stats[0], execution_time)  # min
                stats[1] = max(stats[1], execution_time)  # max
                stats[2] += execution_time  # total
                stats[3] += 1  # count
            
            # Log slow queries
            if execution_time > SLOW_QUERY_THRESHOLD:
                query_stats["slow_queries"] += 1
                slow_query_detail = {
                    "query": statement,
                    "parameters": str(parameters),
                    "execution_time": execution_time,
                    "timestamp": time.time()
                }
                query_stats["slow_queries_detail"].append(slow_query_detail)
                # Limit the number of stored slow queries
                if len(query_stats["slow_queries_detail"]) > MAX_SLOW_QUERIES:
                    query_stats["slow_queries_detail"].pop(0)
                
                # Log the slow query
                logger.warning(f"Slow query detected ({execution_time:.4f}s): {statement}")
            
            # Update top queries
            query_stats["top_queries"] = sorted(
                [(q, stats[3], stats[2] / stats[3]) for q, stats in query_stats["query_times"].items()],
                key=lambda x: x[1],  # Sort by count
                reverse=True
            )[:MAX_TOP_QUERIES]
        
        # Clean up thread local storage
        del thread_local.query_start_time
        del thread_local.query_statement
        del thread_local.query_parameters


def get_query_stats() -> Dict[str, Any]:
    """
    Get the current query statistics.
    
    Returns:
        Dictionary containing query statistics
    """
    with stats_lock:
        return {
            "total_queries": query_stats["total_queries"],
            "slow_queries": query_stats["slow_queries"],
            "top_queries": [
                {
                    "query": q,
                    "count": count,
                    "avg_time": avg_time
                }
                for q, count, avg_time in query_stats["top_queries"]
            ],
            "slow_queries_detail": query_stats["slow_queries_detail"]
        }


def reset_query_stats():
    """Reset all query statistics."""
    with stats_lock:
        query_stats["total_queries"] = 0
        query_stats["slow_queries"] = 0
        query_stats["query_times"] = {}
        query_stats["slow_queries_detail"] = []
        query_stats["top_queries"] = []


def analyze_query(query_str: str) -> Dict[str, Any]:
    """
    Analyze a query string and provide optimization recommendations.
    
    Args:
        query_str: The SQL query to analyze
        
    Returns:
        Dictionary containing analysis results
    """
    # Simple patterns that might indicate optimization opportunities
    patterns = {
        "full_table_scan": (r"\bFROM\s+\w+\s+WHERE\s+(?!.*INDEX)", 
                           "Query may perform a full table scan. Consider adding an index."),
        "select_all": (r"SELECT\s+\*", 
                      "SELECT * fetches all columns which is inefficient. Select only needed columns."),
        "missing_limit": (r"SELECT\s+(?!.*LIMIT)", 
                         "Query doesn't have a LIMIT clause which can lead to large result sets."),
        "complex_join": (r"JOIN.*JOIN.*JOIN", 
                        "Query has multiple JOINs which may be inefficient. Consider denormalizing or adding indexes."),
        "subqueries": (r"\(\s*SELECT", 
                      "Subqueries can be inefficient. Consider using JOINs or CTEs instead."),
    }
    
    results = []
    for issue, (pattern, recommendation) in patterns.items():
        if re.search(pattern, query_str, re.IGNORECASE):
            results.append({
                "issue": issue,
                "recommendation": recommendation
            })
    
    return {
        "query": query_str,
        "potential_issues": len(results),
        "recommendations": results
    }


class SessionTracker:
    """
    SQLAlchemy session wrapper for tracking session usage and query performance.
    
    Wraps a SQLAlchemy session to track execution time of queries and 
    to ensure proper resource management.
    """
    
    def __init__(self, session, context="unknown"):
        """
        Initialize a session tracker.
        
        Args:
            session: SQLAlchemy session to wrap
            context: String describing where this session is used
        """
        self.session = session
        self.context = context
        self.start_time = time.time()
        self.query_count = 0
    
    def __enter__(self):
        """Context manager enter."""
        logger.debug(f"Started session tracking in context: {self.context}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        duration = time.time() - self.start_time
        logger.debug(f"Session in context {self.context} executed {self.query_count} queries in {duration:.4f}s")
        
        # Don't close the session here; that's the responsibility of the session manager
        return False
    
    def __getattr__(self, name):
        """Delegate attribute access to the wrapped session."""
        attr = getattr(self.session, name)
        
        # Wrap query execution methods to count queries
        if name in ('execute', 'query'):
            return self._wrap_query_method(attr)
        
        return attr
    
    def _wrap_query_method(self, method):
        """Wrap a query method to track execution."""
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            self.query_count += 1
            return method(*args, **kwargs)
        
        return wrapper


def optimize_session(session: sqlalchemy.orm.Session) -> sqlalchemy.orm.Session:
    """
    Optimize a SQLAlchemy session with best practice configurations.
    
    Args:
        session: SQLAlchemy session to optimize
        
    Returns:
        Optimized session
    """
    # Auto expire on commit can be inefficient in some scenarios
    # When disabled, the application must be careful to refresh objects as needed
    session.expire_on_commit = False
    
    # Set reasonable batch size for bulk operations
    if hasattr(session, 'configure'):
        session.configure(execution_options={"stream_results": True})
    
    return session


def with_query_timing(func: Callable) -> Callable:
    """
    Decorator to time and log query execution.
    
    Args:
        func: The function to decorate
        
    Returns:
        Decorated function that logs execution time
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            return func(*args, **kwargs)
        finally:
            execution_time = time.time() - start_time
            logger.debug(f"Function {func.__name__} executed in {execution_time:.4f}s")
            if execution_time > SLOW_QUERY_THRESHOLD:
                logger.warning(f"Slow operation detected: {func.__name__} took {execution_time:.4f}s")
    
    return wrapper


# Initialize query timing listeners
setup_query_timing() 