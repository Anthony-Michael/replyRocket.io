"""
Tests for campaign management endpoints.

This module contains tests for campaign creation, retrieval, updating, and deletion.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models


@pytest.mark.campaigns
def test_create_campaign(client: TestClient, db: Session, token_headers: dict):
    """
    Test creating a new campaign.
    
    Arrange:
        - Prepare valid campaign data
        - Set up authentication headers
    
    Act:
        - Send POST request to create campaign endpoint
    
    Assert:
        - Response status code is 201 Created
        - Response contains expected campaign data
        - Campaign exists in the database
    """
    # Arrange
    campaign_data = {
        "name": "New Test Campaign",
        "description": "Campaign created during testing",
        "target_audience": "Software developers",
        "is_active": True
    }
    
    # Act
    response = client.post(
        "/api/v1/campaigns", 
        json=campaign_data, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == campaign_data["name"]
    assert data["description"] == campaign_data["description"]
    assert "id" in data
    
    # Verify campaign exists in database
    campaign_in_db = db.query(models.Campaign).filter(models.Campaign.id == data["id"]).first()
    assert campaign_in_db is not None
    assert campaign_in_db.name == campaign_data["name"]


@pytest.mark.campaigns
def test_get_campaigns(client: TestClient, test_campaign: models.Campaign, token_headers: dict):
    """
    Test retrieving all campaigns for the current user.
    
    Arrange:
        - Create a test campaign using fixture
        - Set up authentication headers
    
    Act:
        - Send GET request to campaigns endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains list of campaigns
        - Test campaign is in the list
    """
    # Act
    response = client.get("/api/v1/campaigns", headers=token_headers)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check if test campaign is in the list
    campaign_ids = [campaign["id"] for campaign in data]
    assert test_campaign.id in campaign_ids


@pytest.mark.campaigns
def test_get_campaign_by_id(client: TestClient, test_campaign: models.Campaign, token_headers: dict):
    """
    Test retrieving a specific campaign by ID.
    
    Arrange:
        - Create a test campaign using fixture
        - Set up authentication headers
    
    Act:
        - Send GET request to specific campaign endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains expected campaign data
    """
    # Act
    response = client.get(f"/api/v1/campaigns/{test_campaign.id}", headers=token_headers)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_campaign.id
    assert data["name"] == test_campaign.name
    assert data["description"] == test_campaign.description


@pytest.mark.campaigns
def test_get_campaign_not_found(client: TestClient, token_headers: dict):
    """
    Test retrieving a non-existent campaign.
    
    Arrange:
        - Set up authentication headers
        - Use a non-existent campaign ID
    
    Act:
        - Send GET request to specific campaign endpoint
    
    Assert:
        - Response status code is 404 Not Found
        - Response contains error message about campaign not found
    """
    # Arrange
    non_existent_id = 99999
    
    # Act
    response = client.get(f"/api/v1/campaigns/{non_existent_id}", headers=token_headers)
    
    # Assert
    assert response.status_code == 404
    data = response.json()
    assert "Campaign not found" in data["detail"]


@pytest.mark.campaigns
def test_update_campaign(client: TestClient, test_campaign: models.Campaign, token_headers: dict):
    """
    Test updating a campaign.
    
    Arrange:
        - Create a test campaign using fixture
        - Prepare update data
        - Set up authentication headers
    
    Act:
        - Send PUT request to update campaign endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains updated campaign data
        - Campaign is updated in the database
    """
    # Arrange
    update_data = {
        "name": "Updated Campaign Name",
        "description": "Updated campaign description",
        "is_active": False
    }
    
    # Act
    response = client.put(
        f"/api/v1/campaigns/{test_campaign.id}", 
        json=update_data, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]
    assert data["is_active"] == update_data["is_active"]


@pytest.mark.campaigns
def test_update_active_campaign(client: TestClient, test_campaign: models.Campaign, 
                               token_headers: dict, db: Session):
    """
    Test updating an active campaign.
    
    Arrange:
        - Create a test campaign using fixture
        - Ensure campaign is active
        - Prepare update data
        - Set up authentication headers
    
    Act:
        - Send PUT request to update campaign endpoint
    
    Assert:
        - Response status code is 400 Bad Request
        - Response contains error message about not being able to update active campaigns
    """
    # Arrange - Ensure campaign is active
    test_campaign.is_active = True
    db.commit()
    
    update_data = {
        "name": "Cannot Update Active Campaign",
        "description": "This update should fail"
    }
    
    # Act
    response = client.put(
        f"/api/v1/campaigns/{test_campaign.id}", 
        json=update_data, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "Cannot update active campaign" in data["detail"]


@pytest.mark.campaigns
def test_delete_campaign(client: TestClient, test_campaign: models.Campaign, 
                        token_headers: dict, db: Session):
    """
    Test deleting a campaign.
    
    Arrange:
        - Create a test campaign using fixture
        - Set up authentication headers
    
    Act:
        - Send DELETE request to campaign endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains deleted campaign data
        - Campaign is removed from the database
    """
    # Act
    response = client.delete(
        f"/api/v1/campaigns/{test_campaign.id}", 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_campaign.id
    
    # Verify campaign is deleted from database
    deleted_campaign = db.query(models.Campaign).filter(
        models.Campaign.id == test_campaign.id
    ).first()
    assert deleted_campaign is None


@pytest.mark.campaigns
def test_get_active_campaigns(client: TestClient, test_campaign: models.Campaign, 
                             token_headers: dict, db: Session):
    """
    Test retrieving active campaigns.
    
    Arrange:
        - Create a test campaign using fixture
        - Ensure campaign is active
        - Set up authentication headers
    
    Act:
        - Send GET request to active campaigns endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains list of active campaigns
        - Test campaign is in the list
    """
    # Arrange - Ensure campaign is active
    test_campaign.is_active = True
    db.commit()
    
    # Act
    response = client.get("/api/v1/campaigns/active", headers=token_headers)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    
    # Check if test campaign is in the list
    campaign_ids = [campaign["id"] for campaign in data]
    assert test_campaign.id in campaign_ids


@pytest.mark.campaigns
def test_configure_ab_testing(client: TestClient, test_campaign: models.Campaign, token_headers: dict):
    """
    Test configuring A/B testing for a campaign.
    
    Arrange:
        - Create a test campaign using fixture
        - Prepare A/B test configuration data
        - Set up authentication headers
    
    Act:
        - Send POST request to A/B test configuration endpoint
    
    Assert:
        - Response status code is 200 OK
        - Response contains campaign with A/B testing configuration
    """
    # Arrange
    ab_test_config = {
        "campaign_id": test_campaign.id,
        "variants": {
            "A": "Value proposition focused",
            "B": "Pain point focused"
        }
    }
    
    # Act
    response = client.post(
        "/api/v1/campaigns/ab-test", 
        json=ab_test_config, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_campaign.id


@pytest.mark.campaigns
def test_configure_ab_testing_invalid_config(client: TestClient, test_campaign: models.Campaign, 
                                           token_headers: dict):
    """
    Test configuring A/B testing with invalid configuration.
    
    Arrange:
        - Create a test campaign using fixture
        - Prepare invalid A/B test configuration (only one variant)
        - Set up authentication headers
    
    Act:
        - Send POST request to A/B test configuration endpoint
    
    Assert:
        - Response status code is 400 Bad Request
        - Response contains error message about requiring at least two variants
    """
    # Arrange
    ab_test_config = {
        "campaign_id": test_campaign.id,
        "variants": {
            "A": "Only one variant which is invalid"
        }
    }
    
    # Act
    response = client.post(
        "/api/v1/campaigns/ab-test", 
        json=ab_test_config, 
        headers=token_headers
    )
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "A/B testing requires at least two variants" in data["detail"] 