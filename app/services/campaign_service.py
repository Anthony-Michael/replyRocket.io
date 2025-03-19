"""
Campaign service for ReplyRocket.io

This module contains business logic for campaign management,
separating it from data access operations in the crud modules.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas, crud
from app.utils.error_handling import handle_db_error

# Set up logger
logger = logging.getLogger(__name__)


def create_campaign(db: Session, campaign_in: schemas.CampaignCreate, user_id: UUID) -> models.EmailCampaign:
    """
    Create a new campaign for a user.
    
    Args:
        db: Database session
        campaign_in: Campaign creation data
        user_id: ID of the user creating the campaign
        
    Returns:
        New EmailCampaign object
    """
    try:
        # Use CRUD operation to create campaign
        db_obj = crud.campaign.create_with_owner(db, obj_in=campaign_in, user_id=user_id)
        
        logger.info(f"Created campaign {db_obj.id} for user {user_id}")
        return db_obj
    except SQLAlchemyError as e:
        logger.error(f"Error creating campaign for user {user_id}: {str(e)}")
        handle_db_error(e)


def get_campaign(db: Session, campaign_id: UUID) -> Optional[models.EmailCampaign]:
    """
    Get a campaign by ID.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        
    Returns:
        EmailCampaign object or None if not found
    """
    try:
        return crud.campaign.get(db, id=campaign_id)
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving campaign {campaign_id}: {str(e)}")
        handle_db_error(e)


def get_campaigns(
    db: Session, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[models.EmailCampaign]:
    """
    Get multiple campaigns by user ID with pagination.
    
    Args:
        db: Database session
        user_id: ID of the user
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of EmailCampaign objects
    """
    try:
        return crud.campaign.get_multi_by_owner(db, user_id=user_id, skip=skip, limit=limit)
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving campaigns for user {user_id}: {str(e)}")
        handle_db_error(e)


def get_active_campaigns(db: Session, user_id: UUID) -> List[models.EmailCampaign]:
    """
    Get all active campaigns for a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        List of active EmailCampaign objects
    """
    try:
        return crud.campaign.get_active_by_owner(db, user_id=user_id)
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving active campaigns for user {user_id}: {str(e)}")
        handle_db_error(e)


def update_campaign(
    db: Session, campaign_id: UUID, campaign_in: schemas.CampaignUpdate
) -> models.EmailCampaign:
    """
    Update a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to update
        campaign_in: Campaign update data
        
    Returns:
        Updated EmailCampaign object
    """
    try:
        # Get campaign
        db_obj = get_campaign(db, campaign_id)
        if not db_obj:
            logger.error(f"Campaign {campaign_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
        
        # Use CRUD operation to update campaign
        updated_campaign = crud.campaign.update(db, db_obj=db_obj, obj_in=campaign_in)
        
        logger.info(f"Updated campaign {campaign_id}")
        return updated_campaign
    except SQLAlchemyError as e:
        logger.error(f"Error updating campaign {campaign_id}: {str(e)}")
        handle_db_error(e)


def delete_campaign(db: Session, campaign_id: UUID) -> models.EmailCampaign:
    """
    Delete a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to delete
        
    Returns:
        Deleted EmailCampaign object
    """
    try:
        # Get campaign
        db_obj = get_campaign(db, campaign_id)
        if not db_obj:
            logger.error(f"Campaign {campaign_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
        
        # Use CRUD operation to delete campaign
        deleted_campaign = crud.campaign.remove(db, id=campaign_id)
        
        logger.info(f"Deleted campaign {campaign_id}")
        return deleted_campaign
    except SQLAlchemyError as e:
        logger.error(f"Error deleting campaign {campaign_id}: {str(e)}")
        handle_db_error(e)


def update_campaign_stats(
    db: Session, campaign_id: UUID, stats: Dict[str, int]
) -> models.EmailCampaign:
    """
    Update campaign statistics.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        stats: Dictionary of stats to update
        
    Returns:
        Updated EmailCampaign object
    """
    try:
        campaign = get_campaign(db, campaign_id)
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
            
        # Use CRUD operation to update stats
        updated_campaign = crud.campaign.update_stats(db, db_obj=campaign, stats=stats)
        
        logger.info(f"Updated stats for campaign {campaign_id}")
        return updated_campaign
    except SQLAlchemyError as e:
        logger.error(f"Error updating stats for campaign {campaign_id}: {str(e)}")
        handle_db_error(e)


def configure_ab_testing(
    db: Session, campaign_id: UUID, variants: Dict[str, str]
) -> models.EmailCampaign:
    """
    Configure A/B testing for a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        variants: Dictionary of A/B test variants
        
    Returns:
        Updated EmailCampaign object
    """
    try:
        campaign = get_campaign(db, campaign_id)
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
            
        # Use CRUD operation to update A/B testing configuration
        updated_campaign = crud.campaign.update_ab_testing(db, db_obj=campaign, variants=variants)
        
        logger.info(f"Configured A/B testing for campaign {campaign_id}")
        return updated_campaign
    except SQLAlchemyError as e:
        logger.error(f"Error configuring A/B testing for campaign {campaign_id}: {str(e)}")
        handle_db_error(e) 