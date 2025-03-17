"""
Schemas initialization module.

This file imports all Pydantic schemas and makes them available at the app.schemas namespace level.
This enables imports like 'from app.schemas import Token' to work properly.
"""

# Import Token schema from token.py
from app.schemas.token import Token, TokenPayload

# Import User schemas from user.py
from app.schemas.user import User, UserCreate, UserInDB, UserUpdate

# Import Email schemas from email.py
from app.schemas.email import (
    Email, 
    EmailBase, 
    EmailCreate, 
    EmailUpdate, 
    EmailGenRequest, 
    EmailGenResponse, 
    EmailSendRequest, 
    EmailSendResponse, 
    EmailMetrics,
    FollowUpRequest
)

# Import Campaign schemas from campaign.py
from app.schemas.campaign import Campaign, CampaignCreate, CampaignStats, CampaignUpdate

# Import A/B Testing configuration schema from ab_test_config.py
from app.schemas.ab_test_config import ABTestConfig, ABTestConfigCreate, ABTestConfigUpdate

# Define __all__ to explicitly specify what is exported from this package
__all__ = [
    # Token schemas
    "Token",
    "TokenPayload",
    
    # User schemas
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    
    # Email schemas
    "Email",
    "EmailBase",
    "EmailCreate",
    "EmailUpdate",
    "EmailGenRequest",
    "EmailGenResponse",
    "EmailSendRequest",
    "EmailSendResponse",
    "EmailMetrics",
    "FollowUpRequest",
    
    # Campaign schemas
    "Campaign",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignStats",
    
    # A/B Testing schemas
    "ABTestConfig",
    "ABTestConfigCreate",
    "ABTestConfigUpdate"
] 