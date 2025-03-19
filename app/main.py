"""
Main module for the ReplyRocket API.

This module creates and configures the FastAPI application.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.utils.db_monitor import setup_query_timing
from app.utils.query_cache import setup_automatic_invalidation
from app.api.deps import get_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager for setup and teardown.
    
    Performs initialization tasks when the application starts up,
    and cleanup when it shuts down.
    """
    # Startup: initialize services and monitoring
    logger.info("Application starting up...")
    
    # Set up database query monitoring
    setup_query_timing()
    logger.info("Database query monitoring initialized")
    
    # Set up query cache invalidation
    # This requires a database session, which we'll get from the first request
    
    # Any other startup tasks
    
    yield  # Application runs here
    
    # Shutdown: perform cleanup
    logger.info("Application shutting down...")
    
    # Any cleanup tasks
    
    logger.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API for the ReplyRocket email automation platform",
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exception handlers
register_exception_handlers(app)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """
    Root endpoint providing basic API information.
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/api/docs",
    }


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """
    Middleware to handle database sessions and exceptions.
    
    Ensures that database sessions are properly closed even if
    exceptions occur during request processing.
    """
    try:
        response = await call_next(request)
        return response
    except SQLAlchemyError as e:
        logger.error(f"Database error in request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Database error occurred", "type": "database_error"}
        )
    except Exception as e:
        logger.error(f"Unhandled error in request: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": "server_error"}
        )


# Set up cache invalidation on the first request
@app.middleware("http")
async def initialize_cache_invalidation(request: Request, call_next):
    """
    Middleware to initialize cache invalidation on the first request.
    
    This is needed because we need a database session to set up the
    cache invalidation, which isn't available during the startup phase.
    """
    # Check if cache invalidation is already initialized
    if not getattr(app.state, "cache_invalidation_initialized", False):
        # Get database session
        try:
            db_generator = get_db()
            db = next(db_generator)
            
            # Set up cache invalidation
            setup_automatic_invalidation(db)
            
            # Mark as initialized
            app.state.cache_invalidation_initialized = True
            logger.info("Query cache invalidation initialized")
            
            # Clean up the database session
            try:
                next(db_generator, None)
            except StopIteration:
                pass
            
        except Exception as e:
            logger.error(f"Failed to initialize cache invalidation: {str(e)}")
    
    # Continue with the request
    return await call_next(request) 