"""
Campaign utility functions for the ReplyRocket application.

This module contains campaign-related utility functions to reduce code
duplication and improve maintainability across the application.
"""

import logging
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.utils.error_handling import handle_db_error

# Set up logger
logger = logging.getLogger(__name__)


def validate_ab_test_config(ab_test_config: schemas.ABTestConfig) -> None:
    """
    Validate A/B test configuration.
    
    Args:
        ab_test_config: A/B test configuration data
        
    Raises:
        HTTPException: 400 if validation fails
    """
    if len(ab_test_config.variants) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A/B testing requires at least two variants"
        )


def configure_campaign_ab_testing(
    db: Session, 
    campaign_id: int, 
    ab_test_config: schemas.ABTestConfig
) -> models.Campaign:
    """
    Configure A/B testing for a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        ab_test_config: A/B test configuration data
        
    Returns:
        Updated campaign object
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        # Configure A/B testing
        campaign = crud.campaign.configure_ab_testing(
            db=db, 
            campaign_id=campaign_id, 
            variants=ab_test_config.variants
        )
        
        return campaign
    except SQLAlchemyError as e:
        handle_db_error(e, "configure A/B testing for", "campaign")


def get_user_campaigns(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[models.Campaign]:
    """
    Get campaigns for a user with pagination.
    
    Args:
        db: Database session
        user_id: ID of the user
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        
    Returns:
        List of campaign objects
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        campaigns = crud.campaign.get_multi_by_user(
            db=db, user_id=user_id, skip=skip, limit=limit
        )
        return campaigns
    except SQLAlchemyError as e:
        handle_db_error(e, "retrieve", "campaigns")


def get_active_campaigns(db: Session, user_id: int) -> List[models.Campaign]:
    """
    Get active campaigns for a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        List of active campaign objects
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        campaigns = crud.campaign.get_active_campaigns_for_user(
            db=db, user_id=user_id
        )
        return campaigns
    except SQLAlchemyError as e:
        handle_db_error(e, "retrieve", "active campaigns")


def create_user_campaign(
    db: Session, 
    campaign_in: schemas.CampaignCreate, 
    user_id: int
) -> models.Campaign:
    """
    Create a new campaign for a user.
    
    Args:
        db: Database session
        campaign_in: Campaign creation data
        user_id: ID of the user
        
    Returns:
        Created campaign object
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        campaign = crud.campaign.create_with_user(
            db=db, obj_in=campaign_in, user_id=user_id
        )
        logger.info(f"User {user_id} created campaign {campaign.id}")
        return campaign
    except SQLAlchemyError as e:
        handle_db_error(e, "create", "campaign")


def update_user_campaign(
    db: Session, 
    campaign: models.Campaign, 
    campaign_in: schemas.CampaignUpdate
) -> models.Campaign:
    """
    Update a campaign.
    
    Args:
        db: Database session
        campaign: Campaign object to update
        campaign_in: Campaign update data
        
    Returns:
        Updated campaign object
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        campaign = crud.campaign.update(db=db, db_obj=campaign, obj_in=campaign_in)
        logger.info(f"Campaign {campaign.id} updated")
        return campaign
    except SQLAlchemyError as e:
        handle_db_error(e, "update", "campaign")


def delete_user_campaign(db: Session, campaign_id: int) -> models.Campaign:
    """
    Delete a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to delete
        
    Returns:
        Deleted campaign object
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        campaign = crud.campaign.remove(db=db, id=campaign_id)
        logger.info(f"Campaign {campaign_id} deleted")
        return campaign
    except SQLAlchemyError as e:
        handle_db_error(e, "delete", "campaign") 