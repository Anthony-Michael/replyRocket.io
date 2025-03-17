"""
Email generation response schema module.

This module defines the schema for responses from the AI email generation service.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EmailGenResponse(BaseModel):
    """
    Schema for responses from the AI email generation service.
    
    Attributes:
        subject: The generated email subject line
        body_text: The generated email body in plain text format
        body_html: The generated email body in HTML format
        variant: Optional variant identifier (for A/B testing)
        generated_at: Timestamp when the email was generated
    """
    subject: str
    body_text: str
    body_html: str
    variant: Optional[str] = None
    generated_at: datetime = datetime.now()  # Added timestamp for when the email was generated
    
    class Config:
        """Configuration for the Pydantic model"""
        schema_extra = {
            "example": {
                "subject": "Innovative cold email automation solution for {company_name}",
                "body_text": "Hello {recipient_name},\n\nI noticed that {company_name} has been...",
                "body_html": "<p>Hello {recipient_name},</p><p>I noticed that {company_name} has been...</p>",
                "variant": "A",
                "generated_at": "2023-03-17T12:34:56.789Z"
            }
        } 