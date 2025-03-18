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
) -> models.EmailCampaign:
    """
    Configure A/B testing for a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        ab_test_config: A/B test configuration data
        
    Returns:
        Updated EmailCampaign model
        
    Raises:
        HTTPException: 404 if campaign not found
        HTTPException: 400 if validation fails
    """
    try:
        # Validate configuration
        validate_ab_test_config(ab_test_config)
        
        # Get campaign
        campaign = db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign_id).first()
        
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )
        
        # Update campaign with AB test config
        campaign.ab_test_active = True
        campaign.ab_test_variants = ab_test_config.variants
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        return campaign
        
    except SQLAlchemyError as e:
        handle_db_error(e)


def get_user_campaigns(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100
) -> List[models.EmailCampaign]:
    """
    Get all campaigns for a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return
        
    Returns:
        List of EmailCampaign models
        
    Raises:
        HTTPException: If DB error occurs
    """
    try:
        campaigns = db.query(models.EmailCampaign).filter(
            models.EmailCampaign.user_id == user_id
        ).offset(skip).limit(limit).all()
        
        return campaigns
        
    except SQLAlchemyError as e:
        handle_db_error(e)


def get_active_campaigns(db: Session, user_id: int) -> List[models.EmailCampaign]:
    """
    Get all active campaigns for a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        List of active EmailCampaign models
        
    Raises:
        HTTPException: If DB error occurs
    """
    try:
        active_campaigns = db.query(models.EmailCampaign).filter(
            models.EmailCampaign.user_id == user_id,
            models.EmailCampaign.is_active == True
        ).all()
        
        return active_campaigns
        
    except SQLAlchemyError as e:
        handle_db_error(e)


def create_user_campaign(
    db: Session, 
    campaign_in: schemas.CampaignCreate, 
    user_id: int
) -> models.EmailCampaign:
    """
    Create a new campaign for a user.
    
    Args:
        db: Database session
        campaign_in: Campaign creation data
        user_id: ID of the user
        
    Returns:
        Created EmailCampaign model
        
    Raises:
        HTTPException: If DB error occurs
    """
    try:
        campaign = models.EmailCampaign(
            user_id=user_id,
            **campaign_in.dict()
        )
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        return campaign
        
    except SQLAlchemyError as e:
        handle_db_error(e)


def update_user_campaign(
    db: Session, 
    campaign: models.EmailCampaign, 
    campaign_in: schemas.CampaignUpdate
) -> models.EmailCampaign:
    """
    Update a campaign.
    
    Args:
        db: Database session
        campaign: Campaign to update
        campaign_in: Campaign update data
        
    Returns:
        Updated EmailCampaign model
        
    Raises:
        HTTPException: If DB error occurs
    """
    try:
        # Convert Pydantic model to dict, excluding unset fields
        update_data = campaign_in.dict(exclude_unset=True)
        
        # Update campaign attributes
        for key, value in update_data.items():
            setattr(campaign, key, value)
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        return campaign
        
    except SQLAlchemyError as e:
        handle_db_error(e)


def delete_user_campaign(db: Session, campaign_id: int) -> models.EmailCampaign:
    """
    Delete a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to delete
        
    Returns:
        Deleted EmailCampaign model
        
    Raises:
        HTTPException: 404 if campaign not found
        HTTPException: If DB error occurs
    """
    try:
        campaign = db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign_id).first()
        
        if not campaign:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Campaign with ID {campaign_id} not found"
            )
        
        db.delete(campaign)
        db.commit()
        
        return campaign
        
    except SQLAlchemyError as e:
        handle_db_error(e) 