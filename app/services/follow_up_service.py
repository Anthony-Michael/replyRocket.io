"""
Follow-up service for ReplyRocket.io

This module contains business logic for follow-up email operations,
separating it from data access operations in the crud modules.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas, crud
from app.services import email_service, campaign_service, user_service
from app.services.ai_email_generator_service import generate_follow_up
from app.services.email_sender_service import send_email
from app.utils.error_handling import handle_db_error
from app.core.exception_handlers import EntityNotFoundError, PermissionDeniedError

# Set up logger
logger = logging.getLogger(__name__)


def generate_follow_up_email(
    db: Session, 
    original_email_id: UUID, 
    user_id: UUID,
    new_approach: Optional[str] = None
) -> schemas.EmailGenResponse:
    """
    Generate a follow-up email using AI based on the original email.
    
    Args:
        db: Database session
        original_email_id: ID of the original email
        user_id: ID of the user requesting the follow-up
        new_approach: Optional new approach for the follow-up
        
    Returns:
        Generated follow-up email content
        
    Raises:
        EntityNotFoundError: If original email not found
        PermissionDeniedError: If user doesn't have permission to access the email
        HTTPException: If follow-up is not allowed or maximum follow-ups reached
    """
    try:
        # Get the original email
        original_email = email_service.get_email(db, original_email_id)
        if not original_email:
            logger.error(f"Original email {original_email_id} not found")
            raise EntityNotFoundError(entity="email", entity_id=original_email_id)
        
        # Check if email belongs to user's campaign
        if original_email.campaign_id:
            campaign = campaign_service.get_campaign(db, original_email.campaign_id)
            if not campaign or campaign.user_id != user_id:
                logger.warning(f"User {user_id} attempted to access email {original_email_id} without permission")
                raise PermissionDeniedError(entity="email", entity_id=original_email_id, user_id=user_id)
        
        # Check if follow-up is allowed
        if original_email.is_replied:
            logger.warning(f"Cannot create follow-up for replied email {original_email_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create follow-up for an email that has been replied to",
            )
        
        # Get campaign for context
        campaign = None
        if original_email.campaign_id:
            campaign = campaign_service.get_campaign(db, original_email.campaign_id)
            
            # Check if max follow-ups reached
            if campaign and original_email.follow_up_number >= campaign.max_follow_ups:
                logger.warning(f"Maximum number of follow-ups reached for email {original_email_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Maximum number of follow-ups ({campaign.max_follow_ups}) reached",
                )
        
        # Generate follow-up email using AI
        follow_up_content = generate_follow_up(
            original_subject=original_email.subject,
            original_body=original_email.body_text,
            recipient_name=original_email.recipient_name,
            recipient_company=original_email.recipient_company,
            recipient_job_title=original_email.recipient_job_title,
            follow_up_number=original_email.follow_up_number + 1,
            new_approach=new_approach,
        )
        
        return follow_up_content
    except SQLAlchemyError as e:
        logger.error(f"Error generating follow-up email for {original_email_id}: {str(e)}")
        handle_db_error(e, "generate", "follow-up")


def send_follow_up_email(
    db: Session,
    original_email_id: UUID,
    user_id: UUID,
    new_approach: Optional[str] = None
) -> schemas.EmailSendResponse:
    """
    Generate and send a follow-up email.
    
    Args:
        db: Database session
        original_email_id: ID of the original email
        user_id: ID of the user sending the follow-up
        new_approach: Optional new approach for the follow-up
        
    Returns:
        Email send response with tracking information
    """
    try:
        # Get the original email
        original_email = email_service.get_email(db, original_email_id)
        if not original_email:
            logger.error(f"Original email {original_email_id} not found")
            raise EntityNotFoundError(entity="email", entity_id=original_email_id)
        
        # Check if email belongs to user's campaign
        if original_email.campaign_id:
            campaign = campaign_service.get_campaign(db, original_email.campaign_id)
            if not campaign or campaign.user_id != user_id:
                logger.warning(f"User {user_id} attempted to access email {original_email_id} without permission")
                raise PermissionDeniedError(entity="email", entity_id=original_email_id, user_id=user_id)
        
        # Get user
        user = user_service.get_user(db, user_id)
        
        # Generate follow-up email
        follow_up_content = generate_follow_up(
            original_subject=original_email.subject,
            original_body=original_email.body_text,
            recipient_name=original_email.recipient_name,
            recipient_company=original_email.recipient_company,
            recipient_job_title=original_email.recipient_job_title,
            follow_up_number=original_email.follow_up_number + 1,
            new_approach=new_approach,
        )
        
        # Create follow-up email record
        follow_up_email = email_service.create_follow_up(
            db=db,
            original_email_id=original_email.id,
            subject=follow_up_content.subject,
            body_text=follow_up_content.body_text,
            body_html=follow_up_content.body_html,
        )
        
        # Send email
        send_result = send_email(
            recipient_email=original_email.recipient_email,
            recipient_name=original_email.recipient_name,
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
            follow_up_email = email_service.mark_as_sent(db=db, email_id=follow_up_email.id)
            
            # Update campaign stats
            if original_email.campaign_id:
                campaign_service.update_campaign_stats(
                    db=db,
                    campaign_id=original_email.campaign_id,
                    stats={"total_emails": campaign.total_emails + 1},
                )
            
            return {
                "id": follow_up_email.id,
                "is_sent": follow_up_email.is_sent,
                "sent_at": follow_up_email.sent_at,
                "tracking_id": follow_up_email.tracking_id,
            }
        else:
            logger.error(f"Failed to send follow-up email for {original_email_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send follow-up email",
            )
    except SQLAlchemyError as e:
        logger.error(f"Error sending follow-up email for {original_email_id}: {str(e)}")
        handle_db_error(e, "send", "follow-up")


def schedule_follow_ups(db: Session, background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    Schedule follow-up emails for all campaigns.
    
    Args:
        db: Database session
        background_tasks: FastAPI background tasks
        
    Returns:
        Dictionary with success message and count of scheduled follow-ups
    """
    try:
        # Get all emails that need follow-ups
        pending_emails = email_service.get_pending_follow_ups(db)
        scheduled_count = 0
        
        # Schedule follow-ups
        for email in pending_emails:
            # Get campaign
            campaign = campaign_service.get_campaign(db, email.campaign_id)
            
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
            scheduled_count += 1
        
        logger.info(f"Scheduled {scheduled_count} follow-up emails")
        return {"message": f"Follow-ups scheduled: {scheduled_count}"}
    except SQLAlchemyError as e:
        logger.error(f"Error scheduling follow-ups: {str(e)}")
        handle_db_error(e, "schedule", "follow-ups")


async def send_automated_follow_up(db: Session, email_id: UUID, campaign_id: UUID) -> None:
    """
    Send an automated follow-up email.
    
    Args:
        db: Database session
        email_id: ID of the original email
        campaign_id: ID of the campaign
    """
    try:
        # Get email and campaign
        email = email_service.get_email(db, email_id)
        campaign = campaign_service.get_campaign(db, campaign_id)
        
        if not email or not campaign:
            return
        
        # Check if email has been replied to
        if email.is_replied:
            return
        
        # Get user
        user = user_service.get_user(db, campaign.user_id)
        if not user:
            return
        
        # Generate follow-up email
        follow_up_content = generate_follow_up(
            original_subject=email.subject,
            original_body=email.body_text,
            recipient_name=email.recipient_name,
            recipient_company=email.recipient_company,
            recipient_job_title=email.recipient_job_title,
            follow_up_number=email.follow_up_number + 1,
        )
        
        # Create follow-up email record
        follow_up_email = email_service.create_follow_up(
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
            email_service.mark_as_sent(db=db, email_id=follow_up_email.id)
            
            # Update campaign stats
            campaign_service.update_campaign_stats(
                db=db,
                campaign_id=campaign.id,
                stats={"total_emails": campaign.total_emails + 1},
            )
            
            logger.info(f"Sent automated follow-up email {follow_up_email.id} for email {email_id}")
    except Exception as e:
        # Log error but don't raise exception to prevent background task failure
        logger.error(f"Error sending automated follow-up email for {email_id}: {str(e)}") 