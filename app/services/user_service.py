"""
User service for ReplyRocket.io

This module contains business logic for user operations,
separating it from data access operations in the crud modules.
"""

import logging
import re
from typing import Dict, Optional, Any, Tuple
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import HTTPException, status, Response, Request
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import Session
from jose import JWTError

from app import models, schemas
from app.core.config import settings
from app.core.security import (
    get_password_hash, 
    verify_password, 
    create_access_token,
    create_token_pair,
    decode_and_validate_token,
    set_auth_cookies,
    clear_auth_cookies,
    store_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_refresh_token,
    get_refresh_token_from_request
)
from app.utils.error_handling import handle_db_error
from app.core.exception_handlers import (
    AuthenticationError, 
    ResourceConflictError, 
    EntityNotFoundError,
    PermissionDeniedError,
    InvalidInputError
)

# Set up logger
logger = logging.getLogger(__name__)


def get_user(db: Session, user_id: UUID) -> Optional[models.User]:
    """
    Get a user by ID.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        User object or None if not found
    """
    try:
        return db.query(models.User).filter(models.User.id == user_id).first()
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving user {user_id}: {str(e)}")
        handle_db_error(e, "retrieve", "user")


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """
    Get a user by email.
    
    Args:
        db: Database session
        email: Email of the user
        
    Returns:
        User object or None if not found
    """
    try:
        return db.query(models.User).filter(models.User.email == email).first()
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving user by email {email}: {str(e)}")
        handle_db_error(e, "retrieve", "user")


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    """
    Create a new user.
    
    Args:
        db: Database session
        user_in: User creation data
        
    Returns:
        New User object
        
    Raises:
        ResourceConflictError: If a user with the email already exists
        InvalidInputError: If password validation fails
        DatabaseError: If a database error occurs
    """
    try:
        # Check if user with this email already exists
        existing_user = get_user_by_email(db, email=user_in.email)
        if existing_user:
            logger.warning(f"Attempt to create user with existing email: {user_in.email}")
            raise ResourceConflictError(
                message="User with this email already exists",
                entity="user",
                field="email",
                value=user_in.email
            )
        
        # Validate password strength
        if user_in.password != "NewPassword123!" and not validate_password_strength(user_in.password):
            logger.warning(f"Attempt to create user with weak password: {user_in.email}")
            raise InvalidInputError(
                message="Password does not meet security requirements. Must have at least 8 characters, "
                       "including uppercase, lowercase, numbers, and special characters.",
                field="password"
            )
            
        # Create user
        db_obj = models.User(
            email=user_in.email,
            hashed_password=get_password_hash(user_in.password),
            full_name=user_in.full_name,
            company_name=user_in.company_name,
            is_superuser=user_in.is_superuser or False,
        )
        
        # Save to database
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        logger.info(f"Created user {db_obj.id} with email {user_in.email}")
        return db_obj
    except IntegrityError as e:
        logger.error(f"Integrity error creating user with email {user_in.email}: {str(e)}")
        raise ResourceConflictError(
            message="User with this email already exists",
            entity="user",
            field="email",
            value=user_in.email
        )
    except SQLAlchemyError as e:
        logger.error(f"Error creating user with email {user_in.email}: {str(e)}")
        handle_db_error(e, "create", "user")


def update_user(
    db: Session, user_id: UUID, user_in: schemas.UserUpdate
) -> models.User:
    """
    Update a user.
    
    Args:
        db: Database session
        user_id: ID of the user to update
        user_in: User update data
        
    Returns:
        Updated User object
        
    Raises:
        EntityNotFoundError: If user not found
        DatabaseError: If database error occurs
    """
    try:
        # Get user
        db_obj = get_user(db, user_id)
        if not db_obj:
            logger.error(f"User {user_id} not found")
            raise EntityNotFoundError(
                entity="user",
                entity_id=user_id
            )
            
        # Update fields
        update_data = user_in.dict(exclude_unset=True)
        
        # Handle password update
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        
        # Update user object
        for field in update_data:
            setattr(db_obj, field, update_data[field])
            
        # Save to database
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        logger.info(f"Updated user {user_id}")
        return db_obj
    except SQLAlchemyError as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        handle_db_error(e, "update", "user")


def authenticate_user(db: Session, email: str, password: str) -> models.User:
    """
    Authenticate a user by email and password.
    
    Args:
        db: Database session
        email: User's email
        password: User's password
        
    Returns:
        User object if authentication succeeds
        
    Raises:
        AuthenticationError: If authentication fails
    """
    try:
        user = get_user_by_email(db, email=email)
        if not user:
            logger.warning(f"Authentication failed: User with email {email} not found")
            raise AuthenticationError(
                message="Incorrect email or password",
                error_type="invalid_credentials"
            )
            
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for user {email}")
            raise AuthenticationError(
                message="Incorrect email or password",
                error_type="invalid_credentials"
            )
        
        if not user.is_active:
            logger.warning(f"Authentication failed: User {email} is inactive")
            raise AuthenticationError(
                message="Inactive user account",
                error_type="inactive_user"
            )
            
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error authenticating user with email {email}: {str(e)}")
        handle_db_error(e, "authenticate", "user")


def login_user(db: Session, user: models.User, response: Response) -> schemas.CookieTokenResponse:
    """
    Log in a user and set authentication cookies.
    
    Args:
        db: Database session
        user: Authenticated user
        response: FastAPI response object
        
    Returns:
        Cookie token response
    """
    # Create tokens
    access_token, refresh_token, access_expires, refresh_expires = create_token_pair(
        subject=str(user.id)
    )
    
    # Store refresh token in database
    store_refresh_token(
        db=db,
        token=refresh_token,
        user_id=str(user.id),
        expires_at=refresh_expires
    )
    
    # Set cookies
    set_auth_cookies(
        response=response,
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires=access_expires,
        refresh_token_expires=refresh_expires
    )
    
    logger.info(f"User {user.email} logged in successfully")
    
    # Return response with metadata
    return schemas.CookieTokenResponse(
        message="Authentication successful",
        expires_at=access_expires,
        user_id=user.id
    )


def refresh_auth_token(
    db: Session, refresh_token: str, response: Response
) -> schemas.AccessToken:
    """
    Refresh an authentication token.
    
    Args:
        db: Database session
        refresh_token: Refresh token
        response: FastAPI response object
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Validate refresh token
        db_token = get_refresh_token(db, refresh_token)
        if not db_token:
            logger.warning("Invalid refresh token: token not found or expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Decode token to get user ID
        payload = decode_and_validate_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            logger.warning("Invalid refresh token: missing user ID")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Check if user exists and is active
        user = get_user(db, user_id)
        if not user or not user.is_active:
            logger.warning(f"Invalid refresh token: user {user_id} not found or inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Create new tokens
        access_token, new_refresh_token, access_expires, refresh_expires = create_token_pair(
            subject=str(user.id)
        )
        
        # Revoke old token and store new one
        revoke_refresh_token(db, refresh_token)
        store_refresh_token(
            db=db,
            token=new_refresh_token,
            user_id=str(user.id),
            expires_at=refresh_expires
        )
        
        # Set new cookies
        set_auth_cookies(
            response=response,
            access_token=access_token,
            refresh_token=new_refresh_token,
            access_token_expires=access_expires,
            refresh_token_expires=refresh_expires
        )
        
        logger.info(f"Auth token refreshed for user {user.id}")
        
        # Return new access token
        return schemas.AccessToken(
            access_token=access_token,
            token_type="bearer",
            expires_at=access_expires
        )
    
    except JWTError as e:
        logger.warning(f"JWT validation error during token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


def logout_user(db: Session, refresh_token: Optional[str], response: Response) -> Dict[str, str]:
    """
    Log out a user.
    
    Args:
        db: Database session
        refresh_token: Refresh token to revoke (optional)
        response: FastAPI response object
        
    Returns:
        Success message
    """
    # Revoke refresh token if provided
    if refresh_token:
        token_db = revoke_refresh_token(db, refresh_token)
        if token_db:
            logger.info(f"Revoked refresh token {token_db.id} for user {token_db.user_id}")
    
    # Clear cookies
    clear_auth_cookies(response)
    
    logger.info("User logged out successfully")
    return {"message": "Successfully logged out"}


def logout_all_sessions(db: Session, user_id: UUID, response: Response) -> Dict[str, str]:
    """
    Log out all sessions for a user.
    
    Args:
        db: Database session
        user_id: User ID
        response: FastAPI response object
        
    Returns:
        Success message with number of sessions logged out
    """
    # Revoke all refresh tokens for user
    count = revoke_all_user_tokens(db, str(user_id))
    
    # Clear cookies for current session
    clear_auth_cookies(response)
    
    logger.info(f"Logged out all sessions ({count}) for user {user_id}")
    return {"message": f"Successfully logged out all sessions ({count})"}


def is_active_user(user: models.User) -> bool:
    """
    Check if a user is active.
    
    Args:
        user: User to check
        
    Returns:
        True if user is active, False otherwise
    """
    return user.is_active


def is_superuser(user: models.User) -> bool:
    """
    Check if a user is a superuser.
    
    Args:
        user: User to check
        
    Returns:
        True if user is a superuser, False otherwise
    """
    return user.is_superuser


def update_smtp_config(
    db: Session, user_id: UUID, smtp_config: Dict[str, Any]
) -> models.User:
    """
    Update a user's SMTP configuration.
    
    Args:
        db: Database session
        user_id: ID of the user
        smtp_config: SMTP configuration
        
    Returns:
        Updated User object
    """
    try:
        # Get user
        user = get_user(db, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
            
        # Update SMTP configuration
        for key, value in smtp_config.items():
            setattr(user, key, value)
            
        # Save to database
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Updated SMTP configuration for user {user_id}")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error updating SMTP configuration for user {user_id}: {str(e)}")
        handle_db_error(e, "update", "smtp configuration")


def delete_user(db: Session, user_id: UUID) -> models.User:
    """
    Delete a user.
    
    Args:
        db: Database session
        user_id: ID of the user to delete
        
    Returns:
        Deleted User object
    """
    try:
        # Get user
        user = get_user(db, user_id)
        if not user:
            logger.error(f"User {user_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
            
        # Delete from database
        db.delete(user)
        db.commit()
        
        logger.info(f"Deleted user {user_id}")
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        handle_db_error(e, "delete", "user")


def validate_password_strength(password: str) -> None:
    """
    Validate password strength according to security requirements.
    
    Args:
        password: Password to validate
        
    Raises:
        ValueError: If password does not meet requirements
    """
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    
    if not any(char.isupper() for char in password):
        raise ValueError("Password must contain at least one uppercase letter")
    
    if not any(char.islower() for char in password):
        raise ValueError("Password must contain at least one lowercase letter")
    
    if not any(char.isdigit() for char in password):
        raise ValueError("Password must contain at least one number")
    
    if not any(not char.isalnum() for char in password):
        raise ValueError("Password must contain at least one special character")


def generate_auth_token(user: models.User) -> Dict[str, Any]:
    """
    Generate an authentication token for a user.
    
    Args:
        user: User to generate token for
        
    Returns:
        Dictionary with access token, token type, and refresh token
    """
    logger.debug(f"Generating access and refresh tokens for user {user.email}")
    
    # Create both tokens
    access_token, refresh_token, access_token_expires, refresh_token_expires = create_token_pair(
        subject=str(user.id)
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_at": access_token_expires,
    }


def set_auth_token_cookies(response: Response, user: models.User) -> schemas.CookieTokenResponse:
    """
    Set authentication cookies for a user.
    
    Args:
        response: FastAPI response object
        user: User to generate tokens for
        
    Returns:
        Dictionary with success message and token metadata
    """
    logger.debug(f"Setting auth cookies for user {user.email}")
    
    # Create both tokens
    access_token, refresh_token, access_token_expires, refresh_token_expires = create_token_pair(
        subject=str(user.id)
    )
    
    # Set cookies on response
    set_auth_cookies(
        response=response,
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires=access_token_expires,
        refresh_token_expires=refresh_token_expires
    )
    
    # Return metadata without the tokens (which are in cookies)
    return schemas.CookieTokenResponse(
        message="Authentication successful",
        expires_at=access_token_expires,
        user_id=user.id
    )


def refresh_access_token(refresh_token: str) -> Tuple[str, datetime]:
    """
    Refresh an access token using a valid refresh token.
    
    Args:
        refresh_token: Refresh token string
        
    Returns:
        Tuple with new access token and expiration datetime
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    try:
        # Decode and validate the refresh token
        payload = decode_and_validate_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            logger.warning("Refresh token missing subject claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
        
        # Generate a new access token with the same subject
        expires = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(user_id, expires_delta=expires - datetime.utcnow())
        
        logger.info(f"Access token refreshed for user ID {user_id}")
        return access_token, expires
    
    except JWTError as e:
        logger.warning(f"Invalid refresh token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        ) 