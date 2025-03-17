from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


# Base schema for campaign
class CampaignBase(BaseModel):
    name: str
    description: Optional[str] = None
    industry: str
    target_job_title: str
    pain_points: str
    follow_up_days: Optional[int] = 3
    max_follow_ups: Optional[int] = 2
    ab_test_active: Optional[bool] = False


# Create campaign
class CampaignCreate(CampaignBase):
    pass


# Update campaign
class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    target_job_title: Optional[str] = None
    pain_points: Optional[str] = None
    follow_up_days: Optional[int] = None
    max_follow_ups: Optional[int] = None
    ab_test_active: Optional[bool] = None
    is_active: Optional[bool] = None


# Campaign in DB
class CampaignInDBBase(CampaignBase):
    id: UUID
    user_id: UUID
    total_emails: int
    opened_emails: int
    replied_emails: int
    converted_emails: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# Campaign for API response
class Campaign(CampaignInDBBase):
    pass


# A/B Test Configuration
class ABTestConfig(BaseModel):
    campaign_id: UUID
    variants: Dict[str, str]  # e.g., {"A": "Professional tone", "B": "Friendly tone"}


# Campaign stats response
class CampaignStats(BaseModel):
    id: UUID
    name: str
    total_emails: int
    opened_emails: int
    replied_emails: int
    converted_emails: int
    open_rate: float
    reply_rate: float
    conversion_rate: float
    ab_test_results: Optional[Dict] = None 