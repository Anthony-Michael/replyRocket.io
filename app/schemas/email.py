from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr


# Base schema for email generation
class EmailGenRequest(BaseModel):
    recipient_name: str
    recipient_email: EmailStr
    recipient_company: Optional[str] = None
    recipient_job_title: Optional[str] = None
    industry: str
    pain_points: List[str]
    personalization_notes: Optional[str] = None
    campaign_id: Optional[UUID] = None


# Response from AI email generation
class EmailGenResponse(BaseModel):
    subject: str
    body_text: str
    body_html: str
    variant: Optional[str] = None


# Base schema for sending email
class EmailSendRequest(BaseModel):
    recipient_email: EmailStr
    recipient_name: Optional[str] = None
    subject: str
    body_text: str
    body_html: str
    campaign_id: Optional[UUID] = None
    ab_test_variant: Optional[str] = None


# Response after sending email
class EmailSendResponse(BaseModel):
    id: UUID
    is_sent: bool
    sent_at: Optional[datetime] = None
    tracking_id: str


# Request for follow-up
class FollowUpRequest(BaseModel):
    original_email_id: UUID
    new_approach: Optional[str] = None  # Instructions for AI on how to approach follow-up


# Email metrics response
class EmailMetrics(BaseModel):
    id: UUID
    is_sent: bool
    is_opened: bool
    is_replied: bool
    is_converted: bool
    num_opens: int
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    converted_at: Optional[datetime] = None 