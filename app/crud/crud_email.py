import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.email import Email
from app.schemas.email import EmailSendRequest


class CRUDEmail(CRUDBase[Email, EmailSendRequest, Any]):
    def create_email(
        self, db: Session, *, obj_in: EmailSendRequest, campaign_id: UUID
    ) -> Email:
        """
        Create a new email.
        """
        tracking_id = secrets.token_urlsafe(16)
        
        db_obj = Email(
            campaign_id=campaign_id,
            recipient_email=obj_in.recipient_email,
            recipient_name=obj_in.recipient_name,
            subject=obj_in.subject,
            body_text=obj_in.body_text,
            body_html=obj_in.body_html,
            ab_test_variant=obj_in.ab_test_variant,
            tracking_id=tracking_id,
        )
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def mark_as_sent(self, db: Session, *, email_id: UUID) -> Email:
        """
        Mark an email as sent.
        """
        email = self.get(db, id=email_id)
        email.is_sent = True
        email.sent_at = datetime.utcnow()
        
        db.add(email)
        db.commit()
        db.refresh(email)
        return email
    
    def mark_as_opened(self, db: Session, *, tracking_id: str) -> Optional[Email]:
        """
        Mark an email as opened.
        """
        email = db.query(Email).filter(Email.tracking_id == tracking_id).first()
        if not email:
            return None
        
        email.is_opened = True
        if not email.opened_at:  # Only record first open time
            email.opened_at = datetime.utcnow()
        
        email.num_opens += 1
        
        db.add(email)
        db.commit()
        db.refresh(email)
        return email
    
    def mark_as_replied(self, db: Session, *, email_id: UUID) -> Email:
        """
        Mark an email as replied.
        """
        email = self.get(db, id=email_id)
        email.is_replied = True
        email.replied_at = datetime.utcnow()
        
        db.add(email)
        db.commit()
        db.refresh(email)
        return email
    
    def mark_as_converted(self, db: Session, *, email_id: UUID) -> Email:
        """
        Mark an email as converted.
        """
        email = self.get(db, id=email_id)
        email.is_converted = True
        email.converted_at = datetime.utcnow()
        
        db.add(email)
        db.commit()
        db.refresh(email)
        return email
    
    def get_pending_follow_ups(self, db: Session) -> List[Email]:
        """
        Get all emails that need follow-ups.
        """
        from app.models.email_campaign import EmailCampaign
        
        # Emails that are sent but not replied, and their campaign allows follow-ups
        return (
            db.query(Email)
            .join(EmailCampaign, Email.campaign_id == EmailCampaign.id)
            .filter(
                and_(
                    Email.is_sent == True,
                    Email.is_replied == False,
                    Email.is_follow_up == False,  # Not already a follow-up
                    EmailCampaign.max_follow_ups > 0,  # Campaign allows follow-ups
                )
            )
            .all()
        )
    
    def create_follow_up(
        self, db: Session, *, original_email_id: UUID, subject: str, body_text: str, body_html: str
    ) -> Email:
        """
        Create a follow-up email.
        """
        original_email = self.get(db, id=original_email_id)
        
        follow_up = Email(
            campaign_id=original_email.campaign_id,
            recipient_email=original_email.recipient_email,
            recipient_name=original_email.recipient_name,
            recipient_company=original_email.recipient_company,
            recipient_job_title=original_email.recipient_job_title,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            is_follow_up=True,
            follow_up_number=original_email.follow_up_number + 1,
            original_email_id=original_email_id,
            tracking_id=secrets.token_urlsafe(16),
        )
        
        db.add(follow_up)
        db.commit()
        db.refresh(follow_up)
        return follow_up
    
    def get_emails_by_campaign(
        self, db: Session, *, campaign_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Email]:
        """
        Get emails by campaign ID.
        """
        return (
            db.query(Email)
            .filter(Email.campaign_id == campaign_id)
            .order_by(desc(Email.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )


email = CRUDEmail(Email) 