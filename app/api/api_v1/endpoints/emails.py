"""
Email generation and sending endpoints.

This module handles AI-powered email generation and sending,
along with email tracking and metrics.
"""

import logging
from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.services import email_service, campaign_service
from app.services.ai_email_generator_service import generate_email
from app.utils.validation import validate_campaign_access, validate_email_access
from app.utils.error_handling import handle_db_error, handle_entity_not_found, handle_permission_error

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate", response_model=schemas.EmailGenResponse, status_code=status.HTTP_201_CREATED)
def generate_email_content(
    *,
    db: Session = Depends(deps.get_db),
    email_request: schemas.EmailGenRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate an email using AI based on recipient details and campaign context.
    
    Args:
        db: Database session
        email_request: Email generation request with recipient details
        current_user: Authenticated user making the request
        
    Returns:
        Generated email content with subject, body text, and HTML
        
    Raises:
        HTTPException: 404 if campaign not found, 403 if not owned by user,
                      422 if AI service returns incomplete data,
                      500 if AI service fails
    """
    # Validate campaign if one is specified
    if email_request.campaign_id:
        validate_campaign_access(db, email_request.campaign_id, current_user.id)
    
    # Generate and validate email content
    return generate_and_validate_email_content(email_request)


def generate_and_validate_email_content(
    email_request: schemas.EmailGenRequest
) -> schemas.EmailGenResponse:
    """
    Generate email content using AI and validate the response.
    
    Args:
        email_request: Email generation request data
        
    Returns:
        Validated email content
        
    Raises:
        HTTPException: If generation fails or validation fails
    """
    try:
        # Generate email using AI service
        email_content = generate_email(
            recipient_name=email_request.recipient_name,
            recipient_company=email_request.recipient_company,
            recipient_job_title=email_request.recipient_job_title,
            industry=email_request.industry,
            pain_points=email_request.pain_points,
            personalization_notes=email_request.personalization_notes,
        )
        
        return email_content
    except ValueError as e:
        # Handle validation or data structure errors
        logger.error(f"Validation error in email generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except Exception as e:
        # Handle other exceptions from the AI service
        logger.error(f"Error generating email: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating email content",
        )


@router.post("/send", response_model=schemas.Email, status_code=status.HTTP_201_CREATED)
def send_email_to_recipient(
    *,
    db: Session = Depends(deps.get_db),
    email_request: schemas.EmailSendRequest,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send an email to a recipient.
    
    Args:
        db: Database session
        email_request: Email send request with recipient and content
        background_tasks: FastAPI background tasks
        current_user: Authenticated user making the request
        
    Returns:
        Created email record
        
    Raises:
        HTTPException: 404 if campaign not found, 403 if not owned by user,
                      400 if SMTP configuration is missing
    """
    try:
        # Validate SMTP configuration
        email_service.validate_smtp_config(current_user)
        
        # Validate campaign access if a campaign ID is provided
        if email_request.campaign_id:
            validate_campaign_access(db, email_request.campaign_id, current_user.id)
            
        # Create email record
        email = email_service.create_email(db, email_request, email_request.campaign_id)
        
        # Schedule email sending as a background task
        email_service.schedule_email_send(
            background_tasks=background_tasks,
            email=email,
            user=current_user,
            email_request=email_request
        )
        
        logger.info(f"Email {email.id} scheduled for sending to {email_request.recipient_email}")
        
        # Return the email record (not waiting for actual sending)
        return email
    except SQLAlchemyError as e:
        handle_db_error(e, "Error creating email record")
    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Unexpected error sending email: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while sending the email",
            )
        raise


@router.get("/tracking/{tracking_id}")
def track_email_open(
    *,
    db: Session = Depends(deps.get_db),
    tracking_id: str,
) -> Any:
    """
    Track email opens via a tracking pixel.
    
    Args:
        db: Database session
        tracking_id: Unique tracking ID for the email
        
    Returns:
        Tracking pixel image
    """
    try:
        email = email_service.track_email_open(db, tracking_id)
        
        if email and email.campaign_id:
            update_campaign_open_stats(db, email)
        
        # Return a 1x1 transparent pixel
        return "Tracking pixel"
    except SQLAlchemyError as e:
        handle_db_error(e, "Error tracking email opens")


def update_campaign_open_stats(db: Session, email: models.Email) -> None:
    """
    Update campaign statistics when an email is opened.
    
    Args:
        db: Database session
        email: The email that was opened
    """
    if not email.is_opened:  # Only update if first open
        campaign = crud.campaign.get(db, id=email.campaign_id)
        if campaign:
            campaign_service.update_campaign_statistics(
                db=db,
                campaign_id=campaign.id,
                stats={"opened_emails": campaign.opened_emails + 1},
            )


@router.get("/{email_id}", response_model=schemas.EmailMetrics)
def get_email_metrics(
    *,
    db: Session = Depends(deps.get_db),
    email_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get metrics for a specific email.
    
    Args:
        db: Database session
        email_id: ID of the email
        current_user: Authenticated user making the request
        
    Returns:
        Email metrics data
        
    Raises:
        HTTPException: 
            - 404 if email not found
            - 403 if user doesn't have permission
    """
    email = crud.email.get(db, id=email_id)
    if not email:
        handle_entity_not_found("email", email_id)
    
    # Check if email belongs to user's campaign
    if email.campaign_id:
        validate_email_campaign_ownership(db, email, current_user.id)
    
    return email


def validate_email_campaign_ownership(
    db: Session, 
    email: models.Email, 
    user_id: UUID
) -> None:
    """
    Validate that an email's campaign belongs to the user.
    
    Args:
        db: Database session
        email: The email to check
        user_id: ID of the user
        
    Raises:
        HTTPException: 403 if user doesn't have permission
    """
    campaign = crud.campaign.get(db, id=email.campaign_id)
    if not campaign or campaign.user_id != user_id:
        handle_permission_error("email", email.id, user_id)


@router.get("/campaign/{campaign_id}", response_model=List[schemas.EmailMetrics])
def get_campaign_emails(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get all emails for a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        skip: Number of records to skip (for pagination)
        limit: Maximum number of records to return
        current_user: Authenticated user making the request
        
    Returns:
        List of email metrics for the campaign
        
    Raises:
        HTTPException: 
            - 404 if campaign not found
            - 403 if user doesn't have permission
    """
    # Validate campaign access and ownership
    validate_campaign_access(db, campaign_id, current_user.id)
    
    # Get emails for the campaign
    emails = crud.email.get_emails_by_campaign(
        db=db, campaign_id=campaign_id, skip=skip, limit=limit
    )
    
    return emails 