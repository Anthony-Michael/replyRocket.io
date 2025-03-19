from typing import Generator
import logging
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)

# Create engine with enhanced connection pool configuration
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,  # Check connection validity before using from pool
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    # Echo SQL for debugging in development only
    echo=settings.DEBUG,
    # Use batch mode for more efficient execution
    execution_options={"stream_results": True}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Connection pool statistics
connection_pool_stats = {
    "checkouts": 0,
    "checkins": 0,
    "connections_created": 0,
    "connections_invalidated": 0,
    "connections_reused": 0,
    "checkout_time": 0,
    "last_checkout_time": 0,
}

# Enhanced SQLAlchemy engine event listeners for monitoring
@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    connection_pool_stats["connections_created"] += 1
    logger.debug(f"Database connection established (connection id: {id(dbapi_connection)})")

@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    connection_pool_stats["checkouts"] += 1
    connection_pool_stats["last_checkout_time"] = time.time()
    logger.debug(f"Database connection checked out from pool (connection id: {id(dbapi_connection)})")

@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    connection_pool_stats["checkins"] += 1
    if connection_pool_stats["last_checkout_time"] > 0:
        connection_pool_stats["checkout_time"] += time.time() - connection_pool_stats["last_checkout_time"]
        connection_pool_stats["last_checkout_time"] = 0
    logger.debug(f"Database connection returned to pool (connection id: {id(dbapi_connection)})")

@event.listens_for(engine, "reset")
def on_reset(dbapi_connection, connection_record):
    connection_pool_stats["connections_reused"] += 1
    logger.debug(f"Database connection reset (connection id: {id(dbapi_connection)})")

@event.listens_for(engine, "invalidate")
def on_invalidate(dbapi_connection, connection_record, exception):
    connection_pool_stats["connections_invalidated"] += 1
    logger.warning(f"Database connection invalidated (connection id: {id(dbapi_connection)}, reason: {exception})")

def get_db() -> Generator:
    """
    Get a database session.
    
    This function should be used with FastAPI Depends() to ensure
    proper session handling in endpoint functions.
    
    Yields:
        Active database session that is automatically closed when done
    """
    db = SessionLocal()
    try:
        logger.debug("Database session started")
        yield db
    except Exception as e:
        logger.error(f"Exception occurred while using database session: {str(e)}")
        db.rollback()
        raise
    finally:
        logger.debug("Database session closed")
        db.close()

@contextmanager
def get_db_context():
    """
    Context manager for database sessions outside of API endpoints.
    
    For use in background tasks, scripts, and other non-endpoint contexts
    where FastAPI dependency injection can't be used.
    
    Example:
        with get_db_context() as db:
            users = db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Exception in database context: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

class SessionManager:
    """Context manager for database sessions."""
    
    def __init__(self, context: str = "unknown"):
        """
        Initialize the session manager.
        
        Args:
            context: A string describing where this session is used
        """
        self.context = context
        self.db = None
    
    def __enter__(self) -> Session:
        """Create and return a new database session."""
        self.db = SessionLocal()
        logger.debug(f"Database session created in context: {self.context}")
        return self.db
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the database session."""
        if self.db:
            try:
                if exc_type:
                    # Rollback the session if there was an exception
                    logger.warning(f"Rolling back session due to exception in {self.context}: {exc_val}")
                    self.db.rollback()
                self.db.close()
                logger.debug(f"Database session closed in context: {self.context}")
            except Exception as e:
                logger.error(f"Error while closing session: {str(e)}")
                # Try to close forcefully
                try:
                    self.db.close()
                except:
                    pass

def get_pool_status():
    """Get status information about the connection pool."""
    if hasattr(engine.pool, "status"):
        status = engine.pool.status()
    else:
        status = "Pool size: %d  Connections in pool: %d Current overflow: %d" % (
            engine.pool.size(),
            engine.pool.checkedin(),
            engine.pool.overflow()
        )
    
    return {
        "pool_status": status,
        "stats": connection_pool_stats,
        "settings": {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
        }
    } 