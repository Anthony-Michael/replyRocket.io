"""
Campaign service for ReplyRocket.io

This module contains business logic for campaign management,
separating it from data access operations in the crud modules.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas
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
        # Create campaign object
        obj_in_data = campaign_in.dict()
        db_obj = models.EmailCampaign(**obj_in_data, user_id=user_id)
        
        # Add to database
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
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
        return db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign_id).first()
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
        return (
            db.query(models.EmailCampaign)
            .filter(models.EmailCampaign.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
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
        return (
            db.query(models.EmailCampaign)
            .filter(models.EmailCampaign.user_id == user_id, models.EmailCampaign.is_active == True)
            .all()
        )
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
        
        # Update fields
        update_data = campaign_in.dict(exclude_unset=True)
        for field in update_data:
            setattr(db_obj, field, update_data[field])
        
        # Save to database
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        
        logger.info(f"Updated campaign {campaign_id}")
        return db_obj
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
        
        # Delete from database
        db.delete(db_obj)
        db.commit()
        
        logger.info(f"Deleted campaign {campaign_id}")
        return db_obj
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
            
        for key, value in stats.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        logger.info(f"Updated stats for campaign {campaign_id}")
        return campaign
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
            
        campaign.ab_test_active = True
        campaign.ab_test_variants = variants
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        logger.info(f"Configured A/B testing for campaign {campaign_id}")
        return campaign
    except SQLAlchemyError as e:
        logger.error(f"Error configuring A/B testing for campaign {campaign_id}: {str(e)}")
        handle_db_error(e) 