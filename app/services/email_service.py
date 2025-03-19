"""
Email service for ReplyRocket.io

This module contains business logic for email operations,
separating it from data access operations in the crud modules.
"""

import logging
import secrets
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import and_, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas, crud
from app.db.session import SessionLocal
from app.services.email_sender_service import send_email
from app.utils.error_handling import handle_db_error

# Set up logger
logger = logging.getLogger(__name__)


def create_email(db: Session, email_data: schemas.EmailSendRequest, campaign_id: UUID) -> models.Email:
    """
    Create a new email record.
    
    Args:
        db: Database session
        email_data: Email data
        campaign_id: ID of the campaign
        
    Returns:
        New Email object
    """
    try:
        # Generate tracking ID
        tracking_id = secrets.token_urlsafe(16)
        
        # Create email object using CRUD operation
        obj_data = {
            "recipient_email": email_data.recipient_email,
            "recipient_name": email_data.recipient_name,
            "subject": email_data.subject,
            "body_text": email_data.body_text,
            "body_html": email_data.body_html,
            "ab_test_variant": email_data.ab_test_variant
        }
        
        # Add optional fields if present
        if hasattr(email_data, "recipient_company") and email_data.recipient_company:
            obj_data["recipient_company"] = email_data.recipient_company
            
        if hasattr(email_data, "recipient_job_title") and email_data.recipient_job_title:
            obj_data["recipient_job_title"] = email_data.recipient_job_title
        
        db_obj = crud.email.create_with_tracking(db, obj_in=obj_data, campaign_id=campaign_id, tracking_id=tracking_id)
        
        logger.info(f"Created email {db_obj.id} for campaign {campaign_id}")
        return db_obj
    except SQLAlchemyError as e:
        logger.error(f"Error creating email for campaign {campaign_id}: {str(e)}")
        handle_db_error(e)


def get_email(db: Session, email_id: UUID) -> Optional[models.Email]:
    """
    Get an email by ID.
    
    Args:
        db: Database session
        email_id: ID of the email
        
    Returns:
        Email object or None if not found
    """
    try:
        return crud.email.get(db, id=email_id)
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving email {email_id}: {str(e)}")
        handle_db_error(e)


def get_email_by_tracking_id(db: Session, tracking_id: str) -> Optional[models.Email]:
    """
    Get an email by tracking ID.
    
    Args:
        db: Database session
        tracking_id: Tracking ID of the email
        
    Returns:
        Email object or None if not found
    """
    try:
        return crud.email.get_by_tracking_id(db, tracking_id=tracking_id)
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving email with tracking ID {tracking_id}: {str(e)}")
        handle_db_error(e)


def mark_as_sent(db: Session, email_id: UUID) -> models.Email:
    """
    Mark an email as sent.
    
    Args:
        db: Database session
        email_id: ID of the email
        
    Returns:
        Updated Email object
    """
    try:
        email = get_email(db, email_id)
        if not email:
            logger.error(f"Email {email_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found",
            )
            
        return crud.email.update_sent_status(db, db_obj=email, is_sent=True)
    except SQLAlchemyError as e:
        logger.error(f"Error marking email {email_id} as sent: {str(e)}")
        handle_db_error(e)


def mark_as_opened(db: Session, tracking_id: str) -> Optional[models.Email]:
    """
    Mark an email as opened.
    
    Args:
        db: Database session
        tracking_id: Tracking ID of the email
        
    Returns:
        Updated Email object or None if not found
    """
    try:
        email = get_email_by_tracking_id(db, tracking_id)
        if not email:
            logger.warning(f"Email with tracking ID {tracking_id} not found")
            return None
        
        return crud.email.update_opened_status(db, db_obj=email, is_opened=True)
    except SQLAlchemyError as e:
        logger.error(f"Error marking email with tracking ID {tracking_id} as opened: {str(e)}")
        handle_db_error(e)


def mark_as_replied(db: Session, email_id: UUID) -> models.Email:
    """
    Mark an email as replied.
    
    Args:
        db: Database session
        email_id: ID of the email
        
    Returns:
        Updated Email object
    """
    try:
        email = get_email(db, email_id)
        if not email:
            logger.error(f"Email {email_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found",
            )
            
        return crud.email.update_replied_status(db, db_obj=email, is_replied=True)
    except SQLAlchemyError as e:
        logger.error(f"Error marking email {email_id} as replied: {str(e)}")
        handle_db_error(e)


def mark_as_converted(db: Session, email_id: UUID) -> models.Email:
    """
    Mark an email as converted.
    
    Args:
        db: Database session
        email_id: ID of the email
        
    Returns:
        Updated Email object
    """
    try:
        email = get_email(db, email_id)
        if not email:
            logger.error(f"Email {email_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found",
            )
            
        return crud.email.update_converted_status(db, db_obj=email, is_converted=True)
    except SQLAlchemyError as e:
        logger.error(f"Error marking email {email_id} as converted: {str(e)}")
        handle_db_error(e)


def get_pending_follow_ups(db: Session) -> List[models.Email]:
    """
    Get all emails that need follow-ups.
    
    Args:
        db: Database session
        
    Returns:
        List of Email objects that need follow-ups
    """
    try:
        return crud.email.get_pending_follow_up_candidates(db)
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving pending follow-ups: {str(e)}")
        handle_db_error(e)


def create_follow_up(
    db: Session, original_email_id: UUID, subject: str, body_text: str, body_html: str
) -> models.Email:
    """
    Create a follow-up email.
    
    Args:
        db: Database session
        original_email_id: ID of the original email
        subject: Subject line of the follow-up
        body_text: Plain text body of the follow-up
        body_html: HTML body of the follow-up
        
    Returns:
        New follow-up Email object
    """
    try:
        original_email = get_email(db, original_email_id)
        if not original_email:
            logger.error(f"Original email {original_email_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original email not found",
            )
            
        # Create the follow-up using CRUD operation
        obj_data = {
            "recipient_email": original_email.recipient_email,
            "recipient_name": original_email.recipient_name,
            "recipient_company": original_email.recipient_company,
            "recipient_job_title": original_email.recipient_job_title,
            "subject": subject,
            "body_text": body_text,
            "body_html": body_html,
            "is_follow_up": True,
            "follow_up_number": original_email.follow_up_number + 1,
            "original_email_id": original_email_id
        }
        
        follow_up = crud.email.create_with_tracking(
            db, 
            obj_in=obj_data, 
            campaign_id=original_email.campaign_id
        )
        
        logger.info(f"Created follow-up email {follow_up.id} for original email {original_email_id}")
        return follow_up
    except SQLAlchemyError as e:
        logger.error(f"Error creating follow-up for email {original_email_id}: {str(e)}")
        handle_db_error(e)


def get_emails_by_campaign(
    db: Session, campaign_id: UUID, skip: int = 0, limit: int = 100
) -> List[models.Email]:
    """
    Get emails by campaign ID.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Email objects for the campaign
    """
    try:
        return crud.email.get_multi_by_campaign(db, campaign_id=campaign_id, skip=skip, limit=limit)
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving emails for campaign {campaign_id}: {str(e)}")
        handle_db_error(e)


def delete_email(db: Session, email_id: UUID) -> models.Email:
    """
    Delete an email.
    
    Args:
        db: Database session
        email_id: ID of the email to delete
        
    Returns:
        Deleted Email object
    """
    try:
        email = get_email(db, email_id)
        if not email:
            logger.error(f"Email {email_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Email not found",
            )
            
        return crud.email.remove(db, id=email_id)
    except SQLAlchemyError as e:
        logger.error(f"Error deleting email {email_id}: {str(e)}")
        handle_db_error(e)


def track_email_open(db: Session, tracking_id: str) -> Optional[models.Email]:
    """
    Track an email open event by marking the email as opened.
    
    Args:
        db: Database session
        tracking_id: Tracking ID of the email
        
    Returns:
        Updated Email object or None if not found
    """
    try:
        # Mark the email as opened
        return mark_as_opened(db, tracking_id)
    except SQLAlchemyError as e:
        logger.error(f"Error tracking email open for tracking ID {tracking_id}: {str(e)}")
        handle_db_error(e)

# Keep the rest of your email service functionality
# ... existing code for sending emails, scheduling, etc. 