"""
Monitoring and error tracking configuration for the application.
This module sets up Sentry for error tracking and provides utilities for logging.
"""

import logging
import os
from typing import Any, Dict, Optional

import sentry_sdk
from fastapi import FastAPI, Request
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """
    Initialize Sentry SDK for error tracking and performance monitoring.
    Only activates if SENTRY_DSN is set in environment variables.
    """
    dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("ENVIRONMENT", "development")
    
    if not dsn:
        logger.info("Sentry DSN not set - error tracking is disabled")
        return

    # Configure Sentry SDK
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        # Set traces_sample_rate to 1.0 for development, lower in production
        traces_sample_rate=0.3 if environment == "production" else 1.0,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.INFO,        # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            ),
        ],
    )
    logger.info(f"Sentry initialized with environment: {environment}")


def setup_monitoring(app: FastAPI) -> None:
    """
    Set up monitoring for the FastAPI application.
    This sets up Sentry and configures middleware for request logging.

    Args:
        app: The FastAPI application instance
    """
    # Initialize Sentry
    init_sentry()
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Any) -> Any:
        """Log information about each request."""
        path = request.url.path
        method = request.method
        
        logger.info(f"Request: {method} {path}")
        response = await call_next(request)
        
        status_code = response.status_code
        logger.info(f"Response: {method} {path} - Status: {status_code}")
        
        return response


def capture_exception(exception: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """
    Capture an exception in Sentry with optional additional context.

    Args:
        exception: The exception to capture
        context: Optional dictionary with additional context data
    """
    if context:
        with sentry_sdk.configure_scope() as scope:
            for key, value in context.items():
                scope.set_extra(key, value)
    
    sentry_sdk.capture_exception(exception) 