"""
API endpoint dependencies.

This module provides dependency injections for API endpoints,
including database sessions and authentication verification.
"""

import logging
from typing import Generator, Optional

from fastapi import Depends, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.config import settings
from app.core.security import decode_and_validate_token
from app.db.session import SessionLocal
from app.services.user_service import get_user
from app.core.exception_handlers import AuthenticationError, PermissionDeniedError

# Set up logger
logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,  # Don't auto-raise errors for cookie-based auth
)


def get_db() -> Generator:
    """
    Get a database session.
    
    Yields:
        Active database session
    """
    db = SessionLocal()
    logger.debug("Creating new database session")
    try:
        yield db
    except Exception as e:
        logger.error(f"Exception occurred while using database session: {str(e)}")
        raise
    finally:
        logger.debug("Closing database session")
        db.close()


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Get token from request (Authorization header or cookie).
    
    Args:
        request: FastAPI request object
        
    Returns:
        Token string or None if not found
    """
    # Try to get from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    
    # Try to get from cookie
    return request.cookies.get("access_token")


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
) -> models.User:
    """
    Get current authenticated user.
    
    Args:
        request: FastAPI request object
        db: Database session
        token: OAuth2 token (optional)
        
    Returns:
        Current authenticated user
        
    Raises:
        AuthenticationError: If authentication fails
    """
    # Get token from request if not provided via OAuth2
    if not token:
        token = get_token_from_request(request)
    
    if not token:
        logger.warning("Authentication required but no token provided")
        raise AuthenticationError(
            message="Not authenticated",
            error_type="missing_token"
        )
    
    try:
        # Decode and validate token
        payload = decode_and_validate_token(token, token_type="access")
        user_id = payload.get("sub")
        
        if not user_id:
            logger.warning("Token missing subject claim")
            raise AuthenticationError(
                message="Invalid token",
                error_type="invalid_token"
            )
        
        # Get user from database
        user = get_user(db, user_id)
        if not user:
            logger.warning(f"User {user_id} from token not found in database")
            raise AuthenticationError(
                message="Invalid credentials",
                error_type="invalid_user"
            )
        
        return user
    
    except (JWTError, ValidationError) as e:
        logger.warning(f"Token validation error: {str(e)}")
        raise AuthenticationError(
            message="Could not validate credentials",
            error_type="token_validation_error",
            details={"error": str(e)}
        )
    except Exception as e:
        if not isinstance(e, AuthenticationError):
            logger.error(f"Unexpected error in authentication: {str(e)}")
            raise AuthenticationError(
                message="Authentication error",
                error_type="unexpected_error",
                details={"error": str(e)}
            )
        raise


def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    Get current active user.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        Current active user
        
    Raises:
        PermissionDeniedError: If user is inactive
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user {current_user.id} attempted to access a protected endpoint")
        raise PermissionDeniedError(
            message="Inactive user",
            details={"user_id": str(current_user.id)}
        )
    
    return current_user


def get_current_superuser(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    Get current superuser.
    
    Args:
        current_user: Current active user
        
    Returns:
        Current superuser
        
    Raises:
        PermissionDeniedError: If user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser {current_user.id} attempted to access a superuser endpoint")
        raise PermissionDeniedError(
            message="The user doesn't have enough privileges",
            details={"user_id": str(current_user.id)}
        )
    
    return current_user


def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    """
    Check if the current user is a superuser.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        The current superuser
        
    Raises:
        PermissionDeniedError: If user is not a superuser
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser {current_user.id} attempted to access a superuser endpoint")
        raise PermissionDeniedError(
            message="The user doesn't have enough privileges",
            details={"user_id": str(current_user.id)}
        )
    return current_user 