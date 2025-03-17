"""
Email generation request schema module.

This module defines the schema for requests to the AI email generation service.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class EmailGenRequest(BaseModel):
    """
    Schema for requests to the AI email generation service.
    
    Attributes:
        recipient: Email address of the recipient
        subject: Subject line of the email to generate or a template
        body: Email body content or a template
    """
    recipient: EmailStr = Field(
        ...,  # This means the field is required
        description="Email address of the recipient"
    )
    subject: str = Field(
        ...,
        description="Subject line of the email to generate or a template"
    )
    body: str = Field(
        ...,
        description="Email body content or a template"
    )
    
    class Config:
        """Configuration for the Pydantic model"""
        schema_extra = {
            "example": {
                "recipient": "john.doe@example.com",
                "subject": "Proposal for {company_name}",
                "body": "Dear {recipient_name},\n\nI'm reaching out regarding..."
            }
        } 