"""
A/B Testing configuration schema module.

This module defines schemas for configuring A/B testing functionality
in the email campaigns.
"""

from pydantic import BaseModel, Field, validator


class ABTestConfig(BaseModel):
    """
    Configuration schema for A/B testing email variants.
    
    Attributes:
        enabled: Whether A/B testing is enabled for this campaign
        variant_a_percentage: Percentage of emails to send as variant A (0.0 to 1.0)
        variant_b_percentage: Percentage of emails to send as variant B (0.0 to 1.0)
    """
    enabled: bool = Field(
        default=False, 
        description="Whether A/B testing is enabled for this campaign"
    )
    variant_a_percentage: float = Field(
        default=0.5, 
        description="Percentage of emails to send as variant A (0.0 to 1.0)"
    )
    variant_b_percentage: float = Field(
        default=0.5, 
        description="Percentage of emails to send as variant B (0.0 to 1.0)"
    )
    
    @validator('variant_a_percentage', 'variant_b_percentage')
    def validate_percentages(cls, v):
        """Validate that percentages are between 0 and 1"""
        if v < 0.0 or v > 1.0:
            raise ValueError('Percentage must be between 0.0 and 1.0')
        return v
    
    @validator('variant_b_percentage')
    def validate_total_percentage(cls, v, values):
        """Validate that the sum of percentages equals 1.0"""
        if 'variant_a_percentage' in values:
            total = values['variant_a_percentage'] + v
            if abs(total - 1.0) > 0.001:  # Allow small floating point errors
                raise ValueError('The sum of variant percentages must equal 1.0')
        return v 