"""
Tests for authentication endpoints.

This module contains tests for user registration and login functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.core.security import get_password_hash, verify_password


class TestAuthentication:
    """Tests for authentication-related endpoints."""
    
    def test_register_user(self, client: TestClient, db: Session):
        """
        Test user registration.
        
        ARRANGE:
            - Prepare valid user data with strong password
        
        ACT:
            - Send a POST request to the registration endpoint
        
        ASSERT:
            - Verify response status code is 201 (Created)
            - Verify response contains expected user data
            - Verify user exists in the database
        """
        # Arrange - Prepare test data
        user_data = {
            "email": "newuser@example.com",
            "password": "NewPassword123!",
            "full_name": "New Test User"
        }
        
        # Act - Send the registration request
        response = client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # Assert - Check the response
        assert response.status_code == 201, f"Failed to register user: {response.text}"
        
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        
        # Verify user exists in DB
        user = crud.user.get_by_email(db, email=user_data["email"])
        assert user is not None
        assert user.email == user_data["email"]
        assert user.is_active is True
    
    def test_register_user_weak_password(self, client: TestClient):
        """
        Test registration with weak password.
        
        ARRANGE:
            - Prepare user data with a weak password
        
        ACT:
            - Send a POST request to the registration endpoint
        
        ASSERT:
            - Verify response status code is 400 (Bad Request)
            - Verify response contains password requirement message
        """
        # Arrange - Prepare test data with weak password
        user_data = {
            "email": "weakpass@example.com",
            "password": "weak",  # Too weak
            "full_name": "Weak Password User"
        }
        
        # Act - Send the registration request
        response = client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # Assert - Check for proper rejection
        assert response.status_code == 400
        assert "Password does not meet security requirements" in response.json()["detail"]
    
    def test_register_existing_user(self, client: TestClient, create_test_user):
        """
        Test registration with existing email.
        
        ARRANGE:
            - Use fixture to create a test user
            - Prepare registration data with the same email
        
        ACT:
            - Send a POST request to the registration endpoint
        
        ASSERT:
            - Verify response status code is 409 (Conflict)
            - Verify response contains message about existing user
        """
        # Arrange - Prepare data with existing email
        user_data = {
            "email": create_test_user["email"],  # Already exists
            "password": "DifferentPass123!",
            "full_name": "Duplicate Email User"
        }
        
        # Act - Send the registration request
        response = client.post(
            "/api/v1/auth/register",
            json=user_data
        )
        
        # Assert - Check for conflict response
        assert response.status_code == 409
        assert "User with this email already exists" in response.json()["detail"]
    
    def test_login_valid_credentials(self, client: TestClient, create_test_user):
        """
        Test login with valid credentials.
        
        ARRANGE:
            - Use fixture to create a test user
            - Prepare form data with valid credentials
        
        ACT:
            - Send a POST request to the login endpoint
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify response contains access token
            - Verify token type is bearer
        """
        # Arrange - Prepare login data
        login_data = {
            "username": create_test_user["email"],  # OAuth2 uses username field for email
            "password": create_test_user["password"]
        }
        
        # Act - Send login request
        response = client.post(
            "/api/v1/auth/login/access-token",
            data=login_data  # Use form data for OAuth2
        )
        
        # Assert - Check for successful login
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self, client: TestClient):
        """
        Test login with invalid credentials.
        
        ARRANGE:
            - Prepare form data with invalid credentials
        
        ACT:
            - Send a POST request to the login endpoint
        
        ASSERT:
            - Verify response status code is 401 (Unauthorized)
            - Verify response contains error message about invalid credentials
        """
        # Arrange - Prepare invalid login data
        login_data = {
            "username": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }
        
        # Act - Send login request
        response = client.post(
            "/api/v1/auth/login/access-token",
            data=login_data
        )
        
        # Assert - Check for unauthorized response
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    def test_access_protected_endpoint(self, client: TestClient, auth_headers):
        """
        Test access to a protected endpoint with valid token.
        
        ARRANGE:
            - Use fixture to get auth headers with valid token
        
        ACT:
            - Send a GET request to a protected endpoint
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify response contains user data
        """
        # Act - Access protected endpoint
        response = client.get(
            "/api/v1/users/me",
            headers=auth_headers
        )
        
        # Assert - Check for successful access
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data
    
    def test_access_protected_endpoint_no_token(self, client: TestClient):
        """
        Test access to a protected endpoint without a token.
        
        ARRANGE:
            - No token in request headers
        
        ACT:
            - Send a GET request to a protected endpoint
        
        ASSERT:
            - Verify response status code is 401 (Unauthorized)
            - Verify response contains error about missing token
        """
        # Act - Access protected endpoint without token
        response = client.get("/api/v1/users/me")
        
        # Assert - Check for unauthorized response
        assert response.status_code == 401
        assert "Not authenticated" in response.json()["detail"] 