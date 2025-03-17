"""
Tests for email generation and sending endpoints.

This module contains tests for AI email generation and email sending endpoints.
"""

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models


@pytest.mark.emails
def test_generate_email(client: TestClient, token_headers: dict, mock_email_generator):
    """
    Test generating an email using the AI service.
    
    Arrange:
        - Prepare email generation request data
        - Set up authentication headers
        - Mock the AI email generator
    
    Act:
        - Send POST request to email generation endpoint
    
    Assert:
        - Response status code is 201 Created
        - Response contains expected email content
    """
    # Arrange
    email_request = {
        "recipient_name": "John Doe",
        "recipient_company": "Acme Corp",
        "recipient_job_title": "CTO",
        "industry": "Technology",
        "pain_points": ["Time management", "Team productivity"],
        "personalization_notes": "Met at TechCon 2023"
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/generate", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "subject" in data
    assert "body_text" in data
    assert "body_html" in data
    assert data["subject"] == "Test Subject Line"
    assert "test plain text" in data["body_text"].lower()
    assert "<p>" in data["body_html"]


@pytest.mark.emails
def test_generate_email_with_campaign(client: TestClient, test_campaign: models.Campaign, 
                                     token_headers: dict, mock_email_generator):
    """
    Test generating an email with a campaign context.
    
    Arrange:
        - Create a test campaign using fixture
        - Prepare email generation request data with campaign ID
        - Set up authentication headers
        - Mock the AI email generator
    
    Act:
        - Send POST request to email generation endpoint
    
    Assert:
        - Response status code is 201 Created
        - Response contains expected email content
    """
    # Arrange
    email_request = {
        "campaign_id": test_campaign.id,
        "recipient_name": "Jane Smith",
        "recipient_company": "XYZ Inc",
        "recipient_job_title": "Marketing Director",
        "industry": "Marketing",
        "pain_points": ["ROI tracking", "Campaign automation"],
        "personalization_notes": "LinkedIn connection"
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/generate", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "subject" in data
    assert "body_text" in data
    assert "body_html" in data


@pytest.mark.emails
def test_generate_email_campaign_not_found(client: TestClient, token_headers: dict):
    """
    Test generating an email with a non-existent campaign.
    
    Arrange:
        - Prepare email generation request data with non-existent campaign ID
        - Set up authentication headers
    
    Act:
        - Send POST request to email generation endpoint
    
    Assert:
        - Response status code is 404 Not Found
        - Response contains error message about campaign not found
    """
    # Arrange
    email_request = {
        "campaign_id": 99999,  # Non-existent campaign
        "recipient_name": "Bob Johnson",
        "recipient_company": "123 Industries",
        "recipient_job_title": "CEO",
        "industry": "Manufacturing",
        "pain_points": ["Supply chain", "Cost reduction"],
        "personalization_notes": "Referred by mutual contact"
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/generate", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "Campaign not found" in data["detail"]


@pytest.mark.emails
def test_generate_email_service_error(client: TestClient, token_headers: dict, monkeypatch):
    """
    Test email generation when AI service raises an error.
    
    Arrange:
        - Prepare email generation request data
        - Set up authentication headers
        - Mock the AI service to raise an exception
    
    Act:
        - Send POST request to email generation endpoint
    
    Assert:
        - Response status code is 500 Internal Server Error
        - Response contains generic error message
    """
    # Arrange
    def mock_generate_error(*args, **kwargs):
        raise Exception("AI service failure")
    
    monkeypatch.setattr("app.services.ai_email_generator.generate_email", mock_generate_error)
    
    email_request = {
        "recipient_name": "Error Test",
        "recipient_company": "Error Corp",
        "recipient_job_title": "CTO",
        "industry": "Technology",
        "pain_points": ["Error handling"],
        "personalization_notes": "Testing error case"
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/generate", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 500
    data = response.json()
    assert "Failed to generate email" in data["detail"]


@pytest.mark.emails
def test_generate_email_invalid_response(client: TestClient, token_headers: dict, monkeypatch):
    """
    Test email generation when AI service returns invalid response.
    
    Arrange:
        - Prepare email generation request data
        - Set up authentication headers
        - Mock the AI service to return incomplete data
    
    Act:
        - Send POST request to email generation endpoint
    
    Assert:
        - Response status code is 422 Unprocessable Entity
        - Response contains error about incomplete data
    """
    # Arrange
    class IncompleteResponse:
        # Missing required fields
        def __init__(self):
            self.subject = "Test Subject"
            # Missing body_text and body_html
    
    def mock_generate_incomplete(*args, **kwargs):
        return IncompleteResponse()
    
    monkeypatch.setattr("app.services.ai_email_generator.generate_email", mock_generate_incomplete)
    
    email_request = {
        "recipient_name": "Incomplete Test",
        "recipient_company": "Incomplete Corp",
        "recipient_job_title": "CTO",
        "industry": "Technology",
        "pain_points": ["Incomplete data"],
        "personalization_notes": "Testing incomplete case"
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/generate", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "incomplete data" in data["detail"].lower()


@pytest.mark.emails
def test_send_email(client: TestClient, test_campaign: models.Campaign, token_headers: dict, 
                   mock_smtp_client, db: Session):
    """
    Test sending an email.
    
    Arrange:
        - Create a test campaign using fixture
        - Prepare email send request data
        - Set up authentication headers
        - Mock the SMTP client
    
    Act:
        - Send POST request to email sending endpoint
    
    Assert:
        - Response status code is 201 Created
        - Response contains email tracking info
        - Email record is created in database
    """
    # Arrange
    email_request = {
        "campaign_id": test_campaign.id,
        "recipient_email": "recipient@example.com",
        "recipient_name": "Email Recipient",
        "subject": "Test Email Subject",
        "body_text": "This is a test email body text.",
        "body_html": "<p>This is a test email body HTML.</p>"
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/send", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "tracking_id" in data
    assert data["is_sent"] is False  # Will be updated by background task
    
    # Verify email record is created in database
    email_record = db.query(models.Email).filter(models.Email.id == data["id"]).first()
    assert email_record is not None
    assert email_record.recipient_email == email_request["recipient_email"]
    assert email_record.subject == email_request["subject"]


@pytest.mark.emails
def test_send_email_no_smtp_config(client: TestClient, test_user: models.User, 
                                  test_campaign: models.Campaign, token_headers: dict, db: Session):
    """
    Test sending an email without SMTP configuration.
    
    Arrange:
        - Create a test campaign using fixture
        - Remove SMTP configuration from user
        - Prepare email send request data
        - Set up authentication headers
    
    Act:
        - Send POST request to email sending endpoint
    
    Assert:
        - Response status code is 400 Bad Request
        - Response contains error about missing SMTP credentials
    """
    # Arrange - Remove SMTP configuration
    test_user.smtp_host = None
    test_user.smtp_user = None
    test_user.smtp_password = None
    db.commit()
    
    email_request = {
        "campaign_id": test_campaign.id,
        "recipient_email": "recipient@example.com",
        "recipient_name": "No SMTP Config",
        "subject": "Test Email No SMTP",
        "body_text": "This email shouldn't send due to missing SMTP config.",
        "body_html": "<p>This email shouldn't send due to missing SMTP config.</p>"
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/send", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "SMTP credentials not configured" in data["detail"]
    
    # Restore SMTP configuration for other tests
    test_user.smtp_host = "smtp.example.com"
    test_user.smtp_user = "smtp_user"
    test_user.smtp_password = "smtp_password"
    db.commit()


@pytest.mark.emails
def test_send_email_missing_fields(client: TestClient, test_campaign: models.Campaign, 
                                  token_headers: dict):
    """
    Test sending an email with missing required fields.
    
    Arrange:
        - Create a test campaign using fixture
        - Prepare email send request with missing required fields
        - Set up authentication headers
    
    Act:
        - Send POST request to email sending endpoint
    
    Assert:
        - Response status code is 422 Unprocessable Entity
        - Response contains validation error details
    """
    # Arrange
    email_request = {
        "campaign_id": test_campaign.id,
        "recipient_email": "recipient@example.com",
        # Missing recipient_name
        # Missing subject
        "body_text": "This is a test email body."
        # Missing body_html
    }
    
    # Act
    response = client.post(
        "/api/v1/emails/send", 
        json=email_request, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data  # Validation error details


@pytest.mark.emails
def test_email_tracking_pixel(client: TestClient, db: Session):
    """
    Test the email tracking pixel endpoint.
    
    Arrange:
        - Create an email record with a tracking ID
    
    Act:
        - Send GET request to the tracking pixel endpoint
    
    Assert:
        - Response status code is 200 OK
        - Email record is marked as opened in database
    """
    # This test would need to create an email record with a tracking ID
    # For now, we'll just test that the endpoint responds
    
    # Arrange - Create a test tracking ID
    tracking_id = "test-tracking-123"
    
    # Act
    response = client.get(f"/api/v1/emails/tracking/{tracking_id}")
    
    # Assert
    assert response.status_code == 200
    
    # Note: We would ideally check that the email was marked as opened,
    # but that would require creating a real email record with this tracking ID


@pytest.mark.emails
def test_get_email_metrics(client: TestClient, test_campaign: models.Campaign, 
                          token_headers: dict, db: Session):
    """
    Test retrieving email metrics.
    
    Arrange:
        - Create a test email record
        - Set up authentication headers
    
    Act:
        - Send GET request to the email metrics endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains email metrics data
    """
    # This test would need to create an email record
    # For a complete test, we would:
    # 1. Create an email record
    # 2. GET the metrics
    # 3. Verify the response
    
    # Since we don't have direct access to create an email,
    # we'll first send an email and then get its metrics
    
    # Arrange - Send a test email
    email_request = {
        "campaign_id": test_campaign.id,
        "recipient_email": "metrics@example.com",
        "recipient_name": "Metrics Test",
        "subject": "Test Email for Metrics",
        "body_text": "This is a test email for getting metrics.",
        "body_html": "<p>This is a test email for getting metrics.</p>"
    }
    
    send_response = client.post(
        "/api/v1/emails/send", 
        json=email_request, 
        headers=token_headers
    )
    
    assert send_response.status_code == 201
    email_id = send_response.json()["id"]
    
    # Act - Get the email metrics
    response = client.get(
        f"/api/v1/emails/{email_id}", 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == email_id
    assert data["recipient_email"] == email_request["recipient_email"]
    assert data["subject"] == email_request["subject"]
    assert "is_opened" in data
    assert "is_sent" in data


@pytest.mark.emails
def test_get_campaign_emails(client: TestClient, test_campaign: models.Campaign, 
                            token_headers: dict):
    """
    Test retrieving all emails for a campaign.
    
    Arrange:
        - Create a test campaign using fixture
        - Send test emails for the campaign
        - Set up authentication headers
    
    Act:
        - Send GET request to the campaign emails endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains list of emails for the campaign
    """
    # Arrange - Send a couple of test emails
    for i in range(2):
        email_request = {
            "campaign_id": test_campaign.id,
            "recipient_email": f"campaign{i}@example.com",
            "recipient_name": f"Campaign Test {i}",
            "subject": f"Test Email for Campaign {i}",
            "body_text": f"This is test email {i} for the campaign.",
            "body_html": f"<p>This is test email {i} for the campaign.</p>"
        }
        
        send_response = client.post(
            "/api/v1/emails/send", 
            json=email_request, 
            headers=token_headers
        )
        
        assert send_response.status_code == 201
    
    # Act - Get all emails for the campaign
    response = client.get(
        f"/api/v1/emails/campaign/{test_campaign.id}", 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # Should have at least our 2 test emails 