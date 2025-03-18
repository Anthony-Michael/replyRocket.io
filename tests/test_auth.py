"""
Tests for authentication endpoints.

This module contains tests for user authentication, refresh tokens, and logout.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.security import decode_and_validate_token


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


@pytest.mark.auth
def test_register_user_weak_password(client: TestClient):
    """
    Test user registration with weak password.
    
    Arrange:
        - Prepare user registration data with weak password
    
    Act:
        - Send POST request to the registration endpoint
    
    Assert:
        - Response status code is 400 Bad Request
        - Response contains error detail about password requirements
    """
    # Arrange
    user_data = {
        "email": "newuser@example.com",
        "password": "password",  # Weak password
        "full_name": "New Test User"
    }
    
    # Act
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "password" in data["detail"].lower()


@pytest.mark.auth
def test_register_existing_user(client: TestClient, test_user: models.User):
    """
    Test user registration with existing email.
    
    Arrange:
        - Test user fixture
        - Prepare user registration data with existing email
    
    Act:
        - Send POST request to the registration endpoint
    
    Assert:
        - Response status code is 400 Bad Request
        - Response contains error detail about existing user
    """
    # Arrange
    user_data = {
        "email": test_user.email,  # Existing email
        "password": "ValidPassword123!",
        "full_name": "Another User"
    }
    
    # Act
    response = client.post("/api/v1/auth/register", json=user_data)
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "exist" in data["detail"].lower()


@pytest.mark.auth
def test_login_valid_credentials(client: TestClient, test_user: models.User):
    """
    Test login with valid credentials.
    
    Arrange:
        - Test user fixture
        - Prepare valid login data
    
    Act:
        - Send POST request to the login endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains message, expires_at, and user_id
        - Access token cookie is set
        - Refresh token cookie is set
    """
    # Arrange
    login_data = {
        "username": test_user.email,
        "password": "password",  # From test_user fixture
    }
    
    # Act
    response = client.post("/api/v1/auth/login", data=login_data)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Authentication successful"
    assert "expires_at" in data
    assert "user_id" in data
    
    # Check cookies
    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies
    
    # Verify the access token is valid
    access_token = cookies["access_token"]
    payload = decode_and_validate_token(access_token, token_type="access")
    assert payload["sub"] == str(test_user.id)


@pytest.mark.auth
def test_login_invalid_credentials(client: TestClient, test_user: models.User):
    """
    Test login with invalid credentials.
    
    Arrange:
        - Test user fixture
        - Prepare invalid login data
    
    Act:
        - Send POST request to the login endpoint
    
    Assert:
        - Response status code is 401 Unauthorized
        - Response contains error detail
    """
    # Arrange
    login_data = {
        "username": test_user.email,
        "password": "wrong_password",  # Wrong password
    }
    
    # Act
    response = client.post("/api/v1/auth/login", data=login_data)
    
    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "incorrect" in data["detail"].lower()


@pytest.mark.auth
def test_login_inactive_user(client: TestClient, test_user: models.User, db: Session):
    """
    Test login with inactive user.
    
    Arrange:
        - Test user fixture
        - Deactivate user
        - Prepare valid login data
    
    Act:
        - Send POST request to the login endpoint
    
    Assert:
        - Response status code is 401 Unauthorized
        - Response contains error detail about inactive user
    """
    # Arrange
    # Deactivate user
    test_user.is_active = False
    db.add(test_user)
    db.commit()
    
    login_data = {
        "username": test_user.email,
        "password": "password",  # From test_user fixture
    }
    
    # Act
    response = client.post("/api/v1/auth/login", data=login_data)
    
    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "inactive" in data["detail"].lower()
    
    # Reactivate user for other tests
    test_user.is_active = True
    db.add(test_user)
    db.commit()


@pytest.mark.auth
def test_refresh_token(client: TestClient, test_user: models.User):
    """
    Test refresh token endpoint.
    
    Arrange:
        - Test user fixture
        - Login to get valid tokens
    
    Act:
        - Send POST request to the refresh token endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains new access token
        - New access token is valid
        - New cookies are set
    """
    # Arrange
    # Login to get valid tokens
    login_data = {
        "username": test_user.email,
        "password": "password",  # From test_user fixture
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    # Act
    # Call refresh token endpoint (cookies are automatically sent)
    response = client.post("/api/v1/auth/refresh-token")
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert "expires_at" in data
    
    # Verify the new access token is valid
    access_token = data["access_token"]
    payload = decode_and_validate_token(access_token, token_type="access")
    assert payload["sub"] == str(test_user.id)
    
    # Check new cookies are set
    cookies = response.cookies
    assert "access_token" in cookies
    assert "refresh_token" in cookies


@pytest.mark.auth
def test_refresh_token_with_body(client: TestClient, test_user: models.User):
    """
    Test refresh token endpoint with token in body.
    
    Arrange:
        - Test user fixture
        - Login to get valid tokens
    
    Act:
        - Send POST request to the refresh token endpoint with token in body
    
    Assert:
        - Response status code is 200 OK
        - Response contains new access token
        - New access token is valid
    """
    # Arrange
    # Login to get valid tokens
    login_data = {
        "username": test_user.email,
        "password": "password",  # From test_user fixture
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    # Get refresh token from cookies
    refresh_token = login_response.cookies["refresh_token"]
    
    # Act
    # Call refresh token endpoint with token in body
    response = client.post(
        "/api/v1/auth/refresh-token",
        json={"refresh_token": refresh_token},
        cookies={}  # No cookies
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert "expires_at" in data


@pytest.mark.auth
def test_logout(client: TestClient, test_user: models.User):
    """
    Test logout endpoint.
    
    Arrange:
        - Test user fixture
        - Login to get valid tokens
    
    Act:
        - Send POST request to the logout endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains success message
    """
    # Arrange
    # Login to get valid tokens
    login_data = {
        "username": test_user.email,
        "password": "password",  # From test_user fixture
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    # Act
    # Call logout endpoint (cookies are automatically sent)
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login_response.cookies.get('access_token', '')}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()


@pytest.mark.auth
def test_access_protected_endpoint(client: TestClient, test_user: models.User):
    """
    Test accessing a protected endpoint with a valid token.
    
    Arrange:
        - Test user fixture
        - Login to get valid tokens
    
    Act:
        - Send GET request to a protected endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains user data
    """
    # Arrange
    # Login to get valid tokens
    login_data = {
        "username": test_user.email,
        "password": "password",  # From test_user fixture
    }
    login_response = client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    # Act
    # Access protected endpoint with token
    response = client.get(
        "/api/v1/auth/me",
        cookies={"access_token": login_response.cookies["access_token"]}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["id"] == str(test_user.id)


@pytest.mark.auth
def test_access_protected_endpoint_no_token(client: TestClient):
    """
    Test accessing a protected endpoint without a token.
    
    Arrange:
        - No authentication
    
    Act:
        - Send GET request to a protected endpoint
    
    Assert:
        - Response status code is 401 Unauthorized
        - Response contains error detail
    """
    # Act
    response = client.get("/api/v1/auth/me")
    
    # Assert
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "not authenticated" in data["detail"].lower()


@pytest.mark.auth
def test_logout_all_sessions(client: TestClient, test_user: models.User, db: Session):
    """
    Test logout all sessions endpoint.
    
    Arrange:
        - Test user fixture
        - Login multiple times to create multiple sessions
    
    Act:
        - Send POST request to the logout all sessions endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains success message
        - All refresh tokens for the user are revoked
    """
    # Arrange
    # Login multiple times to create multiple tokens
    login_data = {
        "username": test_user.email,
        "password": "password",  # From test_user fixture
    }
    for _ in range(3):  # Create 3 sessions
        login_response = client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
    
    # Verify we have tokens in the database
    refresh_tokens = db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == test_user.id,
        models.RefreshToken.revoked == False
    ).all()
    assert len(refresh_tokens) >= 3
    
    # Login one more time to get an active token for the request
    login_response = client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    # Act
    # Call logout all sessions endpoint
    response = client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {login_response.cookies['access_token']}"}
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "logged out all sessions" in data["message"].lower()
    
    # Verify all tokens are revoked
    active_tokens = db.query(models.RefreshToken).filter(
        models.RefreshToken.user_id == test_user.id,
        models.RefreshToken.revoked == False
    ).all()
    assert len(active_tokens) == 0 