"""
Health check endpoints for monitoring application status.
"""

from datetime import datetime
import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

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
    try:
        # Execute a simple query to check DB connection
        db.execute("SELECT 1").fetchall()
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "unhealthy"
    
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "dependencies": {
            "database": db_status
        }
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