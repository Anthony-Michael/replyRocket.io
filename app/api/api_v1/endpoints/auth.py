"""
Authentication endpoints for user registration and login.

This module handles user registration, login, and token-based authentication.
"""

from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.utils.auth_utils import (
    authenticate_user, 
    generate_access_token, 
    create_token_response,
    validate_registration_data,
    create_user
)
from app.utils.error_handling import handle_db_error

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login/access-token", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    Args:
        db: Database session
        form_data: OAuth2 form data containing username (email) and password
        
    Returns:
        JWT access token and type
        
    Raises:
        HTTPException: For invalid credentials or inactive users
    """
    try:
        # Authenticate user and check status
        user = authenticate_user(db, form_data.username, form_data.password)
        
        # Generate token
        token = generate_access_token(user.id)
        
        # Return token response
        return create_token_response(token)
    except SQLAlchemyError as e:
        handle_db_error(e, "login", "user")
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error during login: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred",
            )
        raise


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_new_user(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Create new user with input validation.
    
    Args:
        db: Database session
        user_in: User creation data
        
    Returns:
        Created user object
        
    Raises:
        HTTPException: For validation errors or existing users
    """
    try:
        # Validate registration data
        validate_registration_data(db, user_in)
        
        # Create the user
        return create_user(db, user_in)
    except SQLAlchemyError as e:
        handle_db_error(e, "registration", "user")
    except ValueError as e:
        logger.error(f"Validation error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error during registration: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred",
            )
        raise 