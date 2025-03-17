"""
Tests for campaign-related endpoints.

This module contains tests for campaign creation, retrieval, and updates.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4

from app import crud, models


class TestCampaigns:
    """Tests for campaign-related endpoints."""
    
    def test_create_campaign(self, client: TestClient, auth_headers, db: Session):
        """
        Test campaign creation.
        
        ARRANGE:
            - Prepare test data for campaign creation
        
        ACT:
            - Send a POST request to create a campaign
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify response contains expected campaign data
            - Verify campaign exists in database
        """
        # Arrange - Prepare test data
        campaign_data = {
            "name": "Test Marketing Campaign",
            "description": "A campaign for testing the API",
            "industry": "Technology",
            "target_job_title": "CTO",
            "pain_points": "Time management, resource allocation",
            "follow_up_days": 3,
            "max_follow_ups": 2,
            "ab_test_active": False
        }
        
        # Act - Send campaign creation request
        response = client.post(
            "/api/v1/campaigns",
            json=campaign_data,
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 200, f"Failed to create campaign: {response.text}"
        
        data = response.json()
        assert data["name"] == campaign_data["name"]
        assert data["description"] == campaign_data["description"]
        assert data["industry"] == campaign_data["industry"]
        assert "id" in data
        assert "user_id" in data
        assert "created_at" in data
        
        # Verify campaign exists in database
        campaign_id = data["id"]
        campaign = crud.campaign.get(db, id=campaign_id)
        assert campaign is not None
        assert campaign.name == campaign_data["name"]
        assert campaign.is_active is True  # Default value
    
    def test_create_campaign_validation_error(self, client: TestClient, auth_headers):
        """
        Test campaign creation with validation error.
        
        ARRANGE:
            - Prepare invalid test data (missing required fields)
        
        ACT:
            - Send a POST request to create a campaign
        
        ASSERT:
            - Verify response status code is 422 (Unprocessable Entity)
            - Verify response contains validation error details
        """
        # Arrange - Prepare invalid test data
        invalid_campaign_data = {
            # Missing required "name" field
            "description": "A campaign for testing validation",
            "industry": "Technology"
            # Missing other required fields
        }
        
        # Act - Send campaign creation request
        response = client.post(
            "/api/v1/campaigns",
            json=invalid_campaign_data,
            headers=auth_headers
        )
        
        # Assert - Check for validation error
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_get_campaigns(self, client: TestClient, auth_headers, create_test_campaign):
        """
        Test retrieving all campaigns.
        
        ARRANGE:
            - Use fixture to create a test campaign
        
        ACT:
            - Send a GET request to retrieve all campaigns
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify response contains the test campaign
            - Verify campaign data matches expected values
        """
        # Act - Send get campaigns request
        response = client.get(
            "/api/v1/campaigns",
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 200
        
        campaigns = response.json()
        assert len(campaigns) >= 1  # Should have at least our test campaign
        
        # Find the test campaign in the list
        test_campaign = next(
            (c for c in campaigns if c["id"] == str(create_test_campaign.id)), 
            None
        )
        assert test_campaign is not None
        assert test_campaign["name"] == create_test_campaign.name
        assert test_campaign["industry"] == create_test_campaign.industry
    
    def test_get_active_campaigns(self, client: TestClient, auth_headers, db: Session, create_test_campaign):
        """
        Test retrieving active campaigns.
        
        ARRANGE:
            - Use fixture to create a test campaign
            - Create an inactive campaign
        
        ACT:
            - Send a GET request to retrieve active campaigns
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify response contains only active campaigns
            - Verify inactive campaign is not included
        """
        # Arrange - Create an inactive campaign
        inactive_campaign_data = {
            "name": "Inactive Campaign",
            "description": "This campaign is inactive",
            "industry": "Healthcare",
            "target_job_title": "Doctor",
            "pain_points": "Patient management",
            "is_active": False  # Explicitly inactive
        }
        
        user_id = create_test_campaign.user_id  # Get user ID from existing campaign
        inactive_campaign = crud.campaign.create_with_user(
            db=db,
            obj_in=inactive_campaign_data,
            user_id=user_id
        )
        
        # Act - Send get active campaigns request
        response = client.get(
            "/api/v1/campaigns/active",
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 200
        
        campaigns = response.json()
        assert len(campaigns) >= 1  # Should have at least our active test campaign
        
        # Verify test campaign is included
        campaign_ids = [c["id"] for c in campaigns]
        assert str(create_test_campaign.id) in campaign_ids
        
        # Verify inactive campaign is not included
        assert str(inactive_campaign.id) not in campaign_ids
    
    def test_get_campaign_by_id(self, client: TestClient, auth_headers, create_test_campaign):
        """
        Test retrieving a campaign by ID.
        
        ARRANGE:
            - Use fixture to create a test campaign
        
        ACT:
            - Send a GET request to retrieve the campaign by ID
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify response contains the expected campaign data
        """
        # Act - Send get campaign request
        response = client.get(
            f"/api/v1/campaigns/{create_test_campaign.id}",
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 200
        
        campaign = response.json()
        assert campaign["id"] == str(create_test_campaign.id)
        assert campaign["name"] == create_test_campaign.name
        assert campaign["industry"] == create_test_campaign.industry
        assert campaign["description"] == create_test_campaign.description
    
    def test_get_campaign_not_found(self, client: TestClient, auth_headers):
        """
        Test retrieving a non-existent campaign.
        
        ARRANGE:
            - Generate a random non-existent campaign ID
        
        ACT:
            - Send a GET request to retrieve a non-existent campaign
        
        ASSERT:
            - Verify response status code is 404 (Not Found)
            - Verify response contains not found message
        """
        # Arrange - Generate random UUID for non-existent campaign
        non_existent_id = str(uuid4())
        
        # Act - Send get campaign request with non-existent ID
        response = client.get(
            f"/api/v1/campaigns/{non_existent_id}",
            headers=auth_headers
        )
        
        # Assert - Check for not found response
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_update_campaign(self, client: TestClient, auth_headers, create_test_campaign):
        """
        Test updating a campaign.
        
        ARRANGE:
            - Use fixture to create a test campaign
            - Prepare update data
        
        ACT:
            - Send a PUT request to update the campaign
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify response contains updated campaign data
            - Verify fields are updated as expected
        """
        # Arrange - Prepare update data
        update_data = {
            "name": "Updated Campaign Name",
            "description": "This description has been updated",
            "industry": "Finance",  # Changed from Technology
            "is_active": True  # Ensure it's active
        }
        
        # Act - Send update request
        response = client.put(
            f"/api/v1/campaigns/{create_test_campaign.id}",
            json=update_data,
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 200
        
        updated_campaign = response.json()
        assert updated_campaign["id"] == str(create_test_campaign.id)
        assert updated_campaign["name"] == update_data["name"]
        assert updated_campaign["description"] == update_data["description"]
        assert updated_campaign["industry"] == update_data["industry"]
        assert updated_campaign["is_active"] == update_data["is_active"]
        
        # Fields not in update_data should remain unchanged
        assert updated_campaign["target_job_title"] == create_test_campaign.target_job_title
    
    def test_delete_campaign(self, client: TestClient, auth_headers, db: Session, create_test_user):
        """
        Test deleting a campaign.
        
        ARRANGE:
            - Create a test campaign specifically for deletion
        
        ACT:
            - Send a DELETE request to delete the campaign
        
        ASSERT:
            - Verify response status code is 200 (OK)
            - Verify campaign no longer exists in database
        """
        # Arrange - Create a campaign to delete
        campaign_data = {
            "name": "Campaign to Delete",
            "description": "This campaign will be deleted",
            "industry": "Retail",
            "target_job_title": "Sales Manager",
            "pain_points": "Inventory management",
            "follow_up_days": 5,
            "max_follow_ups": 3
        }
        
        campaign = crud.campaign.create_with_user(
            db=db,
            obj_in=campaign_data,
            user_id=create_test_user["user"].id
        )
        
        # Act - Send delete request
        response = client.delete(
            f"/api/v1/campaigns/{campaign.id}",
            headers=auth_headers
        )
        
        # Assert - Check the response
        assert response.status_code == 200
        
        # Verify campaign is deleted from DB
        deleted_campaign = crud.campaign.get(db, id=campaign.id)
        assert deleted_campaign is None 