import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base

if TYPE_CHECKING:
    from .email_campaign import EmailCampaign  # noqa: F401


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    company_name = Column(String, index=True)
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    
    # Subscription related fields
    stripe_customer_id = Column(String, unique=True, index=True, nullable=True)
    subscription_active = Column(Boolean(), default=False)
    subscription_plan = Column(String, nullable=True)
    
    # SMTP credentials (encrypted in database)
    smtp_host = Column(String, nullable=True)
    smtp_port = Column(String, nullable=True)
    smtp_user = Column(String, nullable=True)
    smtp_password = Column(String, nullable=True)
    smtp_use_tls = Column(Boolean(), default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    email_campaigns = relationship("EmailCampaign", back_populates="user") 