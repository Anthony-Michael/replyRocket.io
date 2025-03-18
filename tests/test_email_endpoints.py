"""
Integration tests for email generation and sending endpoints.

This module contains tests for the email API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
from unittest.mock import patch

from app import models, schemas


@pytest.fixture
def email_gen_request():
    """Sample email generation request data for testing."""
    return {
        "recipient_name": "John Smith",
        "recipient_email": "john.smith@example.com",
        "industry": "Technology",
        "pain_points": ["Time management", "Team collaboration"],
        "recipient_company": "Acme Corp",
        "recipient_job_title": "CTO",
        "personalization_notes": "Met at TechConf 2023, interested in automation"
    }


@pytest.fixture
def email_send_request():
    """Sample email send request data for testing."""
    return {
        "recipient_email": "john.smith@example.com",
        "recipient_name": "John Smith",
        "subject": "Follow-up on our discussion at TechConf",
        "body_text": "Hi John, it was great meeting you at TechConf. Let's discuss how we can help with your time management challenges.",
        "body_html": "<p>Hi John, it was great meeting you at TechConf. Let's discuss how we can help with your time management challenges.</p>",
        "ab_test_variant": "A"
    }


class TestEmailEndpoints:
    """Tests for email endpoints."""

    @patch('app.services.ai_email_generator_service.generate_email')
    def test_generate_email_content(self, mock_generate, client: TestClient, token_headers: dict, email_gen_request: dict, test_campaign: models.EmailCampaign):
        """
        Test email content generation endpoint.
        
        Arrange:
            - Prepare email generation data
            - Set up authentication headers
            - Mock AI generation service
        
        Act:
            - Send POST request to /api/v1/emails/generate
        
        Assert:
            - Response status is 201 Created
            - Generated email content is returned
        """
        # Arrange
        # Add campaign_id to request
        email_gen_request["campaign_id"] = str(test_campaign.id)
        
        # Mock the AI service response
        mock_generate.return_value = schemas.EmailGenResponse(
            subject="Test Subject",
            body_text="Test email body in plain text",
            body_html="<p>Test email body in HTML</p>"
        )
        
        # Act
        response = client.post(
            "/api/v1/emails/generate",
            json=email_gen_request,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "subject" in data
        assert "body_text" in data
        assert "body_html" in data
        assert data["subject"] == "Test Subject"
        assert data["body_text"] == "Test email body in plain text"
        assert data["body_html"] == "<p>Test email body in HTML</p>"
        
        # Verify our mock was called with correct args
        mock_generate.assert_called_once()
        # Check key parameters were passed correctly
        call_kwargs = mock_generate.call_args[1]
        assert call_kwargs["recipient_name"] == email_gen_request["recipient_name"]
        assert call_kwargs["industry"] == email_gen_request["industry"]
        assert call_kwargs["pain_points"] == email_gen_request["pain_points"]

    @patch('app.services.ai_email_generator_service.generate_email')
    def test_generate_email_content_minimal_data(self, mock_generate, client: TestClient, token_headers: dict):
        """
        Test email content generation with minimal data.
        
        Arrange:
            - Prepare minimal email generation data
            - Set up authentication headers
            - Mock AI generation service
        
        Act:
            - Send POST request to /api/v1/emails/generate
        
        Assert:
            - Response status is 201 Created
            - Generated email content is returned
        """
        # Arrange
        minimal_request = {
            "recipient_name": "John Smith",
            "industry": "Technology",
            "pain_points": ["Time management"]
            # Missing optional fields
        }
        
        # Mock the AI service response
        mock_generate.return_value = schemas.EmailGenResponse(
            subject="Test Subject",
            body_text="Test email body in plain text",
            body_html="<p>Test email body in HTML</p>"
        )
        
        # Act
        response = client.post(
            "/api/v1/emails/generate",
            json=minimal_request,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "subject" in data
        assert data["subject"] == "Test Subject"

    @patch('app.services.ai_email_generator_service.generate_email')
    def test_generate_email_content_campaign_not_found(self, mock_generate, client: TestClient, token_headers: dict, email_gen_request: dict):
        """
        Test email generation with non-existent campaign.
        
        Arrange:
            - Prepare email generation data with non-existent campaign ID
            - Set up authentication headers
        
        Act:
            - Send POST request to /api/v1/emails/generate
        
        Assert:
            - Response status is 404 Not Found
            - Error message indicates campaign not found
        """
        # Arrange
        email_gen_request["campaign_id"] = str(uuid.uuid4())  # Non-existent ID
        
        # Act
        response = client.post(
            "/api/v1/emails/generate",
            json=email_gen_request,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        
        # Verify our mock was NOT called
        mock_generate.assert_not_called()

    @patch('app.services.ai_email_generator_service.generate_email')
    def test_generate_email_content_ai_error(self, mock_generate, client: TestClient, token_headers: dict, email_gen_request: dict):
        """
        Test handling AI service errors during email generation.
        
        Arrange:
            - Prepare email generation data
            - Set up authentication headers
            - Mock AI generation service to raise an exception
        
        Act:
            - Send POST request to /api/v1/emails/generate
        
        Assert:
            - Response status is 500 Internal Server Error
            - Error message indicates AI service failure
        """
        # Arrange
        mock_generate.side_effect = Exception("AI service error")
        
        # Act
        response = client.post(
            "/api/v1/emails/generate",
            json=email_gen_request,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "ai" in data["detail"].lower() or "generation" in data["detail"].lower()

    @patch('app.services.email_service.send_email')
    def test_send_email(self, mock_send_email, client: TestClient, token_headers: dict, email_send_request: dict, test_campaign: models.EmailCampaign):
        """
        Test sending an email.
        
        Arrange:
            - Prepare email send request
            - Set up authentication headers
            - Mock email sending service
        
        Act:
            - Send POST request to /api/v1/emails/send
        
        Assert:
            - Response status is 201 Created
            - Email was sent successfully
            - Database record was created
        """
        # Arrange
        mock_send_email.return_value = True
        
        # Add campaign_id to request
        request_data = {**email_send_request, "campaign_id": str(test_campaign.id)}
        
        # Act
        response = client.post(
            "/api/v1/emails/send",
            json=request_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["recipient_email"] == email_send_request["recipient_email"]
        assert data["subject"] == email_send_request["subject"]
        assert data["is_sent"] is True  # Email was sent
        assert data["campaign_id"] == str(test_campaign.id)
        
        # Verify our mock was called
        mock_send_email.assert_called_once()

    @patch('app.services.email_service.send_email')
    def test_send_email_campaign_not_found(self, mock_send_email, client: TestClient, token_headers: dict, email_send_request: dict):
        """
        Test sending an email with non-existent campaign.
        
        Arrange:
            - Prepare email send request with non-existent campaign ID
            - Set up authentication headers
        
        Act:
            - Send POST request to /api/v1/emails/send
        
        Assert:
            - Response status is 404 Not Found
            - Error message indicates campaign not found
        """
        # Arrange
        # Add non-existent campaign_id to request
        request_data = {**email_send_request, "campaign_id": str(uuid.uuid4())}
        
        # Act
        response = client.post(
            "/api/v1/emails/send",
            json=request_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
        
        # Verify our mock was NOT called
        mock_send_email.assert_not_called()

    @patch('app.services.email_service.send_email')
    def test_send_email_failure(self, mock_send_email, client: TestClient, token_headers: dict, email_send_request: dict, test_campaign: models.EmailCampaign):
        """
        Test handling email sending failures.
        
        Arrange:
            - Prepare email send request
            - Set up authentication headers
            - Mock email sending service to return False (send failure)
        
        Act:
            - Send POST request to /api/v1/emails/send
        
        Assert:
            - Response status is 500 Internal Server Error
            - Error message indicates email sending failure
        """
        # Arrange
        mock_send_email.return_value = False  # Simulate sending failure
        
        # Add campaign_id to request
        request_data = {**email_send_request, "campaign_id": str(test_campaign.id)}
        
        # Act
        response = client.post(
            "/api/v1/emails/send",
            json=request_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "send" in data["detail"].lower() or "email" in data["detail"].lower()
        
        # Verify our mock was called
        mock_send_email.assert_called_once()

    def test_get_campaign_emails(self, client: TestClient, db: Session, test_campaign: models.EmailCampaign, token_headers: dict):
        """
        Test retrieving emails for a campaign.
        
        Arrange:
            - Create a test campaign
            - Create test emails for the campaign
            - Set up authentication headers
        
        Act:
            - Send GET request to /api/v1/emails/campaign/{id}
        
        Assert:
            - Response status is 200 OK
            - Response contains list of emails
            - All emails belong to the specified campaign
        """
        # Arrange - create test emails
        for i in range(3):
            email = models.Email(
                campaign_id=test_campaign.id,
                recipient_email=f"recipient{i}@example.com",
                recipient_name=f"Recipient {i}",
                subject=f"Test Subject {i}",
                body_text=f"Test body {i}",
                body_html=f"<p>Test body {i}</p>",
                tracking_id=f"tracking_{i}_{uuid.uuid4()}"
            )
            db.add(email)
        db.commit()
        
        # Act
        response = client.get(
            f"/api/v1/emails/campaign/{test_campaign.id}",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        
        # Verify all emails belong to the campaign
        for email in data:
            assert email["campaign_id"] == str(test_campaign.id)

    def test_get_campaign_emails_not_found(self, client: TestClient, token_headers: dict):
        """
        Test retrieving emails for a non-existent campaign.
        
        Arrange:
            - Generate a random campaign ID
            - Set up authentication headers
        
        Act:
            - Send GET request to /api/v1/emails/campaign/{id}
        
        Assert:
            - Response status is 404 Not Found
            - Error message indicates campaign not found
        """
        # Arrange
        non_existent_id = str(uuid.uuid4())
        
        # Act
        response = client.get(
            f"/api/v1/emails/campaign/{non_existent_id}",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_track_email_open(self, client: TestClient, db: Session, test_campaign: models.EmailCampaign):
        """
        Test tracking email opens via tracking pixel.
        
        Arrange:
            - Create a test email with tracking ID
        
        Act:
            - Send GET request to /api/v1/emails/track/{tracking_id}.png
        
        Assert:
            - Response status is 200 OK
            - Response content type is image/png
            - Email is marked as opened in database
        """
        # Arrange - create test email with tracking ID
        tracking_id = f"track_{uuid.uuid4()}"
        email = models.Email(
            campaign_id=test_campaign.id,
            recipient_email="tracked@example.com",
            recipient_name="Tracked User",
            subject="Tracked Email",
            body_text="This email is being tracked",
            body_html="<p>This email is being tracked</p>",
            tracking_id=tracking_id,
            is_opened=False,
            num_opens=0
        )
        db.add(email)
        db.commit()
        db.refresh(email)
        
        # Act
        response = client.get(f"/api/v1/emails/track/{tracking_id}.png")
        
        # Assert
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"
        
        # Verify email is marked as opened in database
        updated_email = db.query(models.Email).filter(
            models.Email.tracking_id == tracking_id
        ).first()
        assert updated_email.is_opened is True
        assert updated_email.num_opens == 1

    def test_track_email_open_multiple(self, client: TestClient, db: Session, test_campaign: models.EmailCampaign):
        """
        Test tracking multiple email opens.
        
        Arrange:
            - Create a test email with tracking ID
        
        Act:
            - Send multiple GET requests to tracking pixel
        
        Assert:
            - Email num_opens count is incremented
        """
        # Arrange - create test email with tracking ID
        tracking_id = f"multi_track_{uuid.uuid4()}"
        email = models.Email(
            campaign_id=test_campaign.id,
            recipient_email="multitrack@example.com",
            recipient_name="Multi Track User",
            subject="Multi-tracked Email",
            body_text="This email is being tracked multiple times",
            body_html="<p>This email is being tracked multiple times</p>",
            tracking_id=tracking_id,
            is_opened=False,
            num_opens=0
        )
        db.add(email)
        db.commit()
        db.refresh(email)
        
        # Act - send 3 tracking requests
        for _ in range(3):
            response = client.get(f"/api/v1/emails/track/{tracking_id}.png")
            assert response.status_code == 200
        
        # Assert
        updated_email = db.query(models.Email).filter(
            models.Email.tracking_id == tracking_id
        ).first()
        assert updated_email.is_opened is True
        assert updated_email.num_opens == 3 