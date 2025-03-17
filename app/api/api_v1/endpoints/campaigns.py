"""
Campaign management endpoints.

This module handles the creation, retrieval, updating, and deletion
of email campaigns.
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.utils.validation import validate_campaign_access
from app.utils.error_handling import handle_db_error, handle_entity_not_found, handle_permission_error

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
    try:
        campaign = crud.campaign.create_with_user(
            db=db, obj_in=campaign_in, user_id=current_user.id
        )
        logger.info(f"User {current_user.id} created campaign {campaign.id}")
        return campaign
    except SQLAlchemyError as e:
        handle_db_error(e, "create", "campaign")


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
    try:
        campaigns = crud.campaign.get_multi_by_user(
            db=db, user_id=current_user.id, skip=skip, limit=limit
        )
        return campaigns
    except SQLAlchemyError as e:
        handle_db_error(e, "retrieve", "campaigns")


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
    try:
        campaigns = crud.campaign.get_active_campaigns_for_user(
            db=db, user_id=current_user.id
        )
        return campaigns
    except SQLAlchemyError as e:
        handle_db_error(e, "retrieve", "active campaigns")


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
    try:
        # Validate access and check if campaign is in a state that allows updates
        campaign = validate_campaign_access(db, campaign_id, current_user.id, for_update=True)
        
        # Update the campaign
        campaign = crud.campaign.update(db=db, db_obj=campaign, obj_in=campaign_in)
        logger.info(f"User {current_user.id} updated campaign {campaign_id}")
        return campaign
    except HTTPException:
        # Let HTTPException propagate as it's already well-formed
        raise
    except SQLAlchemyError as e:
        handle_db_error(e, "update", "campaign")


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
    try:
        # Validate access before deletion
        validate_campaign_access(db, campaign_id, current_user.id)
        
        # Perform deletion
        campaign = crud.campaign.remove(db=db, id=campaign_id)
        logger.info(f"User {current_user.id} deleted campaign {campaign_id}")
        return campaign
    except SQLAlchemyError as e:
        handle_db_error(e, "delete", "campaign")


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
    try:
        # Validate campaign access
        campaign = validate_campaign_access(db, ab_test_config.campaign_id, current_user.id)
        
        # Validate A/B test configuration
        if len(ab_test_config.variants) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A/B testing requires at least two variants"
            )
        
        # Configure A/B testing
        campaign = crud.campaign.configure_ab_testing(
            db=db, campaign_id=campaign.id, variants=ab_test_config.variants
        )
        
        logger.info(f"User {current_user.id} configured A/B testing for campaign {campaign.id}")
        return campaign
    except SQLAlchemyError as e:
        handle_db_error(e, "configure A/B testing for", "campaign") 