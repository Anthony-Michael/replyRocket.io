"""
Test fixtures for the ReplyRocket application.

This module contains fixtures used across various test modules to
ensure consistent test setup.
"""

import os
import json
import uuid
import pytest
from typing import Dict, Generator, Any, List
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.core import security
from app.db.base import Base
from app.api.deps import get_db
from app.main import app
from app import crud, models, schemas


# Use SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator:
    """
    Create a fresh database for each test, then drop all tables after the test.
    
    Returns:
        Generator yielding a SQLAlchemy Session
    """
    # Create the database
    Base.metadata.create_all(bind=engine)
    
    # Create a new session for the test
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        
    # Drop all tables after the test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """
    Create a FastAPI TestClient with a dependency override for the database.
    
    Args:
        db: The database session fixture
        
    Returns:
        A FastAPI TestClient
    """
    def override_get_db() -> Generator:
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    # Return the test client
    with TestClient(app) as client:
        yield client
    
    # Clear dependency overrides after test
    app.dependency_overrides = {}


@pytest.fixture(scope="function")
def test_user(db: Session) -> models.User:
    """
    Create a test user for authentication tests.
    
    Args:
        db: The database session fixture
        
    Returns:
        A User model instance for testing
    """
    user_in = schemas.UserCreate(
        email="testuser@example.com",
        password="password",  # Simplified for testing
        full_name="Test User"
    )
    
    # Create user with SMTP settings
    user = crud.user.create(db, obj_in=user_in)
    
    # Update with SMTP settings
    smtp_settings = {
        "smtp_host": "smtp.example.com",
        "smtp_port": "587",
        "smtp_user": "smtp_user",
        "smtp_password": "smtp_password",
        "smtp_use_tls": True
    }
    user_update = schemas.UserUpdate(**smtp_settings)
    user = crud.user.update(db, db_obj=user, obj_in=user_update)
    
    return user


@pytest.fixture(scope="function")
def test_superuser(db: Session) -> models.User:
    """
    Create a test superuser for admin-level tests.
    
    Args:
        db: The database session fixture
        
    Returns:
        A User model instance with superuser privileges
    """
    user_in = schemas.UserCreate(
        email="admin@example.com",
        password="AdminPassword123!",
        full_name="Admin User",
        is_superuser=True
    )
    user = crud.user.create(db, obj_in=user_in)
    return user


@pytest.fixture(scope="function")
def test_campaign(db: Session, test_user: models.User) -> models.EmailCampaign:
    """
    Create a test campaign for the test user.
    
    Args:
        db: The database session fixture
        test_user: The test user fixture
        
    Returns:
        A Campaign model instance for testing
    """
    campaign_in = schemas.CampaignCreate(
        name="Test Campaign",
        description="Test campaign description",
        target_audience="Test audience",
        is_active=True
    )
    campaign = crud.campaign.create_with_user(
        db=db, obj_in=campaign_in, user_id=test_user.id
    )
    return campaign


@pytest.fixture(scope="function")
def token_headers(test_user: models.User) -> Dict[str, str]:
    """
    Create authorization headers with JWT token for the test user.
    
    Args:
        test_user: The test user fixture
        
    Returns:
        Headers dictionary with Authorization bearer token
    """
    token = security.create_access_token(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def superuser_token_headers(test_superuser: models.User) -> Dict[str, str]:
    """
    Create authorization headers with JWT token for the test superuser.
    
    Args:
        test_superuser: The test superuser fixture
        
    Returns:
        Headers dictionary with Authorization bearer token
    """
    token = security.create_access_token(test_superuser.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_refresh_token(db: Session, test_user: models.User) -> models.RefreshToken:
    """
    Create a test refresh token for the test user.
    
    Args:
        db: The database session fixture
        test_user: The test user fixture
        
    Returns:
        A RefreshToken model instance for testing
    """
    # Create a refresh token that expires in 7 days
    token = security.generate_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    refresh_token = models.RefreshToken(
        token=token,
        user_id=test_user.id,
        expires_at=expires_at,
        revoked=False,
        created_at=datetime.utcnow()
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token


@pytest.fixture(scope="function")
def revoked_refresh_token(db: Session, test_user: models.User) -> models.RefreshToken:
    """
    Create a revoked refresh token for the test user.
    
    Args:
        db: The database session fixture
        test_user: The test user fixture
        
    Returns:
        A revoked RefreshToken model instance for testing
    """
    # Create a refresh token that expires in 7 days but is revoked
    token = security.generate_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=7)
    
    refresh_token = models.RefreshToken(
        token=token,
        user_id=test_user.id,
        expires_at=expires_at,
        revoked=True,
        created_at=datetime.utcnow()
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token


@pytest.fixture(scope="function")
def expired_refresh_token(db: Session, test_user: models.User) -> models.RefreshToken:
    """
    Create an expired refresh token for the test user.
    
    Args:
        db: The database session fixture
        test_user: The test user fixture
        
    Returns:
        An expired RefreshToken model instance for testing
    """
    # Create a refresh token that expired 1 day ago
    token = security.generate_refresh_token()
    expires_at = datetime.utcnow() - timedelta(days=1)
    
    refresh_token = models.RefreshToken(
        token=token,
        user_id=test_user.id,
        expires_at=expires_at,
        revoked=False,
        created_at=datetime.utcnow() - timedelta(days=8)
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token


# Mocks for external services
@pytest.fixture(scope="function")
def mock_openai_response():
    """
    Mock the OpenAI API response for email generation.
    
    Returns:
        A mock OpenAI API response with email content
    """
    class MockChoice:
        def __init__(self, content):
            self.message = Mock(content=content)
    
    class MockResponse:
        def __init__(self, content):
            self.choices = [MockChoice(content)]
    
    email_json = '''
    {
        "subject": "Test Subject Line",
        "body_text": "This is a test plain text email body.",
        "body_html": "<p>This is a test HTML email body.</p>"
    }
    '''
    
    return MockResponse(email_json)


@pytest.fixture(scope="function")
def mock_email_generator(monkeypatch, mock_openai_response):
    """
    Mock the AI email generator service.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        mock_openai_response: Mock OpenAI API response fixture
        
    Returns:
        A patched version of the generate_email function
    """
    from app.schemas.email import EmailGenResponse
    import json
    
    def mock_generate(*args, **kwargs):
        content = mock_openai_response.choices[0].message.content
        email_data = json.loads(content)
        return EmailGenResponse(**email_data)
    
    # Patch the generate_email function in the service
    monkeypatch.setattr("app.services.ai_email_generator.generate_email", mock_generate)
    
    # Patch the OpenAI client's create method
    monkeypatch.setattr(
        "app.services.ai_email_generator.client.chat.completions.create",
        Mock(return_value=mock_openai_response)
    )
    
    return mock_generate


@pytest.fixture(scope="function")
def mock_smtp_client(monkeypatch):
    """
    Mock the SMTP client used for sending emails.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        
    Returns:
        A patched version of the send_email function that always succeeds
    """
    async def mock_send_email_async(*args, **kwargs):
        return True
    
    def mock_send_email(*args, **kwargs):
        return True
    
    # Patch both sync and async email sending functions
    monkeypatch.setattr("app.services.email_sender.send_email_async", mock_send_email_async)
    monkeypatch.setattr("app.services.email_sender.send_email", mock_send_email)
    
    return mock_send_email


@pytest.fixture
def mock_current_user() -> models.User:
    """
    Mock an authenticated user for testing endpoints that require authentication.
    
    Returns:
        Mock User object
    """
    user = Mock(spec=models.User)
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
    
    return user


@pytest.fixture
def auth_headers(mock_current_user) -> Dict[str, str]:
    """
    Generate authentication headers for testing protected endpoints.
    
    Args:
        mock_current_user: Mock user fixture
        
    Returns:
        Dictionary with Authorization header
    """
    access_token = security.create_access_token(
        subject=str(mock_current_user.id)
    )
    
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_db_session() -> Mock:
    """
    Create a mock database session for testing.
    
    Returns:
        Mock database session
    """
    mock_session = Mock(spec=Session)
    return mock_session


@pytest.fixture
def mock_openai_response() -> Mock:
    """
    Create a mock OpenAI API response.
    
    Returns:
        Mock OpenAI API response
    """
    mock_response = Mock()
    
    # Create a mock choice with content
    mock_choice = Mock()
    mock_choice.message = Mock()
    mock_choice.message.content = json.dumps({
        "subject": "Test Subject",
        "body_text": "This is a test email body.",
        "body_html": "<p>This is a test email body.</p>"
    })
    
    mock_response.choices = [mock_choice]
    
    return mock_response


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    """
    Patch common dependencies to avoid external calls during testing.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
    """
    # Override get_db dependency to use test database
    async def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    monkeypatch.setattr("app.api.deps.get_db", override_get_db)
    
    # Override authentication dependency
    async def override_get_current_user():
        user = Mock(spec=models.User)
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.is_active = True
        return user
    
    monkeypatch.setattr("app.api.deps.get_current_active_user", override_get_current_user)
    
    # Patch any external API calls
    monkeypatch.setattr("app.services.email_sender_service.send_email", Mock(return_value=True)) 