"""
Models initialization module. 

This file imports all models and makes them available at the app.models namespace level.
This allows imports like `from app.models import User` to work properly.
"""

# Import all models here to make them available when importing from app.models
from app.models.user import User, RefreshToken  # Import User and RefreshToken models
from app.models.email import Email  # Import Email model
from app.models.campaign import EmailCampaign  # Import EmailCampaign model

# Define __all__ to explicitly specify what is exported from this package
__all__ = [
    "User",
    "RefreshToken",
    "EmailCampaign",
    "Email",
] 