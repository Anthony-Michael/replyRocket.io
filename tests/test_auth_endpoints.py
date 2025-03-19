import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.core.security import create_token_pair, store_refresh_token
from app import models

client = TestClient(app)

def test_refresh_token_security():
    db = SessionLocal()
    try:
        # Create a test user
        user = models.User(email="test@example.com", hashed_password="fakehashedpassword")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Generate tokens
        access_token, refresh_token, access_expires, refresh_expires = create_token_pair(subject=str(user.id))

        # Store refresh token in database
        store_refresh_token(db=db, token=refresh_token, user_id=str(user.id), expires_at=refresh_expires)

        # Set refresh token in HttpOnly cookie
        client.cookies.set("refresh_token", refresh_token, httponly=True)

        # Test refresh token endpoint
        response = client.post("/api/v1/auth/refresh-token")
        assert response.status_code == 200
        assert "access_token" in response.json()

        # Test that the old refresh token is invalidated
        response = client.post("/api/v1/auth/refresh-token")
        assert response.status_code == 401

    finally:
        db.close()


def test_logout_security():
    db = SessionLocal()
    try:
        # Create a test user
        user = models.User(email="test@example.com", hashed_password="fakehashedpassword")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Generate tokens
        access_token, refresh_token, access_expires, refresh_expires = create_token_pair(subject=str(user.id))

        # Store refresh token in database
        store_refresh_token(db=db, token=refresh_token, user_id=str(user.id), expires_at=refresh_expires)

        # Set refresh token in HttpOnly cookie
        client.cookies.set("refresh_token", refresh_token, httponly=True)

        # Test logout endpoint
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"

        # Test that the refresh token is invalidated
        response = client.post("/api/v1/auth/refresh-token")
        assert response.status_code == 401

    finally:
        db.close() 