"""
Unit tests for the follow-up service layer.

This module contains tests for follow_up_service.py functions,
mocking database dependencies and email handling functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.follow_up_service import (
    generate_follow_up_email,
    schedule_follow_ups,
    send_automated_follow_up
)
from app import schemas, models
from app.core.exception_handlers import DatabaseError, EntityNotFoundError, PermissionDeniedError


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy database session."""
    return Mock()


@pytest.fixture
def mock_user_id():
    """Generate a mock user ID."""
    return uuid4()


@pytest.fixture
def mock_campaign_id():
    """Generate a mock campaign ID."""
    return uuid4()


@pytest.fixture
def mock_email_id():
    """Generate a mock email ID."""
    return uuid4()


@pytest.fixture
def mock_email(mock_email_id, mock_campaign_id, mock_user_id):
    """Create a mock email object."""
    email = MagicMock(spec=models.Email)
    email.id = mock_email_id
    email.campaign_id = mock_campaign_id
    email.user_id = mock_user_id
    email.recipient_email = "test@example.com"
    email.recipient_name = "Test User"
    email.subject = "Test Subject"
    email.body_text = "This is a test email."
    email.body_html = "<p>This is a test email.</p>"
    email.is_sent = True
    email.is_opened = True
    email.is_replied = False
    email.is_converted = False
    email.is_follow_up = False
    email.follow_up_number = 0
    email.original_email_id = None
    email.sent_at = datetime.now() - timedelta(days=7)
    email.opened_at = datetime.now() - timedelta(days=5)
    email.replied_at = None
    email.created_at = datetime.now() - timedelta(days=7)
    return email


@pytest.fixture
def mock_campaign(mock_campaign_id, mock_user_id):
    """Create a mock campaign object."""
    campaign = MagicMock(spec=models.EmailCampaign)
    campaign.id = mock_campaign_id
    campaign.user_id = mock_user_id
    campaign.name = "Test Campaign"
    campaign.follow_up_days = [3, 7, 14]  # Follow up after 3, 7, and 14 days
    campaign.max_follow_ups = 3
    campaign.follow_up_template = "Following up on my previous email. {original_message}"
    campaign.is_active = True
    return campaign


@pytest.fixture
def follow_up_request():
    """Create a follow-up request object."""
    return schemas.FollowUpRequest(
        email_id=uuid4(),
        days_delay=5,
        subject="Re: Original Subject",
        message="This is a follow-up message.",
        custom_body_html="<p>This is a <strong>custom</strong> follow-up message.</p>"
    )


class TestGenerateFollowUpEmail:
    """Tests for generate_follow_up_email function."""

    @patch('app.services.follow_up_service.email_service')
    @patch('app.services.follow_up_service.ai_email_generator_service')
    def test_generate_follow_up_email_with_ai(self, mock_ai_service, mock_email_service, 
                                           mock_db, mock_email_id, mock_email, mock_user_id):
        """Test generating a follow-up email using AI service."""
        # Arrange
        mock_db.query().filter().first.return_value = mock_email
        mock_campaign = MagicMock()
        mock_campaign.id = mock_email.campaign_id
        mock_campaign.user_id = mock_user_id
        
        # Mock the AI service response
        mock_response = schemas.EmailGenResponse(
            subject="Re: Test Subject",
            body_text="This is an AI-generated follow-up email.",
            body_html="<p>This is an AI-generated follow-up email.</p>"
        )
        mock_ai_service.generate_follow_up.return_value = mock_response
        
        # Mock the create_follow_up call
        mock_follow_up = MagicMock(spec=models.Email)
        mock_follow_up.id = uuid4()
        mock_follow_up.is_follow_up = True
        mock_follow_up.follow_up_number = 1
        mock_email_service.create_follow_up.return_value = mock_follow_up
        
        # Act
        result = generate_follow_up_email(
            mock_db, 
            mock_email_id, 
            mock_user_id, 
            use_ai=True
        )
        
        # Assert
        assert result == mock_follow_up
        # Verify AI service was called
        mock_ai_service.generate_follow_up.assert_called_once()
        # Verify email service was called with AI-generated content
        mock_email_service.create_follow_up.assert_called_once_with(
            mock_db,
            mock_email_id,
            mock_response.subject,
            mock_response.body_text,
            mock_response.body_html
        )

    @patch('app.services.follow_up_service.email_service')
    def test_generate_follow_up_email_with_template(self, mock_email_service, 
                                               mock_db, mock_email_id, mock_email, mock_campaign, mock_user_id):
        """Test generating a follow-up email using a template."""
        # Arrange
        mock_db.query().filter().first.side_effect = [mock_email, mock_campaign]
        
        # Mock the create_follow_up call
        mock_follow_up = MagicMock(spec=models.Email)
        mock_follow_up.id = uuid4()
        mock_follow_up.is_follow_up = True
        mock_follow_up.follow_up_number = 1
        mock_email_service.create_follow_up.return_value = mock_follow_up
        
        # Act
        result = generate_follow_up_email(
            mock_db, 
            mock_email_id, 
            mock_user_id, 
            use_ai=False
        )
        
        # Assert
        assert result == mock_follow_up
        # Verify email service was called with template-based content
        mock_email_service.create_follow_up.assert_called_once()
        # Check that subject has "Re:" prefix
        call_args = mock_email_service.create_follow_up.call_args[0]
        assert call_args[0] == mock_db
        assert call_args[1] == mock_email_id
        assert call_args[2].startswith("Re: ")
        assert "Follow" in call_args[3]  # Template content in body

    @patch('app.services.follow_up_service.email_service')
    def test_generate_follow_up_email_with_custom_content(self, mock_email_service, 
                                                    mock_db, mock_email_id, mock_email, mock_user_id, follow_up_request):
        """Test generating a follow-up email with custom content."""
        # Arrange
        mock_db.query().filter().first.return_value = mock_email
        
        # Mock the create_follow_up call
        mock_follow_up = MagicMock(spec=models.Email)
        mock_follow_up.id = uuid4()
        mock_follow_up.is_follow_up = True
        mock_follow_up.follow_up_number = 1
        mock_email_service.create_follow_up.return_value = mock_follow_up
        
        # Act
        result = generate_follow_up_email(
            mock_db, 
            mock_email_id, 
            mock_user_id, 
            use_ai=False,
            follow_up_request=follow_up_request
        )
        
        # Assert
        assert result == mock_follow_up
        # Verify email service was called with custom content
        mock_email_service.create_follow_up.assert_called_once_with(
            mock_db,
            mock_email_id,
            follow_up_request.subject,
            follow_up_request.message,
            follow_up_request.custom_body_html
        )

    def test_generate_follow_up_email_not_found(self, mock_db, mock_email_id, mock_user_id):
        """Test generating a follow-up for a non-existent email."""
        # Arrange
        mock_db.query().filter().first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            generate_follow_up_email(mock_db, mock_email_id, mock_user_id)
        
        assert "Email not found" in str(exc_info.value)

    def test_generate_follow_up_email_permission_denied(self, mock_db, mock_email_id, mock_email, mock_user_id):
        """Test generating a follow-up for an email the user doesn't own."""
        # Arrange
        different_user_id = uuid4()
        mock_email.user_id = different_user_id
        mock_db.query().filter().first.return_value = mock_email
        
        # Act & Assert
        with pytest.raises(PermissionDeniedError) as exc_info:
            generate_follow_up_email(mock_db, mock_email_id, mock_user_id)
        
        assert "You don't have permission" in str(exc_info.value)

    def test_generate_follow_up_email_db_error(self, mock_db, mock_email_id, mock_user_id):
        """Test database error handling during follow-up generation."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            generate_follow_up_email(mock_db, mock_email_id, mock_user_id)
        
        assert "Database error" in str(exc_info.value)


class TestScheduleFollowUps:
    """Tests for schedule_follow_ups function."""

    @patch('app.services.follow_up_service.email_service')
    def test_schedule_follow_ups_success(self, mock_email_service, mock_db, mock_campaign_id, mock_campaign, mock_email):
        """Test successfully scheduling follow-ups for multiple emails."""
        # Arrange
        # Create multiple emails for the campaign
        emails = [mock_email]
        for i in range(2):
            email = MagicMock(spec=models.Email)
            email.id = uuid4()
            email.campaign_id = mock_campaign_id
            email.is_sent = True
            email.is_replied = False
            email.is_converted = False
            email.sent_at = datetime.now() - timedelta(days=8)  # Sent 8 days ago
            email.is_follow_up = False
            email.follow_up_number = 0
            
            # Mock that each email has already had one follow-up
            email.follow_ups = [MagicMock()]
            
            emails.append(email)
        
        # Configure mocks
        mock_db.query().filter().first.return_value = mock_campaign
        mock_db.query().filter().all.return_value = emails
        
        # Create mock scheduled follow-ups
        scheduled_follow_ups = []
        for email in emails:
            follow_up = MagicMock()
            follow_up.email_id = email.id
            follow_up.id = uuid4()
            scheduled_follow_ups.append(follow_up)
        
        # Mock the email service to return one of the scheduled follow-ups
        mock_email_service.create_follow_up.side_effect = scheduled_follow_ups
        
        # Act
        result = schedule_follow_ups(mock_db, mock_campaign_id)
        
        # Assert
        assert len(result) == len(emails)
        # Verify that follow-ups were created for all eligible emails
        assert mock_email_service.create_follow_up.call_count == len(emails)

    @patch('app.services.follow_up_service.email_service')
    def test_schedule_follow_ups_no_eligible_emails(self, mock_email_service, mock_db, mock_campaign_id, mock_campaign):
        """Test scheduling follow-ups when no emails are eligible."""
        # Arrange
        # Create emails that are not eligible for follow-up (replied or converted)
        emails = []
        for i in range(3):
            email = MagicMock(spec=models.Email)
            email.id = uuid4()
            email.campaign_id = mock_campaign_id
            email.is_sent = True
            email.is_replied = True if i % 2 == 0 else False
            email.is_converted = True if i % 2 == 1 else False
            email.sent_at = datetime.now() - timedelta(days=8)
            emails.append(email)
        
        # Configure mocks
        mock_db.query().filter().first.return_value = mock_campaign
        mock_db.query().filter().all.return_value = emails
        
        # Act
        result = schedule_follow_ups(mock_db, mock_campaign_id)
        
        # Assert
        assert len(result) == 0
        # Verify that no follow-ups were created
        mock_email_service.create_follow_up.assert_not_called()

    @patch('app.services.follow_up_service.email_service')
    def test_schedule_follow_ups_max_follow_ups_reached(self, mock_email_service, mock_db, mock_campaign_id, mock_campaign):
        """Test scheduling follow-ups when maximum number has been reached."""
        # Arrange
        # Set max follow-ups to 2
        mock_campaign.max_follow_ups = 2
        
        # Create email that already has 2 follow-ups
        email = MagicMock(spec=models.Email)
        email.id = uuid4()
        email.campaign_id = mock_campaign_id
        email.is_sent = True
        email.is_replied = False
        email.is_converted = False
        email.sent_at = datetime.now() - timedelta(days=8)
        
        # Create 2 mock follow-ups for this email
        follow_up1 = MagicMock()
        follow_up1.id = uuid4()
        follow_up1.is_follow_up = True
        follow_up1.follow_up_number = 1
        follow_up2 = MagicMock()
        follow_up2.id = uuid4()
        follow_up2.is_follow_up = True
        follow_up2.follow_up_number = 2
        
        email.follow_ups = [follow_up1, follow_up2]
        
        # Configure mocks
        mock_db.query().filter().first.return_value = mock_campaign
        mock_db.query().filter().all.return_value = [email]
        
        # Act
        result = schedule_follow_ups(mock_db, mock_campaign_id)
        
        # Assert
        assert len(result) == 0
        # Verify that no follow-ups were created
        mock_email_service.create_follow_up.assert_not_called()

    def test_schedule_follow_ups_campaign_not_found(self, mock_db, mock_campaign_id):
        """Test scheduling follow-ups for a non-existent campaign."""
        # Arrange
        mock_db.query().filter().first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            schedule_follow_ups(mock_db, mock_campaign_id)
        
        assert "Campaign not found" in str(exc_info.value)

    def test_schedule_follow_ups_db_error(self, mock_db, mock_campaign_id):
        """Test database error handling during follow-up scheduling."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            schedule_follow_ups(mock_db, mock_campaign_id)
        
        assert "Database error" in str(exc_info.value)


class TestSendAutomatedFollowUp:
    """Tests for send_automated_follow_up function."""

    @patch('app.services.follow_up_service.email_sender_service')
    @patch('app.services.follow_up_service.email_service')
    def test_send_automated_follow_up_success(self, mock_email_service, mock_sender_service, 
                                         mock_db, mock_email_id, mock_email):
        """Test successfully sending an automated follow-up email."""
        # Arrange
        mock_db.query().filter().first.return_value = mock_email
        
        # Mock successful email sending
        mock_sender_service.send_email.return_value = True
        
        # Act
        result = send_automated_follow_up(mock_db, mock_email_id)
        
        # Assert
        assert result is True
        # Verify email was marked as sent
        mock_email_service.mark_as_sent.assert_called_once_with(mock_db, mock_email_id)
        # Verify email was sent with correct parameters
        mock_sender_service.send_email.assert_called_once()
        call_args = mock_sender_service.send_email.call_args[1]
        assert call_args["recipient_email"] == mock_email.recipient_email
        assert call_args["recipient_name"] == mock_email.recipient_name
        assert call_args["subject"] == mock_email.subject
        assert call_args["body_text"] == mock_email.body_text
        assert call_args["body_html"] == mock_email.body_html

    @patch('app.services.follow_up_service.email_sender_service')
    def test_send_automated_follow_up_email_not_found(self, mock_sender_service, mock_db, mock_email_id):
        """Test sending a follow-up for a non-existent email."""
        # Arrange
        mock_db.query().filter().first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            send_automated_follow_up(mock_db, mock_email_id)
        
        assert "Email not found" in str(exc_info.value)
        # Verify no email was sent
        mock_sender_service.send_email.assert_not_called()

    @patch('app.services.follow_up_service.email_sender_service')
    @patch('app.services.follow_up_service.email_service')
    def test_send_automated_follow_up_already_sent(self, mock_email_service, mock_sender_service, 
                                             mock_db, mock_email_id, mock_email):
        """Test sending a follow-up that has already been sent."""
        # Arrange
        mock_email.is_sent = True
        mock_db.query().filter().first.return_value = mock_email
        
        # Act
        result = send_automated_follow_up(mock_db, mock_email_id)
        
        # Assert
        assert result is False
        # Verify no attempt to mark as sent or send email
        mock_email_service.mark_as_sent.assert_not_called()
        mock_sender_service.send_email.assert_not_called()

    @patch('app.services.follow_up_service.email_sender_service')
    @patch('app.services.follow_up_service.email_service')
    def test_send_automated_follow_up_send_failure(self, mock_email_service, mock_sender_service, 
                                             mock_db, mock_email_id, mock_email):
        """Test handling email sending failure."""
        # Arrange
        mock_email.is_sent = False
        mock_db.query().filter().first.return_value = mock_email
        
        # Mock failed email sending
        mock_sender_service.send_email.return_value = False
        
        # Act
        result = send_automated_follow_up(mock_db, mock_email_id)
        
        # Assert
        assert result is False
        # Verify email sending was attempted
        mock_sender_service.send_email.assert_called_once()
        # Verify email was not marked as sent
        mock_email_service.mark_as_sent.assert_not_called()

    def test_send_automated_follow_up_db_error(self, mock_db, mock_email_id):
        """Test database error handling during follow-up sending."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            send_automated_follow_up(mock_db, mock_email_id)
        
        assert "Database error" in str(exc_info.value) 