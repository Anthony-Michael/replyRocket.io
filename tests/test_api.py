from fastapi.testclient import TestClient

from app.core.config import settings
from main import app

client = TestClient(app)


def test_read_main():
    response = client.get(f"{settings.API_V1_STR}/")
    assert response.status_code == 404  # No root endpoint


def test_create_user():
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User",
            "company_name": "Test Company",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert data["company_name"] == "Test Company"
    assert "id" in data


def test_login():
    # First create a user
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "login_test@example.com",
            "password": "password123",
            "full_name": "Login Test",
        },
    )
    
    # Then try to login
    response = client.post(
        f"{settings.API_V1_STR}/auth/login/access-token",
        data={
            "username": "login_test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer" 