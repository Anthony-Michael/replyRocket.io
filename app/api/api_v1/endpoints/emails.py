import secrets
import logging
from typing import Any, List, Optional, Dict, Union

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings
from app.services.ai_email_generator import generate_email
from app.services.email_sender import send_email
from app.db.session import SessionLocal

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
        HTTPException: If campaign doesn't exist or doesn't belong to user
                      If AI service fails to generate email
    """
    # Check if campaign exists and belongs to user
    if email_request.campaign_id:
        try:
            campaign = crud.campaign.get(db, id=email_request.campaign_id)
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaign not found",
                )
            
            if campaign.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to access this campaign",
                )
        except SQLAlchemyError as e:
            logger.error(f"Database error when retrieving campaign: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while checking campaign",
            )
    
    # Generate email using AI
    try:
        email_content = generate_email(
            recipient_name=email_request.recipient_name,
            recipient_company=email_request.recipient_company,
            recipient_job_title=email_request.recipient_job_title,
            industry=email_request.industry,
            pain_points=email_request.pain_points,
            personalization_notes=email_request.personalization_notes,
        )
        
        # Validate the response structure
        if not all(key in email_content for key in ["subject", "body_text", "body_html"]):
            logger.error(f"Invalid AI response structure: {email_content}")
            raise ValueError("AI service returned incomplete data")
        
        return email_content
    except ValueError as e:
        # Handle validation or data structure errors
        logger.error(f"Value error in email generation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Email generation error: {str(e)}",
        )
    except Exception as e:
        # Log the full exception for debugging
        logger.error(f"Email generation failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate email. Please try again later.",
        )


@router.post("/send", response_model=schemas.EmailSendResponse, status_code=status.HTTP_201_CREATED)
def send_email_to_recipient(
    *,
    db: Session = Depends(deps.get_db),
    email_request: schemas.EmailSendRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
    background_tasks: BackgroundTasks,
) -> Any:
    """
    Send an email to a recipient.
    
    Args:
        db: Database session
        email_request: Email send request with recipient and content details
        current_user: Authenticated user making the request
        background_tasks: FastAPI background tasks for async processing
        
    Returns:
        Email record with tracking information
        
    Raises:
        HTTPException: For various validation and processing errors
    """
    # Validate input data
    if not email_request.subject or not email_request.body_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email subject and body are required",
        )
    
    # Check if campaign exists and belongs to user
    if email_request.campaign_id:
        try:
            campaign = crud.campaign.get(db, id=email_request.campaign_id)
            if not campaign:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaign not found",
                )
            
            if campaign.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions to access this campaign",
                )
        except SQLAlchemyError as e:
            logger.error(f"Database error when retrieving campaign: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error occurred while checking campaign",
            )
    
    # Check if user has SMTP credentials
    if not current_user.smtp_host or not current_user.smtp_user or not current_user.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP credentials not configured. Please set up your email service first.",
        )
    
    # Generate tracking ID
    tracking_id = secrets.token_urlsafe(16)
    
    # Create email record
    try:
        email_obj = crud.email.create_email(
            db=db, 
            obj_in=email_request, 
            campaign_id=email_request.campaign_id,
            tracking_id=tracking_id
        )
    except SQLAlchemyError as e:
        logger.error(f"Failed to create email record: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create email record in database",
        )
    
    # Function for background task
    def send_email_in_background(email_id: str):
        """Background task for sending email to avoid blocking the main thread"""
        with SessionLocal() as task_db:
            try:
                # Get fresh reference to the email object
                email = crud.email.get(task_db, id=email_id)
                if not email:
                    logger.error(f"Email {email_id} not found for background sending")
                    return
                
                # Send the email
                send_result = send_email(
                    recipient_email=email_request.recipient_email,
                    recipient_name=email_request.recipient_name,
                    subject=email_request.subject,
                    body_text=email_request.body_text,
                    body_html=email_request.body_html,
                    smtp_config={
                        "host": current_user.smtp_host,
                        "port": int(current_user.smtp_port),
                        "username": current_user.smtp_user,
                        "password": current_user.smtp_password,
                        "use_tls": current_user.smtp_use_tls,
                    },
                    sender_name=current_user.full_name or current_user.email,
                    sender_email=current_user.email,
                    tracking_id=email.tracking_id,
                )
                
                if send_result:
                    # Mark email as sent
                    crud.email.mark_as_sent(task_db, email_id=email.id)
                    
                    # Update campaign stats if applicable
                    if email.campaign_id:
                        campaign = crud.campaign.get(task_db, id=email.campaign_id)
                        if campaign:
                            crud.campaign.update_campaign_stats(
                                task_db,
                                campaign_id=campaign.id,
                                stats={"total_emails": campaign.total_emails + 1},
                            )
                else:
                    logger.error(f"Failed to send email {email_id}")
            except Exception as e:
                logger.error(f"Error in background email sending: {str(e)}", exc_info=True)
    
    # Schedule email to be sent in the background
    background_tasks.add_task(send_email_in_background, str(email_obj.id))
    
    # Return immediate response with tracking info
    return {
        "id": email_obj.id,
        "is_sent": False,  # Will be updated by background task
        "sent_at": None,   # Will be updated by background task
        "tracking_id": email_obj.tracking_id,
    }


@router.get("/tracking/{tracking_id}")
def track_email_open(
    *,
    db: Session = Depends(deps.get_db),
    tracking_id: str,
) -> Any:
    """
    Track email opens via a tracking pixel.
    """
    email = crud.email.mark_as_opened(db=db, tracking_id=tracking_id)
    
    if email and email.campaign_id:
        campaign = crud.campaign.get(db, id=email.campaign_id)
        if campaign and not email.is_opened:
            crud.campaign.update_campaign_stats(
                db=db,
                campaign_id=campaign.id,
                stats={"opened_emails": campaign.opened_emails + 1},
            )
    
    # Return a 1x1 transparent pixel
    return "Tracking pixel"


@router.get("/{email_id}", response_model=schemas.EmailMetrics)
def get_email_metrics(
    *,
    db: Session = Depends(deps.get_db),
    email_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get metrics for a specific email.
    """
    email = crud.email.get(db, id=email_id)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found",
        )
    
    # Check if email belongs to user's campaign
    if email.campaign_id:
        campaign = crud.campaign.get(db, id=email.campaign_id)
        if not campaign or campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
    
    return email


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
    """
    campaign = crud.campaign.get(db, id=campaign_id)
    if not campaign or campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    
    emails = crud.email.get_emails_by_campaign(
        db=db, campaign_id=campaign_id, skip=skip, limit=limit
    )
    
    return emails 