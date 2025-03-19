"""
Unit tests for the AI email generator service.

This module tests the AI email generator service with mocked OpenAI API calls.
"""

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
import os

from app.services.ai_email_generator_service import (
    generate_email,
    build_email_prompt,
    call_openai_api,
    parse_email_response,
    generate_follow_up,
    build_follow_up_prompt,
    generate_ab_test_variants
)
from app.schemas.email import EmailGenResponse


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response."""
    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = json.dumps({
        "subject": "Test Subject Line",
        "body_text": "This is a test plain text email body.",
        "body_html": "<p>This is a test HTML email body.</p>"
    })
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    return mock_response


@pytest.fixture
def email_gen_params():
    """Provide standard parameters for email generation tests."""
    return {
        "recipient_name": "John Doe",
        "industry": "Technology",
        "pain_points": ["Managing remote teams", "Tracking project progress"],
        "recipient_company": "Tech Solutions Inc.",
        "recipient_job_title": "CTO",
        "personalization_notes": "Met at TechConf 2023"
    }


@pytest.fixture
def follow_up_params():
    """Provide standard parameters for follow-up email generation tests."""
    return {
        "original_subject": "Regarding your project management challenges",
        "original_body": "Hi John, I noticed your company might be facing challenges with project management...",
        "recipient_name": "John Doe",
        "follow_up_number": 1,
        "recipient_company": "Tech Solutions Inc.",
        "recipient_job_title": "CTO",
        "new_approach": "Focus on ROI benefits"
    }


class TestBuildEmailPrompt:
    """Tests for the build_email_prompt function."""

    def test_build_email_prompt_with_all_parameters(self, email_gen_params):
        """Test that the prompt includes all provided parameters."""
        result = build_email_prompt(**email_gen_params)
        
        # Check that all the parameters are included in the prompt
        assert email_gen_params["recipient_name"] in result
        assert email_gen_params["industry"] in result
        assert all(point in result for point in email_gen_params["pain_points"])
        assert email_gen_params["recipient_company"] in result
        assert email_gen_params["recipient_job_title"] in result
        assert email_gen_params["personalization_notes"] in result
        
        # Check that the formatting instructions are included
        assert "JSON" in result
        assert "subject" in result
        assert "body_text" in result
        assert "body_html" in result

    def test_build_email_prompt_with_minimal_parameters(self):
        """Test prompt building with only required parameters."""
        minimal_params = {
            "recipient_name": "Jane Smith",
            "industry": "Healthcare",
            "pain_points": ["Patient scheduling"]
        }
        
        result = build_email_prompt(**minimal_params)
        
        # Check that mandatory parameters are included
        assert minimal_params["recipient_name"] in result
        assert minimal_params["industry"] in result
        assert minimal_params["pain_points"][0] in result
        
        # Optional parameters should not be present
        assert "personalization notes" not in result.lower()
        assert "Additional personalization" not in result
        
        # But the formatting instructions should still be there
        assert "JSON" in result


class TestBuildFollowUpPrompt:
    """Tests for the build_follow_up_prompt function."""

    def test_build_follow_up_prompt_with_all_parameters(self, follow_up_params):
        """Test that the follow-up prompt includes all provided parameters."""
        result = build_follow_up_prompt(**follow_up_params)
        
        # Check that all parameters are included
        assert follow_up_params["recipient_name"] in result
        assert follow_up_params["original_subject"] in result
        assert follow_up_params["original_body"] in result
        assert f"follow-up #{follow_up_params['follow_up_number']}" in result
        assert follow_up_params["recipient_company"] in result
        assert follow_up_params["recipient_job_title"] in result
        assert follow_up_params["new_approach"] in result
        
        # Check that formatting instructions are included
        assert "JSON" in result
        assert "subject" in result
        assert "body_text" in result
        assert "body_html" in result

    def test_build_follow_up_prompt_with_minimal_parameters(self):
        """Test follow-up prompt building with only required parameters."""
        minimal_params = {
            "original_subject": "Initial outreach",
            "original_body": "Hi Jane, just reaching out about your software needs...",
            "recipient_name": "Jane Smith",
            "follow_up_number": 2
        }
        
        result = build_follow_up_prompt(**minimal_params)
        
        # Check that mandatory parameters are included
        assert minimal_params["recipient_name"] in result
        assert minimal_params["original_subject"] in result
        assert minimal_params["original_body"] in result
        assert f"follow-up #{minimal_params['follow_up_number']}" in result
        
        # Optional parameters should not be included
        assert "new approach" not in result.lower()
        
        # But the formatting instructions should still be there
        assert "JSON" in result


class TestCallOpenAiApi:
    """Tests for the call_openai_api function."""

    @patch('app.services.ai_email_generator_service.client')
    def test_call_openai_api_production(self, mock_client):
        """Test OpenAI API call in production mode."""
        # Setup the mock
        mock_response = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        
        # Set environment to production
        with patch('app.services.ai_email_generator_service.is_test_mode', False):
            # Call the function
            prompt = "Test prompt"
            system_role = "Test system role"
            result = call_openai_api(prompt, system_role)
            
            # Verify the client was called correctly
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args[1]
            assert call_args['messages'][0]['content'] == system_role
            assert call_args['messages'][1]['content'] == prompt
            assert result == mock_response

    @patch('app.services.ai_email_generator_service.client')
    def test_call_openai_api_error_handling(self, mock_client):
        """Test error handling in OpenAI API call."""
        # Setup the mock to raise an exception
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Set environment to production
        with patch('app.services.ai_email_generator_service.is_test_mode', False):
            # Call the function and expect an exception
            with pytest.raises(Exception) as excinfo:
                call_openai_api("Test prompt", "Test system role")
            
            # Verify the error message
            assert "Failed to generate content" in str(excinfo.value)

    def test_call_openai_api_test_mode(self):
        """Test OpenAI API call in test mode."""
        # Set environment to test
        with patch('app.services.ai_email_generator_service.is_test_mode', True):
            # Call the function
            result = call_openai_api("Test prompt", "Test system role")
            
            # Verify we get a mock response
            assert result is not None
            assert hasattr(result, 'choices')
            assert len(result.choices) > 0
            assert hasattr(result.choices[0], 'message')
            assert hasattr(result.choices[0].message, 'content')
            # Verify the content is valid JSON
            content = result.choices[0].message.content
            data = json.loads(content)
            assert "subject" in data
            assert "body_text" in data
            assert "body_html" in data


class TestParseEmailResponse:
    """Tests for the parse_email_response function."""

    def test_parse_valid_response(self, mock_openai_response):
        """Test parsing a valid OpenAI response."""
        result = parse_email_response(mock_openai_response)
        
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Test Subject Line"
        assert result.body_text == "This is a test plain text email body."
        assert result.body_html == "<p>This is a test HTML email body.</p>"

    def test_parse_invalid_response(self):
        """Test parsing an invalid response (missing required fields)."""
        # Create a response with missing fields
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = json.dumps({
            "subject": "Test Subject Line",
            # Missing body_text and body_html
        })
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        # Should raise an exception
        with pytest.raises(Exception) as excinfo:
            parse_email_response(mock_response)
        
        assert "Failed to parse AI response" in str(excinfo.value)

    def test_parse_non_json_response(self):
        """Test parsing a response that doesn't contain valid JSON."""
        # Create a response with invalid JSON
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "This is not JSON"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        # Should raise an exception
        with pytest.raises(Exception) as excinfo:
            parse_email_response(mock_response)
        
        assert "Failed to parse AI response" in str(excinfo.value)


class TestGenerateEmail:
    """Tests for the generate_email function."""

    @patch('app.services.ai_email_generator_service.build_email_prompt')
    @patch('app.services.ai_email_generator_service.call_openai_api')
    @patch('app.services.ai_email_generator_service.parse_email_response')
    def test_generate_email_success(self, mock_parse, mock_call_api, mock_build_prompt, 
                                   email_gen_params, mock_openai_response):
        """Test successful email generation with all parameters."""
        # Setup mocks
        mock_build_prompt.return_value = "Mocked prompt"
        mock_call_api.return_value = mock_openai_response
        mock_parse.return_value = EmailGenResponse(
            subject="Test Subject",
            body_text="Test body text",
            body_html="<p>Test body HTML</p>"
        )
        
        # Call the function
        result = generate_email(**email_gen_params)
        
        # Verify mocks were called correctly
        mock_build_prompt.assert_called_once_with(**email_gen_params)
        mock_call_api.assert_called_once_with(
            prompt="Mocked prompt", 
            system_role="You are an expert cold email copywriter who specializes in writing personalized, effective cold emails that get responses."
        )
        mock_parse.assert_called_once_with(mock_openai_response)
        
        # Verify result
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Test Subject"
        assert result.body_text == "Test body text"
        assert result.body_html == "<p>Test body HTML</p>"

    @patch('app.services.ai_email_generator_service.build_email_prompt')
    @patch('app.services.ai_email_generator_service.call_openai_api')
    def test_generate_email_api_error(self, mock_call_api, mock_build_prompt, email_gen_params):
        """Test handling of API errors during email generation."""
        # Setup mocks
        mock_build_prompt.return_value = "Mocked prompt"
        mock_call_api.side_effect = Exception("API Error")
        
        # Call the function and expect an exception
        with pytest.raises(Exception) as excinfo:
            generate_email(**email_gen_params)
        
        # Verify the error is passed through
        assert "API Error" in str(excinfo.value)


class TestGenerateFollowUp:
    """Tests for the generate_follow_up function."""
    
    @patch('app.services.ai_email_generator_service.build_follow_up_prompt')
    @patch('app.services.ai_email_generator_service.call_openai_api')
    @patch('app.services.ai_email_generator_service.parse_email_response')
    def test_generate_follow_up_success(self, mock_parse, mock_call_api, mock_build_prompt, 
                                       follow_up_params, mock_openai_response):
        """Test successful follow-up email generation."""
        # Setup mocks
        mock_build_prompt.return_value = "Mocked follow-up prompt"
        mock_call_api.return_value = mock_openai_response
        mock_parse.return_value = EmailGenResponse(
            subject="Re: Test Subject",
            body_text="Follow-up body text",
            body_html="<p>Follow-up body HTML</p>"
        )
        
        # Call the function
        result = generate_follow_up(**follow_up_params)
        
        # Verify mocks were called correctly
        mock_build_prompt.assert_called_once_with(**follow_up_params)
        mock_call_api.assert_called_once_with(
            prompt="Mocked follow-up prompt", 
            system_role="You are an expert cold email copywriter who specializes in writing effective follow-up emails that get responses."
        )
        mock_parse.assert_called_once_with(mock_openai_response)
        
        # Verify result
        assert isinstance(result, EmailGenResponse)
        assert result.subject == "Re: Test Subject"
        assert result.body_text == "Follow-up body text"
        assert result.body_html == "<p>Follow-up body HTML</p>"

    @patch('app.services.ai_email_generator_service.build_follow_up_prompt')
    @patch('app.services.ai_email_generator_service.call_openai_api')
    def test_generate_follow_up_error(self, mock_call_api, mock_build_prompt, follow_up_params):
        """Test error handling during follow-up generation."""
        # Setup mocks
        mock_build_prompt.return_value = "Mocked follow-up prompt"
        mock_call_api.side_effect = Exception("API Error")
        
        # Call the function and expect an exception
        with pytest.raises(Exception) as excinfo:
            generate_follow_up(**follow_up_params)
        
        # Verify the error is passed through
        assert "API Error" in str(excinfo.value)


class TestGenerateABTestVariants:
    """Tests for the generate_ab_test_variants function."""
    
    @patch('app.services.ai_email_generator_service.client')
    def test_generate_ab_test_variants_success(self, mock_client, email_gen_params, mock_openai_response):
        """Test successful generation of A/B test variants."""
        # Setup the parameters
        variants = {
            "A": "Focus on ROI and business value",
            "B": "Focus on ease of implementation"
        }
        email_gen_params["variants"] = variants
        
        # Setup the mock
        mock_client.chat.completions.create.return_value = mock_openai_response
        
        # Set environment to production
        with patch('app.services.ai_email_generator_service.is_test_mode', False):
            # Call the function
            result = generate_ab_test_variants(
                recipient_name=email_gen_params["recipient_name"],
                industry=email_gen_params["industry"],
                pain_points=email_gen_params["pain_points"],
                variants=variants,
                recipient_company=email_gen_params["recipient_company"],
                recipient_job_title=email_gen_params["recipient_job_title"]
            )
            
            # Verify the result
            assert isinstance(result, dict)
            assert "A" in result and "B" in result
            assert isinstance(result["A"], EmailGenResponse)
            assert isinstance(result["B"], EmailGenResponse)
            assert result["A"].variant == "A"
            assert result["B"].variant == "B"
            
            # Verify the API was called twice (once for each variant)
            assert mock_client.chat.completions.create.call_count == 2

    @patch('app.services.ai_email_generator_service.client')
    def test_generate_ab_test_variants_error(self, mock_client, email_gen_params):
        """Test error handling during A/B test variant generation."""
        # Setup the parameters
        variants = {
            "A": "Focus on ROI",
            "B": "Focus on ease of use"
        }
        email_gen_params["variants"] = variants
        
        # Setup the mock to raise an exception
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Set environment to production
        with patch('app.services.ai_email_generator_service.is_test_mode', False):
            # Call the function and expect an exception
            with pytest.raises(Exception) as excinfo:
                generate_ab_test_variants(
                    recipient_name=email_gen_params["recipient_name"],
                    industry=email_gen_params["industry"],
                    pain_points=email_gen_params["pain_points"],
                    variants=variants,
                    recipient_company=email_gen_params["recipient_company"],
                    recipient_job_title=email_gen_params["recipient_job_title"]
                )
            
            # Verify the error message
            assert "API Error" in str(excinfo.value)

    @patch('app.services.ai_email_generator_service.client')
    def test_generate_ab_test_variants_parse_error(self, mock_client, email_gen_params):
        """Test handling of response parsing errors during A/B test variant generation."""
        # Setup the parameters
        variants = {
            "A": "Focus on ROI",
            "B": "Focus on ease of use"
        }
        email_gen_params["variants"] = variants
        
        # Create a mock response with invalid JSON
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "This is not JSON"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        # Setup the mock to return the invalid response
        mock_client.chat.completions.create.return_value = mock_response
        
        # Set environment to production
        with patch('app.services.ai_email_generator_service.is_test_mode', False):
            # Call the function and expect an exception
            with pytest.raises(Exception) as excinfo:
                generate_ab_test_variants(
                    recipient_name=email_gen_params["recipient_name"],
                    industry=email_gen_params["industry"],
                    pain_points=email_gen_params["pain_points"],
                    variants=variants,
                    recipient_company=email_gen_params["recipient_company"],
                    recipient_job_title=email_gen_params["recipient_job_title"]
                )
            
            # Verify the error message
            assert "Failed to parse AI response" in str(excinfo.value)


# Integration-like tests (still using mocks, but testing the full flow)
class TestEmailGenerationIntegration:
    """Integration-like tests for the email generation flow."""
    
    def test_email_generation_flow(self, email_gen_params):
        """Test the complete flow of email generation."""
        # Force test mode
        with patch('app.services.ai_email_generator_service.is_test_mode', True):
            # Generate an email
            result = generate_email(**email_gen_params)
            
            # Verify the result structure
            assert isinstance(result, EmailGenResponse)
            assert result.subject
            assert result.body_text
            assert result.body_html
    
    def test_follow_up_generation_flow(self, follow_up_params):
        """Test the complete flow of follow-up generation."""
        # Force test mode
        with patch('app.services.ai_email_generator_service.is_test_mode', True):
            # Generate a follow-up
            result = generate_follow_up(**follow_up_params)
            
            # Verify the result structure
            assert isinstance(result, EmailGenResponse)
            assert result.subject
            assert result.body_text
            assert result.body_html 