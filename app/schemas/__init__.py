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

# Import A/B Testing configuration schema from ab_test_config.py
from app.schemas.ab_test_config import ABTestConfig  # Import ABTestConfig schema to fix import error

# Import Email Generation Response schema from email_gen_response.py
from app.schemas.email_gen_response import EmailGenResponse  # Import EmailGenResponse schema to fix import error

# Import Email Generation Request schema from email_gen_request.py
from app.schemas.email_gen_request import EmailGenRequest  # Import EmailGenRequest schema to fix import error

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
    "CampaignUpdate",
    
    # A/B Testing schemas
    "ABTestConfig",  # Added ABTestConfig to the exported schemas
    
    # Email Generation Response schema
    "EmailGenResponse",  # Added EmailGenResponse to the exported schemas
    
    # Email Generation Request schema
    "EmailGenRequest"  # Added EmailGenRequest to the exported schemas
] 