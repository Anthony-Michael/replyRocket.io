"""
Tests for email-related endpoints.

This module contains tests for email generation and sending functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app import crud, models


class TestEmails:
    """Tests for email-related endpoints."""
    
    def test_generate_email(self, client: TestClient, auth_headers, create_test_campaign, mock_ai_service):
        """
        Test email generation endpoint.
        
        ARRANGE:
            - Use mock_ai_service fixture to mock the AI service
            - Set up test data for email generation
        
        ACT:
            - Send a POST request to the email generation endpoint
        
        ASSERT:
            - Verify response status code is 201 (Created)
            - Verify response contains expected email content
        """
        # Arrange - Set up test data
        email_request_data = {
            "recipient_name": "John Doe",
            "recipient_email": "john.doe@example.com",
            "recipient_company": "Test Corp",
            "recipient_job_title": "CTO",
            "industry": "Technology",
            "pain_points": ["Testing", "Automation"],
            "personalization_notes": "Met at tech conference",
            "campaign_id": str(create_test_campaign.id)
        }
        
        # Configure mock_ai_service with expected response
        expected_response = {
            "subject": "Test Email Subject",
            "body_text": "This is a test email body in plain text.",
            "body_html": "<p>This is a test email body in HTML.</p>",
            "message_type": "INITIAL_OUTREACH"
        }
        mock_ai_service.set_response(content=expected_response)
        
        # Act - Send request to generate email
        response = client.post(
            "/api/v1/emails/generate",
            json=email_request_data,
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 201, f"Failed to generate email: {response.text}"
        
        data = response.json()
        assert data["subject"] == expected_response["subject"]
        assert data["body_text"] == expected_response["body_text"]
        assert data["body_html"] == expected_response["body_html"]
    
    def test_generate_email_campaign_not_found(self, client: TestClient, auth_headers):
        """
        Test email generation with non-existent campaign.
        
        ARRANGE:
            - Set up test data with a non-existent campaign ID
        
        ACT:
            - Send a POST request to the email generation endpoint
        
        ASSERT:
            - Verify response status code is 404 (Not Found)
            - Verify response contains error message about campaign
        """
        # Arrange - Set up test data with non-existent campaign
        email_request_data = {
            "recipient_name": "John Doe",
            "recipient_email": "john.doe@example.com",
            "recipient_company": "Test Corp",
            "recipient_job_title": "CTO",
            "industry": "Technology",
            "pain_points": ["Testing", "Automation"],
            "personalization_notes": "Met at tech conference",
            "campaign_id": str(uuid4())  # Random non-existent ID
        }
        
        # Act - Send request to generate email
        response = client.post(
            "/api/v1/emails/generate",
            json=email_request_data,
            headers=auth_headers
        )
        
        # Assert - Check for not found response
        assert response.status_code == 404
        assert "Campaign not found" in response.json()["detail"]
    
    def test_generate_email_service_error(self, client: TestClient, auth_headers, create_test_campaign, mock_ai_service):
        """
        Test email generation with AI service error.
        
        ARRANGE:
            - Configure mock_ai_service to raise an exception
            - Set up test data for email generation
        
        ACT:
            - Send a POST request to the email generation endpoint
        
        ASSERT:
            - Verify response status code is 500 (Internal Server Error)
            - Verify response contains generic error message
        """
        # Arrange - Set up test data and mock to raise error
        email_request_data = {
            "recipient_name": "John Doe",
            "recipient_email": "john.doe@example.com",
            "recipient_company": "Test Corp",
            "recipient_job_title": "CTO",
            "industry": "Technology",
            "pain_points": ["Testing", "Automation"],
            "personalization_notes": "Met at tech conference",
            "campaign_id": str(create_test_campaign.id)
        }
        
        # Configure mock to raise an exception
        mock_ai_service.set_response(error=Exception("AI service unavailable"))
        
        # Act - Send request to generate email
        response = client.post(
            "/api/v1/emails/generate",
            json=email_request_data,
            headers=auth_headers
        )
        
        # Assert - Check for error response
        assert response.status_code == 500
        assert "Failed to generate email" in response.json()["detail"]
    
    def test_generate_email_invalid_response(self, client: TestClient, auth_headers, create_test_campaign, mock_ai_service):
        """
        Test email generation with invalid AI response.
        
        ARRANGE:
            - Configure mock_ai_service to return incomplete data
            - Set up test data for email generation
        
        ACT:
            - Send a POST request to the email generation endpoint
        
        ASSERT:
            - Verify response status code is 422 (Unprocessable Entity)
            - Verify response contains error about incomplete data
        """
        # Arrange - Set up test data and mock with incomplete response
        email_request_data = {
            "recipient_name": "John Doe",
            "recipient_email": "john.doe@example.com",
            "recipient_company": "Test Corp",
            "recipient_job_title": "CTO",
            "industry": "Technology",
            "pain_points": ["Testing", "Automation"],
            "personalization_notes": "Met at tech conference",
            "campaign_id": str(create_test_campaign.id)
        }
        
        # Return incomplete data (missing body_html)
        incomplete_response = {
            "subject": "Test Email Subject",
            "body_text": "This is a test email body."
            # Missing body_html
        }
        mock_ai_service.set_response(content=incomplete_response)
        
        # Act - Send request to generate email
        response = client.post(
            "/api/v1/emails/generate",
            json=email_request_data,
            headers=auth_headers
        )
        
        # Assert - Check for validation error response
        assert response.status_code == 422
        assert "incomplete data" in response.json()["detail"].lower()
    
    def test_send_email(self, client: TestClient, auth_headers, db: Session, create_test_user, create_test_campaign, mock_smtp_service):
        """
        Test email sending endpoint.
        
        ARRANGE:
            - Use mock_smtp_service fixture to mock the email service
            - Add SMTP credentials to test user
            - Set up test data for email sending
        
        ACT:
            - Send a POST request to the email sending endpoint
        
        ASSERT:
            - Verify response status code is 201 (Created)
            - Verify response contains expected tracking info
            - Verify email record was created in database
        """
        # Arrange - Set up test data
        # First update user with SMTP credentials
        user = create_test_user["user"]
        crud.user.update(db, db_obj=user, obj_in={
            "smtp_host": "smtp.test.com",
            "smtp_port": "587",
            "smtp_user": "test@example.com",
            "smtp_password": "smtp_password",
            "smtp_use_tls": True
        })
        
        email_send_data = {
            "recipient_email": "recipient@example.com",
            "recipient_name": "Recipient Name",
            "subject": "Test Email Subject",
            "body_text": "This is a test email body in plain text.",
            "body_html": "<p>This is a test email body in HTML.</p>",
            "campaign_id": str(create_test_campaign.id)
        }
        
        # Act - Send request to send email
        response = client.post(
            "/api/v1/emails/send",
            json=email_send_data,
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 201, f"Failed to send email: {response.text}"
        
        data = response.json()
        assert data["is_sent"] is True
        assert "tracking_id" in data
        
        # Verify email was created in database
        emails = crud.email.get_multi_by_campaign(
            db, campaign_id=create_test_campaign.id, limit=10
        )
        assert len(emails) > 0
        email = emails[0]
        assert email.recipient_email == email_send_data["recipient_email"]
        assert email.subject == email_send_data["subject"]
    
    def test_send_email_no_smtp_config(self, client: TestClient, auth_headers, create_test_campaign):
        """
        Test sending email without SMTP configuration.
        
        ARRANGE:
            - Ensure user has no SMTP credentials configured
            - Set up test data for email sending
        
        ACT:
            - Send a POST request to the email sending endpoint
        
        ASSERT:
            - Verify response status code is 400 (Bad Request)
            - Verify response contains error about missing SMTP credentials
        """
        # Arrange - Set up test data without SMTP config
        email_send_data = {
            "recipient_email": "recipient@example.com",
            "recipient_name": "Recipient Name",
            "subject": "Test Email Subject",
            "body_text": "This is a test email body in plain text.",
            "body_html": "<p>This is a test email body in HTML.</p>",
            "campaign_id": str(create_test_campaign.id)
        }
        
        # Act - Send request to send email
        response = client.post(
            "/api/v1/emails/send",
            json=email_send_data,
            headers=auth_headers
        )
        
        # Assert - Check for SMTP config error
        assert response.status_code == 400
        assert "SMTP configuration" in response.json()["detail"]
    
    def test_send_email_missing_fields(self, client: TestClient, auth_headers, db: Session, create_test_user):
        """
        Test sending email with missing required fields.
        
        ARRANGE:
            - Add SMTP credentials to test user
            - Set up test data with missing required fields
        
        ACT:
            - Send a POST request to the email sending endpoint
        
        ASSERT:
            - Verify response status code is 422 (Unprocessable Entity)
            - Verify response contains validation error details
        """
        # Arrange - Update user with SMTP credentials
        user = create_test_user["user"]
        crud.user.update(db, db_obj=user, obj_in={
            "smtp_host": "smtp.test.com",
            "smtp_port": "587",
            "smtp_user": "test@example.com",
            "smtp_password": "smtp_password",
            "smtp_use_tls": True
        })
        
        # Create invalid data (missing subject)
        invalid_email_data = {
            "recipient_email": "recipient@example.com",
            "recipient_name": "Recipient Name",
            # Missing subject
            "body_text": "This is a test email body in plain text.",
            "body_html": "<p>This is a test email body in HTML.</p>"
        }
        
        # Act - Send request to send email
        response = client.post(
            "/api/v1/emails/send",
            json=invalid_email_data,
            headers=auth_headers
        )
        
        # Assert - Check for validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        
        # Verify response contains validation error details
        assert "subject" in data["detail"]
        assert "is required" in data["detail"]["subject"] 