"""
Utility functions for API endpoints.

This module contains shared utility functions to reduce code duplication
and improve maintainability across API endpoints.
"""

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models

# Set up logger
logger = logging.getLogger(__name__)


def validate_campaign_access(
    db: Session, 
    campaign_id: UUID, 
    user_id: UUID
) -> models.EmailCampaign:
    """
    Validate that a campaign exists and belongs to the user.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to validate
        user_id: ID of the user attempting to access the campaign
        
    Returns:
        The campaign object if validation passes
        
    Raises:
        HTTPException: 
            - 404 if campaign not found
            - 403 if user doesn't have permission
            - 500 if database error occurs
    """
    try:
        campaign = crud.campaign.get(db, id=campaign_id)
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
        
        if campaign.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this campaign",
            )
        
        return campaign
    except SQLAlchemyError as e:
        logger.error(f"Database error when retrieving campaign: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database error occurred while checking campaign",
        )


def validate_smtp_config(user: models.User) -> None:
    """
    Validate that a user has SMTP credentials configured.
    
    Args:
        user: The user to validate SMTP configuration for
        
    Raises:
        HTTPException: 400 if SMTP credentials are not configured
    """
    if not user.smtp_host or not user.smtp_user or not user.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP credentials not configured. Please set up your email service first.",
        )


def handle_db_error(e: SQLAlchemyError, operation: str) -> None:
    """
    Handle database errors with consistent logging and error responses.
    
    Args:
        e: The SQLAlchemy exception
        operation: Description of the database operation being performed
        
    Raises:
        HTTPException: 500 with appropriate error message
    """
    logger.error(f"Database error during {operation}: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Database error occurred during {operation}",
    )


def validate_email(
    db: Session, 
    email_id: UUID, 
    user_id: UUID
) -> models.Email:
    """
    Validate that an email exists and belongs to the user's campaign.
    
    Args:
        db: Database session
        email_id: ID of the email to validate
        user_id: ID of the user attempting to access the email
        
    Returns:
        The email object if validation passes
        
    Raises:
        HTTPException: 
            - 404 if email not found
            - 403 if user doesn't have permission
    """
    email = crud.email.get(db, id=email_id)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    # Check if email belongs to user's campaign
    if email.campaign_id:
        campaign = crud.campaign.get(db, id=email.campaign_id)
        if not campaign or campaign.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this email",
            )
    
    return email 