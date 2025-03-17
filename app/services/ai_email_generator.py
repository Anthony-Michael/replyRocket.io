import random
from typing import Dict, List, Optional

from openai import OpenAI

from app.core.config import settings
from app.schemas.email import EmailGenResponse

# Initialize OpenAI client
client = OpenAI(api_key=settings.OPENAI_API_KEY)


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
    """
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
    
    if personalization_notes:
        prompt += f"\nAdditional personalization notes: {personalization_notes}\n"
    
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
        
        return EmailGenResponse(
            subject=email_data["subject"],
            body_text=email_data["body_text"],
            body_html=email_data["body_html"],
        )
    except Exception as e:
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
    """
    # Construct the prompt
    prompt = f"""
    Write a follow-up email (follow-up #{follow_up_number}) to {recipient_name}"""
    
    if recipient_job_title:
        prompt += f", who is a {recipient_job_title}"
    
    if recipient_company:
        prompt += f" at {recipient_company}"
    
    prompt += f""".

    This is a follow-up to the original email with subject: "{original_subject}"
    
    Original email content:
    {original_body}
    """
    
    if new_approach:
        prompt += f"\nFor this follow-up, try a different approach: {new_approach}\n"
    
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
    
    # Call OpenAI API
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an expert cold email copywriter who specializes in writing effective follow-up emails that get responses."},
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
        
        return EmailGenResponse(
            subject=email_data["subject"],
            body_text=email_data["body_text"],
            body_html=email_data["body_html"],
        )
    except Exception as e:
        raise Exception(f"Failed to parse AI response: {str(e)}")


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