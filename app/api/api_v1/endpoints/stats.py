from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.api import deps

router = APIRouter()


@router.get("/campaign/{campaign_id}", response_model=schemas.CampaignStats)
def get_campaign_stats(
    *,
    db: Session = Depends(deps.get_db),
    campaign_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get statistics for a specific campaign.
    """
    campaign = crud.campaign.get(db, id=campaign_id)
    if not campaign or campaign.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Campaign not found",
        )
    
    # Calculate rates
    total_emails = campaign.total_emails or 1  # Avoid division by zero
    open_rate = campaign.opened_emails / total_emails if total_emails > 0 else 0
    reply_rate = campaign.replied_emails / total_emails if total_emails > 0 else 0
    conversion_rate = campaign.converted_emails / total_emails if total_emails > 0 else 0
    
    # Get A/B test results if active
    ab_test_results = None
    if campaign.ab_test_active and campaign.ab_test_variants:
        ab_test_results = calculate_ab_test_results(db, campaign_id)
    
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


@router.get("/user", response_model=List[schemas.CampaignStats])
def get_user_stats(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """
    Get statistics for all campaigns of the current user.
    """
    campaigns = crud.campaign.get_multi_by_user(db, user_id=current_user.id)
    
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


def calculate_ab_test_results(db: Session, campaign_id: str) -> Dict:
    """
    Calculate A/B test results for a campaign.
    """
    from app.models.email import Email
    
    # Get all emails for the campaign
    emails = crud.email.get_emails_by_campaign(db, campaign_id=campaign_id)
    
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