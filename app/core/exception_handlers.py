"""
Custom exceptions and exception handlers for ReplyRocket.io.

This module provides:
1. Custom exception classes for different error scenarios
2. FastAPI exception handlers to convert these exceptions to HTTP responses
3. Utility functions for consistent error handling
"""

import logging
from typing import Any, Dict, Optional, Type, Union, List

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

# Setup logger
logger = logging.getLogger(__name__)


class BaseReplyRocketException(Exception):
    """Base exception for all custom ReplyRocket exceptions."""
    
    def __init__(
        self, 
        message: str, 
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details
        super().__init__(self.message)


class DatabaseError(BaseReplyRocketException):
    """Exception raised for database-related errors."""
    
    def __init__(
        self, 
        message: str, 
        operation: str,
        entity: str,
        original_error: Optional[Exception] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        self.entity = entity
        self.original_error = original_error
        super().__init__(
            message=message, 
            status_code=status_code,
            error_code="DatabaseError",
            details=details or {
                "operation": operation,
                "entity": entity,
                "error_type": type(original_error).__name__ if original_error else None
            }
        )


class EntityNotFoundError(BaseReplyRocketException):
    """Exception raised when a requested entity is not found."""
    
    def __init__(
        self, 
        entity: str, 
        entity_id: Optional[Any] = None,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.entity = entity
        self.entity_id = entity_id
        
        if not message:
            message = f"{entity.capitalize()} not found"
            if entity_id:
                message += f" (ID: {entity_id})"
                
        super().__init__(
            message=message, 
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="EntityNotFound",
            details=details or {"entity": entity, "entity_id": entity_id}
        )


class PermissionDeniedError(BaseReplyRocketException):
    """Exception raised when a user doesn't have required permissions."""
    
    def __init__(
        self, 
        message: str = "Not enough permissions",
        entity: Optional[str] = None,
        entity_id: Optional[Any] = None,
        user_id: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.entity = entity
        self.entity_id = entity_id
        self.user_id = user_id
        
        super().__init__(
            message=message, 
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PermissionDenied",
            details=details or {
                "entity": entity,
                "entity_id": entity_id,
                "user_id": user_id
            }
        )


class AuthenticationError(BaseReplyRocketException):
    """Exception raised for authentication failures."""
    
    def __init__(
        self, 
        message: str = "Authentication failed",
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_type = error_type
        
        super().__init__(
            message=message, 
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AuthenticationError",
            details=details or {"error_type": error_type}
        )


class InvalidInputError(BaseReplyRocketException):
    """Exception raised for validation errors in input data."""
    
    def __init__(
        self, 
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.field = field
        self.value = value
        
        super().__init__(
            message=message, 
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="InvalidInput",
            details=details or {"field": field, "value": value}
        )


class ResourceConflictError(BaseReplyRocketException):
    """Exception raised for resource conflicts (e.g., duplicate entry)."""
    
    def __init__(
        self, 
        message: str,
        entity: Optional[str] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.entity = entity
        self.field = field
        self.value = value
        
        super().__init__(
            message=message, 
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="ResourceConflict",
            details=details or {
                "entity": entity,
                "field": field,
                "value": value
            }
        )


class OperationError(BaseReplyRocketException):
    """Exception raised for errors in operations or services."""
    
    def __init__(
        self, 
        message: str,
        operation: Optional[str] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        self.operation = operation
        
        super().__init__(
            message=message, 
            status_code=status_code,
            error_code="OperationError",
            details=details or {"operation": operation}
        )


class ServiceUnavailableError(BaseReplyRocketException):
    """Exception raised when an external service is unavailable."""
    
    def __init__(
        self, 
        message: str,
        service: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.service = service
        
        super().__init__(
            message=message, 
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="ServiceUnavailable",
            details=details or {"service": service}
        )


class RateLimitExceededError(BaseReplyRocketException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(
        self, 
        message: str = "Rate limit exceeded",
        reset_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.reset_after = reset_after
        
        super().__init__(
            message=message, 
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RateLimitExceeded",
            details=details or {"reset_after_seconds": reset_after}
        )


# Exception handlers for FastAPI

async def base_exception_handler(request: Request, exc: BaseReplyRocketException) -> JSONResponse:
    """Handle BaseReplyRocketException and convert to JSONResponse."""
    # Log the error
    logger.error(
        f"Error {exc.error_code}: {exc.message}",
        extra={
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # Create error response
    error_response = {
        "detail": exc.message,
        "error_code": exc.error_code,
    }
    
    # Include details for non-production environments or if explicitly enabled
    if exc.details:
        error_response["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )


async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
    """Handle DatabaseError and convert to JSONResponse."""
    # Get database error message
    error_detail = f"Database error during {exc.operation} {exc.entity}"
    if hasattr(exc, 'original_error') and exc.original_error:
        error_detail += f": {str(exc.original_error)}"
    
    # Log the error
    logger.error(
        error_detail,
        extra={
            "operation": exc.operation,
            "entity": exc.entity,
            "original_error": str(exc.original_error) if exc.original_error else None,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=exc.original_error
    )
    
    # Create error response
    error_response = {
        "detail": exc.message,
        "error_code": exc.error_code,
    }
    
    # Include details for non-production environments
    if exc.details:
        error_response["details"] = exc.details
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response,
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle SQLAlchemy errors and convert to appropriate responses."""
    # Determine the type of database error
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "DatabaseError"
    message = "A database error occurred"
    
    if isinstance(exc, IntegrityError):
        error_str = str(exc).lower()
        if "unique constraint" in error_str or "duplicate key" in error_str:
            status_code = status.HTTP_409_CONFLICT
            error_code = "UniqueViolation"
            message = "A duplicate record already exists"
            
            if "email" in error_str:
                message = "A user with this email already exists"
        elif "foreign key constraint" in error_str:
            status_code = status.HTTP_400_BAD_REQUEST
            error_code = "ForeignKeyViolation"
            message = "Referenced entity does not exist"
    
    # Log the error
    logger.error(
        f"Database error: {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=exc
    )
    
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "error_code": error_code,
        },
    )


async def validation_error_handler(request: Request, exc: Union[RequestValidationError, ValidationError]) -> JSONResponse:
    """Handle validation errors from FastAPI and Pydantic."""
    # Extract error details
    if hasattr(exc, 'errors'):
        errors = exc.errors()
    else:
        errors = [{"loc": ["body"], "msg": str(exc), "type": "value_error"}]
    
    # Format error messages
    error_messages: List[Dict[str, Any]] = []
    for error in errors:
        field_path = " > ".join([str(loc) for loc in error.get("loc", [])])
        error_messages.append({
            "field": field_path,
            "message": error.get("msg"),
            "type": error.get("type")
        })
    
    # Log the error
    logger.error(
        f"Validation error: {error_messages}",
        extra={
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "error_code": "ValidationError",
            "errors": error_messages,
        },
    )


async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """General exception handler for unexpected exceptions."""
    # Log the error
    logger.error(
        f"Unexpected error: {str(exc)}",
        extra={
            "error_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=exc
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "error_code": "InternalServerError",
        },
    )


# Utility for extracting clean error message from SQLAlchemy error
def get_db_error_message(error: SQLAlchemyError) -> str:
    """Extract a clean error message from SQLAlchemy error."""
    error_str = str(error)
    
    # Handle specific error types
    if isinstance(error, IntegrityError):
        if "unique constraint" in error_str.lower() or "duplicate key" in error_str.lower():
            if "email" in error_str.lower():
                return "A user with this email already exists"
            return "A duplicate record already exists"
        elif "foreign key constraint" in error_str.lower():
            return "Referenced entity does not exist"
    
    # Return generic message if no specific message is available
    return "A database error occurred"


def translate_sqlalchemy_error(error: SQLAlchemyError, operation: str, entity: str) -> BaseReplyRocketException:
    """Translate SQLAlchemy errors to custom exceptions."""
    error_str = str(error).lower()
    
    if isinstance(error, IntegrityError):
        if "unique constraint" in error_str or "duplicate key" in error_str:
            if "email" in error_str:
                return ResourceConflictError(
                    message=f"{entity.capitalize()} with this email already exists",
                    entity=entity,
                    field="email",
                    original_error=error
                )
            return ResourceConflictError(
                message=f"{entity.capitalize()} already exists",
                entity=entity,
                original_error=error
            )
        elif "foreign key constraint" in error_str:
            return InvalidInputError(
                message="Referenced entity does not exist",
                original_error=error
            )
    
    # Generic database error
    return DatabaseError(
        message=f"Database error occurred while {operation} {entity}",
        operation=operation,
        entity=entity,
        original_error=error
    )


# Function to register all exception handlers with FastAPI app
def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    # Custom exceptions
    app.add_exception_handler(BaseReplyRocketException, base_exception_handler)
    app.add_exception_handler(DatabaseError, database_error_handler)
    
    # Built-in exceptions
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, exception_handler) 