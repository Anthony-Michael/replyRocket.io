"""
Database optimization utility.

This module provides utilities for optimizing database performance,
suggesting indexes, and analyzing query patterns.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any, Set

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.engine import Inspector

logger = logging.getLogger(__name__)


def extract_tables_and_columns(query: str) -> Dict[str, List[str]]:
    """
    Extract table and column names from a SQL query.
    
    Args:
        query: The SQL query to analyze
        
    Returns:
        Dictionary mapping table names to lists of column names
    """
    tables_and_columns = {}
    
    # Extract table names from FROM and JOIN clauses
    from_pattern = r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    join_pattern = r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    
    tables = set()
    for pattern in [from_pattern, join_pattern]:
        matches = re.finditer(pattern, query, re.IGNORECASE)
        for match in matches:
            tables.add(match.group(1))
    
    # Extract column names for each table
    for table in tables:
        # Find column references for this table (table.column pattern)
        column_pattern = r'\b' + table + r'\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
        column_matches = re.finditer(column_pattern, query, re.IGNORECASE)
        columns = set(match.group(1) for match in column_matches)
        
        if columns:
            tables_and_columns[table] = list(columns)
    
    return tables_and_columns


def analyze_where_conditions(query: str) -> List[Dict[str, str]]:
    """
    Analyze WHERE conditions in a SQL query to identify potential index candidates.
    
    Args:
        query: The SQL query to analyze
        
    Returns:
        List of dictionaries with table and column information for potential indexes
    """
    # Look for WHERE conditions
    where_pattern = r'\bWHERE\s+(.*?)(?:\bGROUP BY\b|\bHAVING\b|\bORDER BY\b|\bLIMIT\b|$)'
    where_match = re.search(where_pattern, query, re.IGNORECASE | re.DOTALL)
    
    if not where_match:
        return []
    
    where_clause = where_match.group(1).strip()
    
    # Split into individual conditions (handling basic AND/OR logic)
    conditions = re.split(r'\bAND\b', where_clause, flags=re.IGNORECASE)
    
    # Extract table.column patterns from each condition
    index_candidates = []
    table_column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
    
    for condition in conditions:
        # Skip OR conditions as they're less effective for indexing
        if re.search(r'\bOR\b', condition, re.IGNORECASE):
            continue
        
        match = re.search(table_column_pattern, condition, re.IGNORECASE)
        if match:
            table, column = match.groups()
            # Check if this is an equality, comparison, or LIKE condition
            if (
                re.search(r'=\s*["\']?\w+', condition) or
                re.search(r'IS\s+(?:NOT\s+)?NULL', condition, re.IGNORECASE) or
                re.search(r'IN\s*\(', condition, re.IGNORECASE)
            ):
                index_type = "equality"
            elif re.search(r'LIKE\s+', condition, re.IGNORECASE):
                index_type = "like"
            elif re.search(r'[<>]', condition):
                index_type = "range"
            else:
                index_type = "unknown"
            
            index_candidates.append({
                "table": table,
                "column": column,
                "condition_type": index_type,
                "condition": condition.strip()
            })
    
    return index_candidates


def analyze_order_by(query: str) -> List[Dict[str, str]]:
    """
    Analyze ORDER BY clauses in a SQL query.
    
    Args:
        query: The SQL query to analyze
        
    Returns:
        List of dictionaries with table and column information for ORDER BY clauses
    """
    order_by_pattern = r'\bORDER\s+BY\s+(.*?)(?:\bLIMIT\b|$)'
    order_match = re.search(order_by_pattern, query, re.IGNORECASE | re.DOTALL)
    
    if not order_match:
        return []
    
    order_clause = order_match.group(1).strip()
    
    # Split into individual columns
    columns = [col.strip() for col in order_clause.split(',')]
    
    # Extract table.column patterns
    order_columns = []
    table_column_pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)'
    
    for column in columns:
        match = re.search(table_column_pattern, column, re.IGNORECASE)
        if match:
            table, column_name = match.groups()
            
            # Check for ASC/DESC
            direction = "ASC"
            if re.search(r'\bDESC\b', column, re.IGNORECASE):
                direction = "DESC"
            
            order_columns.append({
                "table": table,
                "column": column_name,
                "direction": direction
            })
    
    return order_columns


def get_existing_indexes(db: Session, table_name: str) -> List[Dict[str, Any]]:
    """
    Get existing indexes for a table.
    
    Args:
        db: Database session
        table_name: Name of the table to check
        
    Returns:
        List of dictionaries with index information
    """
    try:
        inspector = inspect(db.bind)
        indexes = inspector.get_indexes(table_name)
        return indexes
    except Exception as e:
        logger.error(f"Error getting indexes for table {table_name}: {str(e)}")
        return []


def is_table_large(db: Session, table_name: str, threshold_rows: int = 10000) -> bool:
    """
    Check if a table is considered large based on row count.
    
    Args:
        db: Database session
        table_name: Name of the table to check
        threshold_rows: Threshold for considering a table large
        
    Returns:
        Boolean indicating if the table is large
    """
    try:
        result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        return result > threshold_rows
    except Exception as e:
        logger.error(f"Error checking table size for {table_name}: {str(e)}")
        return False


def suggest_indexes(db: Session, query: str) -> List[Dict[str, Any]]:
    """
    Suggest indexes based on query analysis.
    
    Args:
        db: Database session
        query: The SQL query to analyze
        
    Returns:
        List of dictionaries with index suggestions
    """
    # Get tables and columns used in the query
    tables_and_columns = extract_tables_and_columns(query)
    
    # Analyze WHERE conditions
    where_conditions = analyze_where_conditions(query)
    
    # Analyze ORDER BY clauses
    order_by_columns = analyze_order_by(query)
    
    # Get existing indexes and check table sizes
    suggestions = []
    for table in tables_and_columns:
        # Check table size
        is_large = is_table_large(db, table)
        
        # Get existing indexes
        existing_indexes = get_existing_indexes(db, table)
        existing_indexed_columns = set()
        
        for idx in existing_indexes:
            for col in idx.get("column_names", []):
                existing_indexed_columns.add(col.lower())
        
        # Suggest indexes based on WHERE conditions
        where_columns = []
        for cond in where_conditions:
            if cond["table"].lower() == table.lower() and cond["column"].lower() not in existing_indexed_columns:
                where_columns.append({
                    "column": cond["column"],
                    "type": cond["condition_type"],
                    "condition": cond["condition"]
                })
        
        # Suggest indexes based on ORDER BY
        order_columns = []
        for col in order_by_columns:
            if col["table"].lower() == table.lower() and col["column"].lower() not in existing_indexed_columns:
                order_columns.append({
                    "column": col["column"],
                    "direction": col["direction"]
                })
        
        # Combine recommendations
        if where_columns or order_columns:
            suggestions.append({
                "table": table,
                "is_large_table": is_large,
                "existing_indexes": existing_indexes,
                "where_columns": where_columns,
                "order_columns": order_columns
            })
    
    return suggestions


def generate_index_ddl(suggestions: List[Dict[str, Any]]) -> List[str]:
    """
    Generate DDL statements for suggested indexes.
    
    Args:
        suggestions: List of index suggestions
        
    Returns:
        List of CREATE INDEX statements
    """
    ddl_statements = []
    
    for suggestion in suggestions:
        table = suggestion["table"]
        
        # Generate indexes for WHERE conditions
        for i, col in enumerate(suggestion["where_columns"]):
            column = col["column"]
            index_name = f"idx_{table}_{column}_auto"
            
            # For LIKE conditions, consider a functional index for PostgreSQL
            if col["type"] == "like" and suggestion.get("is_postgresql", True):
                ddl = f"CREATE INDEX {index_name} ON {table} (lower({column}) text_pattern_ops);"
                ddl_statements.append(ddl)
            else:
                ddl = f"CREATE INDEX {index_name} ON {table} ({column});"
                ddl_statements.append(ddl)
        
        # Generate indexes for ORDER BY conditions if the table is large
        if suggestion.get("is_large_table", False):
            for i, col in enumerate(suggestion["order_columns"]):
                column = col["column"]
                index_name = f"idx_{table}_{column}_order_auto"
                ddl = f"CREATE INDEX {index_name} ON {table} ({column});"
                ddl_statements.append(ddl)
    
    return ddl_statements


def get_table_stats(db: Session, table_name: str) -> Dict[str, Any]:
    """
    Get statistics for a database table.
    
    Args:
        db: Database session
        table_name: Name of the table to check
        
    Returns:
        Dictionary with table statistics
    """
    try:
        # Get basic table info
        inspector = inspect(db.bind)
        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)
        
        # Get row count
        row_count = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar()
        
        # For PostgreSQL, get additional statistics
        if db.bind.dialect.name == 'postgresql':
            # Get table size
            size_query = text("""
                SELECT
                    pg_size_pretty(pg_total_relation_size(:table_name)) as total_size,
                    pg_size_pretty(pg_relation_size(:table_name)) as table_size,
                    pg_size_pretty(pg_total_relation_size(:table_name) - pg_relation_size(:table_name)) as index_size
            """)
            size_result = db.execute(size_query, {"table_name": table_name}).first()
            
            # Get column statistics
            column_stats_query = text("""
                SELECT
                    a.attname as column_name,
                    n_distinct,
                    null_frac
                FROM pg_stats s
                JOIN pg_attribute a ON a.attrelid = s.tablename::regclass 
                                   AND a.attnum = s.attnum
                WHERE schemaname = 'public'
                AND tablename = :table_name
            """)
            column_stats = db.execute(column_stats_query, {"table_name": table_name}).fetchall()
            
            return {
                "table_name": table_name,
                "row_count": row_count,
                "columns": columns,
                "primary_key": pk_constraint,
                "foreign_keys": foreign_keys,
                "indexes": indexes,
                "size": {
                    "total": size_result[0],
                    "table": size_result[1],
                    "indexes": size_result[2]
                },
                "column_stats": [
                    {
                        "name": stat[0],
                        "distinct_values": stat[1],
                        "null_fraction": stat[2]
                    }
                    for stat in column_stats
                ]
            }
        
        # Generic stats for other databases
        return {
            "table_name": table_name,
            "row_count": row_count,
            "columns": columns,
            "primary_key": pk_constraint,
            "foreign_keys": foreign_keys,
            "indexes": indexes
        }
    
    except Exception as e:
        logger.error(f"Error getting table stats for {table_name}: {str(e)}")
        return {
            "table_name": table_name,
            "error": str(e)
        }


def optimize_query(query: str) -> Dict[str, Any]:
    """
    Analyze and provide optimization suggestions for a SQL query.
    
    Args:
        query: The SQL query to analyze
        
    Returns:
        Dictionary with optimization suggestions
    """
    original_query = query
    optimized_query = query
    
    # Optimization patterns
    optimizations = []
    
    # Check for SELECT *
    if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
        optimizations.append({
            "issue": "select_all",
            "description": "Using SELECT * retrieves all columns including those that may not be needed",
            "suggestion": "Specify only the columns you need in the SELECT clause"
        })
    
    # Check for missing LIMIT
    if not re.search(r'\bLIMIT\b', query, re.IGNORECASE) and re.search(r'\bSELECT\b', query, re.IGNORECASE):
        optimizations.append({
            "issue": "missing_limit",
            "description": "Query doesn't limit the number of rows returned",
            "suggestion": "Add a LIMIT clause to prevent fetching too many rows"
        })
    
    # Check for inefficient subqueries
    if re.search(r'\(\s*SELECT', query, re.IGNORECASE):
        optimizations.append({
            "issue": "subquery",
            "description": "Subqueries can be inefficient",
            "suggestion": "Consider using JOINs or CTEs (WITH) instead of subqueries"
        })
    
    # Check for missing WHERE clause on large tables
    if not re.search(r'\bWHERE\b', query, re.IGNORECASE) and re.search(r'\bFROM\b', query, re.IGNORECASE):
        optimizations.append({
            "issue": "missing_where",
            "description": "Query doesn't have a WHERE clause which may scan entire tables",
            "suggestion": "Add a WHERE clause to filter rows if possible"
        })
    
    # Check for inefficient LIKE patterns
    like_patterns = re.finditer(r'(\w+)\s+LIKE\s+[\'"]%(.+?)[\'"]', query, re.IGNORECASE)
    for match in like_patterns:
        if match.group(2).startswith('%'):
            optimizations.append({
                "issue": "inefficient_like",
                "description": f"LIKE '%...%' pattern on column '{match.group(1)}' prevents index usage",
                "suggestion": "Avoid leading wildcards in LIKE patterns if possible or consider using full-text search"
            })
    
    # Check for lack of join conditions
    if re.search(r'\bJOIN\b', query, re.IGNORECASE):
        join_conditions = re.findall(r'JOIN\s+\w+\s+ON', query, re.IGNORECASE)
        joins = re.findall(r'\bJOIN\b', query, re.IGNORECASE)
        
        if len(join_conditions) < len(joins):
            optimizations.append({
                "issue": "missing_join_condition",
                "description": "Some JOINs may be missing explicit ON conditions",
                "suggestion": "Ensure all JOINs have explicit ON conditions"
            })
    
    return {
        "original_query": original_query,
        "optimized_query": optimized_query if optimizations else original_query,
        "optimizations": optimizations,
        "tables_columns": extract_tables_and_columns(query),
        "where_conditions": analyze_where_conditions(query),
        "order_by": analyze_order_by(query)
    } 