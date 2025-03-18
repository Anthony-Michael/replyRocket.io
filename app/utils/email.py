"""
Email utility functions for the ReplyRocket application.

This module contains email-related utility functions to reduce code
duplication and improve maintainability across the application.
"""

import logging
import secrets
from typing import Any, Dict

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.db.session import SessionLocal
from app.services.email_sender_service import send_email
from app.utils.error_handling import handle_db_error

# Set up logger
logger = logging.getLogger(__name__)


def validate_email_content(email_content: Any) -> None:
    """
    Validate that the generated email content has all required fields.
    
    Args:
        email_content: The email content to validate
        
    Raises:
        ValueError: If required fields are missing
    """
    required_fields = ["subject", "body_text", "body_html"]
    if not all(key in email_content for key in required_fields):
        logger.error(f"Invalid AI response structure: {email_content}")
        raise ValueError("AI service returned incomplete data")


def validate_email_request(email_request: schemas.EmailSendRequest) -> None:
    """
    Validate the email request data.
    
    Args:
        email_request: The email request to validate
        
    Raises:
        HTTPException: 422 if validation fails
    """
    if not email_request.subject or not email_request.body_text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email subject and body are required",
        )


def create_email_record(
    db: Session, 
    email_request: schemas.EmailSendRequest
) -> models.Email:
    """
    Create a new email record in the database.
    
    Args:
        db: Database session
        email_request: The email request data
        
    Returns:
        The created email object
        
    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        tracking_id = secrets.token_urlsafe(16)
        
        email_obj = crud.email.create_email(
            db=db, 
            obj_in=email_request, 
            campaign_id=email_request.campaign_id,
            tracking_id=tracking_id
        )
        
        return email_obj
    except SQLAlchemyError as e:
        handle_db_error(e, "creating", "email record")


def schedule_email_sending(
    background_tasks: BackgroundTasks,
    email_obj: models.Email,
    user: models.User,
    email_request: schemas.EmailSendRequest
) -> None:
    """
    Schedule the email to be sent as a background task.
    
    Args:
        background_tasks: FastAPI background tasks
        email_obj: The email object to send
        user: The user sending the email
        email_request: The email request data
    """
    background_tasks.add_task(
        send_email_in_background, 
        str(email_obj.id), 
        email_request=email_request,
        smtp_config=get_smtp_config(user),
        sender_name=user.full_name or user.email,
        sender_email=user.email,
    )


def get_smtp_config(user: models.User) -> Dict[str, Any]:
    """
    Get SMTP configuration from user.
    
    Args:
        user: The user with SMTP credentials
        
    Returns:
        SMTP configuration dictionary
    """
    return {
        "host": user.smtp_host,
        "port": int(user.smtp_port),
        "username": user.smtp_user,
        "password": user.smtp_password,
        "use_tls": user.smtp_use_tls,
    }


def create_email_response(email_obj: models.Email) -> Dict[str, Any]:
    """
    Create the response for a newly created email.
    
    Args:
        email_obj: The email object
        
    Returns:
        Response dictionary with tracking information
    """
    return {
        "id": email_obj.id,
        "is_sent": False,  # Will be updated by background task
        "sent_at": None,   # Will be updated by background task
        "tracking_id": email_obj.tracking_id,
    }


def send_email_in_background(
    email_id: str,
    email_request: schemas.EmailSendRequest,
    smtp_config: Dict[str, Any],
    sender_name: str,
    sender_email: str,
) -> None:
    """
    Background task for sending email.
    
    Args:
        email_id: ID of the email to send
        email_request: The email request data
        smtp_config: SMTP configuration dictionary
        sender_name: Name of the sender
        sender_email: Email of the sender
    """
    db = None
    try:
        # Create a new session using context manager to ensure proper cleanup
        with SessionLocal() as db:
            # Get fresh reference to the email object
            email = crud.email.get(db, id=email_id)
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
                smtp_config=smtp_config,
                sender_name=sender_name,
                sender_email=sender_email,
                tracking_id=email.tracking_id,
            )
            
            # Update email and campaign records
            update_records_after_sending(db, email, send_result)
    except SQLAlchemyError as e:
        logger.error(f"Database error in background email sending: {str(e)}", exc_info=True)
        # No need to close the session as the context manager handles it
    except Exception as e:
        logger.error(f"Error in background email sending: {str(e)}", exc_info=True)
        # No need to close the session as the context manager handles it


def update_records_after_sending(
    db: Session, 
    email: models.Email, 
    send_success: bool
) -> None:
    """
    Update database records after sending an email.
    
    Args:
        db: Database session
        email: The email that was sent
        send_success: Whether the email was sent successfully
    """
    if send_success:
        # Mark email as sent
        crud.email.mark_as_sent(db, email_id=email.id)
        
        # Update campaign stats if applicable
        if email.campaign_id:
            campaign = crud.campaign.get(db, id=email.campaign_id)
            if campaign:
                crud.campaign.update_campaign_stats(
                    db,
                    campaign_id=campaign.id,
                    stats={"total_emails": campaign.total_emails + 1},
                )
    else:
        logger.error(f"Failed to send email {email.id}")


def validate_smtp_config(user: models.User) -> None:
    """
    Validate that a user has SMTP credentials configured.
    
    Args:
        user: The user to validate SMTP configuration for
        
    Raises:
        HTTPException: 400 if SMTP credentials are not configured
    """
    if not user.smtp_host or not user.smtp_user or not user.smtp_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP credentials not configured. Please set up your email service first.",
        ) 