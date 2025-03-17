import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base

if TYPE_CHECKING:
    from .email_campaign import EmailCampaign  # noqa: F401


class Email(Base):
    __tablename__ = "emails"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("email_campaigns.id"), nullable=False)
    
    # Recipient information
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String)
    recipient_company = Column(String)
    recipient_job_title = Column(String)
    
    # Email content
    subject = Column(String, nullable=False)
    body_text = Column(Text, nullable=False)
    body_html = Column(Text, nullable=False)
    
    # Email status
    is_sent = Column(Boolean, default=False)
    is_opened = Column(Boolean, default=False)
    is_replied = Column(Boolean, default=False)
    is_converted = Column(Boolean, default=False)
    
    # Tracking
    tracking_id = Column(String, unique=True, index=True)
    num_opens = Column(Integer, default=0)
    
    # Follow-up information
    is_follow_up = Column(Boolean, default=False)
    follow_up_number = Column(Integer, default=0)  # 0 = initial email, 1 = first follow-up, etc.
    original_email_id = Column(UUID(as_uuid=True), ForeignKey("emails.id"), nullable=True)
    
    # A/B testing
    ab_test_variant = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    campaign = relationship("EmailCampaign", back_populates="emails")
    follow_ups = relationship("Email", 
                             foreign_keys=[original_email_id],
                             backref="original_email") 