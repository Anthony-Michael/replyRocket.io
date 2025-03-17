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
from app.utils.validation import validate_campaign_access
from app.utils.campaign_utils import (
    validate_ab_test_config,
    configure_campaign_ab_testing,
    get_user_campaigns,
    get_active_campaigns,
    create_user_campaign,
    update_user_campaign,
    delete_user_campaign
)

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=schemas.Campaign, status_code=status.HTTP_201_CREATED)
def create_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_in: schemas.CampaignCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a new email campaign.
    
    Args:
        db: Database session
        campaign_in: Campaign creation data with name, description, etc.
        current_user: Authenticated user making the request
        
    Returns:
        The created campaign object
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    return create_user_campaign(db, campaign_in, current_user.id)


@router.get("", response_model=List[schemas.Campaign])
def read_campaigns(
    *,
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve all campaigns for the current user.
    
    Args:
        db: Database session
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user making the request
        
    Returns:
        List of campaign objects belonging to the user
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    return get_user_campaigns(db, current_user.id, skip, limit)


@router.get("/active", response_model=List[schemas.Campaign])
def read_active_campaigns(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve all active campaigns for the current user.
    
    Args:
        db: Database session
        current_user: Authenticated user making the request
        
    Returns:
        List of active campaign objects belonging to the user
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    return get_active_campaigns(db, current_user.id)


@router.get("/{campaign_id}", response_model=schemas.Campaign)
def read_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get a specific campaign by ID.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to retrieve
        current_user: Authenticated user making the request
        
    Returns:
        The requested campaign object
        
    Raises:
        HTTPException: 
            - 404 if campaign not found
            - 403 if user doesn't have permission
    """
    return validate_campaign_access(db, campaign_id, current_user.id)


@router.put("/{campaign_id}", response_model=schemas.Campaign)
def update_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: int,
    campaign_in: schemas.CampaignUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to update
        campaign_in: Campaign update data
        current_user: Authenticated user making the request
        
    Returns:
        The updated campaign object
        
    Raises:
        HTTPException: 
            - 404 if campaign not found
            - 403 if user doesn't have permission
            - 400 if attempting to update an active campaign
    """
    # Validate access and check if campaign is in a state that allows updates
    campaign = validate_campaign_access(db, campaign_id, current_user.id, for_update=True)
    
    # Update the campaign
    return update_user_campaign(db, campaign, campaign_in)


@router.delete("/{campaign_id}", response_model=schemas.Campaign)
def delete_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: int,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign to delete
        current_user: Authenticated user making the request
        
    Returns:
        The deleted campaign object
        
    Raises:
        HTTPException: 
            - 404 if campaign not found
            - 403 if user doesn't have permission
            - 500 if database error occurs
    """
    # Validate access before deletion
    validate_campaign_access(db, campaign_id, current_user.id)
    
    # Perform deletion
    return delete_user_campaign(db, campaign_id)


@router.post("/ab-test", response_model=schemas.Campaign)
def configure_ab_testing(
    *,
    db: Session = Depends(deps.get_db),
    ab_test_config: schemas.ABTestConfig,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Configure A/B testing for a campaign.
    
    Args:
        db: Database session
        ab_test_config: A/B test configuration data
        current_user: Authenticated user making the request
        
    Returns:
        The updated campaign object with A/B testing configuration
        
    Raises:
        HTTPException: 
            - 404 if campaign not found
            - 403 if user doesn't have permission
            - 400 if invalid A/B test configuration
            - 500 if database error occurs
    """
    # Validate campaign access
    validate_campaign_access(db, ab_test_config.campaign_id, current_user.id)
    
    # Validate A/B test configuration
    validate_ab_test_config(ab_test_config)
    
    # Configure A/B testing
    campaign = configure_campaign_ab_testing(db, ab_test_config.campaign_id, ab_test_config)
    
    logger.info(f"User {current_user.id} configured A/B testing for campaign {campaign.id}")
    return campaign 