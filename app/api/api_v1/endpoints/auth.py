"""
Authentication endpoints for user registration and login.

This module handles user registration, login, token-based authentication,
refresh tokens, and logout functionality.
"""

from typing import Any
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import datetime

from app import models, schemas
from app.api import deps
from app.services import user_service
from app.utils.error_handling import handle_db_error
from app.core.security import REFRESH_TOKEN_COOKIE_NAME, get_refresh_token_from_request
from app.core.exception_handlers import (
    AuthenticationError, 
    InvalidInputError, 
    ResourceConflictError,
    DatabaseError
)

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/login/access-token", 
    response_model=schemas.Token,
    summary="Get access token (Legacy JWT method)"
)
def login_access_token(
    db: Session = Depends(deps.get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    This endpoint returns the token directly in the response for backward compatibility.
    New clients should use the cookie-based authentication method instead.
    
    Args:
        db: Database session
        form_data: OAuth2 form data containing username (email) and password
        
    Returns:
        JWT access token, refresh token, type, and expiration
        
    Raises:
        AuthenticationError: For invalid credentials or inactive users
    """
    try:
        # Authenticate user - will raise AuthenticationError if fails
        user = user_service.authenticate_user(db, form_data.username, form_data.password)
        
        # Generate tokens
        return user_service.generate_auth_token(user)
    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {str(e)}")
        handle_db_error(e, "login", "user")
    except Exception as e:
        logger.error(f"Error during access token login: {str(e)}")
        # Let the exception handlers handle the error
        raise


@router.post("/login", response_model=schemas.CookieTokenResponse)
def login(
    *,
    db: Session = Depends(deps.get_db),
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response,
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    Args:
        db: Database session
        form_data: OAuth2 form data with username (email) and password
        response: FastAPI response object
        
    Returns:
        Cookie token response
        
    Raises:
        AuthenticationError: If authentication fails
    """
    try:
        # This will raise AuthenticationError if authentication fails
        user = user_service.authenticate_user(
            db, email=form_data.username, password=form_data.password
        )
        
        # Generate tokens and set cookies
        return user_service.login_user(db, user, response)
    except Exception as e:
        logger.error(f"Error during login for user {form_data.username}: {str(e)}")
        # Let the exception handlers handle the error
        raise


@router.post("/refresh-token", response_model=schemas.AccessToken)
def refresh_token(
    *,
    db: Session = Depends(deps.get_db),
    request: Request,
    response: Response,
    token_data: schemas.TokenRefresh = None,
) -> Any:
    """
    Refresh access token.
    
    Args:
        db: Database session
        request: FastAPI request object
        response: FastAPI response object
        token_data: Optional refresh token data (if not provided, extract from cookie)
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid
    """
    # Get refresh token from cookie or request body
    refresh_token = None
    
    if token_data and token_data.refresh_token:
        # Token provided in request body
        refresh_token = token_data.refresh_token
    else:
        # Try to get token from cookie
        refresh_token = get_refresh_token_from_request(request)
    
    if not refresh_token:
        logger.warning("Refresh token request without token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    
    # Refresh token
    return user_service.refresh_auth_token(db, refresh_token, response)


@router.post("/logout")
def logout(
    *,
    db: Session = Depends(deps.get_db),
    request: Request,
    response: Response,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Logout current session.
    
    Args:
        db: Database session
        request: FastAPI request object
        response: FastAPI response object
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    # Get refresh token from cookie
    refresh_token = get_refresh_token_from_request(request)
    
    # Logout user
    return user_service.logout_user(db, refresh_token, response)


@router.post("/logout-all")
def logout_all(
    *,
    db: Session = Depends(deps.get_db),
    response: Response,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Logout all sessions for the current user.
    
    Args:
        db: Database session
        response: FastAPI response object
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    # Logout all sessions
    return user_service.logout_all_sessions(db, current_user.id, response)


@router.get("/me", response_model=schemas.User)
def read_users_me(
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get current user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current user information
    """
    return current_user


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_new_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Register a new user.
    
    Args:
        db: Database session
        user_in: User creation data
        
    Returns:
        Created user object
        
    Raises:
        ResourceConflictError: For existing users
        InvalidInputError: For validation errors
        DatabaseError: For database errors
    """
    try:
        # Create the user (validation is done inside the service)
        return user_service.create_user(db, user_in)
    except ValueError as e:
        # Log the error
        logger.error(f"Validation error during registration: {str(e)}")
        raise InvalidInputError(message=str(e))
    except Exception as e:
        # Log the error
        logger.error(f"Error during user registration: {str(e)}")
        # Let exception handlers handle it
        raise 