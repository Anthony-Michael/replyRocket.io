import json
import pytest
from fastapi import status
from unittest.mock import Mock, patch, MagicMock

from app.models.email_campaign import EmailCampaign


# Test API endpoint that uses validate_campaign_access
@pytest.mark.api
@pytest.mark.campaigns
@pytest.mark.validation
@pytest.mark.integration
def test_read_campaign_success(client, mocker, mock_current_user):
    """Test successful access to a campaign belonging to the user."""
    # Arrange
    campaign_id = 123
    mock_campaign = MagicMock(spec=EmailCampaign)
    mock_campaign.id = campaign_id
    mock_campaign.user_id = mock_current_user.id
    mock_campaign.name = "Test Campaign"
    mock_campaign.is_active = True
    mock_campaign.industry = "Technology"
    
    # Convert campaign to dict for response
    campaign_dict = {
        "id": str(campaign_id),
        "user_id": str(mock_current_user.id),
        "name": "Test Campaign",
        "is_active": True,
        "industry": "Technology",
        "description": "Test description",
        "total_emails": 0,
        "opened_emails": 0,
        "replied_emails": 0,
        "converted_emails": 0
    }
    
    # Mock the validate_campaign_access function
    mocker.patch('app.api.api_v1.endpoints.campaigns.validate_campaign_access',
                return_value=mock_campaign)
    
    # Mock campaign schema to dict conversion
    mocker.patch.object(mock_campaign, '__dict__', return_value=campaign_dict)
    
    # Act
    response = client.get(f"/api/v1/campaigns/{campaign_id}")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["id"] == str(campaign_id)
    assert response.json()["name"] == "Test Campaign"


@pytest.mark.api
@pytest.mark.campaigns
@pytest.mark.validation
@pytest.mark.integration
def test_read_campaign_not_found(client, mocker, mock_current_user):
    """Test 404 response when campaign doesn't exist."""
    # Arrange
    campaign_id = 123
    
    # Mock the validate_campaign_access function to raise 404
    from fastapi import HTTPException
    mocker.patch('app.api.api_v1.endpoints.campaigns.validate_campaign_access',
                side_effect=HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaign not found"
                ))
    
    # Act
    response = client.get(f"/api/v1/campaigns/{campaign_id}")
    
    # Assert
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.api
@pytest.mark.campaigns
@pytest.mark.validation
@pytest.mark.integration
def test_read_campaign_forbidden(client, mocker, mock_current_user):
    """Test 403 response when user doesn't have permission to access the campaign."""
    # Arrange
    campaign_id = 123
    
    # Mock the validate_campaign_access function to raise 403
    from fastapi import HTTPException
    mocker.patch('app.api.api_v1.endpoints.campaigns.validate_campaign_access',
                side_effect=HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not enough permissions"
                ))
    
    # Act
    response = client.get(f"/api/v1/campaigns/{campaign_id}")
    
    # Assert
    assert response.status_code == 403
    assert "permissions" in response.json()["detail"].lower()


@pytest.mark.api
@pytest.mark.campaigns
@pytest.mark.validation
@pytest.mark.integration
def test_update_campaign_success(client, mocker, mock_current_user):
    """Test successful update of a campaign belonging to the user."""
    # Arrange
    campaign_id = 123
    mock_campaign = MagicMock(spec=EmailCampaign)
    mock_campaign.id = campaign_id
    mock_campaign.user_id = mock_current_user.id
    mock_campaign.name = "Old Name"
    mock_campaign.is_active = False
    
    # Updated campaign
    updated_campaign = MagicMock(spec=EmailCampaign)
    updated_campaign.id = campaign_id
    updated_campaign.user_id = mock_current_user.id
    updated_campaign.name = "New Name"
    updated_campaign.is_active = False
    
    # Convert campaign to dict for response
    campaign_dict = {
        "id": str(campaign_id),
        "user_id": str(mock_current_user.id),
        "name": "New Name",
        "is_active": False,
        "description": "Updated description",
        "industry": "Technology",
        "total_emails": 0,
        "opened_emails": 0,
        "replied_emails": 0,
        "converted_emails": 0
    }
    
    # Mock the validate_campaign_access function
    mocker.patch('app.api.api_v1.endpoints.campaigns.validate_campaign_access',
                return_value=mock_campaign)
    
    # Mock the update_user_campaign function
    mocker.patch('app.api.api_v1.endpoints.campaigns.update_user_campaign',
                return_value=updated_campaign)
    
    # Mock campaign schema to dict conversion
    mocker.patch.object(updated_campaign, '__dict__', return_value=campaign_dict)
    
    # Update data
    update_data = {
        "name": "New Name",
        "description": "Updated description",
        "industry": "Technology"
    }
    
    # Act
    response = client.put(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    
    # Assert
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["description"] == "Updated description"


@pytest.mark.api
@pytest.mark.campaigns
@pytest.mark.validation
@pytest.mark.integration
def test_update_active_campaign_fails(client, mocker, mock_current_user):
    """Test that updating an active campaign fails with 400 error."""
    # Arrange
    campaign_id = 123
    
    # Mock the validate_campaign_access function to raise 400
    from fastapi import HTTPException
    mocker.patch('app.api.api_v1.endpoints.campaigns.validate_campaign_access',
                side_effect=HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot update active campaign. Please deactivate it first."
                ))
    
    # Update data
    update_data = {
        "name": "New Name",
        "description": "Updated description"
    }
    
    # Act
    response = client.put(f"/api/v1/campaigns/{campaign_id}", json=update_data)
    
    # Assert
    assert response.status_code == 400
    assert "active campaign" in response.json()["detail"].lower()


@pytest.mark.api
@pytest.mark.campaigns
@pytest.mark.validation
@pytest.mark.integration
def test_delete_campaign_success(client, mocker, mock_current_user):
    """Test successful deletion of a campaign belonging to the user."""
    # Arrange
    campaign_id = 123
    mock_campaign = MagicMock(spec=EmailCampaign)
    mock_campaign.id = campaign_id
    mock_campaign.user_id = mock_current_user.id
    mock_campaign.name = "Test Campaign"
    
    # Convert campaign to dict for response
    campaign_dict = {
        "id": str(campaign_id),
        "user_id": str(mock_current_user.id),
        "name": "Test Campaign",
        "is_active": True,
        "description": "Test description",
        "industry": "Technology",
        "total_emails": 0,
        "opened_emails": 0,
        "replied_emails": 0,
        "converted_emails": 0
    }
    
    # Mock the validate_campaign_access function
    mocker.patch('app.api.api_v1.endpoints.campaigns.validate_campaign_access',
                return_value=mock_campaign)
    
    # Mock the delete_user_campaign function
    mocker.patch('app.api.api_v1.endpoints.campaigns.delete_user_campaign',
                return_value=mock_campaign)
    
    # Mock campaign schema to dict conversion
    mocker.patch.object(mock_campaign, '__dict__', return_value=campaign_dict)
    
    # Act
    response = client.delete(f"/api/v1/campaigns/{campaign_id}")
    
    # Assert
    assert response.status_code == 200
    assert response.json()["id"] == str(campaign_id)
    assert response.json()["name"] == "Test Campaign" 