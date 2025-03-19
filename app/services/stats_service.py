"""
Stats service for ReplyRocket.io

This module contains business logic for generating statistics,
separating it from data access operations in the crud modules.
"""

import logging
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import models, schemas, crud
from app.utils.error_handling import handle_db_error
from app.core.exception_handlers import EntityNotFoundError, PermissionDeniedError

# Set up logger
logger = logging.getLogger(__name__)


def get_campaign_stats(db: Session, campaign_id: UUID, user_id: UUID) -> schemas.CampaignStats:
    """
    Get statistics for a specific campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        user_id: ID of the user requesting the stats
        
    Returns:
        Campaign statistics
        
    Raises:
        EntityNotFoundError: If campaign not found
        PermissionDeniedError: If user doesn't have permission to access the campaign
    """
    try:
        # Get campaign from database
        campaign = crud.campaign.get(db, id=campaign_id)
        if not campaign:
            logger.error(f"Campaign {campaign_id} not found")
            raise EntityNotFoundError(entity="campaign", entity_id=campaign_id)
        
        # Check if user has permission to access the campaign
        if campaign.user_id != user_id:
            logger.warning(f"User {user_id} attempted to access campaign {campaign_id} without permission")
            raise PermissionDeniedError(entity="campaign", entity_id=campaign_id, user_id=user_id)
        
        # Calculate rates
        total_emails = campaign.total_emails or 1  # Avoid division by zero
        open_rate = campaign.opened_emails / total_emails if total_emails > 0 else 0
        reply_rate = campaign.replied_emails / total_emails if total_emails > 0 else 0
        conversion_rate = campaign.converted_emails / total_emails if total_emails > 0 else 0
        
        # Get A/B test results if active
        ab_test_results = None
        if campaign.ab_test_active and campaign.ab_test_variants:
            ab_test_results = calculate_ab_test_results(db, campaign_id)
        
        # Return stats
        return {
            "id": campaign.id,
            "name": campaign.name,
            "total_emails": campaign.total_emails,
            "opened_emails": campaign.opened_emails,
            "replied_emails": campaign.replied_emails,
            "converted_emails": campaign.converted_emails,
            "open_rate": open_rate,
            "reply_rate": reply_rate,
            "conversion_rate": conversion_rate,
            "ab_test_results": ab_test_results,
        }
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving campaign stats for campaign {campaign_id}: {str(e)}")
        handle_db_error(e, "retrieve", "campaign stats")


def get_user_stats(db: Session, user_id: UUID) -> List[schemas.CampaignStats]:
    """
    Get statistics for all campaigns of a user.
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        List of campaign statistics
    """
    try:
        # Get campaigns from database
        campaigns = crud.campaign.get_multi_by_owner(db, user_id=user_id)
        
        # Calculate stats for each campaign
        result = []
        for campaign in campaigns:
            # Calculate rates
            total_emails = campaign.total_emails or 1  # Avoid division by zero
            open_rate = campaign.opened_emails / total_emails if total_emails > 0 else 0
            reply_rate = campaign.replied_emails / total_emails if total_emails > 0 else 0
            conversion_rate = campaign.converted_emails / total_emails if total_emails > 0 else 0
            
            # Get A/B test results if active
            ab_test_results = None
            if campaign.ab_test_active and campaign.ab_test_variants:
                ab_test_results = calculate_ab_test_results(db, campaign.id)
            
            # Add to result
            result.append({
                "id": campaign.id,
                "name": campaign.name,
                "total_emails": campaign.total_emails,
                "opened_emails": campaign.opened_emails,
                "replied_emails": campaign.replied_emails,
                "converted_emails": campaign.converted_emails,
                "open_rate": open_rate,
                "reply_rate": reply_rate,
                "conversion_rate": conversion_rate,
                "ab_test_results": ab_test_results,
            })
        
        return result
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving user stats for user {user_id}: {str(e)}")
        handle_db_error(e, "retrieve", "user stats")


def calculate_ab_test_results(db: Session, campaign_id: UUID) -> Dict:
    """
    Calculate A/B test results for a campaign.
    
    Args:
        db: Database session
        campaign_id: ID of the campaign
        
    Returns:
        Dictionary with A/B test results
    """
    try:
        # Get all emails for the campaign
        emails = crud.email.get_multi_by_campaign(db, campaign_id=campaign_id)
        
        # Group emails by variant
        variants = {}
        for email in emails:
            if not email.ab_test_variant:
                continue
            
            if email.ab_test_variant not in variants:
                variants[email.ab_test_variant] = {
                    "total": 0,
                    "opened": 0,
                    "replied": 0,
                    "converted": 0,
                }
            
            variants[email.ab_test_variant]["total"] += 1
            if email.is_opened:
                variants[email.ab_test_variant]["opened"] += 1
            if email.is_replied:
                variants[email.ab_test_variant]["replied"] += 1
            if email.is_converted:
                variants[email.ab_test_variant]["converted"] += 1
        
        # Calculate rates for each variant
        results = {}
        for variant, stats in variants.items():
            total = stats["total"] or 1  # Avoid division by zero
            results[variant] = {
                "total_emails": stats["total"],
                "opened_emails": stats["opened"],
                "replied_emails": stats["replied"],
                "converted_emails": stats["converted"],
                "open_rate": stats["opened"] / total,
                "reply_rate": stats["replied"] / total,
                "conversion_rate": stats["converted"] / total,
            }
        
        return results
    except SQLAlchemyError as e:
        logger.error(f"Error calculating A/B test results for campaign {campaign_id}: {str(e)}")
        handle_db_error(e, "calculate", "A/B test results") 