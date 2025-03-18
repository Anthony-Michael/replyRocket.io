"""
Unit tests for the AI email generator service.

This module contains tests for ai_email_generator_service.py,
mocking the OpenAI API calls to test email generation logic.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
import os

from app.services.ai_email_generator_service import (
    generate_email,
    generate_follow_up,
    generate_ab_test_variants,
    build_email_prompt,
    parse_ai_response,
    format_email_html
)
from app.schemas.email import EmailGenResponse


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    with patch('app.services.ai_email_generator_service.client') as mock_client:
        yield mock_client


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "subject": "Test Email Subject",
        "body_text": "This is a test email body in plain text.",
        "body_html": "<p>This is a test email body in HTML.</p>"
    })
    return mock_response


@pytest.fixture
def email_generation_params():
    """Create parameters for email generation."""
    return {
        "recipient_name": "John Doe",
        "industry": "Technology",
        "pain_points": ["Time management", "Team collaboration"],
        "recipient_company": "Acme Inc",
        "recipient_job_title": "CTO",
        "personalization_notes": "Met at TechConf 2023"
    }


@pytest.fixture
def follow_up_params():
    """Create parameters for follow-up email generation."""
    return {
        "original_subject": "Original Subject",
        "original_body": "This is the original email body.",
        "recipient_name": "John Doe",
        "follow_up_number": 1,
        "recipient_company": "Acme Inc",
        "recipient_job_title": "CTO",
        "new_approach": "Focus on cost savings"
    }


@pytest.fixture
def ab_test_params():
    """Create parameters for A/B test variant generation."""
    return {
        "recipient_name": "John Doe",
        "industry": "Technology",
        "pain_points": ["Time management", "Team collaboration"],
        "variants": {
            "A": "Value proposition focused",
            "B": "Problem-solution focused"
        },
        "recipient_company": "Acme Inc",
        "recipient_job_title": "CTO"
    }


class TestGenerateEmail:
    """Tests for generate_email function."""

    def test_generate_email_success(self, mock_openai_client, mock_openai_response, email_generation_params):
        """Test successful email generation."""
        # Arrange
        mock_openai_client.chat.completions.create.return_value = mock_openai_response
        
        # Act
        result = generate_email(**email_generation_params)
        
        # Assert
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Test Email Subject"
        assert result.body_text == "This is a test email body in plain text."
        assert result.body_html == "<p>This is a test email body in HTML.</p>"
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_generate_email_minimal_params(self, mock_openai_client, mock_openai_response):
        """Test email generation with minimal required parameters."""
        # Arrange
        mock_openai_client.chat.completions.create.return_value = mock_openai_response
        
        # Act
        result = generate_email(
            recipient_name="John Doe",
            industry="Technology",
            pain_points=["Time management"]
        )
        
        # Assert
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Test Email Subject"
        mock_openai_client.chat.completions.create.assert_called_once()

    @patch('app.services.ai_email_generator_service.logger')
    def test_generate_email_openai_error(self, mock_logger, mock_openai_client, email_generation_params):
        """Test error handling when OpenAI API call fails."""
        # Arrange
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(**email_generation_params)
        
        assert "API Error" in str(exc_info.value)
        mock_logger.error.assert_called_once()

    @patch('app.services.ai_email_generator_service.logger')
    def test_generate_email_parse_error(self, mock_logger, mock_openai_client, email_generation_params):
        """Test error handling when parsing API response fails."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Invalid JSON"
        mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_email(**email_generation_params)
        
        assert "Failed to parse AI response" in str(exc_info.value)
        mock_logger.error.assert_called_once()


class TestBuildEmailPrompt:
    """Tests for build_email_prompt function."""

    def test_build_email_prompt_all_fields(self, email_generation_params):
        """Test building an email prompt with all optional fields."""
        # Act
        prompt = build_email_prompt(**email_generation_params)
        
        # Assert
        assert "John Doe" in prompt
        assert "Technology" in prompt
        assert "Time management" in prompt
        assert "Team collaboration" in prompt
        assert "Acme Inc" in prompt
        assert "CTO" in prompt
        assert "Met at TechConf 2023" in prompt

    def test_build_email_prompt_minimal_fields(self):
        """Test building an email prompt with only required fields."""
        # Act
        prompt = build_email_prompt(
            recipient_name="John Doe",
            industry="Technology",
            pain_points=["Time management"]
        )
        
        # Assert
        assert "John Doe" in prompt
        assert "Technology" in prompt
        assert "Time management" in prompt
        assert "recipient_company: None" not in prompt  # Should handle None values gracefully


class TestParseAIResponse:
    """Tests for parse_ai_response function."""

    def test_parse_ai_response_valid_json(self, mock_openai_response):
        """Test parsing a valid JSON response."""
        # Act
        result = parse_ai_response(mock_openai_response.choices[0].message.content)
        
        # Assert
        assert isinstance(result, dict)
        assert result["subject"] == "Test Email Subject"
        assert result["body_text"] == "This is a test email body in plain text."
        assert result["body_html"] == "<p>This is a test email body in HTML.</p>"

    def test_parse_ai_response_invalid_json(self):
        """Test parsing an invalid JSON response."""
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            parse_ai_response("Invalid JSON")
        
        assert "Failed to parse AI response" in str(exc_info.value)

    def test_parse_ai_response_missing_fields(self):
        """Test parsing a JSON response with missing required fields."""
        # Arrange
        invalid_json = json.dumps({"subject": "Test Subject"})  # Missing body fields
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            parse_ai_response(invalid_json)
        
        assert "Invalid AI response format" in str(exc_info.value)


class TestFormatEmailHtml:
    """Tests for format_email_html function."""

    def test_format_email_html_plain_text(self):
        """Test converting plain text to HTML."""
        # Arrange
        plain_text = "Line 1\nLine 2\n\nParagraph 2"
        
        # Act
        result = format_email_html(plain_text)
        
        # Assert
        assert "<p>Line 1<br>Line 2</p>" in result
        assert "<p>Paragraph 2</p>" in result

    def test_format_email_html_already_html(self):
        """Test handling text that is already HTML."""
        # Arrange
        html = "<p>This is already HTML</p>"
        
        # Act
        result = format_email_html(html)
        
        # Assert
        assert result == html  # Should return as-is

    def test_format_email_html_mixed_content(self):
        """Test handling mixed plain text and HTML content."""
        # Arrange
        mixed = "Plain text\n<p>HTML content</p>\nMore plain text"
        
        # Act
        result = format_email_html(mixed)
        
        # Assert
        assert "<p>Plain text</p>" in result
        assert "<p>HTML content</p>" in result
        assert "<p>More plain text</p>" in result


class TestGenerateFollowUp:
    """Tests for generate_follow_up function."""

    def test_generate_follow_up_success(self, mock_openai_client, mock_openai_response, follow_up_params):
        """Test successful follow-up email generation."""
        # Arrange
        mock_openai_client.chat.completions.create.return_value = mock_openai_response
        
        # Act
        result = generate_follow_up(**follow_up_params)
        
        # Assert
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Test Email Subject"
        assert result.body_text == "This is a test email body in plain text."
        assert result.body_html == "<p>This is a test email body in HTML.</p>"
        mock_openai_client.chat.completions.create.assert_called_once()

    def test_generate_follow_up_minimal_params(self, mock_openai_client, mock_openai_response):
        """Test follow-up email generation with minimal required parameters."""
        # Arrange
        mock_openai_client.chat.completions.create.return_value = mock_openai_response
        
        # Act
        result = generate_follow_up(
            original_subject="Original Subject",
            original_body="This is the original email body.",
            recipient_name="John Doe",
            follow_up_number=1
        )
        
        # Assert
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Test Email Subject"
        mock_openai_client.chat.completions.create.assert_called_once()

    @patch('app.services.ai_email_generator_service.logger')
    def test_generate_follow_up_openai_error(self, mock_logger, mock_openai_client, follow_up_params):
        """Test error handling when OpenAI API call fails for follow-up generation."""
        # Arrange
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_follow_up(**follow_up_params)
        
        assert "API Error" in str(exc_info.value)
        mock_logger.error.assert_called_once()


class TestGenerateABTestVariants:
    """Tests for generate_ab_test_variants function."""

    @patch('app.services.ai_email_generator_service.client.chat.completions.create')
    def test_generate_ab_test_variants_success(self, mock_create, ab_test_params):
        """Test successful A/B test variant generation."""
        # Arrange
        mock_responses = {}
        for variant_key in ab_test_params["variants"].keys():
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.content = json.dumps({
                "subject": f"Test Subject {variant_key}",
                "body_text": f"This is test variant {variant_key} in plain text.",
                "body_html": f"<p>This is test variant {variant_key} in HTML.</p>"
            })
            mock_responses[variant_key] = mock_response

        # Setup the side effect to return different responses for each call
        mock_create.side_effect = list(mock_responses.values())
        
        # Act
        result = generate_ab_test_variants(**ab_test_params)
        
        # Assert
        assert len(result) == 2
        assert "A" in result and "B" in result
        assert isinstance(result["A"], EmailGenResponse)
        assert isinstance(result["B"], EmailGenResponse)
        assert result["A"].subject == "Test Subject A"
        assert result["B"].subject == "Test Subject B"
        assert result["A"].variant == "A"
        assert result["B"].variant == "B"
        assert mock_create.call_count == 2

    @patch('app.services.ai_email_generator_service.client.chat.completions.create')
    @patch('app.services.ai_email_generator_service.logger')
    def test_generate_ab_test_variants_api_error(self, mock_logger, mock_create, ab_test_params):
        """Test error handling when OpenAI API call fails for AB test generation."""
        # Arrange
        mock_create.side_effect = Exception("API Error")
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_ab_test_variants(**ab_test_params)
        
        assert "API Error" in str(exc_info.value)
        mock_logger.error.assert_called()

    @patch('app.services.ai_email_generator_service.client.chat.completions.create')
    @patch('app.services.ai_email_generator_service.logger')
    def test_generate_ab_test_variants_parse_error(self, mock_logger, mock_create, ab_test_params):
        """Test error handling when parsing API response fails for AB test generation."""
        # Arrange
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = MagicMock()
        mock_response.choices[0].message.content = "Invalid JSON"
        mock_create.return_value = mock_response
        
        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            generate_ab_test_variants(**ab_test_params)
        
        assert "Failed to parse AI response" in str(exc_info.value)
        mock_logger.error.assert_called() 