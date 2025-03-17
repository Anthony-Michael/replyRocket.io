import json
import uuid
import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.utils.validation import validate_campaign_access
from app.utils.error_handling import handle_db_error
from app.services.ai_email_generator import generate_email, call_openai_api, parse_email_response


# ==================== Tests for validate_campaign_access ====================
@pytest.mark.utils
@pytest.mark.validation
@pytest.mark.unit
class TestValidateCampaignAccess:
    def test_campaign_exists_and_belongs_to_user(self, mocker):
        """Test that validate_campaign_access returns campaign when it exists and belongs to user."""
        # Arrange
        mock_campaign = MagicMock()
        mock_campaign.user_id = 1
        mock_campaign.is_active = False
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_campaign
        
        # Act
        result = validate_campaign_access(mock_db, 123, 1)
        
        # Assert
        assert result == mock_campaign
        mock_db.query.assert_called_once()
        mock_query.filter.assert_called_once()
        mock_filter.first.assert_called_once()
    
    def test_campaign_not_found(self, mocker):
        """Test that validate_campaign_access raises 404 when campaign is not found."""
        # Arrange
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_campaign_access(mock_db, 123, 1)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail
    
    def test_campaign_belongs_to_different_user(self, mocker):
        """Test that validate_campaign_access raises 403 when campaign belongs to different user."""
        # Arrange
        mock_campaign = MagicMock()
        mock_campaign.user_id = 2  # Different user id
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_campaign
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_campaign_access(mock_db, 123, 1)
        
        assert exc_info.value.status_code == 403
        assert "permission" in exc_info.value.detail.lower()
    
    def test_active_campaign_not_updated(self, mocker):
        """Test that validate_campaign_access raises 400 when trying to update active campaign."""
        # Arrange
        mock_campaign = MagicMock()
        mock_campaign.user_id = 1
        mock_campaign.is_active = True
        
        mock_db = MagicMock()
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_campaign
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_campaign_access(mock_db, 123, 1, for_update=True)
        
        assert exc_info.value.status_code == 400
        assert "active campaign" in exc_info.value.detail.lower()


# ==================== Tests for handle_db_error ====================
@pytest.mark.utils
@pytest.mark.error_handling
@pytest.mark.unit
class TestHandleDBError:
    def test_integrity_error_duplicate_email(self):
        """Test handling of IntegrityError with duplicate email."""
        # Arrange
        error = IntegrityError("statement", "params", 
                              Exception("duplicate key value violates unique constraint on email"))
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "create", "user")
        
        assert exc_info.value.status_code == 409
        assert "email already exists" in exc_info.value.detail.lower()
    
    def test_integrity_error_unique_constraint(self):
        """Test handling of IntegrityError with generic unique constraint violation."""
        # Arrange
        error = IntegrityError("statement", "params", 
                              Exception("duplicate key value violates unique constraint"))
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "create", "campaign")
        
        assert exc_info.value.status_code == 409
        assert "already exists" in exc_info.value.detail.lower()
    
    def test_integrity_error_foreign_key(self):
        """Test handling of IntegrityError with foreign key constraint violation."""
        # Arrange
        error = IntegrityError("statement", "params", 
                              Exception("violates foreign key constraint"))
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "create", "email")
        
        assert exc_info.value.status_code == 400
        assert "does not exist" in exc_info.value.detail.lower()
    
    def test_generic_db_error(self):
        """Test handling of generic SQLAlchemy error."""
        # Arrange
        error = SQLAlchemyError("Database connection lost")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "update", "campaign")
        
        assert exc_info.value.status_code == 500
        assert "database error occurred while update campaign" in exc_info.value.detail.lower()
    
    def test_custom_error_message(self):
        """Test handling error with custom error message."""
        # Arrange
        error = SQLAlchemyError("Some error")
        custom_msg = "Custom error message"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "delete", "user", detail=custom_msg)
        
        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == custom_msg


# ==================== Tests for generate_email ====================
@pytest.mark.utils
@pytest.mark.emails
@pytest.mark.unit
class TestGenerateEmail:
    def test_successful_email_generation(self, mocker):
        """Test successful email generation with all required parameters."""
        # Arrange
        expected_response = {
            "subject": "Test Subject",
            "body_text": "Test body text",
            "body_html": "<p>Test body HTML</p>"
        }
        
        # Mock the OpenAI API call
        mock_api_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = json.dumps(expected_response)
        mock_api_response.choices = [mock_choice]
        
        mocker.patch('app.services.ai_email_generator.call_openai_api', 
                    return_value=mock_api_response)
        
        # Act
        result = generate_email(
            recipient_name="John Doe",
            industry="Technology",
            pain_points=["Problem 1", "Problem 2"],
            recipient_company="Acme Inc",
            recipient_job_title="CTO",
            personalization_notes="Met at conference"
        )
        
        # Assert
        assert result.subject == expected_response["subject"]
        assert result.body_text == expected_response["body_text"]
        assert result.body_html == expected_response["body_html"]
    
    def test_minimal_parameters(self, mocker):
        """Test email generation with only required parameters."""
        # Arrange
        expected_response = {
            "subject": "Test Subject",
            "body_text": "Test body text",
            "body_html": "<p>Test body HTML</p>"
        }
        
        # Mock the OpenAI API call
        mock_api_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = json.dumps(expected_response)
        mock_api_response.choices = [mock_choice]
        
        mocker.patch('app.services.ai_email_generator.call_openai_api', 
                    return_value=mock_api_response)
        
        # Act
        result = generate_email(
            recipient_name="John Doe",
            industry="Technology",
            pain_points=["Problem 1"]
        )
        
        # Assert
        assert result.subject == expected_response["subject"]
        assert result.body_text == expected_response["body_text"]
        assert result.body_html == expected_response["body_html"]
    
    def test_api_call_failure(self, mocker):
        """Test that generate_email properly handles API call failure."""
        # Arrange
        api_error = Exception("API connection error")
        mocker.patch('app.services.ai_email_generator.call_openai_api', 
                    side_effect=api_error)
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(
                recipient_name="John Doe",
                industry="Technology",
                pain_points=["Problem 1"]
            )
        
        assert "Failed to generate content" in str(exc_info.value)
    
    def test_response_parsing_failure(self, mocker):
        """Test that generate_email properly handles response parsing failure."""
        # Arrange
        # Mock the OpenAI API call to return invalid JSON
        mock_api_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = "Invalid JSON"
        mock_api_response.choices = [mock_choice]
        
        mocker.patch('app.services.ai_email_generator.call_openai_api', 
                    return_value=mock_api_response)
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(
                recipient_name="John Doe",
                industry="Technology",
                pain_points=["Problem 1"]
            )
        
        assert "Failed to parse AI response" in str(exc_info.value)
    
    def test_missing_fields_in_response(self, mocker):
        """Test that generate_email properly handles response with missing fields."""
        # Arrange
        incomplete_response = {
            "subject": "Test Subject",
            # Missing body_text and body_html
        }
        
        # Mock the OpenAI API call
        mock_api_response = Mock()
        mock_choice = Mock()
        mock_choice.message.content = json.dumps(incomplete_response)
        mock_api_response.choices = [mock_choice]
        
        mocker.patch('app.services.ai_email_generator.call_openai_api', 
                    return_value=mock_api_response)
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(
                recipient_name="John Doe",
                industry="Technology",
                pain_points=["Problem 1"]
            )
        
        assert "Failed to parse AI response" in str(exc_info.value)


# Test API endpoint using TestClient
@pytest.mark.api
@pytest.mark.emails
@pytest.mark.integration
def test_generate_email_endpoint_success(client, mocker, mock_current_user):
    """Test the generate email endpoint with successful email generation."""
    # Arrange
    expected_response = {
        "subject": "Test Subject",
        "body_text": "Test body text",
        "body_html": "<p>Test body HTML</p>"
    }
    
    # Mock the generate_email function
    mocker.patch('app.api.api_v1.endpoints.emails.generate_and_validate_email_content',
                return_value=expected_response)
    
    # Create test request data
    request_data = {
        "recipient_name": "John Doe",
        "recipient_company": "Acme Inc",
        "recipient_job_title": "CTO",
        "industry": "Technology",
        "pain_points": ["Problem 1", "Problem 2"],
        "personalization_notes": "Met at conference"
    }
    
    # Act
    response = client.post("/api/v1/emails/generate", json=request_data)
    
    # Assert
    assert response.status_code == 201
    assert response.json() == expected_response


@pytest.mark.api
@pytest.mark.emails
@pytest.mark.integration
def test_generate_email_endpoint_failure(client, mocker, mock_current_user):
    """Test the generate email endpoint with failed email generation."""
    # Arrange
    # Mock the generate_email function to raise an exception
    mocker.patch('app.api.api_v1.endpoints.emails.generate_and_validate_email_content',
                side_effect=HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate email"
                ))
    
    # Create test request data
    request_data = {
        "recipient_name": "John Doe",
        "industry": "Technology",
        "pain_points": ["Problem 1"]
    }
    
    # Act
    response = client.post("/api/v1/emails/generate", json=request_data)
    
    # Assert
    assert response.status_code == 500
    assert "Failed to generate email" in response.json()["detail"] 