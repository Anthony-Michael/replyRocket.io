from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False


# Properties to receive via API on creation
class UserCreate(UserBase):
    email: EmailStr
    password: str


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None


# Additional properties to return via API
class UserInDBBase(UserBase):
    id: UUID
    subscription_active: bool = False
    subscription_plan: Optional[str] = None
    
    class Config:
        from_attributes = True


# Additional properties stored in DB
class UserInDB(UserInDBBase):
    hashed_password: str
    stripe_customer_id: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True


# Return model
class User(UserInDBBase):
    pass


# SMTP Config
class SMTPConfig(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_use_tls: bool = True 