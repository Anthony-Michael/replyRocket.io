from datetime import datetime, timedelta
from typing import Any, Union, Optional
import logging
import re

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# Set up logger
logger = logging.getLogger(__name__)

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT algorithm
ALGORITHM = "HS256"

# Regular expression for password validation
# At least 8 chars, 1 uppercase, 1 lowercase, 1 number
PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token with additional security claims.
    
    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Custom expiration time, defaults to settings
        
    Returns:
        Encoded JWT token string
        
    Notes:
        Includes timestamp and jti (JWT ID) claims for additional security
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Current timestamp for iat (issued at) claim
    now = datetime.utcnow()
    
    # Build the token payload with additional security claims
    to_encode = {
        "exp": expire,                  # Expiration time
        "sub": str(subject),            # Subject (user ID)
        "iat": now,                     # Issued at time
        "nbf": now,                     # Not valid before time
        "jti": f"{now.timestamp()}-{subject}",  # JWT ID for uniqueness
        "iss": settings.PROJECT_NAME    # Issuer
    }
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation error: {str(e)}")
        raise


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generate a secure hash from a password.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Securely hashed password
    """
    return pwd_context.hash(password)


def validate_password_strength(password: str) -> bool:
    """
    Validate password strength using regex.
    
    Args:
        password: Password to validate
        
    Returns:
        True if password meets requirements, False otherwise
        
    Notes:
        Requires minimum 8 characters, uppercase, lowercase, 
        number, and special character
    """
    if len(password) < 8:
        return False
    
    # Simpler validation if regex match fails
    has_upper = any(char.isupper() for char in password)
    has_lower = any(char.islower() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_special = any(not char.isalnum() for char in password)
    
    return has_upper and has_lower and has_digit and has_special


def decode_and_validate_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload as dictionary
        
    Raises:
        JWTError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT validation error: {str(e)}")
        raise 