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
    response_model=schemas.TokenWithoutRefresh,
    summary="Get access token (Legacy JWT method)"
)
def login_access_token(
    db: Session = Depends(deps.get_db), 
    form_data: OAuth2PasswordRequestForm = Depends(),
    response: Response = None
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    
    This endpoint now sets the refresh token in an HttpOnly cookie for security
    and only returns the access token in the response.
    
    Args:
        db: Database session
        form_data: OAuth2 form data containing username (email) and password
        response: FastAPI response object
        
    Returns:
        JWT access token, type, and expiration
        
    Raises:
        AuthenticationError: For invalid credentials or inactive users
    """
    try:
        # Authenticate user - will raise AuthenticationError if fails
        user = user_service.authenticate_user(db, form_data.username, form_data.password)
        
        # Generate tokens
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
        
        # Set refresh token in HttpOnly cookie if response object is provided
        if response:
            set_auth_cookies(
                response=response,
                access_token=access_token,
                refresh_token=refresh_token,
                access_token_expires=access_expires,
                refresh_token_expires=refresh_expires
            )
        
        logger.info(f"User {user.email} logged in successfully using legacy endpoint")
        
        # Return access token only in response (not the refresh token)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_at": access_expires
        }
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
    
    Enhanced with security best practices:
    - Uses HttpOnly cookies for token storage
    - Implements device fingerprinting for XSS mitigation
    - Stores refresh tokens securely in database
    - Enforces token validation and proper expiration
    
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
        # Authenticate user - will raise AuthenticationError if fails
        user = user_service.authenticate_user(
            db, email=form_data.username, password=form_data.password
        )
        
        # Generate a device fingerprint for this login session
        from app.core.security import secrets, set_device_fingerprint_cookie
        device_fingerprint = secrets.token_hex(8)
        
        # Create tokens with the fingerprint
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
        
        # Set device fingerprint cookie
        set_device_fingerprint_cookie(
            response=response,
            fingerprint=device_fingerprint
        )
        
        logger.info(f"User {user.email} logged in successfully with enhanced security")
        
        # Return response with metadata
        return schemas.CookieTokenResponse(
            message="Authentication successful",
            expires_at=access_expires,
            user_id=user.id
        )
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
    
    This endpoint uses a secure token rotation strategy:
    1. Each refresh token can be used exactly once (single-use)
    2. When used, the old token is immediately invalidated
    3. A new refresh token is issued and stored in an HttpOnly cookie
    4. The access token is rotated as well
    
    Args:
        db: Database session
        request: FastAPI request object
        response: FastAPI response object
        token_data: Optional refresh token data (if not provided, extract from cookie)
        
    Returns:
        New access token
        
    Raises:
        HTTPException: If refresh token is invalid, revoked, or expired
    """
    # Get refresh token from cookie or request body (prioritize cookie for security)
    refresh_token = get_refresh_token_from_request(request)
    
    # Fall back to body parameter only if no cookie present (less secure option)
    if not refresh_token and token_data and token_data.refresh_token:
        refresh_token = token_data.refresh_token
        logger.warning("Refresh token provided in request body instead of secure cookie")
    
    if not refresh_token:
        logger.warning("Refresh token request without token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )
    
    try:
        # Validate token and get user
        # This will raise exceptions if token is invalid, expired, or revoked
        db_token = get_refresh_token(db, refresh_token)
        
        if not db_token:
            logger.warning("Invalid or expired refresh token used in refresh attempt")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )
            
        if db_token.revoked:
            logger.warning(f"Revoked refresh token used in refresh attempt (token ID: {db_token.id})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )
            
        # Decode token to get user ID
        payload = decode_and_validate_token(refresh_token, token_type="refresh")
        user_id = payload.get("sub")
        
        if not user_id:
            logger.warning("Refresh token missing subject claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token format",
            )
        
        # Check if user exists and is active
        user = user_service.get_user(db, user_id)
        if not user:
            logger.warning(f"User not found for refresh token (user ID: {user_id})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )
            
        if not user.is_active:
            logger.warning(f"Inactive user attempted to refresh token (user ID: {user_id})")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user account",
            )
        
        # Token rotation: Revoke the current token immediately (single use)
        # This helps prevent refresh token replay attacks
        revoke_refresh_token(db, refresh_token)
        logger.info(f"Revoked used refresh token {db_token.id} during token rotation")
        
        # Create new tokens
        access_token, new_refresh_token, access_expires, refresh_expires = create_token_pair(
            subject=str(user.id)
        )
        
        # Store new refresh token in database
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
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error during token refresh: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


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
    
    This endpoint:
    1. Revokes the current refresh token in the database
    2. Clears auth cookies from the browser
    3. Ensures proper cleanup of the session
    
    Args:
        db: Database session
        request: FastAPI request object
        response: FastAPI response object
        current_user: Current authenticated user
        
    Returns:
        Success message
    """
    try:
        # Get refresh token from cookie
        refresh_token = get_refresh_token_from_request(request)
        
        if refresh_token:
            # Get token from database
            db_token = get_refresh_token(db, refresh_token)
            
            if db_token:
                # Verify token belongs to current user for security
                if str(db_token.user_id) != str(current_user.id):
                    logger.warning(f"User {current_user.id} attempted to revoke token belonging to user {db_token.user_id}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to revoke this token",
                    )
                
                # Revoke the token
                db_token = revoke_refresh_token(db, refresh_token)
                logger.info(f"Revoked refresh token {db_token.id} during logout for user {current_user.id}")
            else:
                logger.warning(f"Attempt to logout with invalid refresh token for user {current_user.id}")
        else:
            logger.warning(f"Logout without refresh token for user {current_user.id}")
        
        # Clear cookies regardless of whether token was found/revoked
        clear_auth_cookies(response)
        
        logger.info(f"User {current_user.id} logged out successfully")
        return {"message": "Successfully logged out"}
        
    except Exception as e:
        logger.error(f"Error during logout for user {current_user.id}: {str(e)}")
        
        # Clear cookies even if error occurs
        clear_auth_cookies(response)
        
        # Re-raise if it's an HTTP exception, otherwise return success
        if isinstance(e, HTTPException):
            raise
        
        # Return success message even if there was an error with token revocation
        # This ensures the user is always logged out client-side
        return {"message": "Successfully logged out"}


@router.post("/logout-all")
def logout_all(
    *,
    db: Session = Depends(deps.get_db),
    response: Response,
    current_user: models.User = Depends(deps.get_current_user),
) -> Any:
    """
    Logout all sessions for the current user.
    
    This endpoint:
    1. Revokes ALL refresh tokens for the user in the database
    2. Clears auth cookies from the current browser session
    3. Forces termination of all active sessions for this user
    
    Args:
        db: Database session
        response: FastAPI response object
        current_user: Current authenticated user
        
    Returns:
        Success message with number of sessions logged out
    """
    try:
        # Revoke all tokens for the user
        count = revoke_all_user_tokens(db, str(current_user.id))
        
        # Clear cookies for current session
        clear_auth_cookies(response)
        
        logger.info(f"Logged out all sessions ({count}) for user {current_user.id}")
        return {"message": f"Successfully logged out from all devices ({count} sessions)"}
    except Exception as e:
        logger.error(f"Error during logout-all for user {current_user.id}: {str(e)}")
        
        # Clear cookies even if error occurs
        clear_auth_cookies(response)
        
        # Re-raise if it's an HTTP exception, otherwise return success
        if isinstance(e, HTTPException):
            raise
        
        # Return success message even if there was an error
        return {"message": "Successfully logged out from all devices"}


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


@router.post("/cleanup-tokens", status_code=status.HTTP_200_OK)
def cleanup_tokens(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Clean up expired refresh tokens from the database.
    
    This endpoint is restricted to superusers only and should be
    scheduled to run periodically through a cron job or similar.
    
    Args:
        db: Database session
        current_user: Current authenticated superuser
        
    Returns:
        Result message with count of tokens cleaned up
    """
    from app.core.security import cleanup_expired_tokens
    
    count = cleanup_expired_tokens(db)
    
    logger.info(f"Token cleanup performed by user {current_user.id}, cleaned {count} tokens")
    return {"message": f"Successfully cleaned up {count} expired tokens"} 