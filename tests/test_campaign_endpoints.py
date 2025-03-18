"""
Integration tests for campaign endpoints.

This module contains tests for the campaign API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid

from app import models, schemas


@pytest.fixture
def campaign_data():
    """Sample campaign data for testing."""
    return {
        "name": "API Test Campaign",
        "description": "Campaign for API testing",
        "target_audience": "Developers",
        "is_active": True
    }


@pytest.fixture
def campaign_update_data():
    """Sample campaign update data for testing."""
    return {
        "name": "Updated Campaign Name",
        "description": "Updated campaign description",
        "is_active": False
    }


@pytest.fixture
def ab_test_data():
    """Sample A/B testing data for testing."""
    return {
        "enabled": True,
        "variant_a_name": "Original",
        "variant_b_name": "Test Version",
        "variant_a_percentage": 60,
        "variant_b_percentage": 40,
        "test_metric": "open_rate"
    }


class TestCampaignEndpoints:
    """Tests for campaign endpoints."""

    def test_create_campaign(self, client: TestClient, db: Session, token_headers: dict, campaign_data: dict):
        """
        Test campaign creation endpoint.
        
        Arrange:
            - Prepare campaign data
            - Set up authentication headers
        
        Act:
            - Send POST request to /api/v1/campaigns/
        
        Assert:
            - Response status is 201 Created
            - Campaign details match input data
            - Campaign ID is present
        """
        # Act
        response = client.post(
            "/api/v1/campaigns/",
            json=campaign_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == campaign_data["name"]
        assert data["description"] == campaign_data["description"]
        assert data["target_audience"] == campaign_data["target_audience"]
        assert data["is_active"] == campaign_data["is_active"]
        assert "id" in data
        
        # Verify in database
        campaign_in_db = db.query(models.EmailCampaign).filter(
            models.EmailCampaign.id == data["id"]
        ).first()
        assert campaign_in_db is not None
        assert campaign_in_db.name == campaign_data["name"]

    def test_get_campaigns(self, client: TestClient, test_campaign: models.EmailCampaign, token_headers: dict):
        """
        Test retrieving all campaigns.
        
        Arrange:
            - Create a test campaign
            - Set up authentication headers
        
        Act:
            - Send GET request to /api/v1/campaigns/
        
        Assert:
            - Response status is 200 OK
            - Response contains list of campaigns
            - Test campaign is in the list
        """
        # Act
        response = client.get(
            "/api/v1/campaigns/",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Check that our test campaign is in the list
        campaign_ids = [campaign["id"] for campaign in data]
        assert str(test_campaign.id) in campaign_ids

    def test_get_campaign_by_id(self, client: TestClient, test_campaign: models.EmailCampaign, token_headers: dict):
        """
        Test retrieving a specific campaign by ID.
        
        Arrange:
            - Create a test campaign
            - Set up authentication headers
        
        Act:
            - Send GET request to /api/v1/campaigns/{id}
        
        Assert:
            - Response status is 200 OK
            - Campaign details match test campaign
        """
        # Act
        response = client.get(
            f"/api/v1/campaigns/{test_campaign.id}",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_campaign.id)
        assert data["name"] == test_campaign.name
        assert data["description"] == test_campaign.description

    def test_get_campaign_not_found(self, client: TestClient, token_headers: dict):
        """
        Test retrieving a non-existent campaign.
        
        Arrange:
            - Generate a random campaign ID
            - Set up authentication headers
        
        Act:
            - Send GET request to /api/v1/campaigns/{id}
        
        Assert:
            - Response status is 404 Not Found
            - Error message indicates campaign not found
        """
        # Arrange
        non_existent_id = str(uuid.uuid4())
        
        # Act
        response = client.get(
            f"/api/v1/campaigns/{non_existent_id}",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_update_campaign(self, client: TestClient, test_campaign: models.EmailCampaign, token_headers: dict, campaign_update_data: dict):
        """
        Test updating a campaign.
        
        Arrange:
            - Create a test campaign
            - Prepare update data
            - Set up authentication headers
        
        Act:
            - Send PUT request to /api/v1/campaigns/{id}
        
        Assert:
            - Response status is 200 OK
            - Campaign details match updated data
        """
        # Act
        response = client.put(
            f"/api/v1/campaigns/{test_campaign.id}",
            json=campaign_update_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_campaign.id)
        assert data["name"] == campaign_update_data["name"]
        assert data["description"] == campaign_update_data["description"]
        assert data["is_active"] == campaign_update_data["is_active"]

    def test_update_campaign_not_found(self, client: TestClient, token_headers: dict, campaign_update_data: dict):
        """
        Test updating a non-existent campaign.
        
        Arrange:
            - Generate a random campaign ID
            - Prepare update data
            - Set up authentication headers
        
        Act:
            - Send PUT request to /api/v1/campaigns/{id}
        
        Assert:
            - Response status is 404 Not Found
            - Error message indicates campaign not found
        """
        # Arrange
        non_existent_id = str(uuid.uuid4())
        
        # Act
        response = client.put(
            f"/api/v1/campaigns/{non_existent_id}",
            json=campaign_update_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_delete_campaign(self, client: TestClient, db: Session, test_campaign: models.EmailCampaign, token_headers: dict):
        """
        Test deleting a campaign.
        
        Arrange:
            - Create a test campaign
            - Set up authentication headers
        
        Act:
            - Send DELETE request to /api/v1/campaigns/{id}
        
        Assert:
            - Response status is 200 OK
            - Campaign is no longer in the database
        """
        # Act
        response = client.delete(
            f"/api/v1/campaigns/{test_campaign.id}",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["id"] == str(test_campaign.id)
        
        # Verify campaign was deleted from database
        deleted_campaign = db.query(models.EmailCampaign).filter(
            models.EmailCampaign.id == test_campaign.id
        ).first()
        assert deleted_campaign is None

    def test_delete_campaign_not_found(self, client: TestClient, token_headers: dict):
        """
        Test deleting a non-existent campaign.
        
        Arrange:
            - Generate a random campaign ID
            - Set up authentication headers
        
        Act:
            - Send DELETE request to /api/v1/campaigns/{id}
        
        Assert:
            - Response status is 404 Not Found
            - Error message indicates campaign not found
        """
        # Arrange
        non_existent_id = str(uuid.uuid4())
        
        # Act
        response = client.delete(
            f"/api/v1/campaigns/{non_existent_id}",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_active_campaigns(self, client: TestClient, db: Session, test_campaign: models.EmailCampaign, token_headers: dict):
        """
        Test retrieving only active campaigns.
        
        Arrange:
            - Create a test campaign (active)
            - Create a second inactive campaign
            - Set up authentication headers
        
        Act:
            - Send GET request to /api/v1/campaigns/active
        
        Assert:
            - Response status is 200 OK
            - Response contains only active campaigns
            - Inactive campaign is not in the list
        """
        # Arrange - create an inactive campaign
        user_id = test_campaign.user_id
        inactive_campaign = models.EmailCampaign(
            name="Inactive Campaign",
            description="This campaign is inactive",
            user_id=user_id,
            is_active=False
        )
        db.add(inactive_campaign)
        db.commit()
        db.refresh(inactive_campaign)
        
        # Ensure our test campaign is active
        test_campaign.is_active = True
        db.add(test_campaign)
        db.commit()
        
        # Act
        response = client.get(
            "/api/v1/campaigns/active",
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Check that only active campaigns are in the list
        campaign_ids = [campaign["id"] for campaign in data]
        assert str(test_campaign.id) in campaign_ids
        assert str(inactive_campaign.id) not in campaign_ids
        
        # Verify all returned campaigns are active
        for campaign in data:
            assert campaign["is_active"] is True

    def test_configure_ab_testing(self, client: TestClient, test_campaign: models.EmailCampaign, token_headers: dict, ab_test_data: dict):
        """
        Test configuring A/B testing for a campaign.
        
        Arrange:
            - Create a test campaign
            - Prepare A/B testing data
            - Set up authentication headers
        
        Act:
            - Send POST request to /api/v1/campaigns/{id}/ab-testing
        
        Assert:
            - Response status is 200 OK
            - A/B testing configuration matches input data
        """
        # Act
        response = client.post(
            f"/api/v1/campaigns/{test_campaign.id}/ab-testing",
            json=ab_test_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_campaign.id)
        assert data["ab_testing"] is not None
        assert data["ab_testing"]["enabled"] == ab_test_data["enabled"]
        assert data["ab_testing"]["variant_a_name"] == ab_test_data["variant_a_name"]
        assert data["ab_testing"]["variant_b_name"] == ab_test_data["variant_b_name"]
        assert data["ab_testing"]["variant_a_percentage"] == ab_test_data["variant_a_percentage"]
        assert data["ab_testing"]["variant_b_percentage"] == ab_test_data["variant_b_percentage"]
        assert data["ab_testing"]["test_metric"] == ab_test_data["test_metric"]

    def test_configure_ab_testing_invalid_data(self, client: TestClient, test_campaign: models.EmailCampaign, token_headers: dict):
        """
        Test configuring A/B testing with invalid data.
        
        Arrange:
            - Create a test campaign
            - Prepare invalid A/B testing data (percentages don't add up to 100)
            - Set up authentication headers
        
        Act:
            - Send POST request to /api/v1/campaigns/{id}/ab-testing
        
        Assert:
            - Response status is 422 Unprocessable Entity
            - Error details indicate validation error
        """
        # Arrange - invalid percentages that don't add up to 100
        invalid_ab_test_data = {
            "enabled": True,
            "variant_a_name": "Original",
            "variant_b_name": "Test Version",
            "variant_a_percentage": 70,
            "variant_b_percentage": 40,  # 70 + 40 != 100
            "test_metric": "open_rate"
        }
        
        # Act
        response = client.post(
            f"/api/v1/campaigns/{test_campaign.id}/ab-testing",
            json=invalid_ab_test_data,
            headers=token_headers
        )
        
        # Assert
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
        # Validate that the error is about percentages
        assert any("percentage" in str(error).lower() for error in data.get("errors", [{}])) 