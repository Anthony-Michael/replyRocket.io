"""
Base class for the SQLAlchemy models.

This module imports and re-exports the Base class from session.py
and all models to enable alembic to discover the models.
"""

from app.db.session import Base

# Import all models here so alembic can discover them
from app.models.user import User, RefreshToken
from app.models.campaign import EmailCampaign
from app.models.email import Email

# Make all models available when importing from app.db.base
__all__ = ["Base", "User", "RefreshToken", "EmailCampaign", "Email"] 