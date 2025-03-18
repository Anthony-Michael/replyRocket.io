"""
Initial data setup script for ReplyRocket.io.

This script is used to create the initial superuser when the application starts
for the first time. It's intended to be run from the Docker entrypoint.
"""

import logging
import os
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_superuser(db: Session) -> None:
    """
    Create an initial superuser if it doesn't already exist.
    
    Uses environment variables FIRST_SUPERUSER_EMAIL and FIRST_SUPERUSER_PASSWORD.
    Will not create the user if it already exists.
    """
    email = settings.FIRST_SUPERUSER_EMAIL
    password = settings.FIRST_SUPERUSER_PASSWORD
    
    if not email or not password:
        logger.info("Superuser email or password not set in environment variables. Skipping initial superuser creation.")
        return
    
    # Check if user already exists
    user = db.query(User).filter(User.email == email).first()
    if user:
        logger.info(f"Superuser {email} already exists. Skipping creation.")
        return
    
    # Create the superuser
    try:
        user_in = User(
            email=email,
            hashed_password=get_password_hash(password),
            is_active=True,
            is_superuser=True,
            full_name="Initial Superuser"
        )
        db.add(user_in)
        db.commit()
        logger.info(f"Initial superuser {email} created successfully.")
    except Exception as e:
        logger.error(f"Error creating superuser: {e}")
        db.rollback()
        raise


def main() -> None:
    """
    Entry point for the script. Sets up initial data.
    """
    logger.info("Creating initial data...")
    db = SessionLocal()
    try:
        init_superuser(db)
        logger.info("Initial data setup complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main() 