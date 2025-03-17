import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.session import Base

if TYPE_CHECKING:
    from .user import User  # noqa: F401
    from .email import Email  # noqa: F401


class EmailCampaign(Base):
    __tablename__ = "email_campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Campaign settings
    industry = Column(String)
    target_job_title = Column(String)
    pain_points = Column(Text)
    follow_up_days = Column(Integer, default=3)  # Days to wait before follow-up
    max_follow_ups = Column(Integer, default=2)  # Maximum number of follow-ups
    
    # Campaign statistics
    total_emails = Column(Integer, default=0)
    opened_emails = Column(Integer, default=0)
    replied_emails = Column(Integer, default=0)
    converted_emails = Column(Integer, default=0)
    
    # A/B testing data
    ab_test_active = Column(Boolean, default=False)
    ab_test_variants = Column(JSONB, default={})
    ab_test_results = Column(JSONB, default={})
    
    # Campaign status
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="email_campaigns")
    emails = relationship("Email", back_populates="campaign") 