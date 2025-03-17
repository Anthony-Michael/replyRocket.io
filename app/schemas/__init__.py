"""
Schemas initialization module.

This file imports all Pydantic schemas and makes them available at the app.schemas namespace level.
This enables imports like 'from app.schemas import Token' to work properly.
"""

# Import Token schema from token.py
from app.schemas.token import Token, TokenPayload  # Import Token schema so it can be accessed as app.schemas.Token

# Import User schemas from user.py
from app.schemas.user import User, UserCreate, UserUpdate, UserInDB

# Import Email schemas from email.py
from app.schemas.email import Email, EmailCreate, EmailUpdate

# Import Campaign schemas from campaign.py
from app.schemas.campaign import Campaign, CampaignCreate, CampaignUpdate

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
    "EmailCreate",
    "EmailUpdate",
    
    # Campaign schemas
    "Campaign",
    "CampaignCreate",
    "CampaignUpdate"
] 