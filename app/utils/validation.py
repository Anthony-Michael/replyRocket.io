"""
Validation utility functions for the ReplyRocket application.

This module contains common validation logic used across different parts of the application,
helping to reduce code duplication and ensure consistent validation behavior.
"""

import logging
from typing import Optional, Union

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.campaign import EmailCampaign
from app.models.user import User
from app.models.email import Email
from app.core.security import validate_password_strength

# Set up logger
logger = logging.getLogger(__name__)


def validate_campaign_access(
    db: Session, campaign_id: int, user_id: int, *, for_update: bool = False
) -> EmailCampaign:
    """
    Validate that a campaign exists and the user has access to it.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to validate
        user_id: ID of the user requesting access
        for_update: If True, check if the campaign is in a state that allows updates
    
    Returns:
        EmailCampaign: The validated campaign object
        
    Raises:
        HTTPException: 404 if campaign not found, 403 if user doesn't have permission
    """
    campaign = db.query(EmailCampaign).filter(EmailCampaign.id == campaign_id).first()
    
    if not campaign:
        logger.warning(f"Campaign with id {campaign_id} not found")
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if campaign.user_id != user_id:
        logger.warning(f"User {user_id} attempted to access campaign {campaign_id} without permission")
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    if for_update and campaign.is_active:
        logger.warning(f"User {user_id} attempted to update active campaign {campaign_id}")
        raise HTTPException(
            status_code=400, 
            detail="Cannot update active campaign. Please deactivate it first."
        )
    
    return campaign


def validate_email_access(
    db: Session, email_id: int, user_id: int
) -> Email:
    """
    Validate that an email exists and the user has access to it.
    
    Args:
        db: Database session
        email_id: ID of the email to validate
        user_id: ID of the user requesting access
    
    Returns:
        Email: The validated email object
        
    Raises:
        HTTPException: 404 if email not found, 403 if user doesn't have permission
    """
    email = db.query(Email).filter(Email.id == email_id).first()
    
    if not email:
        logger.warning(f"Email with id {email_id} not found")
        raise HTTPException(status_code=404, detail="Email not found")
        
    # Check campaign ownership to determine email access
    campaign = db.query(EmailCampaign).filter(EmailCampaign.id == email.campaign_id).first()
    
    if not campaign or campaign.user_id != user_id:
        logger.warning(f"User {user_id} attempted to access email {email_id} without permission")
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return email


def validate_user_password(
    password: str, raise_exception: bool = True
) -> Union[bool, None]:
    """
    Validate that a password meets strength requirements.
    
    Args:
        password: The password to validate
        raise_exception: If True, raise HTTPException on validation failure
                         If False, return False on validation failure
    
    Returns:
        bool: True if password meets requirements, False if not (and raise_exception is False)
        
    Raises:
        HTTPException: 400 if password doesn't meet requirements (and raise_exception is True)
    """
    if not validate_password_strength(password):
        error_msg = (
            "Password must be at least 8 characters long and contain "
            "uppercase, lowercase, number and special character."
        )
        
        if raise_exception:
            raise HTTPException(status_code=400, detail=error_msg)
        return False
    
    return True


def validate_user_exists(
    db: Session, user_id: int, raise_exception: bool = True
) -> Optional[User]:
    """
    Validate that a user exists in the database.
    
    Args:
        db: Database session
        user_id: ID of the user to validate
        raise_exception: If True, raise HTTPException if user doesn't exist
                         If False, return None if user doesn't exist
    
    Returns:
        User: The user object if found
        None: If user not found and raise_exception is False
        
    Raises:
        HTTPException: 404 if user not found and raise_exception is True
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user and raise_exception:
        logger.warning(f"User with id {user_id} not found")
        raise HTTPException(status_code=404, detail="User not found")
    
    return user 