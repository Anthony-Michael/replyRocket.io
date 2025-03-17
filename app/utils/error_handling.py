"""
Error handling utilities for the ReplyRocket application.

This module contains error handling functions and helpers to ensure consistent 
error responses across the application.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

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
        HTTPException: With appropriate status code and detail message
    """
    error_msg = detail or f"Database error occurred while {operation} {entity}"
    
    if isinstance(error, IntegrityError):
        # Handle constraint violations
        err_str = str(error).lower()
        if "unique constraint" in err_str or "duplicate key" in err_str:
            if "email" in err_str:
                # Handle duplicate email case
                logger.warning(f"Duplicate email error: {str(error)}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"{entity.capitalize()} with this email already exists"
                )
            else:
                # Generic unique constraint
                logger.warning(f"Unique constraint error: {str(error)}")
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"{entity.capitalize()} already exists"
                )
        
        # Foreign key violations
        if "foreign key constraint" in err_str:
            logger.warning(f"Foreign key error: {str(error)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Referenced entity does not exist"
            )
    
    # Generic database error
    logger.error(f"Database error during {operation} {entity}: {str(error)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_msg
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
        HTTPException: 404 Not Found with appropriate detail message
    """
    log_msg = f"{entity.capitalize()} with id {entity_id} not found"
    if user_info:
        log_msg += f" (requested by {user_info})"
    
    logger.warning(log_msg)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{entity.capitalize()} not found"
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
        HTTPException: 403 Forbidden with appropriate detail message
    """
    logger.warning(
        f"User {user_id} attempted to access {entity} {entity_id} without permission"
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not enough permissions"
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
        response["error_type"] = error_type
        
    return response 