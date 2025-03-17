import secrets
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.core.config import settings
from app.services.ai_email_generator import generate_email
from app.services.email_sender import send_email

router = APIRouter()


@router.post("/generate", response_model=schemas.EmailGenResponse)
def generate_email_content(
    *,
    db: Session = Depends(deps.get_db),
    email_request: schemas.EmailGenRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Generate an email using AI based on recipient details and campaign context.
    """
    # Check if campaign exists and belongs to user
    if email_request.campaign_id:
        campaign = crud.campaign.get(db, id=email_request.campaign_id)
        if not campaign or campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
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
        
        return email_content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate email: {str(e)}",
        )


@router.post("/send", response_model=schemas.EmailSendResponse)
def send_email_to_recipient(
    *,
    db: Session = Depends(deps.get_db),
    email_request: schemas.EmailSendRequest,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Send an email to a recipient.
    """
    # Check if campaign exists and belongs to user
    if email_request.campaign_id:
        campaign = crud.campaign.get(db, id=email_request.campaign_id)
        if not campaign or campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaign not found",
            )
    
    # Create email record
    email_obj = crud.email.create_email(
        db=db, 
        obj_in=email_request, 
        campaign_id=email_request.campaign_id
    )
    
    # Check if user has SMTP credentials
    if not current_user.smtp_host or not current_user.smtp_user or not current_user.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP credentials not configured. Please set up your email service first.",
        )
    
    # Send email
    try:
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
            tracking_id=email_obj.tracking_id,
        )
        
        if send_result:
            # Mark email as sent
            email_obj = crud.email.mark_as_sent(db=db, email_id=email_obj.id)
            
            # Update campaign stats
            if email_request.campaign_id:
                campaign = crud.campaign.get(db, id=email_request.campaign_id)
                crud.campaign.update_campaign_stats(
                    db=db,
                    campaign_id=campaign.id,
                    stats={"total_emails": campaign.total_emails + 1},
                )
            
            return {
                "id": email_obj.id,
                "is_sent": email_obj.is_sent,
                "sent_at": email_obj.sent_at,
                "tracking_id": email_obj.tracking_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send email",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}",
        )


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