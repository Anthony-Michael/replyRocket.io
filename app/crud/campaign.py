from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.campaign import EmailCampaign
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CRUDCampaign(CRUDBase[EmailCampaign, CampaignCreate, CampaignUpdate]):
    def create_with_owner(
        self, db: Session, *, obj_in: CampaignCreate, user_id: UUID
    ) -> EmailCampaign:
        """
        Create a new campaign with owner ID. Pure database operation.
        """
        db_obj = EmailCampaign(**obj_in.dict(), user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_by_owner(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[EmailCampaign]:
        """
        Get multiple campaigns by owner ID. Pure database operation.
        """
        return (
            db.query(self.model)
            .filter(EmailCampaign.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active_by_owner(
        self, db: Session, *, user_id: UUID
    ) -> List[EmailCampaign]:
        """
        Get all active campaigns for a user. Pure database operation.
        """
        return (
            db.query(self.model)
            .filter(EmailCampaign.user_id == user_id, EmailCampaign.is_active == True)
            .all()
        )
    
    def update_stats(
        self, db: Session, *, db_obj: EmailCampaign, stats: Dict[str, int]
    ) -> EmailCampaign:
        """
        Update campaign statistics. Pure database operation.
        """
        for key, value in stats.items():
            if hasattr(db_obj, key):
                setattr(db_obj, key, value)
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def update_ab_testing(
        self, db: Session, *, db_obj: EmailCampaign, variants: Dict[str, str]
    ) -> EmailCampaign:
        """
        Update A/B testing configuration. Pure database operation.
        """
        db_obj.ab_test_active = True
        db_obj.ab_test_variants = variants
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj


campaign = CRUDCampaign(EmailCampaign) 