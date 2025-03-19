"""
Unit tests for the campaign service layer.

This module contains tests for campaign_service.py functions,
using mocks to isolate from database dependencies.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from uuid import uuid4, UUID

from app.services.campaign_service import (
    create_campaign,
    get_campaign,
    get_campaigns,
    update_campaign,
    delete_campaign,
    get_active_campaigns,
    configure_ab_testing,
    update_campaign_stats
)
from app import schemas, models
from app.core.exception_handlers import DatabaseError, EntityNotFoundError, ResourceConflictError


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
def campaign_create_data():
    """Generate sample campaign creation data."""
    return schemas.CampaignCreate(
        name="Test Campaign",
        description="A test campaign",
        target_audience="Software developers",
        is_active=True
    )


@pytest.fixture
def campaign_update_data():
    """Generate sample campaign update data."""
    return schemas.CampaignUpdate(
        name="Updated Campaign",
        description="Updated description",
        is_active=False
    )


@pytest.fixture
def mock_campaign(mock_campaign_id, mock_user_id):
    """Create a mock campaign object."""
    campaign = MagicMock(spec=models.EmailCampaign)
    campaign.id = mock_campaign_id
    campaign.user_id = mock_user_id
    campaign.name = "Test Campaign"
    campaign.description = "A test campaign"
    campaign.target_audience = "Software developers"
    campaign.is_active = True
    campaign.created_at = "2023-01-01T00:00:00"
    campaign.updated_at = "2023-01-01T00:00:00"
    campaign.total_emails = 10
    campaign.opened_emails = 5
    campaign.replied_emails = 2
    campaign.converted_emails = 1
    campaign.ab_test_active = False
    campaign.ab_test_variants = None
    return campaign


class TestCreateCampaign:
    """Tests for create_campaign function."""

    def test_create_campaign_success(self, mock_db, campaign_create_data, mock_user_id, mock_campaign):
        """Test successful campaign creation."""
        # Arrange
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Set up the mocked EmailCampaign to be created
        with patch('app.models.EmailCampaign', return_value=mock_campaign) as mock_model:
            # Act
            result = create_campaign(mock_db, campaign_create_data, mock_user_id)
            
            # Assert
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once()
            assert result == mock_campaign
            # Verify model init was called with correct params
            mock_model.assert_called_once()

    def test_create_campaign_db_error(self, mock_db, campaign_create_data, mock_user_id):
        """Test database error handling during campaign creation."""
        # Arrange
        mock_db.add.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            create_campaign(mock_db, campaign_create_data, mock_user_id)
        
        assert "Database error" in str(exc_info.value)
        mock_db.commit.assert_not_called()


class TestGetCampaign:
    """Tests for get_campaign function."""

    def test_get_campaign_found(self, mock_db, mock_campaign_id, mock_campaign):
        """Test retrieving an existing campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        
        # Act
        result = get_campaign(mock_db, mock_campaign_id)
        
        # Assert
        assert result == mock_campaign
        mock_db.query.assert_called_once()

    def test_get_campaign_not_found(self, mock_db, mock_campaign_id):
        """Test retrieving a non-existent campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act
        result = get_campaign(mock_db, mock_campaign_id)
        
        # Assert
        assert result is None
        mock_db.query.assert_called_once()

    def test_get_campaign_db_error(self, mock_db, mock_campaign_id):
        """Test database error handling during campaign retrieval."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_campaign(mock_db, mock_campaign_id)
        
        assert "Database error" in str(exc_info.value)


class TestGetCampaigns:
    """Tests for get_campaigns function."""

    def test_get_campaigns_success(self, mock_db, mock_user_id, mock_campaign):
        """Test successfully retrieving a list of campaigns."""
        # Arrange
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_campaign]
        
        # Act
        result = get_campaigns(mock_db, mock_user_id, skip=0, limit=10)
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_campaign
        mock_db.query.assert_called_once()

    def test_get_campaigns_empty(self, mock_db, mock_user_id):
        """Test retrieving an empty list of campaigns."""
        # Arrange
        mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
        
        # Act
        result = get_campaigns(mock_db, mock_user_id, skip=0, limit=10)
        
        # Assert
        assert len(result) == 0
        mock_db.query.assert_called_once()

    def test_get_campaigns_db_error(self, mock_db, mock_user_id):
        """Test database error handling during campaigns retrieval."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_campaigns(mock_db, mock_user_id)
        
        assert "Database error" in str(exc_info.value)


class TestUpdateCampaign:
    """Tests for update_campaign function."""

    def test_update_campaign_success(self, mock_db, mock_campaign_id, mock_user_id, mock_campaign, campaign_update_data):
        """Test successful campaign update."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        
        # Act
        result = update_campaign(mock_db, mock_campaign_id, campaign_update_data)
        
        # Assert
        assert result == mock_campaign
        assert result.name == campaign_update_data.name
        assert result.description == campaign_update_data.description
        assert result.is_active == campaign_update_data.is_active
        mock_db.add.assert_called_once_with(mock_campaign)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_campaign)

    def test_update_campaign_not_found(self, mock_db, mock_campaign_id, campaign_update_data):
        """Test updating a non-existent campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            update_campaign(mock_db, mock_campaign_id, campaign_update_data)
        
        assert "not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_update_campaign_db_error(self, mock_db, mock_campaign_id, mock_campaign, campaign_update_data):
        """Test database error handling during campaign update."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            update_campaign(mock_db, mock_campaign_id, campaign_update_data)
        
        assert "Database error" in str(exc_info.value)


class TestDeleteCampaign:
    """Tests for delete_campaign function."""

    def test_delete_campaign_success(self, mock_db, mock_campaign_id, mock_campaign):
        """Test successful campaign deletion."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        
        # Act
        result = delete_campaign(mock_db, mock_campaign_id)
        
        # Assert
        assert result == mock_campaign
        mock_db.delete.assert_called_once_with(mock_campaign)
        mock_db.commit.assert_called_once()

    def test_delete_campaign_not_found(self, mock_db, mock_campaign_id):
        """Test deleting a non-existent campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            delete_campaign(mock_db, mock_campaign_id)
        
        assert "not found" in str(exc_info.value)
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_delete_campaign_db_error(self, mock_db, mock_campaign_id, mock_campaign):
        """Test database error handling during campaign deletion."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            delete_campaign(mock_db, mock_campaign_id)
        
        assert "Database error" in str(exc_info.value)


class TestGetActiveCampaigns:
    """Tests for get_active_campaigns function."""

    def test_get_active_campaigns_success(self, mock_db, mock_user_id, mock_campaign):
        """Test successfully retrieving active campaigns."""
        # Arrange
        mock_campaign.is_active = True
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_campaign]
        
        # Act
        result = get_active_campaigns(mock_db, mock_user_id)
        
        # Assert
        assert len(result) == 1
        assert result[0] == mock_campaign
        assert result[0].is_active is True
        mock_db.query.assert_called_once()

    def test_get_active_campaigns_empty(self, mock_db, mock_user_id):
        """Test retrieving an empty list of active campaigns."""
        # Arrange
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        # Act
        result = get_active_campaigns(mock_db, mock_user_id)
        
        # Assert
        assert len(result) == 0
        mock_db.query.assert_called_once()


class TestConfigureABTesting:
    """Tests for configure_ab_testing function."""

    def test_configure_ab_testing_success(self, mock_db, mock_campaign_id, mock_campaign):
        """Test successful A/B testing configuration."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        
        ab_variants = {
            "A": "Value proposition focused",
            "B": "Problem-solution focused"
        }
        
        # Act
        result = configure_ab_testing(mock_db, mock_campaign_id, ab_variants, True)
        
        # Assert
        assert result == mock_campaign
        assert result.ab_test_active is True
        assert result.ab_test_variants == ab_variants
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_configure_ab_testing_disable(self, mock_db, mock_campaign_id, mock_campaign):
        """Test disabling A/B testing for a campaign."""
        # Arrange
        mock_campaign.ab_test_active = True
        mock_campaign.ab_test_variants = {"A": "Test A", "B": "Test B"}
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        
        # Act
        result = configure_ab_testing(mock_db, mock_campaign_id, None, False)
        
        # Assert
        assert result == mock_campaign
        assert result.ab_test_active is False
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_configure_ab_testing_update_variants(self, mock_db, mock_campaign_id, mock_campaign):
        """Test updating A/B test variants for a campaign."""
        # Arrange
        mock_campaign.ab_test_active = True
        mock_campaign.ab_test_variants = {"A": "Original A", "B": "Original B"}
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        
        new_variants = {
            "A": "New approach A",
            "B": "New approach B",
            "C": "New approach C"
        }
        
        # Act
        result = configure_ab_testing(mock_db, mock_campaign_id, new_variants, True)
        
        # Assert
        assert result == mock_campaign
        assert result.ab_test_active is True
        assert result.ab_test_variants == new_variants
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_configure_ab_testing_campaign_not_found(self, mock_db, mock_campaign_id):
        """Test A/B testing configuration for non-existent campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        ab_variants = {
            "A": "Value proposition focused",
            "B": "Problem-solution focused"
        }
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            configure_ab_testing(mock_db, mock_campaign_id, ab_variants, True)
        
        assert "Campaign not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_configure_ab_testing_db_error(self, mock_db, mock_campaign_id, mock_campaign):
        """Test database error handling during A/B testing configuration."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        ab_variants = {
            "A": "Value proposition focused",
            "B": "Problem-solution focused"
        }
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            configure_ab_testing(mock_db, mock_campaign_id, ab_variants, True)
        
        assert "Database error" in str(exc_info.value)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_not_called()


class TestUpdateCampaignStats:
    """Tests for update_campaign_stats function."""

    def test_update_stats_success(self, mock_db, mock_campaign_id, mock_campaign):
        """Test successful campaign stats update."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        original_total = mock_campaign.total_emails
        original_opened = mock_campaign.opened_emails
        
        stats_update = {
            "total_emails": original_total + 5,
            "opened_emails": original_opened + 3
        }
        
        # Act
        result = update_campaign_stats(mock_db, mock_campaign_id, stats_update)
        
        # Assert
        assert result == mock_campaign
        assert result.total_emails == original_total + 5
        assert result.opened_emails == original_opened + 3
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_stats_partial(self, mock_db, mock_campaign_id, mock_campaign):
        """Test updating only some campaign stats fields."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        original_total = mock_campaign.total_emails
        original_replied = mock_campaign.replied_emails
        
        # Only update replied_emails
        stats_update = {
            "replied_emails": original_replied + 1
        }
        
        # Act
        result = update_campaign_stats(mock_db, mock_campaign_id, stats_update)
        
        # Assert
        assert result == mock_campaign
        assert result.total_emails == original_total  # Unchanged
        assert result.replied_emails == original_replied + 1  # Updated
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_stats_campaign_not_found(self, mock_db, mock_campaign_id):
        """Test updating stats for a non-existent campaign."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        stats_update = {
            "total_emails": 15,
            "opened_emails": 8
        }
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            update_campaign_stats(mock_db, mock_campaign_id, stats_update)
        
        assert "Campaign not found" in str(exc_info.value)
        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_update_stats_invalid_field(self, mock_db, mock_campaign_id, mock_campaign):
        """Test handling invalid stats field names."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        
        # Include an invalid field name
        stats_update = {
            "total_emails": 15,
            "invalid_field": 8
        }
        
        # Act
        result = update_campaign_stats(mock_db, mock_campaign_id, stats_update)
        
        # Assert
        assert result == mock_campaign
        assert result.total_emails == 15
        # Should not have set the invalid field
        assert not hasattr(result, "invalid_field")
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_update_stats_db_error(self, mock_db, mock_campaign_id, mock_campaign):
        """Test database error handling during stats update."""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_campaign
        mock_db.commit.side_effect = SQLAlchemyError("Database error")
        
        stats_update = {
            "total_emails": 15,
            "opened_emails": 8
        }
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            update_campaign_stats(mock_db, mock_campaign_id, stats_update)
        
        assert "Database error" in str(exc_info.value)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_not_called() 