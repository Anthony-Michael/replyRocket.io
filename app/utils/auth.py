"""
Authentication utility functions for the ReplyRocket application.

This module contains authentication-related utility functions to reduce code
duplication and improve maintainability across the application.
"""

import logging
from datetime import timedelta
from typing import Any, Dict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core import security
from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)


def authenticate_user(db: Session, email: str, password: str) -> models.User:
    """
    Authenticate a user and verify active status.
    
    Args:
        db: Database session
        email: User's email address
        password: User's password
        
    Returns:
        User object if authentication succeeds
        
    Raises:
        HTTPException: For authentication failure or inactive user
    """
    # Authenticate user
    user = crud.user.authenticate(db, email=email, password=password)
    
    if not user:
        # Log failed login attempt
        logger.warning(f"Failed login attempt for email: {email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Inactive user account",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    logger.info(f"Successful login for user: {user.id}")
    return user


def generate_access_token(user_id: Any) -> str:
    """
    Generate a JWT access token for a user.
    
    Args:
        user_id: The ID of the user
        
    Returns:
        JWT token string
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return security.create_access_token(user_id, expires_delta=access_token_expires)


def create_token_response(token: str) -> Dict[str, str]:
    """
    Create the token response format.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with access_token and token_type
    """
    return {
        "access_token": token,
        "token_type": "bearer",
    }


def validate_registration_data(db: Session, user_in: schemas.UserCreate) -> None:
    """
    Validate user registration data.
    
    Args:
        db: Database session
        user_in: User creation data
        
    Raises:
        HTTPException: If email exists or password is weak
    """
    # Check if user with this email already exists
    check_email_not_taken(db, user_in.email)
    
    # Validate password strength
    validate_password_strength(user_in.password, user_in.email)


def check_email_not_taken(db: Session, email: str) -> None:
    """
    Check if an email is already registered.
    
    Args:
        db: Database session
        email: Email to check
        
    Raises:
        HTTPException: If email already exists
    """
    user = crud.user.get_by_email(db, email=email)
    if user:
        logger.warning(f"Registration attempt with existing email: {email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )


def validate_password_strength(password: str, email: str) -> None:
    """
    Validate that a password meets strength requirements.
    
    Args:
        password: Password to validate
        email: User's email (for logging)
        
    Raises:
        HTTPException: If password is too weak
    """
    if not security.validate_password_strength(password):
        logger.warning(f"Registration with weak password: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password does not meet security requirements. Must have at least 8 characters, "
                   "including uppercase, lowercase, numbers, and special characters.",
        )


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    """
    Create a new user in the database.
    
    Args:
        db: Database session
        user_in: User creation data
        
    Returns:
        The created user object
    """
    user = crud.user.create(db, obj_in=user_in)
    logger.info(f"New user registered: {user.id}")
    return user 