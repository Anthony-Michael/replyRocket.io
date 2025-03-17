"""
Test configuration and fixtures for pytest.

This module provides fixtures for testing the FastAPI application,
including database setup, client, and authentication helpers.
"""

import os
import pytest
import asyncio
from typing import Dict, Generator, List
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy_utils import database_exists, create_database, drop_database

from app.main import app
from app.db.session import Base
from app.api import deps
from app.core.config import settings
from app.core import security
from app import crud, models, schemas

# Test database URL - using SQLite in-memory for tests
TEST_DATABASE_URL = "sqlite:///./test.db"

# Create test engine
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session factory
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_test_db():
    """
    Return a test database session.
    
    This function overrides the default get_db dependency in the application
    to use the test database instead.
    """
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def setup_test_db():
    """
    Set up the test database.
    
    Creates all tables before tests run and drops them after tests complete.
    """
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after tests complete
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(setup_test_db):
    """
    Create a fresh test database session for each test function.
    
    Provides transaction isolation between tests and rollback after each test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Use the session for the tests
    yield session
    
    # Rollback transaction to reset the database after the test
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db) -> Generator:
    """
    Create a FastAPI TestClient with the test database session.
    
    Overrides the default get_db dependency to use the test database,
    ensuring tests don't affect the real database.
    """
    # Override the get_db dependency
    app.dependency_overrides[deps.get_db] = lambda: db
    
    # Return a test client
    with TestClient(app) as test_client:
        yield test_client
    
    # Clear dependency overrides after test
    app.dependency_overrides.clear()


@pytest.fixture
def create_test_user(db):
    """
    Create a test user in the database.
    
    This fixture creates a user that can be used for authentication tests.
    Returns the user object and plain password.
    """
    # Create a new user
    user_in = schemas.UserCreate(
        email="test@example.com",
        password="Test1234!",  # Strong password to pass validation
        full_name="Test User"
    )
    user = crud.user.get_by_email(db, email=user_in.email)
    
    if not user:
        user = crud.user.create(db, obj_in=user_in)
    
    return {
        "user": user,
        "email": user_in.email,
        "password": user_in.password
    }


@pytest.fixture
def auth_token(client, create_test_user) -> str:
    """
    Get an authentication token for the test user.
    
    Authenticates with the test user and returns the access token
    for authenticated endpoint tests.
    """
    login_data = {
        "username": create_test_user["email"],  # OAuth2 form uses username for email
        "password": create_test_user["password"],
    }
    response = client.post("/api/v1/auth/login/access-token", data=login_data)
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    return token


@pytest.fixture
def auth_headers(auth_token) -> Dict[str, str]:
    """
    Create authorization headers with the test user's token.
    
    This fixture provides headers that can be used for authenticated requests.
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def create_test_campaign(db, create_test_user):
    """
    Create a test campaign for the test user.
    
    This fixture provides a campaign that can be used for testing
    email generation and other campaign-related endpoints.
    """
    campaign_in = schemas.CampaignCreate(
        name="Test Campaign",
        description="Campaign for testing",
        industry="Technology",
        target_job_title="Developer",
        pain_points="Testing difficulties",
        follow_up_days=3,
        max_follow_ups=2,
        ab_test_active=False
    )
    
    campaign = crud.campaign.create_with_user(
        db=db, 
        obj_in=campaign_in, 
        user_id=create_test_user["user"].id
    )
    
    return campaign 


@pytest.fixture
def mock_ai_service(monkeypatch):
    """
    Mock the AI service client for email generation tests.
    
    This fixture patches the external AI service client to return predefined responses
    instead of making actual API calls during testing.
    """
    class MockAIResponse:
        """Mock response from the AI service."""
        def __init__(self, content=None, error=None):
            self.content = content
            self.error = error
            
        async def content_as_json(self):
            """Return predefined content or raise an error if specified."""
            if self.error:
                raise self.error
            return self.content
    
    class MockAIClient:
        """Mock AI client that returns predefined responses."""
        def __init__(self):
            self.response = None
            
        def set_response(self, content=None, error=None):
            """Set the response to be returned by the mock."""
            self.response = MockAIResponse(content, error)
            
        async def generate(self, prompt, **kwargs):
            """Return the predefined response."""
            return self.response
    
    # Create a mock client instance
    mock_client = MockAIClient()
    
    # Set up a default successful response
    default_response = {
        "subject": "Test Email Subject",
        "body_text": "This is a test email body in plain text.",
        "body_html": "<p>This is a test email body in HTML.</p>",
        "message_type": "INITIAL_OUTREACH"
    }
    mock_client.set_response(content=default_response)
    
    # Patch the AI service client
    from app.services import ai_service
    monkeypatch.setattr(ai_service, "get_ai_client", lambda: mock_client)
    
    return mock_client


@pytest.fixture
def mock_smtp_service(monkeypatch):
    """
    Mock the SMTP service for email sending tests.
    
    This fixture patches the email sending functionality to avoid
    actually sending emails during tests.
    """
    class MockSMTPResponse:
        """Mock response from the SMTP service."""
        def __init__(self, is_sent=True, error=None):
            self.is_sent = is_sent
            self.error = error
            self.id = "test-email-123"
            self.tracking_id = "track-456"
    
    # Create a mock send_email function
    async def mock_send_email(*args, **kwargs):
        """Mock function that returns a successful email response."""
        return MockSMTPResponse()
    
    # Patch the email sending function
    from app.services import email_service
    monkeypatch.setattr(email_service, "send_email", mock_send_email)
    
    return mock_send_email 