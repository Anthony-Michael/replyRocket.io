"""
Database monitoring endpoints for administrators.

This module provides endpoints for monitoring database performance,
analyzing slow queries, and providing optimization recommendations.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import text, inspect
import psutil

from app.api import deps
from app.utils.db_monitor import get_query_stats, reset_query_stats, analyze_query
from app.utils.db_optimization import (
    optimize_query, suggest_indexes, generate_index_ddl, 
    get_table_stats as get_db_table_stats
)
from app.utils.query_cache import (
    get_cache_stats, invalidate_cache, invalidate_table_cache,
    cached_db_query
)
from app.db.session import get_pool_status
from app.core.config import settings

router = APIRouter()


@router.get("/performance", status_code=status.HTTP_200_OK)
def get_db_performance(
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get database performance statistics.
    
    This endpoint:
    1. Returns query statistics (slow queries, frequent queries)
    2. Provides connection pool information
    3. Reports system resource usage
    
    Only accessible to superusers.
    
    Returns:
        Dict with database performance metrics
    """
    # Get query statistics
    query_stats = get_query_stats()
    
    # Get connection pool information
    pool_info = get_pool_status()
    
    # Get system resource usage
    system_info = {
        "cpu_percent": psutil.cpu_percent(),
        "memory_percent": psutil.virtual_memory().percent,
        "memory_available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
        "disk_usage_percent": psutil.disk_usage('/').percent,
    }
    
    # Check PostgreSQL metadata for database size
    db_size = None
    try:
        if "postgresql" in settings.SQLALCHEMY_DATABASE_URI:
            result = db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as size,
                       pg_size_pretty(pg_total_relation_size('users')) as users_size
            """)).first()
            db_size = {
                "total": result[0],
                "users_table": result[1]
            }
    except Exception as e:
        db_size = {"error": str(e)}
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "query_stats": query_stats,
        "connection_pool": pool_info,
        "system_resources": system_info,
        "db_size": db_size
    }


@router.get("/slow-queries", status_code=status.HTTP_200_OK)
def get_slow_queries(
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_active_superuser),
    limit: int = Query(20, ge=1, le=100),
    min_time: float = Query(0.5, ge=0.1),
) -> Dict[str, Any]:
    """
    Get detailed information about slow queries.
    
    This endpoint returns information about slow queries that took longer
    than the specified threshold to execute.
    
    Only accessible to superusers.
    
    Args:
        limit: Maximum number of slow queries to return
        min_time: Minimum execution time threshold in seconds
        
    Returns:
        Dict with slow query details
    """
    # Get query statistics
    query_stats = get_query_stats()
    
    # Filter slow queries based on threshold
    filtered_queries = [
        q for q in query_stats.get("slow_queries_detail", [])
        if q.get("execution_time", 0) >= min_time
    ]
    
    # Sort by execution time (slowest first) and limit the results
    sorted_queries = sorted(
        filtered_queries,
        key=lambda q: q.get("execution_time", 0),
        reverse=True
    )[:limit]
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "threshold": min_time,
        "total_slow_queries": len(filtered_queries),
        "queries": sorted_queries
    }


@router.post("/analyze-query", status_code=status.HTTP_200_OK)
def analyze_sql_query(
    query_data: Dict[str, str] = Body(...),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Analyze a SQL query for potential performance issues.
    
    This endpoint analyzes a provided SQL query string and returns
    optimization recommendations.
    
    Only accessible to superusers.
    
    Request body:
        query: The SQL query string to analyze
        
    Returns:
        Dict with analysis results and recommendations
    """
    query_str = query_data.get("query")
    if not query_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string is required"
        )
    
    analysis = analyze_query(query_str)
    
    # Also run the query optimization analysis
    optimization = optimize_query(query_str)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "analysis": analysis,
        "optimization": optimization
    }


@router.post("/optimize-query", status_code=status.HTTP_200_OK)
def get_query_optimization(
    query_data: Dict[str, str] = Body(...),
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get comprehensive query optimization recommendations.
    
    This endpoint:
    1. Analyzes a SQL query for optimization opportunities
    2. Suggests indexes that could improve performance
    3. Provides DDL statements for creating suggested indexes
    
    Only accessible to superusers.
    
    Request body:
        query: The SQL query string to optimize
        
    Returns:
        Dict with optimization recommendations and index suggestions
    """
    query_str = query_data.get("query")
    if not query_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string is required"
        )
    
    # Get optimization recommendations
    optimization = optimize_query(query_str)
    
    # Suggest indexes based on query analysis
    index_suggestions = suggest_indexes(db, query_str)
    
    # Generate DDL statements for suggested indexes
    ddl_statements = generate_index_ddl(index_suggestions)
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "optimization": optimization,
        "index_suggestions": index_suggestions,
        "ddl_statements": ddl_statements
    }


@router.get("/table-stats/{table_name}", status_code=status.HTTP_200_OK)
def get_table_stats(
    table_name: str,
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get detailed statistics for a database table.
    
    This endpoint provides comprehensive statistics about a table including:
    - Row count
    - Column information
    - Index details
    - Table size (for PostgreSQL)
    - Column statistics (for PostgreSQL)
    
    Only accessible to superusers.
    
    Args:
        table_name: The name of the table to analyze
        
    Returns:
        Dict with table statistics
    """
    # Get table statistics
    table_stats = get_db_table_stats(db, table_name)
    
    if "error" in table_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error getting table statistics: {table_stats['error']}"
        )
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "table_stats": table_stats
    }


@router.get("/tables", status_code=status.HTTP_200_OK)
def list_tables(
    db: Session = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    List all tables in the database with basic statistics.
    
    This endpoint returns a list of all tables in the database,
    along with basic statistics like row count and size (if available).
    
    Only accessible to superusers.
    
    Returns:
        Dict with list of tables and basic statistics
    """
    try:
        # Get list of tables
        inspector = inspect(db.bind)
        table_names = inspector.get_table_names()
        
        # Get basic statistics for each table
        tables = []
        for table_name in table_names:
            try:
                # Get row count
                row_count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
                
                # Get table size for PostgreSQL
                table_size = None
                if db.bind.dialect.name == 'postgresql':
                    size_result = db.execute(text(
                        "SELECT pg_size_pretty(pg_total_relation_size(:table_name))"
                    ), {"table_name": table_name}).scalar()
                    table_size = size_result
                
                tables.append({
                    "name": table_name,
                    "row_count": row_count,
                    "size": table_size
                })
            except Exception as e:
                tables.append({
                    "name": table_name,
                    "error": str(e)
                })
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "tables": tables
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing tables: {str(e)}"
        )


@router.get("/cache", status_code=status.HTTP_200_OK)
def get_query_cache_stats(
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get query cache statistics.
    
    This endpoint returns statistics about the query cache,
    including hit rate, size, and other metrics.
    
    Only accessible to superusers.
    
    Returns:
        Dict with cache statistics
    """
    # Get cache statistics
    cache_stats = get_cache_stats()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "cache_stats": cache_stats
    }


@router.post("/cache/invalidate", status_code=status.HTTP_200_OK)
def invalidate_query_cache(
    invalidation_data: Dict[str, Any] = Body(default={}),
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Invalidate entries in the query cache.
    
    This endpoint allows invalidating specific cache entries
    or the entire cache.
    
    Only accessible to superusers.
    
    Request body:
        cache_key: Optional specific cache key to invalidate
        table_name: Optional table name to invalidate all related cache entries
        
    Returns:
        Dict with invalidation result
    """
    cache_key = invalidation_data.get("cache_key")
    table_name = invalidation_data.get("table_name")
    
    invalidated_count = 0
    
    if table_name:
        # Invalidate cache for specific table
        invalidated_count = invalidate_table_cache(table_name)
    elif cache_key:
        # Invalidate specific cache key
        invalidated_count = invalidate_cache(cache_key)
    else:
        # Invalidate entire cache
        invalidated_count = invalidate_cache()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "invalidated_count": invalidated_count,
        "success": True
    }


@router.post("/reset-stats", status_code=status.HTTP_200_OK)
def reset_statistics(
    current_user: Any = Depends(deps.get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Reset query statistics.
    
    This endpoint resets all query statistics, clearing counters and
    query history.
    
    Only accessible to superusers.
    
    Returns:
        Dict with success message
    """
    reset_query_stats()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Query statistics have been reset",
        "success": True
    } 