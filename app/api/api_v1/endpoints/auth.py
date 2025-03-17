from datetime import timedelta
from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core import security
from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/login/access-token", response_model=schemas.Token)
def login_access_token(
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
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
        # Authenticate user
        user = crud.user.authenticate(
            db, email=form_data.username, password=form_data.password
        )
        
        if not user:
            # Log failed login attempt
            logger.warning(f"Failed login attempt for email: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Inactive user account",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Generate access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        token = security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
        
        # Log successful login
        logger.info(f"Successful login for user: {user.id}")
        
        return {
            "access_token": token,
            "token_type": "bearer",
        }
    except SQLAlchemyError as e:
        logger.error(f"Database error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during login",
        )
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


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
        # Check if user with this email already exists
        user = crud.user.get_by_email(db, email=user_in.email)
        if user:
            logger.warning(f"Registration attempt with existing email: {user_in.email}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )
        
        # Validate password strength
        if not security.validate_password_strength(user_in.password):
            logger.warning(f"Registration with weak password: {user_in.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password does not meet security requirements. Must have at least 8 characters, "
                       "including uppercase, lowercase, numbers, and special characters.",
            )
        
        # Validate email format (already done by Pydantic)
        # Create new user
        user = crud.user.create(db, obj_in=user_in)
        logger.info(f"New user registered: {user.id}")
        
        return user
    except SQLAlchemyError as e:
        logger.error(f"Database error during registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred during registration",
        )
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