"""
Unit tests for the email service layer.

This module contains tests for email_service.py functions,
mocking database dependencies and email sending functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.email_service import (
    create_email,
    get_email,
    get_email_by_tracking_id,
    get_emails_by_campaign,
    mark_as_sent,
    mark_as_opened,
    mark_as_replied,
    mark_as_converted,
    create_follow_up,
    get_pending_follow_ups,
    track_email_open,
    delete_email
)
from app import schemas, models
from app.core.exception_handlers import DatabaseError, EntityNotFoundError


@pytest.fixture
def mock_db():
    """Mock SQLAlchemy database session."""
    return Mock()


@pytest.fixture
def mock_campaign_id():
    """Generate a mock campaign ID."""
    return uuid4()


@pytest.fixture
def mock_email_id():
    """Generate a mock email ID."""
    return uuid4()


@pytest.fixture
def mock_tracking_id():
    """Generate a mock tracking ID."""
    return "tracking_123456789"


@pytest.fixture
def email_data():
    """Generate sample email send request data."""
    return schemas.EmailSendRequest(
        recipient_email="test@example.com",
        recipient_name="Test User",
        subject="Test Subject",
        body_text="This is a test email.",
        body_html="<p>This is a test email.</p>",
        recipient_company="Test Company",
        recipient_job_title="Test Manager",
        ab_test_variant="A"
    )


@pytest.fixture
def mock_email(mock_email_id, mock_campaign_id, mock_tracking_id):
    """Create a mock email object."""
    email = MagicMock(spec=models.Email)
    email.id = mock_email_id
    email.campaign_id = mock_campaign_id
    email.recipient_email = "test@example.com"
    email.recipient_name = "Test User"
    email.recipient_company = "Test Company"
    email.recipient_job_title = "Test Manager"
    email.subject = "Test Subject"
    email.body_text = "This is a test email."
    email.body_html = "<p>This is a test email.</p>"
    email.is_sent = False
    email.is_opened = False
    email.is_replied = False
    email.is_converted = False
    email.is_follow_up = False
    email.follow_up_number = 0
    email.original_email_id = None
    email.tracking_id = mock_tracking_id
    email.sent_at = None
    email.opened_at = None
    email.replied_at = None
    email.converted_at = None
    email.created_at = datetime.now()
    email.num_opens = 0
    return email


class TestCreateEmail:
    """Tests for create_email function."""

    def test_create_email_success(self, mock_db, email_data, mock_campaign_id, mock_email):
        """Test successful email creation."""
        # Arrange
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Set up the mocked Email to be created
        with patch('app.models.Email', return_value=mock_email) as mock_model:
            # Act
            result = create_email(mock_db, email_data, mock_campaign_id)
            
            # Assert
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
            assert result == mock_email
            # Verify model init was called with correct params
            mock_model.assert_called_once()

    def test_create_email_with_minimal_data(self, mock_db, mock_campaign_id, mock_email):
        """Test email creation with minimal required data."""
        # Arrange
        minimal_data = schemas.EmailSendRequest(
            recipient_email="minimal@example.com",
            recipient_name="Minimal User",
            subject="Minimal Subject",
            body_text="Minimal body text",
            body_html="<p>Minimal body HTML</p>"
        )
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Set up the mocked Email to be created
        with patch('app.models.Email', return_value=mock_email) as mock_model:
            # Act
            result = create_email(mock_db, minimal_data, mock_campaign_id)
            
            # Assert
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
            assert result == mock_email

    def test_create_email_db_error(self, mock_db, email_data, mock_campaign_id):
        """Test database error handling during email creation."""
        # Arrange
        mock_db.add.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            create_email(mock_db, email_data, mock_campaign_id)
        
        assert "Database error" in str(exc_info.value)
        mock_db.commit.assert_not_called()


class TestGetEmail:
    """Tests for get_email function."""

    def test_get_email_found(self, mock_db, mock_email_id, mock_email):
        """Test retrieving an existing email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = get_email(mock_db, mock_email_id)
        
        # Assert
        assert result == mock_email
        mock_db.query.assert_called_once()

    def test_get_email_not_found(self, mock_db, mock_email_id):
        """Test retrieving a non-existent email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = get_email(mock_db, mock_email_id)
        
        # Assert
        assert result is None
        mock_db.query.assert_called_once()

    def test_get_email_db_error(self, mock_db, mock_email_id):
        """Test database error handling during email retrieval."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_email(mock_db, mock_email_id)
        
        assert "Database error" in str(exc_info.value)


class TestGetEmailByTrackingId:
    """Tests for get_email_by_tracking_id function."""

    def test_get_email_by_tracking_id_found(self, mock_db, mock_tracking_id, mock_email):
        """Test retrieving an email by its tracking ID."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = get_email_by_tracking_id(mock_db, mock_tracking_id)
        
        # Assert
        assert result == mock_email
        mock_db.query.assert_called_once()

    def test_get_email_by_tracking_id_not_found(self, mock_db, mock_tracking_id):
        """Test retrieving an email with non-existent tracking ID."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = get_email_by_tracking_id(mock_db, mock_tracking_id)
        
        # Assert
        assert result is None
        mock_db.query.assert_called_once()

    def test_get_email_by_tracking_id_db_error(self, mock_db, mock_tracking_id):
        """Test database error handling during email retrieval by tracking ID."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_email_by_tracking_id(mock_db, mock_tracking_id)
        
        assert "Database error" in str(exc_info.value)


class TestGetEmailsByCampaign:
    """Tests for get_emails_by_campaign function."""

    def test_get_emails_by_campaign_success(self, mock_db, mock_campaign_id, mock_email):
        """Test successfully retrieving emails for a campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_email]
        
        # Act
        result = get_emails_by_campaign(mock_db, mock_campaign_id)
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_email
        mock_db.query.assert_called_once()

    def test_get_emails_by_campaign_empty(self, mock_db, mock_campaign_id):
        """Test retrieving an empty list of emails for a campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        # Act
        result = get_emails_by_campaign(mock_db, mock_campaign_id)
        
        # Assert
        assert len(result) == 0
        mock_db.query.assert_called_once()

    def test_get_emails_by_campaign_with_pagination(self, mock_db, mock_campaign_id, mock_email):
        """Test retrieving emails for a campaign with pagination."""
        # Arrange
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_email]
        
        # Act
        result = get_emails_by_campaign(mock_db, mock_campaign_id, skip=10, limit=5)
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_email
        # Verify that offset and limit were called with correct values
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.assert_called_once_with(10)
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.assert_called_once_with(5)

    def test_get_emails_by_campaign_db_error(self, mock_db, mock_campaign_id):
        """Test database error handling during emails retrieval."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_emails_by_campaign(mock_db, mock_campaign_id)
        
        assert "Database error" in str(exc_info.value)


class TestMarkAsSent:
    """Tests for mark_as_sent function."""

    def test_mark_as_sent_success(self, mock_db, mock_email_id, mock_email):
        """Test successfully marking an email as sent."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = mark_as_sent(mock_db, mock_email_id)
        
        # Assert
        assert result == mock_email
        assert result.is_sent is True
        assert result.sent_at is not None
        mock_db.add.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_email)

    def test_mark_as_sent_not_found(self, mock_db, mock_email_id):
        """Test marking a non-existent email as sent."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            mark_as_sent(mock_db, mock_email_id)
        
        assert "Email not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_mark_as_sent_db_error(self, mock_db, mock_email_id, mock_email):
        """Test database error handling when marking an email as sent."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            mark_as_sent(mock_db, mock_email_id)
        
        assert "Database error" in str(exc_info.value)


class TestMarkAsOpened:
    """Tests for mark_as_opened function."""

    def test_mark_as_opened_success(self, mock_db, mock_tracking_id, mock_email):
        """Test successfully marking an email as opened."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = mark_as_opened(mock_db, mock_tracking_id)
        
        # Assert
        assert result == mock_email
        assert result.is_opened is True
        assert result.num_opens == 1
        assert result.opened_at is not None
        mock_db.add.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_email)

    def test_mark_as_opened_multiple_times(self, mock_db, mock_tracking_id, mock_email):
        """Test marking an email as opened multiple times (counts should increment)."""
        # Arrange
        mock_email.is_opened = True
        mock_email.num_opens = 2
        mock_email.opened_at = datetime.now() - timedelta(days=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = mark_as_opened(mock_db, mock_tracking_id)
        
        # Assert
        assert result == mock_email
        assert result.is_opened is True
        assert result.num_opens == 3  # Incremented from 2 to 3
        # opened_at should not be updated on subsequent opens
        assert result.opened_at == mock_email.opened_at
        mock_db.add.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_email)

    def test_mark_as_opened_not_found(self, mock_db, mock_tracking_id):
        """Test marking a non-existent email as opened."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = mark_as_opened(mock_db, mock_tracking_id)
        
        # Assert
        assert result is None
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_mark_as_opened_db_error(self, mock_db, mock_tracking_id, mock_email):
        """Test database error handling when marking an email as opened."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            mark_as_opened(mock_db, mock_tracking_id)
        
        assert "Database error" in str(exc_info.value)


class TestMarkAsReplied:
    """Tests for mark_as_replied function."""

    def test_mark_as_replied_success(self, mock_db, mock_email_id, mock_email):
        """Test successfully marking an email as replied."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = mark_as_replied(mock_db, mock_email_id)
        
        # Assert
        assert result == mock_email
        assert result.is_replied is True
        assert result.replied_at is not None
        mock_db.add.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_email)

    def test_mark_as_replied_already_replied(self, mock_db, mock_email_id, mock_email):
        """Test marking an already replied email."""
        # Arrange
        mock_email.is_replied = True
        mock_email.replied_at = datetime.now() - timedelta(days=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = mark_as_replied(mock_db, mock_email_id)
        
        # Assert
        assert result == mock_email
        assert result.is_replied is True
        # replied_at should not be updated when already replied
        assert result.replied_at == mock_email.replied_at
        mock_db.add.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_email)

    def test_mark_as_replied_not_found(self, mock_db, mock_email_id):
        """Test marking a non-existent email as replied."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            mark_as_replied(mock_db, mock_email_id)
        
        assert "not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_mark_as_replied_db_error(self, mock_db, mock_email_id, mock_email):
        """Test database error handling when marking an email as replied."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            mark_as_replied(mock_db, mock_email_id)
        
        assert "Database error" in str(exc_info.value)


class TestMarkAsConverted:
    """Tests for mark_as_converted function."""

    def test_mark_as_converted_success(self, mock_db, mock_email_id, mock_email):
        """Test successful marking email as converted."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_email.is_converted = False
        mock_email.converted_at = None
        
        # Act
        result = mark_as_converted(mock_db, mock_email_id)
        
        # Assert
        assert result == mock_email
        assert result.is_converted is True
        assert result.converted_at is not None
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_mark_as_converted_already_converted(self, mock_db, mock_email_id, mock_email):
        """Test marking an already converted email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_email.is_converted = True
        mock_email.converted_at = datetime.now() - timedelta(days=1)
        
        # Act
        result = mark_as_converted(mock_db, mock_email_id)
        
        # Assert
        assert result == mock_email
        assert result.is_converted is True
        # The converted_at timestamp should not change
        assert result.converted_at == mock_email.converted_at
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_mark_as_converted_not_found(self, mock_db, mock_email_id):
        """Test marking as converted for non-existent email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            mark_as_converted(mock_db, mock_email_id)
        
        assert "Email not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_mark_as_converted_db_error(self, mock_db, mock_email_id, mock_email):
        """Test database error handling during marking as converted."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_email.is_converted = False
        mock_email.converted_at = None
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            mark_as_converted(mock_db, mock_email_id)
        
        assert "Database error" in str(exc_info.value)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_not_called()


class TestCreateFollowUp:
    """Tests for create_follow_up function."""

    def test_create_follow_up_success(self, mock_db, mock_email_id, mock_email):
        """Test successful follow-up creation."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        follow_up_data = {
            "subject": "Follow-up: Test Subject",
            "body_text": "This is a follow-up email.",
            "body_html": "<p>This is a follow-up email.</p>",
        }
        
        # Create a mock follow-up email
        mock_follow_up = MagicMock(spec=models.Email)
        mock_follow_up.id = uuid4()
        mock_follow_up.campaign_id = mock_email.campaign_id
        mock_follow_up.recipient_email = mock_email.recipient_email
        mock_follow_up.recipient_name = mock_email.recipient_name
        mock_follow_up.subject = follow_up_data["subject"]
        mock_follow_up.body_text = follow_up_data["body_text"]
        mock_follow_up.body_html = follow_up_data["body_html"]
        mock_follow_up.is_follow_up = True
        mock_follow_up.follow_up_number = 1
        mock_follow_up.original_email_id = mock_email_id
        
        # Set up the mocked Email to be created
        with patch('app.models.Email', return_value=mock_follow_up) as mock_model:
            # Act
            result = create_follow_up(mock_db, mock_email_id, follow_up_data["subject"], 
                                     follow_up_data["body_text"], follow_up_data["body_html"])
            
            # Assert
            assert result == mock_follow_up
            assert result.is_follow_up is True
            assert result.follow_up_number == 1
            assert result.original_email_id == mock_email_id
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    def test_create_follow_up_for_follow_up(self, mock_db, mock_email_id, mock_email):
        """Test creating a follow-up for a follow-up email."""
        # Arrange
        mock_email.is_follow_up = True
        mock_email.follow_up_number = 1
        mock_email.original_email_id = uuid4()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        follow_up_data = {
            "subject": "Follow-up 2: Test Subject",
            "body_text": "This is a second follow-up email.",
            "body_html": "<p>This is a second follow-up email.</p>",
        }
        
        # Create a mock follow-up email
        mock_follow_up = MagicMock(spec=models.Email)
        mock_follow_up.id = uuid4()
        mock_follow_up.campaign_id = mock_email.campaign_id
        mock_follow_up.recipient_email = mock_email.recipient_email
        mock_follow_up.recipient_name = mock_email.recipient_name
        mock_follow_up.subject = follow_up_data["subject"]
        mock_follow_up.body_text = follow_up_data["body_text"]
        mock_follow_up.body_html = follow_up_data["body_html"]
        mock_follow_up.is_follow_up = True
        mock_follow_up.follow_up_number = 2
        mock_follow_up.original_email_id = mock_email_id
        
        # Set up the mocked Email to be created
        with patch('app.models.Email', return_value=mock_follow_up) as mock_model:
            # Act
            result = create_follow_up(mock_db, mock_email_id, follow_up_data["subject"], 
                                     follow_up_data["body_text"], follow_up_data["body_html"])
            
            # Assert
            assert result == mock_follow_up
            assert result.is_follow_up is True
            assert result.follow_up_number == 2  # Increased from previous follow-up
            assert result.original_email_id == mock_email_id
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()

    def test_create_follow_up_email_not_found(self, mock_db, mock_email_id):
        """Test follow-up creation for non-existent email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        follow_up_data = {
            "subject": "Follow-up: Test Subject",
            "body_text": "This is a follow-up email.",
            "body_html": "<p>This is a follow-up email.</p>",
        }
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            create_follow_up(mock_db, mock_email_id, follow_up_data["subject"], 
                            follow_up_data["body_text"], follow_up_data["body_html"])
        
        assert "Email not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_create_follow_up_db_error(self, mock_db, mock_email_id, mock_email):
        """Test database error handling during follow-up creation."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_db.add.side_effect = SQLAlchemyError("Database error")
        
        follow_up_data = {
            "subject": "Follow-up: Test Subject",
            "body_text": "This is a follow-up email.",
            "body_html": "<p>This is a follow-up email.</p>",
        }
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            create_follow_up(mock_db, mock_email_id, follow_up_data["subject"], 
                            follow_up_data["body_text"], follow_up_data["body_html"])
        
        assert "Database error" in str(exc_info.value)
        mock_db.commit.assert_not_called()


class TestGetPendingFollowUps:
    """Tests for get_pending_follow_ups function."""

    def test_get_pending_follow_ups_success(self, mock_db, mock_email, mock_campaign_id):
        """Test successful retrieval of pending follow-ups."""
        # Arrange
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_email]
        
        # Act
        result = get_pending_follow_ups(mock_db)
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_email
        mock_db.query.assert_called_once()

    def test_get_pending_follow_ups_empty(self, mock_db):
        """Test retrieval of pending follow-ups when none are available."""
        # Arrange
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Act
        result = get_pending_follow_ups(mock_db)
        
        # Assert
        assert len(result) == 0
        mock_db.query.assert_called_once()

    def test_get_pending_follow_ups_db_error(self, mock_db):
        """Test database error handling during pending follow-ups retrieval."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_pending_follow_ups(mock_db)
        
        assert "Database error" in str(exc_info.value)


class TestTrackEmailOpen:
    """Tests for track_email_open function."""

    def test_track_email_open_success(self, mock_db, mock_tracking_id, mock_email):
        """Test successful tracking of email open."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = track_email_open(mock_db, mock_tracking_id)
        
        # Assert
        assert result == mock_email
        assert result.is_opened is True
        assert result.num_opens == 1
        assert result.opened_at is not None
        mock_db.add.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_email)

    def test_track_email_open_not_found(self, mock_db, mock_tracking_id):
        """Test tracking open for non-existent email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = track_email_open(mock_db, mock_tracking_id)
        
        # Assert
        assert result is None
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_track_email_open_db_error(self, mock_db, mock_tracking_id, mock_email):
        """Test database error handling during open tracking."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            track_email_open(mock_db, mock_tracking_id)
        
        assert "Database error" in str(exc_info.value)


class TestDeleteEmail:
    """Tests for delete_email function."""

    def test_delete_email_success(self, mock_db, mock_email_id, mock_email):
        """Test successful email deletion."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        
        # Act
        result = delete_email(mock_db, mock_email_id)
        
        # Assert
        assert result == mock_email
        mock_db.delete.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once()

    def test_delete_email_not_found(self, mock_db, mock_email_id):
        """Test deleting non-existent email."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            delete_email(mock_db, mock_email_id)
        
        assert "Email not found" in str(exc_info.value)
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_delete_email_db_error(self, mock_db, mock_email_id, mock_email):
        """Test database error handling during email deletion."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_email
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            delete_email(mock_db, mock_email_id)
        
        assert "Database error" in str(exc_info.value)
        mock_db.delete.assert_called_once_with(mock_email)
        mock_db.commit.assert_called_once() 