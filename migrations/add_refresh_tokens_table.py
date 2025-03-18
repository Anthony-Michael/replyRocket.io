"""
Migration script to add refresh token table.

Run this script to add the refresh token table to the database.
"""

import logging
import sys
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL from environment or use default
DB_URL = sys.argv[1] if len(sys.argv) > 1 else "postgresql://postgres:password@localhost/replyrocket"

# Create SQLAlchemy engine and session
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# Define RefreshToken model for migration
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def create_refresh_tokens_table():
    """Create the refresh_tokens table."""
    try:
        # Create table
        RefreshToken.__table__.create(engine)
        logger.info("Successfully created refresh_tokens table")
        return True
    except Exception as e:
        logger.error(f"Error creating refresh_tokens table: {e}")
        return False


if __name__ == "__main__":
    logger.info("Starting migration to add refresh_tokens table")
    
    if create_refresh_tokens_table():
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration failed")
        sys.exit(1) 