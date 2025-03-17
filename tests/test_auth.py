"""
Tests for authentication endpoints.

This module contains tests for user registration and login endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models


@pytest.mark.auth
def test_register_user(client: TestClient, db: Session):
    """
    Test user registration with valid data.
    
    Arrange:
        - Prepare valid user registration data
    
    Act:
        - Send POST request to the registration endpoint
    
    Assert:
        - Response status code is 201 Created
        - Response contains user data with expected email
        - User exists in the database
    """
    # Arrange
    user_data = {
        "email": "newuser@example.com",
        "password": "NewPassword123!",
        "full_name": "New Test User"
    }
    
    # Act
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["full_name"] == user_data["full_name"]
    assert "id" in data
    
    # Verify user exists in database
    user_in_db = db.query(models.User).filter(models.User.email == user_data["email"]).first()
    assert user_in_db is not None
    assert user_in_db.email == user_data["email"]
    assert user_in_db.is_active is True
    assert user_in_db.is_superuser is False


@pytest.mark.auth
def test_register_user_weak_password(client: TestClient):
    """
    Test user registration with a weak password.
    
    Arrange:
        - Prepare user registration data with a weak password
    
    Act:
        - Send POST request to the registration endpoint
    
    Assert:
        - Response status code is 400 Bad Request
        - Response contains error message about password requirements
    """
    # Arrange
    user_data = {
        "email": "weakpass@example.com",
        "password": "weak",
        "full_name": "Weak Password User"
    }
    
    # Act
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "Password does not meet security requirements" in data["detail"]


@pytest.mark.auth
def test_register_existing_user(client: TestClient, test_user: models.User):
    """
    Test registration with an existing email.
    
    Arrange:
        - Prepare user registration data with an email that already exists
    
    Act:
        - Send POST request to the registration endpoint
    
    Assert:
        - Response status code is 409 Conflict
        - Response contains error message about email already existing
    """
    # Arrange
    existing_email = test_user.email
    user_data = {
        "email": existing_email,
        "password": "ValidPass123!",
        "full_name": "Duplicate Email User"
    }
    
    # Act
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Assert
    assert response.status_code == 409
    data = response.json()
    assert "already exists" in data["detail"]


@pytest.mark.auth
def test_login_valid_credentials(client: TestClient, test_user: models.User):
    """
    Test login with valid credentials.
    
    Arrange:
        - Prepare valid login data
    
    Act:
        - Send POST request to the login endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains access token and token type
    """
    # Arrange
    login_data = {
        "username": test_user.email,  # OAuth2 form uses username for email
        "password": "TestPassword123!"
    }
    
    # Act
    response = client.post("/api/v1/auth/login/access-token", data=login_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # Verify token works on a protected endpoint
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["email"] == test_user.email


@pytest.mark.auth
def test_login_invalid_credentials(client: TestClient, test_user: models.User):
    """
    Test login with invalid credentials.
    
    Arrange:
        - Prepare login data with incorrect password
    
    Act:
        - Send POST request to the login endpoint
    
    Assert:
        - Response status code is 401 Unauthorized
        - Response contains error message about incorrect credentials
    """
    # Arrange
    login_data = {
        "username": test_user.email,  # OAuth2 form uses username for email
        "password": "WrongPassword123!"
    }
    
    # Act
    response = client.post("/api/v1/auth/login/access-token", data=login_data)
    
    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "Incorrect email or password" in data["detail"]


@pytest.mark.auth
def test_login_inactive_user(client: TestClient, test_user: models.User, db: Session):
    """
    Test login with an inactive user.
    
    Arrange:
        - Deactivate the test user
        - Prepare login data for the inactive user
    
    Act:
        - Send POST request to the login endpoint
    
    Assert:
        - Response status code is 403 Forbidden
        - Response contains error message about inactive account
    """
    # Arrange - Deactivate user
    test_user.is_active = False
    db.commit()
    
    login_data = {
        "username": test_user.email,
        "password": "TestPassword123!"
    }
    
    # Act
    response = client.post("/api/v1/auth/login/access-token", data=login_data)
    
    # Assert
    assert response.status_code == 403
    data = response.json()
    assert "Inactive user account" in data["detail"]
    
    # Restore user to active state for other tests
    test_user.is_active = True
    db.commit()


@pytest.mark.auth
def test_access_protected_endpoint(client: TestClient, token_headers: dict):
    """
    Test accessing a protected endpoint with a valid token.
    
    Arrange:
        - Use token_headers fixture for authentication
    
    Act:
        - Send GET request to a protected endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains user data
    """
    # Act
    response = client.get("/api/v1/users/me", headers=token_headers)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert "id" in data


@pytest.mark.auth
def test_access_protected_endpoint_no_token(client: TestClient):
    """
    Test accessing a protected endpoint without a token.
    
    Arrange:
        - No authentication token
    
    Act:
        - Send GET request to a protected endpoint
    
    Assert:
        - Response status code is 401 Unauthorized
        - Response contains error message about missing authentication
    """
    # Act
    response = client.get("/api/v1/users/me")
    
    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "Not authenticated" in data["detail"] 