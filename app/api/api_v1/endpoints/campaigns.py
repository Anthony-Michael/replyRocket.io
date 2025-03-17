from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.post("", response_model=schemas.Campaign)
def create_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_in: schemas.CampaignCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Create a new email campaign.
    """
    campaign = crud.campaign.create_with_user(
        db=db, obj_in=campaign_in, user_id=current_user.id
    )
    return campaign


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
    """
    campaigns = crud.campaign.get_multi_by_user(
        db=db, user_id=current_user.id, skip=skip, limit=limit
    )
    return campaigns


@router.get("/active", response_model=List[schemas.Campaign])
def read_active_campaigns(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Retrieve all active campaigns for the current user.
    """
    campaigns = crud.campaign.get_active_campaigns_for_user(
        db=db, user_id=current_user.id
    )
    return campaigns


@router.get("/{campaign_id}", response_model=schemas.Campaign)
def read_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get a specific campaign by ID.
    """
    campaign = crud.campaign.get(db=db, id=campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return campaign


@router.put("/{campaign_id}", response_model=schemas.Campaign)
def update_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    campaign_in: schemas.CampaignUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Update a campaign.
    """
    campaign = crud.campaign.get(db=db, id=campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    campaign = crud.campaign.update(db=db, db_obj=campaign, obj_in=campaign_in)
    return campaign


@router.delete("/{campaign_id}", response_model=schemas.Campaign)
def delete_campaign(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Delete a campaign.
    """
    campaign = crud.campaign.get(db=db, id=campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    campaign = crud.campaign.remove(db=db, id=campaign_id)
    return campaign


@router.post("/ab-test", response_model=schemas.Campaign)
def configure_ab_testing(
    *,
    db: Session = Depends(deps.get_db),
    ab_test_config: schemas.ABTestConfig,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Configure A/B testing for a campaign.
    """
    campaign = crud.campaign.get(db=db, id=ab_test_config.campaign_id)
    if not campaign:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    if campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    
    # Configure A/B testing
    campaign = crud.campaign.configure_ab_testing(
        db=db, campaign_id=campaign.id, variants=ab_test_config.variants
    )
    
    return campaign 