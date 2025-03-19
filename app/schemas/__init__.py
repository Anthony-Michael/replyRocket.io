"""
Schemas initialization module.

This file imports all Pydantic schemas and makes them available at the app.schemas namespace level.
This enables imports like 'from app.schemas import Token' to work properly.
"""

# Import Token schema from token.py
from app.schemas.token import (
    Token,
    TokenPayload, 
    TokenRefresh, 
    CookieTokenResponse,
    AccessToken,
    RefreshTokenCreate,
    RefreshTokenDB,
    TokenWithoutRefresh,
)

# Import User schemas from user.py
from app.schemas.user import (
    User, 
    UserCreate, 
    UserUpdate, 
    UserInDB,
    SMTPConfig,
)

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
    FollowUpRequest,
    EmailInDB,
)

# Import Campaign schemas from campaign.py
from app.schemas.campaign import (
    Campaign, 
    CampaignCreate, 
    CampaignUpdate, 
    CampaignInDB,
    CampaignStats,
)

# Import A/B Testing configuration schema from ab_test.py
from app.schemas.ab_test import ABTestConfig

# Define __all__ to explicitly specify what is exported from this package
__all__ = [
    # Token schemas
    "Token",
    "TokenPayload",
    "TokenRefresh",
    "CookieTokenResponse",
    "AccessToken",
    "RefreshTokenCreate",
    "RefreshTokenDB",
    "TokenWithoutRefresh",
    
    # User schemas
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "SMTPConfig",
    
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
    "EmailInDB",
    
    # Campaign schemas
    "Campaign",
    "CampaignCreate",
    "CampaignUpdate",
    "CampaignInDB",
    "CampaignStats",
    
    # A/B Testing schemas
    "ABTestConfig"
] 