import random
import json
import logging
import os
from typing import Dict, List, Optional, Any

from openai import OpenAI

from app.core.config import settings
from app.schemas.email import EmailGenResponse

# Set up logger
logger = logging.getLogger(__name__)

# Check if we're in test mode
is_test_mode = settings.ENVIRONMENT == "test" or os.environ.get("PYTEST_CURRENT_TEST")

# Initialize OpenAI client with error handling
try:
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
except Exception as e:
    if is_test_mode:
        logger.warning(f"Using mock OpenAI client for testing: {str(e)}")
        client = None
    else:
        logger.error(f"Failed to initialize OpenAI client: {str(e)}")
        raise


def generate_email(
    recipient_name: str,
    industry: str,
    pain_points: List[str],
    recipient_company: Optional[str] = None,
    recipient_job_title: Optional[str] = None,
    personalization_notes: Optional[str] = None,
) -> EmailGenResponse:
    """
    Generate a personalized cold email using AI.
    
    Args:
        recipient_name: Name of the recipient
        industry: Industry of the recipient
        pain_points: List of pain points to address
        recipient_company: Company name of the recipient (optional)
        recipient_job_title: Job title of the recipient (optional)
        personalization_notes: Additional personalization context (optional)
        
    Returns:
        EmailGenResponse with subject, body_text, and body_html
        
    Raises:
        Exception: If OpenAI API call fails or response parsing fails
    """
    # Construct the prompt
    prompt = build_email_prompt(
        recipient_name=recipient_name,
        industry=industry,
        pain_points=pain_points,
        recipient_company=recipient_company,
        recipient_job_title=recipient_job_title,
        personalization_notes=personalization_notes
    )
    
    # Call OpenAI API and get the response
    response = call_openai_api(
        prompt=prompt, 
        system_role="You are an expert cold email copywriter who specializes in writing personalized, effective cold emails that get responses."
    )
    
    # Parse the response and return email content
    return parse_email_response(response)


def build_email_prompt(
    recipient_name: str,
    industry: str,
    pain_points: List[str],
    recipient_company: Optional[str] = None,
    recipient_job_title: Optional[str] = None,
    personalization_notes: Optional[str] = None,
) -> str:
    """
    Build a prompt for the AI to generate a cold email.
    
    Args:
        recipient_name: Name of the recipient
        industry: Industry of the recipient
        pain_points: List of pain points to address
        recipient_company: Company name of the recipient (optional)
        recipient_job_title: Job title of the recipient (optional)
        personalization_notes: Additional personalization context (optional)
        
    Returns:
        Prompt string for the AI
    """
    # Start with basic information
    prompt = f"""
    Write a personalized cold email to {recipient_name}"""
    
    # Add job title if provided
    if recipient_job_title:
        prompt += f", who is a {recipient_job_title}"
    
    # Add company if provided
    if recipient_company:
        prompt += f" at {recipient_company}"
    
    prompt += f""".

    The recipient is in the {industry} industry and has the following pain points:
    """
    
    # Add each pain point
    for point in pain_points:
        prompt += f"- {point}\n"
    
    # Add personalization notes if provided
    if personalization_notes:
        prompt += f"\nAdditional personalization notes: {personalization_notes}\n"
    
    # Add email requirements
    prompt += """
    The email should be:
    1. Concise and respectful of their time
    2. Personalized to their specific situation
    3. Focused on how we can solve their pain points
    4. Include a clear but non-pushy call to action
    
    Format your response as JSON with the following structure:
    {
        "subject": "The email subject line",
        "body_text": "The plain text version of the email",
        "body_html": "The HTML version of the email with proper formatting"
    }
    
    The HTML version should include proper formatting, paragraph breaks, and styling.
    """
    
    return prompt


def call_openai_api(prompt: str, system_role: str) -> Any:
    """
    Call the OpenAI API with the given prompt.
    
    Args:
        prompt: The prompt to send to the API
        system_role: The system role to set for the conversation
        
    Returns:
        OpenAI API response
        
    Raises:
        Exception: If API call fails
    """
    # If in test mode, return a mock response
    if is_test_mode:
        logger.info("Using mock OpenAI response for testing")
        
        class MockChoice:
            def __init__(self, content):
                self.message = type('obj', (object,), {'content': content})
        
        class MockResponse:
            def __init__(self, content):
                self.choices = [MockChoice(content)]
        
        mock_email_json = '''
        {
            "subject": "Test Subject Line",
            "body_text": "This is a test plain text email body for testing purposes.",
            "body_html": "<p>This is a test HTML email body for testing purposes.</p>"
        }
        '''
        
        return MockResponse(mock_email_json)
    
    # Normal operation for production
    try:
        return client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
    except Exception as e:
        logger.error(f"OpenAI API call failed: {str(e)}")
        raise Exception(f"Failed to generate content: {str(e)}")


def parse_email_response(response: Any) -> EmailGenResponse:
    """
    Parse the OpenAI API response into an EmailGenResponse.
    
    Args:
        response: OpenAI API response
        
    Returns:
        EmailGenResponse with subject, body_text, and body_html
        
    Raises:
        Exception: If response parsing fails
    """
    try:
        content = response.choices[0].message.content
        email_data = json.loads(content)
        
        return EmailGenResponse(
            subject=email_data["subject"],
            body_text=email_data["body_text"],
            body_html=email_data["body_html"],
        )
    except Exception as e:
        logger.error(f"Failed to parse AI response: {str(e)}")
        raise Exception(f"Failed to parse AI response: {str(e)}")


def generate_follow_up(
    original_subject: str,
    original_body: str,
    recipient_name: str,
    follow_up_number: int,
    recipient_company: Optional[str] = None,
    recipient_job_title: Optional[str] = None,
    new_approach: Optional[str] = None,
) -> EmailGenResponse:
    """
    Generate a follow-up email using AI.
    
    Args:
        original_subject: Subject of the original email
        original_body: Body of the original email
        recipient_name: Name of the recipient
        follow_up_number: Which follow-up number this is (e.g., 1, 2, 3)
        recipient_company: Company name of the recipient (optional)
        recipient_job_title: Job title of the recipient (optional)
        new_approach: Alternative approach to try (optional)
        
    Returns:
        EmailGenResponse with subject, body_text, and body_html
    """
    # Build the follow-up prompt
    prompt = build_follow_up_prompt(
        original_subject=original_subject,
        original_body=original_body,
        recipient_name=recipient_name,
        follow_up_number=follow_up_number,
        recipient_company=recipient_company,
        recipient_job_title=recipient_job_title,
        new_approach=new_approach
    )
    
    # Call OpenAI API
    response = call_openai_api(
        prompt=prompt,
        system_role="You are an expert cold email copywriter who specializes in writing effective follow-up emails that get responses."
    )
    
    # Parse response
    return parse_email_response(response)


def build_follow_up_prompt(
    original_subject: str,
    original_body: str,
    recipient_name: str,
    follow_up_number: int,
    recipient_company: Optional[str] = None,
    recipient_job_title: Optional[str] = None,
    new_approach: Optional[str] = None,
) -> str:
    """
    Build a prompt for the AI to generate a follow-up email.
    
    Args:
        original_subject: Subject of the original email
        original_body: Body of the original email
        recipient_name: Name of the recipient
        follow_up_number: Which follow-up number this is (e.g., 1, 2, 3)
        recipient_company: Company name of the recipient (optional)
        recipient_job_title: Job title of the recipient (optional)
        new_approach: Alternative approach to try (optional)
        
    Returns:
        Prompt string for the AI
    """
    # Start with recipient information
    prompt = f"""
    Write a follow-up email (follow-up #{follow_up_number}) to {recipient_name}"""
    
    # Add job title if provided
    if recipient_job_title:
        prompt += f", who is a {recipient_job_title}"
    
    # Add company if provided
    if recipient_company:
        prompt += f" at {recipient_company}"
    
    # Add original email details
    prompt += f""".

    This is a follow-up to the original email with subject: "{original_subject}"
    
    Original email content:
    {original_body}
    """
    
    # Add new approach if provided
    if new_approach:
        prompt += f"\nFor this follow-up, try a different approach: {new_approach}\n"
    
    # Add follow-up requirements
    prompt += f"""
    The follow-up email should:
    1. Reference the original email briefly
    2. Provide additional value or information
    3. Be even more concise than the original
    4. Have a different angle or approach than the original
    5. Include a clear but gentle call to action
    
    Format your response as JSON with the following structure:
    {{
        "subject": "The email subject line (should reference the original email)",
        "body_text": "The plain text version of the email",
        "body_html": "The HTML version of the email with proper formatting"
    }}
    
    The HTML version should include proper formatting, paragraph breaks, and styling.
    """
    
    return prompt


def generate_ab_test_variants(
    recipient_name: str,
    industry: str,
    pain_points: List[str],
    variants: Dict[str, str],
    recipient_company: Optional[str] = None,
    recipient_job_title: Optional[str] = None,
) -> Dict[str, EmailGenResponse]:
    """
    Generate multiple variants of an email for A/B testing.
    """
    result = {}
    
    for variant_key, variant_description in variants.items():
        # Construct the prompt
        prompt = f"""
        Write a personalized cold email to {recipient_name}"""
        
        if recipient_job_title:
            prompt += f", who is a {recipient_job_title}"
        
        if recipient_company:
            prompt += f" at {recipient_company}"
        
        prompt += f""".

        The recipient is in the {industry} industry and has the following pain points:
        """
        
        for point in pain_points:
            prompt += f"- {point}\n"
        
        prompt += f"""
        This is variant "{variant_key}" with the following approach: {variant_description}
        
        The email should be:
        1. Concise and respectful of their time
        2. Personalized to their specific situation
        3. Focused on how we can solve their pain points
        4. Include a clear but non-pushy call to action
        5. Follow the specific approach for this variant: {variant_description}
        
        Format your response as JSON with the following structure:
        {{
            "subject": "The email subject line",
            "body_text": "The plain text version of the email",
            "body_html": "The HTML version of the email with proper formatting"
        }}
        
        The HTML version should include proper formatting, paragraph breaks, and styling.
        """
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert cold email copywriter who specializes in writing personalized, effective cold emails that get responses."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        
        # Parse the response
        try:
            content = response.choices[0].message.content
            import json
            email_data = json.loads(content)
            
            result[variant_key] = EmailGenResponse(
                subject=email_data["subject"],
                body_text=email_data["body_text"],
                body_html=email_data["body_html"],
                variant=variant_key,
            )
        except Exception as e:
            raise Exception(f"Failed to parse AI response for variant {variant_key}: {str(e)}")
    
    return result 