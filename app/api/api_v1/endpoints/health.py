"""
Health check endpoints for monitoring application status.
"""

from datetime import datetime
import logging
from typing import Dict, Any
import time

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.config import settings
from app.db.session import get_db, get_pool_status

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Perform a health check on the API and its dependencies.
    
    This endpoint:
    1. Verifies the API is running
    2. Checks database connectivity
    3. Returns API version and environment information
    
    Returns:
        Dict with status and version information
    """
    # Check database connectivity
    start_time = time.time()
    try:
        # Execute a simple query to check DB connection
        db.execute(text("SELECT 1")).fetchall()
        db_status = "healthy"
        db_response_time = time.time() - start_time
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
        db_response_time = -1
    
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": {
                "status": db_status,
                "response_time_ms": round(db_response_time * 1000, 2) if db_response_time >= 0 else None
            }
        }
    }


@router.get("/health/db", status_code=status.HTTP_200_OK)
def db_health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Perform an extended database health check with detailed pool information.
    
    This endpoint:
    1. Verifies database connectivity
    2. Returns connection pool statistics
    3. Provides database configuration information
    
    Returns:
        Dict with detailed database health information
    """
    # Check database connectivity
    start_time = time.time()
    try:
        # Execute a simple query to check DB connection
        result = db.execute(text("SELECT 1")).fetchall()
        db_status = "healthy"
        db_response_time = time.time() - start_time
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
        db_response_time = -1
        result = None
    
    # Get connection pool statistics
    pool_info = get_pool_status()
    
    return {
        "status": db_status,
        "timestamp": datetime.utcnow().isoformat(),
        "response_time_ms": round(db_response_time * 1000, 2) if db_response_time >= 0 else None,
        "pool": pool_info,
        "connection_type": settings.SQLALCHEMY_DATABASE_URI.split("://")[0] if settings.SQLALCHEMY_DATABASE_URI else None,
        "environment": settings.ENVIRONMENT
    }


@router.get("/health/readiness", status_code=status.HTTP_200_OK)
def readiness_check() -> Dict[str, str]:
    """
    Readiness check endpoint for Kubernetes/container orchestration.
    
    This is a lightweight check that verifies the application is ready to
    accept traffic. It doesn't verify dependencies like the main health check.
    
    Returns:
        Simple status response
    """
    return {"status": "ready"} 