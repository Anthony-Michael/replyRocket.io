import pytest
from unittest.mock import Mock, patch
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError

from app.utils.error_handling import (
    handle_db_error,
    handle_entity_not_found,
    handle_permission_error,
    create_error_response
)


@pytest.mark.utils
@pytest.mark.error_handling
@pytest.mark.unit
class TestErrorHandlingUtils:
    def test_handle_db_error_integrity_error_duplicate_email(self):
        """Test handling of IntegrityError with duplicate email."""
        # Arrange
        error = IntegrityError(
            "statement", 
            "params", 
            Exception("duplicate key value violates unique constraint on email")
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "create", "user")
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "email already exists" in exc_info.value.detail.lower()
    
    def test_handle_db_error_integrity_error_unique_constraint(self):
        """Test handling of IntegrityError with generic unique constraint violation."""
        # Arrange
        error = IntegrityError(
            "statement", 
            "params", 
            Exception("duplicate key value violates unique constraint")
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "create", "campaign")
        
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in exc_info.value.detail.lower()
    
    def test_handle_db_error_integrity_error_foreign_key(self):
        """Test handling of IntegrityError with foreign key constraint violation."""
        # Arrange
        error = IntegrityError(
            "statement", 
            "params", 
            Exception("violates foreign key constraint")
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "create", "email")
        
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "does not exist" in exc_info.value.detail.lower()
    
    def test_handle_db_error_operational_error(self):
        """Test handling of OperationalError."""
        # Arrange
        error = OperationalError(
            "statement", 
            "params", 
            Exception("database is locked")
        )
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "update", "campaign")
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "database error occurred" in exc_info.value.detail.lower()
    
    def test_handle_db_error_generic_error(self):
        """Test handling of generic SQLAlchemy error."""
        # Arrange
        error = SQLAlchemyError("Some generic error")
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "delete", "user")
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "database error occurred while delete user" in exc_info.value.detail.lower()
    
    def test_handle_db_error_custom_detail(self):
        """Test handling error with custom detail message."""
        # Arrange
        error = SQLAlchemyError("Some error")
        custom_detail = "Custom error message"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_db_error(error, "query", "email", detail=custom_detail)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert exc_info.value.detail == custom_detail
    
    def test_handle_entity_not_found(self):
        """Test handling of entity not found scenario."""
        # Arrange
        entity = "campaign"
        entity_id = 123
        user_info = "user@example.com"
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_entity_not_found(entity, entity_id, user_info)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"{entity.capitalize()} not found" in exc_info.value.detail
    
    def test_handle_entity_not_found_without_user_info(self):
        """Test handling of entity not found scenario without user info."""
        # Arrange
        entity = "email"
        entity_id = 456
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_entity_not_found(entity, entity_id)
        
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert f"{entity.capitalize()} not found" in exc_info.value.detail
    
    def test_handle_permission_error(self):
        """Test handling of permission error scenario."""
        # Arrange
        entity = "campaign"
        entity_id = 123
        user_id = 456
        
        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            handle_permission_error(entity, entity_id, user_id)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Not enough permissions" in exc_info.value.detail
    
    def test_create_error_response(self):
        """Test creating an error response."""
        # Arrange
        status_code = status.HTTP_400_BAD_REQUEST
        message = "Invalid input"
        details = {"field": "name", "error": "Cannot be empty"}
        
        # Act
        error_response = create_error_response(status_code, message, details)
        
        # Assert
        assert error_response["status_code"] == status_code
        assert error_response["message"] == message
        assert error_response["details"] == details
    
    def test_create_error_response_without_details(self):
        """Test creating an error response without details."""
        # Arrange
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Server error"
        
        # Act
        error_response = create_error_response(status_code, message)
        
        # Assert
        assert error_response["status_code"] == status_code
        assert error_response["message"] == message
        assert error_response["details"] is None 