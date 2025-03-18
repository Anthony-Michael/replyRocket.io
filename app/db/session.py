from typing import Generator
import logging

from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)

# Create engine with connection pool configuration
engine = create_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# SQLAlchemy engine event listeners for monitoring
@event.listens_for(engine, "connect")
def on_connect(dbapi_connection, connection_record):
    logger.debug("Database connection established")


@event.listens_for(engine, "checkout")
def on_checkout(dbapi_connection, connection_record, connection_proxy):
    logger.debug("Database connection checked out from pool")


@event.listens_for(engine, "checkin")
def on_checkin(dbapi_connection, connection_record):
    logger.debug("Database connection returned to pool")


def get_db() -> Generator:
    """
    Get a database session.
    """
    db = SessionLocal()
    try:
        logger.debug("Database session started")
        yield db
    finally:
        logger.debug("Database session closed")
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
        from app.utils.db_monitor import SessionTracker
        
        self.db = SessionLocal()
        return SessionTracker(self.db, self.context).__enter__()
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the database session."""
        if self.db:
            try:
                if exc_type:
                    # Rollback the session if there was an exception
                    logger.warning(f"Rolling back session due to exception: {exc_val}")
                    self.db.rollback()
                self.db.close()
            except Exception as e:
                logger.error(f"Error while closing session: {str(e)}")
                # Try to close forcefully
                try:
                    self.db.close()
                except:
                    pass 