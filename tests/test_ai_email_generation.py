"""
Tests for the AI email generation functionality.

This module contains unit and integration tests for the AI email generator,
focusing on error handling and edge cases.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.services.ai_email_generator import (
    generate_email,
    build_email_prompt,
    parse_email_response,
    generate_follow_up_email
)
from app.schemas.email import EmailGenResponse


@pytest.mark.unit
@pytest.mark.emails
class TestAIEmailGeneration:
    """Test suite for AI email generation functionality."""
    
    def test_build_email_prompt_required_fields(self):
        """Test that build_email_prompt constructs a valid prompt with required fields."""
        # Arrange
        recipient_name = "John Doe"
        industry = "Technology"
        pain_points = ["Inefficient processes", "High customer churn"]
        
        # Act
        prompt = build_email_prompt(
            recipient_name=recipient_name,
            industry=industry,
            pain_points=pain_points
        )
        
        # Assert
        assert recipient_name in prompt
        assert industry in prompt
        assert all(point in prompt for point in pain_points)
        assert "cold email" in prompt.lower()
    
    def test_build_email_prompt_all_fields(self):
        """Test that build_email_prompt includes all optional fields when provided."""
        # Arrange
        recipient_name = "Jane Smith"
        industry = "Healthcare"
        pain_points = ["Data security", "Compliance issues"]
        recipient_company = "HealthTech Inc."
        recipient_job_title = "Chief Information Officer"
        personalization_notes = "Recently spoke at cybersecurity conference"
        
        # Act
        prompt = build_email_prompt(
            recipient_name=recipient_name,
            industry=industry,
            pain_points=pain_points,
            recipient_company=recipient_company,
            recipient_job_title=recipient_job_title,
            personalization_notes=personalization_notes
        )
        
        # Assert
        assert recipient_name in prompt
        assert industry in prompt
        assert all(point in prompt for point in pain_points)
        assert recipient_company in prompt
        assert recipient_job_title in prompt
        assert personalization_notes in prompt
    
    @patch("app.services.ai_email_generator.client.chat.completions.create")
    def test_generate_email_success(self, mock_openai):
        """Test successful email generation with valid OpenAI response."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "subject": "Improving Data Security at HealthTech Inc.",
            "body_text": "Dear Jane, I noticed your company has been facing challenges...",
            "body_html": "<p>Dear Jane, I noticed your company has been facing challenges...</p>"
        })
        mock_openai.return_value = mock_response
        
        # Act
        result = generate_email(
            recipient_name="Jane Smith",
            industry="Healthcare",
            pain_points=["Data security"],
            recipient_company="HealthTech Inc."
        )
        
        # Assert
        assert isinstance(result, EmailGenResponse)
        assert "Improving Data Security" in result.subject
        assert "Dear Jane" in result.body_text
        assert "<p>" in result.body_html
        mock_openai.assert_called_once()
    
    @patch("app.services.ai_email_generator.client.chat.completions.create")
    def test_generate_email_api_error(self, mock_openai):
        """Test error handling when OpenAI API raises an exception."""
        # Arrange
        mock_openai.side_effect = Exception("API quota exceeded")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(
                recipient_name="John Doe",
                industry="Technology",
                pain_points=["Inefficient processes"]
            )
        
        assert "API quota exceeded" in str(exc_info.value)
    
    @patch("app.services.ai_email_generator.client.chat.completions.create")
    def test_generate_email_invalid_json(self, mock_openai):
        """Test error handling when OpenAI returns invalid JSON."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is not valid JSON"
        mock_openai.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(
                recipient_name="John Doe",
                industry="Technology",
                pain_points=["Inefficient processes"]
            )
        
        assert "JSON" in str(exc_info.value)
    
    @patch("app.services.ai_email_generator.client.chat.completions.create")
    def test_generate_email_missing_fields(self, mock_openai):
        """Test error handling when OpenAI response is missing required fields."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        # Missing subject field
        mock_response.choices[0].message.content = json.dumps({
            "body_text": "Dear Jane, I noticed your company has been facing challenges...",
            "body_html": "<p>Dear Jane, I noticed your company has been facing challenges...</p>"
        })
        mock_openai.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(
                recipient_name="Jane Smith",
                industry="Healthcare",
                pain_points=["Data security"]
            )
        
        assert "Missing required fields" in str(exc_info.value)
    
    @patch("app.services.ai_email_generator.client.chat.completions.create")
    def test_generate_email_empty_response(self, mock_openai):
        """Test error handling when OpenAI returns an empty response."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = []
        mock_openai.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(
                recipient_name="John Doe",
                industry="Technology",
                pain_points=["Inefficient processes"]
            )
        
        assert "Empty response" in str(exc_info.value)
    
    def test_parse_email_response_valid(self):
        """Test parsing a valid email response."""
        # Arrange
        valid_json = json.dumps({
            "subject": "Test Subject",
            "body_text": "Test Body Text",
            "body_html": "<p>Test Body HTML</p>"
        })
        
        # Act
        result = parse_email_response(valid_json)
        
        # Assert
        assert result.subject == "Test Subject"
        assert result.body_text == "Test Body Text"
        assert result.body_html == "<p>Test Body HTML</p>"
    
    def test_parse_email_response_invalid_json(self):
        """Test parsing an invalid JSON response."""
        # Arrange
        invalid_json = "This is not valid JSON"
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            parse_email_response(invalid_json)
        
        assert "JSON" in str(exc_info.value)
    
    def test_parse_email_response_missing_fields(self):
        """Test parsing a response with missing required fields."""
        # Arrange
        incomplete_json = json.dumps({
            "subject": "Test Subject",
            # Missing body_text and body_html
        })
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            parse_email_response(incomplete_json)
        
        assert "Missing required fields" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.emails
class TestAIEmailGenerationIntegration:
    """Integration tests for AI email generation."""
    
    @patch("app.services.ai_email_generator.client.chat.completions.create")
    def test_end_to_end_email_generation(self, mock_openai):
        """Test the full email generation process from input to output."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "subject": "Partnership Opportunity with Acme Corp",
            "body_text": "Dear John,\n\nI hope this email finds you well...",
            "body_html": "<p>Dear John,</p><p>I hope this email finds you well...</p>"
        })
        mock_openai.return_value = mock_response
        
        # Act
        result = generate_email(
            recipient_name="John Doe",
            industry="Technology",
            pain_points=["Inefficient processes", "High operational costs"],
            recipient_company="Acme Corp",
            recipient_job_title="CTO",
            personalization_notes="Recently expanded to European market"
        )
        
        # Assert
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Partnership Opportunity with Acme Corp"
        assert "Dear John" in result.body_text
        assert "<p>Dear John" in result.body_html
``` 