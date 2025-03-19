from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.services import stats_service
from app.core.exception_handlers import EntityNotFoundError, PermissionDeniedError

router = APIRouter()


@router.get("/campaign/{campaign_id}", response_model=schemas.CampaignStats)
def get_campaign_stats(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get statistics for a specific campaign.
    """
    try:
        return stats_service.get_campaign_stats(db, campaign_id, current_user.id)
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


@router.get("/user", response_model=List[schemas.CampaignStats])
def get_user_stats(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get statistics for all campaigns of the current user.
    """
    return stats_service.get_user_stats(db, current_user.id) 