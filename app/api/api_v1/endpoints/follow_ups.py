from datetime import datetime, timedelta
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps
from app.services.ai_email_generator_service import generate_follow_up
from app.services.email_sender_service import send_email

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
    # Get the original email
    original_email = crud.email.get(db, id=follow_up_request.original_email_id)
    if not original_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original email not found",
        )
    
    # Check if email belongs to user's campaign
    if original_email.campaign_id:
        campaign = crud.campaign.get(db, id=original_email.campaign_id)
        if not campaign or campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
    
    # Check if follow-up is allowed
    if original_email.is_replied:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create follow-up for an email that has been replied to",
        )
    
    # Get campaign for context
    campaign = None
    if original_email.campaign_id:
        campaign = crud.campaign.get(db, id=original_email.campaign_id)
        
        # Check if max follow-ups reached
        if campaign and original_email.follow_up_number >= campaign.max_follow_ups:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum number of follow-ups ({campaign.max_follow_ups}) reached",
            )
    
    # Generate follow-up email using AI
    try:
        follow_up_content = generate_follow_up(
            original_subject=original_email.subject,
            original_body=original_email.body_text,
            recipient_name=original_email.recipient_name,
            recipient_company=original_email.recipient_company,
            recipient_job_title=original_email.recipient_job_title,
            follow_up_number=original_email.follow_up_number + 1,
            new_approach=follow_up_request.new_approach,
        )
        
        return follow_up_content
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate follow-up email: {str(e)}",
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
    # Get the original email
    original_email = crud.email.get(db, id=follow_up_request.original_email_id)
    if not original_email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original email not found",
        )
    
    # Check if email belongs to user's campaign
    if original_email.campaign_id:
        campaign = crud.campaign.get(db, id=original_email.campaign_id)
        if not campaign or campaign.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
    
    # Generate follow-up email
    follow_up_content = generate_follow_up(
        original_subject=original_email.subject,
        original_body=original_email.body_text,
        recipient_name=original_email.recipient_name,
        recipient_company=original_email.recipient_company,
        recipient_job_title=original_email.recipient_job_title,
        follow_up_number=original_email.follow_up_number + 1,
        new_approach=follow_up_request.new_approach,
    )
    
    # Create follow-up email record
    follow_up_email = crud.email.create_follow_up(
        db=db,
        original_email_id=original_email.id,
        subject=follow_up_content.subject,
        body_text=follow_up_content.body_text,
        body_html=follow_up_content.body_html,
    )
    
    # Send email
    try:
        send_result = send_email(
            recipient_email=original_email.recipient_email,
            recipient_name=original_email.recipient_name,
            subject=follow_up_content.subject,
            body_text=follow_up_content.body_text,
            body_html=follow_up_content.body_html,
            smtp_config={
                "host": current_user.smtp_host,
                "port": int(current_user.smtp_port),
                "username": current_user.smtp_user,
                "password": current_user.smtp_password,
                "use_tls": current_user.smtp_use_tls,
            },
            sender_name=current_user.full_name or current_user.email,
            sender_email=current_user.email,
            tracking_id=follow_up_email.tracking_id,
        )
        
        if send_result:
            # Mark email as sent
            follow_up_email = crud.email.mark_as_sent(db=db, email_id=follow_up_email.id)
            
            # Update campaign stats
            if original_email.campaign_id:
                campaign = crud.campaign.get(db, id=original_email.campaign_id)
                crud.campaign.update_campaign_stats(
                    db=db,
                    campaign_id=campaign.id,
                    stats={"total_emails": campaign.total_emails + 1},
                )
            
            return {
                "id": follow_up_email.id,
                "is_sent": follow_up_email.is_sent,
                "sent_at": follow_up_email.sent_at,
                "tracking_id": follow_up_email.tracking_id,
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send follow-up email",
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send follow-up email: {str(e)}",
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
    # Get all emails that need follow-ups
    pending_emails = crud.email.get_pending_follow_ups(db)
    
    # Schedule follow-ups
    for email in pending_emails:
        # Get campaign
        campaign = crud.campaign.get(db, id=email.campaign_id)
        
        # Check if campaign is active
        if not campaign or not campaign.is_active:
            continue
        
        # Check if follow-up is due
        follow_up_due_date = email.sent_at + timedelta(days=campaign.follow_up_days)
        if datetime.utcnow() < follow_up_due_date:
            continue
        
        # Check if max follow-ups reached
        if email.follow_up_number >= campaign.max_follow_ups:
            continue
        
        # Schedule follow-up
        background_tasks.add_task(
            send_automated_follow_up,
            db=db,
            email_id=email.id,
            campaign_id=campaign.id,
        )
    
    return {"message": "Follow-ups scheduled"}


async def send_automated_follow_up(db: Session, email_id: str, campaign_id: str) -> None:
    """
    Send an automated follow-up email.
    """
    # Get email and campaign
    email = crud.email.get(db, id=email_id)
    campaign = crud.campaign.get(db, id=campaign_id)
    
    if not email or not campaign:
        return
    
    # Check if email has been replied to
    if email.is_replied:
        return
    
    # Get user
    user = crud.user.get(db, id=campaign.user_id)
    if not user:
        return
    
    # Generate follow-up email
    try:
        follow_up_content = generate_follow_up(
            original_subject=email.subject,
            original_body=email.body_text,
            recipient_name=email.recipient_name,
            recipient_company=email.recipient_company,
            recipient_job_title=email.recipient_job_title,
            follow_up_number=email.follow_up_number + 1,
        )
        
        # Create follow-up email record
        follow_up_email = crud.email.create_follow_up(
            db=db,
            original_email_id=email.id,
            subject=follow_up_content.subject,
            body_text=follow_up_content.body_text,
            body_html=follow_up_content.body_html,
        )
        
        # Send email
        send_result = send_email(
            recipient_email=email.recipient_email,
            recipient_name=email.recipient_name,
            subject=follow_up_content.subject,
            body_text=follow_up_content.body_text,
            body_html=follow_up_content.body_html,
            smtp_config={
                "host": user.smtp_host,
                "port": int(user.smtp_port),
                "username": user.smtp_user,
                "password": user.smtp_password,
                "use_tls": user.smtp_use_tls,
            },
            sender_name=user.full_name or user.email,
            sender_email=user.email,
            tracking_id=follow_up_email.tracking_id,
        )
        
        if send_result:
            # Mark email as sent
            crud.email.mark_as_sent(db=db, email_id=follow_up_email.id)
            
            # Update campaign stats
            crud.campaign.update_campaign_stats(
                db=db,
                campaign_id=campaign.id,
                stats={"total_emails": campaign.total_emails + 1},
            )
    except Exception:
        # Log error but don't raise exception
        pass 