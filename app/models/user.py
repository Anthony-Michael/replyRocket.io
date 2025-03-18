import uuid
from typing import TYPE_CHECKING
from datetime import datetime
from typing import List, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, String, func, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID as UUIDPG
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import relationship

from app.db.session import Base

if TYPE_CHECKING:
    from .email_campaign import EmailCampaign  # noqa: F401


# Custom UUID type for SQLite compatibility
class SQLAlchemyUUID(TypeDecorator):
    """Platform-independent UUID type.
    
    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36).
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUIDPG())
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(value))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                value = uuid.UUID(value)
            return value


class User(Base):
    __tablename__ = "users"

    id = Column(SQLAlchemyUUID, primary_key=True, index=True, default=uuid4)
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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    email_campaigns = relationship("EmailCampaign", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    
    id = Column(SQLAlchemyUUID, primary_key=True, index=True, default=uuid4)
    token = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(SQLAlchemyUUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens") 