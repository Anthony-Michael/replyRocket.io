"""
Error handling utilities for the ReplyRocket application.

This module contains error handling functions and helpers to ensure consistent 
error responses across the application.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError, TimeoutError, ResourceClosedError

from app.core.exception_handlers import (
    DatabaseError,
    EntityNotFoundError,
    PermissionDeniedError,
    ResourceConflictError,
    InvalidInputError
)

# Set up logger
logger = logging.getLogger(__name__)


def handle_db_error(
    error: SQLAlchemyError, 
    operation: str, 
    entity: str, 
    detail: Optional[str] = None
) -> None:
    """
    Handle database errors consistently across the application.
    
    Args:
        error: The SQLAlchemy exception that occurred
        operation: The operation being performed (e.g., "create", "update")
        entity: The entity being operated on (e.g., "user", "campaign")
        detail: Optional custom error message
        
    Raises:
        DatabaseError: With appropriate error details
        ResourceConflictError: For unique constraint violations
        InvalidInputError: For foreign key violations
    """
    error_msg = detail or f"Database error occurred while {operation} {entity}"
    
    # Get the stack trace for better debugging
    stack_trace = traceback.format_exc()
    
    # Check for specific connection or session-related errors
    if isinstance(error, (OperationalError, TimeoutError, ResourceClosedError)):
        # These errors often indicate connection issues or session misuse
        logger.error(
            f"Database connection error during {operation} {entity}: {str(error)}\n"
            f"This may indicate a potential session leak or connection issue.\n"
            f"Stack trace: {stack_trace}"
        )
    elif isinstance(error, IntegrityError):
        # Handle constraint violations
        err_str = str(error).lower()
        if "unique constraint" in err_str or "duplicate key" in err_str:
            if "email" in err_str:
                # Handle duplicate email case
                logger.warning(f"Duplicate email error: {str(error)}")
                raise ResourceConflictError(
                    message=f"{entity.capitalize()} with this email already exists",
                    entity=entity,
                    field="email"
                )
            else:
                # Generic unique constraint
                logger.warning(f"Unique constraint error: {str(error)}")
                raise ResourceConflictError(
                    message=f"{entity.capitalize()} already exists",
                    entity=entity
                )
        
        # Foreign key violations
        if "foreign key constraint" in err_str:
            logger.warning(f"Foreign key error: {str(error)}")
            raise InvalidInputError(
                message="Referenced entity does not exist",
                details={"error": str(error)}
            )
    else:
        # Generic database error
        logger.error(
            f"Database error during {operation} {entity}: {str(error)}\n"
            f"Stack trace: {stack_trace}"
        )
    
    # Raise the appropriate exception
    raise DatabaseError(
        message=error_msg,
        operation=operation,
        entity=entity,
        original_error=error
    )


def handle_entity_not_found(
    entity: str, 
    entity_id: Any, 
    user_info: Optional[str] = None
) -> None:
    """
    Handle entity not found errors consistently.
    
    Args:
        entity: The type of entity (e.g., "user", "campaign")
        entity_id: The ID of the entity that wasn't found
        user_info: Optional additional user information for logging
        
    Raises:
        EntityNotFoundError: With appropriate error details
    """
    log_msg = f"{entity.capitalize()} with id {entity_id} not found"
    if user_info:
        log_msg += f" (requested by {user_info})"
    
    logger.warning(log_msg)
    raise EntityNotFoundError(
        entity=entity,
        entity_id=entity_id,
        details={"user_info": user_info} if user_info else None
    )


def handle_permission_error(
    entity: str,
    entity_id: Any,
    user_id: int
) -> None:
    """
    Handle permission errors consistently.
    
    Args:
        entity: The type of entity (e.g., "campaign", "email")
        entity_id: The ID of the entity being accessed
        user_id: The ID of the user attempting the access
        
    Raises:
        PermissionDeniedError: With appropriate error details
    """
    logger.warning(
        f"User {user_id} attempted to access {entity} {entity_id} without permission"
    )
    raise PermissionDeniedError(
        entity=entity,
        entity_id=entity_id,
        user_id=user_id
    )


def create_error_response(
    status_code: int,
    detail: str,
    error_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response dictionary.
    
    Args:
        status_code: HTTP status code
        detail: Error message
        error_type: Optional error type classification
        
    Returns:
        Dict: Standardized error response
    """
    response = {
        "status": "error",
        "code": status_code,
        "message": detail,
    }
    
    if error_type:
        response["error_code"] = error_type
        
    return response 