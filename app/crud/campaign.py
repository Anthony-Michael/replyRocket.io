from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.base import CRUDBase
from app.models.campaign import EmailCampaign
from app.schemas.campaign import CampaignCreate, CampaignUpdate


class CRUDCampaign(CRUDBase[EmailCampaign, CampaignCreate, CampaignUpdate]):
    def create_with_user(
        self, db: Session, *, obj_in: CampaignCreate, user_id: UUID
    ) -> EmailCampaign:
        """
        Create a new campaign with user ID.
        """
        obj_in_data = obj_in.dict()
        db_obj = EmailCampaign(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_by_user(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> List[EmailCampaign]:
        """
        Get multiple campaigns by user ID.
        """
        return (
            db.query(self.model)
            .filter(EmailCampaign.user_id == user_id)
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_active_campaigns_for_user(
        self, db: Session, *, user_id: UUID
    ) -> List[EmailCampaign]:
        """
        Get all active campaigns for a user.
        """
        return (
            db.query(self.model)
            .filter(EmailCampaign.user_id == user_id, EmailCampaign.is_active == True)
            .all()
        )
    
    def update_campaign_stats(
        self, db: Session, *, campaign_id: UUID, stats: Dict[str, int]
    ) -> EmailCampaign:
        """
        Update campaign statistics.
        """
        campaign = self.get(db, id=campaign_id)
        for key, value in stats.items():
            if hasattr(campaign, key):
                setattr(campaign, key, value)
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign
    
    def configure_ab_testing(
        self, db: Session, *, campaign_id: UUID, variants: Dict[str, str]
    ) -> EmailCampaign:
        """
        Configure A/B testing for a campaign.
        """
        campaign = self.get(db, id=campaign_id)
        campaign.ab_test_active = True
        campaign.ab_test_variants = variants
        
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        return campaign


campaign = CRUDCampaign(EmailCampaign) 