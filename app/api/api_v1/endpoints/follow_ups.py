from datetime import datetime, timedelta
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.api import deps
from app.services import follow_up_service
from app.core.exception_handlers import EntityNotFoundError, PermissionDeniedError

router = APIRouter()


@router.post("/generate", response_model=schemas.EmailGenResponse)
def generate_follow_up_email(
    *,
    db: Session = Depends(deps.get_db),
    follow_up_request: schemas.FollowUpRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate a follow-up email using AI based on the original email.
    """
    try:
        return follow_up_service.generate_follow_up_email(
            db=db,
            original_email_id=follow_up_request.original_email_id,
            user_id=current_user.id,
            new_approach=follow_up_request.new_approach,
        )
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original email not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


@router.post("/send", response_model=schemas.EmailSendResponse)
def send_follow_up_email(
    *,
    db: Session = Depends(deps.get_db),
    follow_up_request: schemas.FollowUpRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate and send a follow-up email.
    """
    try:
        return follow_up_service.send_follow_up_email(
            db=db,
            original_email_id=follow_up_request.original_email_id,
            user_id=current_user.id,
            new_approach=follow_up_request.new_approach,
        )
    except EntityNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original email not found",
        )
    except PermissionDeniedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )


@router.post("/schedule")
def schedule_follow_ups(
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_superuser),
) -> Any:
    """
    Schedule follow-up emails for all campaigns.
    This endpoint is for admin use only.
    """
    return follow_up_service.schedule_follow_ups(db, background_tasks) 