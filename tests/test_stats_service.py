"""
Unit tests for the stats service layer.

This module contains tests for stats_service.py functions,
mocking database dependencies and ensuring proper statistics calculations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError
from uuid import uuid4
from datetime import datetime

from app.services.stats_service import (
    get_campaign_stats,
    get_user_stats,
    calculate_ab_test_results
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
def mock_campaign(mock_campaign_id, mock_user_id):
    """Create a mock campaign object."""
    campaign = MagicMock(spec=models.EmailCampaign)
    campaign.id = mock_campaign_id
    campaign.user_id = mock_user_id
    campaign.name = "Test Campaign"
    campaign.description = "A test campaign"
    campaign.target_audience = "Software developers"
    campaign.is_active = True
    campaign.created_at = datetime.now()
    campaign.updated_at = datetime.now()
    campaign.total_emails = 100
    campaign.opened_emails = 50
    campaign.replied_emails = 20
    campaign.converted_emails = 10
    campaign.ab_test_active = True
    campaign.ab_test_variants = {"A": "Version A", "B": "Version B"}
    return campaign


@pytest.fixture
def mock_emails():
    """Create a list of mock email objects for testing stats."""
    emails = []
    
    # Create 30 "A" variant emails
    for i in range(30):
        email = MagicMock(spec=models.Email)
        email.id = uuid4()
        email.ab_test_variant = "A"
        email.is_sent = True
        # Set different open/reply/conversion rates for each variant
        email.is_opened = i < 15  # 15/30 = 50% open rate
        email.is_replied = i < 9  # 9/30 = 30% reply rate
        email.is_converted = i < 3  # 3/30 = 10% conversion rate
        emails.append(email)
    
    # Create 30 "B" variant emails
    for i in range(30):
        email = MagicMock(spec=models.Email)
        email.id = uuid4()
        email.ab_test_variant = "B"
        email.is_sent = True
        # Set different open/reply/conversion rates for each variant
        email.is_opened = i < 21  # 21/30 = 70% open rate
        email.is_replied = i < 12  # 12/30 = 40% reply rate
        email.is_converted = i < 6  # 6/30 = 20% conversion rate
        emails.append(email)
    
    # Create 20 emails with no variant (control group)
    for i in range(20):
        email = MagicMock(spec=models.Email)
        email.id = uuid4()
        email.ab_test_variant = None
        email.is_sent = True
        email.is_opened = i < 10  # 10/20 = 50% open rate
        email.is_replied = i < 6  # 6/20 = 30% reply rate
        email.is_converted = i < 2  # 2/20 = 10% conversion rate
        emails.append(email)
    
    return emails


class TestGetCampaignStats:
    """Tests for get_campaign_stats function."""

    def test_get_campaign_stats_success(self, mock_db, mock_campaign_id, mock_user_id, mock_campaign, mock_emails):
        """Test successfully retrieving campaign statistics."""
        # Arrange
        mock_db.query().filter().first.return_value = mock_campaign
        mock_db.query().filter().all.return_value = mock_emails
        
        # Mock the calculate_ab_test_results function
        ab_test_results = {
            "A": {"sent": 30, "opened": 15, "replied": 9, "converted": 3, 
                 "open_rate": 50.0, "reply_rate": 30.0, "conversion_rate": 10.0},
            "B": {"sent": 30, "opened": 21, "replied": 12, "converted": 6,
                 "open_rate": 70.0, "reply_rate": 40.0, "conversion_rate": 20.0},
            "winner": "B"
        }
        
        with patch('app.services.stats_service.calculate_ab_test_results', return_value=ab_test_results):
            # Act
            result = get_campaign_stats(mock_db, mock_campaign_id, mock_user_id)
            
            # Assert
            assert result.campaign_id == mock_campaign_id
            assert result.name == mock_campaign.name
            assert result.total_emails == mock_campaign.total_emails
            assert result.opened_emails == mock_campaign.opened_emails
            assert result.replied_emails == mock_campaign.replied_emails
            assert result.converted_emails == mock_campaign.converted_emails
            assert result.open_rate == 50.0  # 50/100 = 50%
            assert result.reply_rate == 20.0  # 20/100 = 20%
            assert result.conversion_rate == 10.0  # 10/100 = 10%
            assert result.ab_test_results == ab_test_results

    def test_get_campaign_stats_campaign_not_found(self, mock_db, mock_campaign_id, mock_user_id):
        """Test retrieving stats for a non-existent campaign."""
        # Arrange
        mock_db.query().filter().first.return_value = None
        
        # Act & Assert
        with pytest.raises(EntityNotFoundError) as exc_info:
            get_campaign_stats(mock_db, mock_campaign_id, mock_user_id)
        
        assert "Campaign not found" in str(exc_info.value)

    def test_get_campaign_stats_permission_denied(self, mock_db, mock_campaign_id, mock_user_id, mock_campaign):
        """Test retrieving stats for a campaign the user doesn't own."""
        # Arrange
        mock_campaign.user_id = uuid4()  # Different from mock_user_id
        mock_db.query().filter().first.return_value = mock_campaign
        
        # Act & Assert
        with pytest.raises(PermissionDeniedError) as exc_info:
            get_campaign_stats(mock_db, mock_campaign_id, mock_user_id)
        
        assert "You don't have permission" in str(exc_info.value)

    def test_get_campaign_stats_no_ab_testing(self, mock_db, mock_campaign_id, mock_user_id, mock_campaign):
        """Test retrieving stats for a campaign without A/B testing."""
        # Arrange
        mock_campaign.ab_test_active = False
        mock_db.query().filter().first.return_value = mock_campaign
        
        # Act
        result = get_campaign_stats(mock_db, mock_campaign_id, mock_user_id)
        
        # Assert
        assert result.campaign_id == mock_campaign_id
        assert result.ab_test_results is None

    def test_get_campaign_stats_db_error(self, mock_db, mock_campaign_id, mock_user_id):
        """Test database error handling during stats retrieval."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_campaign_stats(mock_db, mock_campaign_id, mock_user_id)
        
        assert "Database error" in str(exc_info.value)


class TestGetUserStats:
    """Tests for get_user_stats function."""

    def test_get_user_stats_success(self, mock_db, mock_user_id, mock_campaign):
        """Test successfully retrieving user statistics."""
        # Arrange
        # Create multiple campaigns for the user
        campaigns = [mock_campaign]
        for i in range(2):
            campaign = MagicMock(spec=models.EmailCampaign)
            campaign.id = uuid4()
            campaign.user_id = mock_user_id
            campaign.name = f"Test Campaign {i+2}"
            campaign.total_emails = 50 + i*20
            campaign.opened_emails = 25 + i*10
            campaign.replied_emails = 10 + i*5
            campaign.converted_emails = 5 + i*2
            campaign.ab_test_active = False
            campaigns.append(campaign)
        
        mock_db.query().filter().all.return_value = campaigns
        
        # Mock get_campaign_stats to return predefined stats
        def mock_get_stats(db, campaign_id, user_id):
            for c in campaigns:
                if c.id == campaign_id:
                    stats = schemas.CampaignStats(
                        campaign_id=c.id,
                        name=c.name,
                        total_emails=c.total_emails,
                        opened_emails=c.opened_emails,
                        replied_emails=c.replied_emails,
                        converted_emails=c.converted_emails,
                        open_rate=c.opened_emails / c.total_emails * 100 if c.total_emails else 0,
                        reply_rate=c.replied_emails / c.total_emails * 100 if c.total_emails else 0,
                        conversion_rate=c.converted_emails / c.total_emails * 100 if c.total_emails else 0,
                        ab_test_results=None
                    )
                    return stats
            return None
        
        with patch('app.services.stats_service.get_campaign_stats', side_effect=mock_get_stats):
            # Act
            result = get_user_stats(mock_db, mock_user_id)
            
            # Assert
            assert len(result) == 3
            assert all(isinstance(stats, schemas.CampaignStats) for stats in result)
            # Check if stats for all campaigns are included
            campaign_ids = [c.id for c in campaigns]
            result_ids = [stats.campaign_id for stats in result]
            assert all(cid in result_ids for cid in campaign_ids)

    def test_get_user_stats_no_campaigns(self, mock_db, mock_user_id):
        """Test retrieving stats when user has no campaigns."""
        # Arrange
        mock_db.query().filter().all.return_value = []
        
        # Act
        result = get_user_stats(mock_db, mock_user_id)
        
        # Assert
        assert len(result) == 0

    def test_get_user_stats_with_errors(self, mock_db, mock_user_id, mock_campaign):
        """Test handling errors for individual campaigns during stats retrieval."""
        # Arrange
        # Create multiple campaigns for the user
        campaigns = [mock_campaign]
        for i in range(2):
            campaign = MagicMock(spec=models.EmailCampaign)
            campaign.id = uuid4()
            campaign.user_id = mock_user_id
            campaign.name = f"Test Campaign {i+2}"
            campaigns.append(campaign)
        
        mock_db.query().filter().all.return_value = campaigns
        
        # Mock get_campaign_stats to raise an error for one campaign
        def mock_get_stats(db, campaign_id, user_id):
            if campaign_id == campaigns[1].id:
                raise Exception("Error getting stats for this campaign")
            
            stats = schemas.CampaignStats(
                campaign_id=campaign_id,
                name="Test Campaign",
                total_emails=100,
                opened_emails=50,
                replied_emails=20,
                converted_emails=10,
                open_rate=50.0,
                reply_rate=20.0,
                conversion_rate=10.0,
                ab_test_results=None
            )
            return stats
        
        with patch('app.services.stats_service.get_campaign_stats', side_effect=mock_get_stats):
            # Act
            result = get_user_stats(mock_db, mock_user_id)
            
            # Assert
            # Should still return stats for campaigns that didn't error
            assert len(result) == 2
            # The campaign that errored should be excluded
            result_ids = [stats.campaign_id for stats in result]
            assert campaigns[1].id not in result_ids

    def test_get_user_stats_db_error(self, mock_db, mock_user_id):
        """Test database error handling during user stats retrieval."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            get_user_stats(mock_db, mock_user_id)
        
        assert "Database error" in str(exc_info.value)


class TestCalculateABTestResults:
    """Tests for calculate_ab_test_results function."""

    def test_calculate_ab_test_results_success(self, mock_db, mock_campaign_id, mock_emails):
        """Test successful A/B test results calculation."""
        # Arrange
        mock_db.query().filter().all.return_value = mock_emails
        
        # Act
        result = calculate_ab_test_results(mock_db, mock_campaign_id)
        
        # Assert
        assert "A" in result
        assert "B" in result
        assert "winner" in result
        
        # Check variant A stats
        assert result["A"]["sent"] == 30
        assert result["A"]["opened"] == 15
        assert result["A"]["replied"] == 9
        assert result["A"]["converted"] == 3
        assert result["A"]["open_rate"] == 50.0
        assert result["A"]["reply_rate"] == 30.0
        assert result["A"]["conversion_rate"] == 10.0
        
        # Check variant B stats (should be winning)
        assert result["B"]["sent"] == 30
        assert result["B"]["opened"] == 21
        assert result["B"]["replied"] == 12
        assert result["B"]["converted"] == 6
        assert result["B"]["open_rate"] == 70.0
        assert result["B"]["reply_rate"] == 40.0
        assert result["B"]["conversion_rate"] == 20.0
        
        # Check that B is the winner
        assert result["winner"] == "B"

    def test_calculate_ab_test_results_no_emails(self, mock_db, mock_campaign_id):
        """Test A/B test results calculation with no emails."""
        # Arrange
        mock_db.query().filter().all.return_value = []
        
        # Act
        result = calculate_ab_test_results(mock_db, mock_campaign_id)
        
        # Assert
        assert result == {"winner": None}

    def test_calculate_ab_test_results_single_variant(self, mock_db, mock_campaign_id):
        """Test A/B test results calculation with only one variant."""
        # Arrange
        emails = []
        # Create 20 "A" variant emails only
        for i in range(20):
            email = MagicMock(spec=models.Email)
            email.id = uuid4()
            email.ab_test_variant = "A"
            email.is_sent = True
            email.is_opened = i < 10
            email.is_replied = i < 6
            email.is_converted = i < 3
            emails.append(email)
            
        mock_db.query().filter().all.return_value = emails
        
        # Act
        result = calculate_ab_test_results(mock_db, mock_campaign_id)
        
        # Assert
        assert "A" in result
        assert result["A"]["sent"] == 20
        assert result["A"]["opened"] == 10
        assert result["A"]["replied"] == 6
        assert result["A"]["converted"] == 3
        assert result["A"]["open_rate"] == 50.0
        assert result["A"]["reply_rate"] == 30.0
        assert result["A"]["conversion_rate"] == 15.0
        
        # With only one variant, there is no winner
        assert result["winner"] == None

    def test_calculate_ab_test_results_equal_performance(self, mock_db, mock_campaign_id):
        """Test A/B test results calculation with variants performing equally."""
        # Arrange
        emails = []
        # Create 20 emails for each variant with identical stats
        for variant in ["A", "B"]:
            for i in range(20):
                email = MagicMock(spec=models.Email)
                email.id = uuid4()
                email.ab_test_variant = variant
                email.is_sent = True
                email.is_opened = i < 10  # 50% open rate
                email.is_replied = i < 6   # 30% reply rate
                email.is_converted = i < 2  # 10% conversion rate
                emails.append(email)
            
        mock_db.query().filter().all.return_value = emails
        
        # Act
        result = calculate_ab_test_results(mock_db, mock_campaign_id)
        
        # Assert
        # Both variants should have the same stats
        assert result["A"]["open_rate"] == result["B"]["open_rate"]
        assert result["A"]["reply_rate"] == result["B"]["reply_rate"]
        assert result["A"]["conversion_rate"] == result["B"]["conversion_rate"]
        
        # In case of a tie, there is no clear winner
        assert result["winner"] is None

    def test_calculate_ab_test_results_db_error(self, mock_db, mock_campaign_id):
        """Test database error handling during A/B test calculation."""
        # Arrange
        mock_db.query.side_effect = SQLAlchemyError("Database error")
        
        # Act & Assert
        with pytest.raises(DatabaseError) as exc_info:
            calculate_ab_test_results(mock_db, mock_campaign_id)
        
        assert "Database error" in str(exc_info.value) 