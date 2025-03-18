from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, UUID4


class Token(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: datetime


class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: Optional[str] = None
    exp: Optional[datetime] = None
    token_type: Optional[str] = None


class TokenRefresh(BaseModel):
    """Refresh token request model."""
    refresh_token: Optional[str] = None


class AccessToken(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime


class CookieTokenResponse(BaseModel):
    """Response model when token is set in HttpOnly cookie."""
    message: str
    expires_at: datetime
    user_id: UUID4


class RefreshTokenCreate(BaseModel):
    token: str
    user_id: UUID4
    expires_at: datetime


class RefreshTokenDB(RefreshTokenCreate):
    id: UUID4
    created_at: datetime
    revoked: bool

    class Config:
        orm_mode = True 