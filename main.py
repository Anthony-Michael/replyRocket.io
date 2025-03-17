"""
Main application module for the ReplyRocket API.

This module initializes the FastAPI application, configures middleware,
sets up exception handlers, includes API routes, and initializes monitoring.
"""

# Standard library imports
import logging
from typing import Any, Dict

# Third-party imports
import uvicorn
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

# Application imports
from app.core.config import settings
from app.api.api_v1.api import api_router
from app.core.auth import get_current_active_user
from app.core.monitoring import setup_monitoring, capture_exception

# Set up logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="AI-Powered Cold Email Automation SaaS API",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up monitoring (Sentry)
setup_monitoring(app)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handlers for consistent error responses
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle validation errors from request data.
    
    Args:
        request: The incoming request that failed validation
        exc: The validation error exception
        
    Returns:
        A 422 Unprocessable Entity response with detailed error information
    """
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "body": exc.body},
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    Handle database-related errors.
    
    Args:
        request: The incoming request that caused the database error
        exc: The SQLAlchemy error exception
        
    Returns:
        A 500 Internal Server Error response with generic error message
    """
    logger.error(f"Database error: {str(exc)}", exc_info=True)
    # Capture exception in Sentry with additional context
    capture_exception(exc, {"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal database error occurred. Please try again later."},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all other exceptions that aren't caught by more specific handlers.
    
    Args:
        request: The incoming request that caused the exception
        exc: The exception that was raised
        
    Returns:
        A 500 Internal Server Error response
    """
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    # Capture exception in Sentry with additional context
    capture_exception(exc, {"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Our team has been notified."},
    )


# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Execute tasks when the application starts up."""
    logger.info("Application startup: ReplyRocket API is running")


@app.on_event("shutdown")
async def shutdown_event():
    """Execute tasks when the application is shutting down."""
    logger.info("Application shutdown: ReplyRocket API is shutting down")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 