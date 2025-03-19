import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.email import Email
from app.schemas.email import EmailCreate, EmailUpdate
from app.models.campaign import EmailCampaign


class CRUDEmail(CRUDBase[Email, EmailCreate, EmailUpdate]):
    def create_with_tracking(
        self, db: Session, *, obj_in: dict, campaign_id: UUID, tracking_id: str = None
    ) -> Email:
        """
        Create a new email with tracking ID. Pure database operation.
        """
        if not tracking_id:
            tracking_id = secrets.token_urlsafe(16)
            
        db_obj = Email(
            campaign_id=campaign_id,
            tracking_id=tracking_id,
            **obj_in
        )
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_sent_status(self, db: Session, *, db_obj: Email, is_sent: bool = True) -> Email:
        """
        Update email sent status. Pure database operation.
        """
        db_obj.is_sent = is_sent
        if is_sent:
            db_obj.sent_at = datetime.utcnow()
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_opened_status(self, db: Session, *, db_obj: Email, is_opened: bool = True) -> Email:
        """
        Update email opened status. Pure database operation.
        """
        db_obj.is_opened = is_opened
        if is_opened and not db_obj.opened_at:  # Only record first open time
            db_obj.opened_at = datetime.utcnow()
        
        db_obj.num_opens += 1
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_replied_status(self, db: Session, *, db_obj: Email, is_replied: bool = True) -> Email:
        """
        Update email replied status. Pure database operation.
        """
        db_obj.is_replied = is_replied
        if is_replied:
            db_obj.replied_at = datetime.utcnow()
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_converted_status(self, db: Session, *, db_obj: Email, is_converted: bool = True) -> Email:
        """
        Update email converted status. Pure database operation.
        """
        db_obj.is_converted = is_converted
        if is_converted:
            db_obj.converted_at = datetime.utcnow()
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def get_by_tracking_id(self, db: Session, *, tracking_id: str) -> Optional[Email]:
        """
        Get email by tracking ID. Pure database operation.
        """
        return db.query(Email).filter(Email.tracking_id == tracking_id).first()
    
    def get_pending_follow_up_candidates(self, db: Session) -> List[Email]:
        """
        Get all emails that are candidates for follow-ups. Pure database operation.
        """
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
    
    def get_multi_by_campaign(
        self, db: Session, *, campaign_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[Email]:
        """
        Get emails by campaign ID. Pure database operation.
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