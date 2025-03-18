"""
Campaign management endpoints.

This module handles the creation, retrieval, updating, and deletion
of email campaigns.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.services import (
    create_campaign,
    get_campaign,
    get_campaigns,
    get_active_campaigns,
    update_campaign,
    delete_campaign,
    configure_ab_testing
)
from app.utils.validation import validate_campaign_access

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=schemas.Campaign)
def create_campaign_endpoint(
    *,
    db: Session = Depends(deps.get_db),
    campaign_in: schemas.CampaignCreate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Create new campaign.
    """
    logger.info(f"Creating new campaign for user {current_user.id}")
    return create_campaign(db, campaign_in, current_user.id)


@router.get("/", response_model=List[schemas.Campaign])
def read_campaigns(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve campaigns.
    """
    logger.info(f"Retrieving campaigns for user {current_user.id}")
    return get_campaigns(db, current_user.id, skip=skip, limit=limit)


@router.get("/active", response_model=List[schemas.Campaign])
def read_active_campaigns(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Retrieve active campaigns.
    """
    logger.info(f"Retrieving active campaigns for user {current_user.id}")
    return get_active_campaigns(db, current_user.id)


@router.get("/{campaign_id}", response_model=schemas.Campaign)
def read_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Get campaign by ID.
    """
    logger.info(f"Retrieving campaign {campaign_id} for user {current_user.id}")
    campaign = get_campaign(db, campaign_id)
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
        
    # Validate access
    validate_campaign_access(campaign, current_user)
    
    return campaign


@router.put("/{campaign_id}", response_model=schemas.Campaign)
def update_campaign_endpoint(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    campaign_in: schemas.CampaignUpdate,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Update a campaign.
    """
    logger.info(f"Updating campaign {campaign_id} for user {current_user.id}")
    campaign = get_campaign(db, campaign_id)
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
        
    # Validate access
    validate_campaign_access(campaign, current_user)
    
    return update_campaign(db, campaign_id, campaign_in)


@router.delete("/{campaign_id}", response_model=schemas.Campaign)
def delete_campaign_endpoint(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Delete a campaign.
    """
    logger.info(f"Deleting campaign {campaign_id} for user {current_user.id}")
    campaign = get_campaign(db, campaign_id)
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
        
    # Validate access
    validate_campaign_access(campaign, current_user)
    
    return delete_campaign(db, campaign_id)


@router.post("/{campaign_id}/ab-testing", response_model=schemas.Campaign)
def configure_ab_testing_endpoint(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    ab_test_in: schemas.ABTestConfig,
    current_user: models.User = Depends(deps.get_current_active_user)
) -> Any:
    """
    Configure A/B testing for a campaign.
    """
    logger.info(f"Configuring A/B testing for campaign {campaign_id}")
    campaign = get_campaign(db, campaign_id)
    
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
        
    # Validate access
    validate_campaign_access(campaign, current_user)
    
    # Validate A/B test configuration
    if len(ab_test_in.variants) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A/B testing requires at least two variants",
        )
    
    return configure_ab_testing(db, campaign_id, ab_test_in.variants) 