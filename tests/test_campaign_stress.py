"""
Stress tests for campaign creation functionality.

This module contains tests to verify the system's performance
under high load conditions for campaign creation.
"""

import pytest
import time
import random
import string
import concurrent.futures
from typing import List, Dict, Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import models, schemas
from app.core.config import settings
from app.services import campaign_service
from app.api.deps import get_current_active_user


@pytest.mark.stress
@pytest.mark.campaigns
class TestCampaignStress:
    """Stress tests for campaign operations."""
    
    @pytest.fixture
    def random_campaign_data(self) -> Dict[str, Any]:
        """Generate random campaign data for testing."""
        def random_string(length: int = 10) -> str:
            return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        
        industries = [
            "Technology", "Healthcare", "Finance", "Education", 
            "Retail", "Manufacturing", "Hospitality", "Real Estate"
        ]
        
        return {
            "name": f"Test Campaign {random_string(8)}",
            "description": f"Description for stress test {random_string(15)}",
            "industry": random.choice(industries),
            "target_audience": f"Target audience for {random_string(10)}",
            "is_active": random.choice([True, False]),
        }
    
    def test_create_campaign_sequential(self, db: Session, test_user: models.User):
        """Test creating multiple campaigns sequentially and measure performance."""
        num_campaigns = 20
        start_time = time.time()
        
        created_campaigns = []
        for i in range(num_campaigns):
            # Create campaign data
            campaign_data = schemas.CampaignCreate(
                name=f"Stress Test Campaign {i}",
                description=f"Description for campaign {i}",
                industry="Technology",
                target_audience="CTOs and IT Directors",
                is_active=True
            )
            
            # Create campaign
            campaign = campaign_service.create_campaign(db, campaign_data, test_user.id)
            created_campaigns.append(campaign)
            
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert all campaigns were created successfully
        assert len(created_campaigns) == num_campaigns
        
        # Log performance metrics
        campaigns_per_second = num_campaigns / duration
        print(f"\nSequential Campaign Creation Performance:")
        print(f"Created {num_campaigns} campaigns in {duration:.2f} seconds")
        print(f"Rate: {campaigns_per_second:.2f} campaigns per second")
        
        # Verify each campaign exists in the database
        for campaign in created_campaigns:
            db_campaign = db.query(models.EmailCampaign).filter(models.EmailCampaign.id == campaign.id).first()
            assert db_campaign is not None
            assert db_campaign.user_id == test_user.id
    
    def test_create_campaign_parallel(self, client: TestClient, auth_headers: Dict[str, str]):
        """Test creating multiple campaigns in parallel and measure performance."""
        num_campaigns = 20
        max_workers = 10
        start_time = time.time()
        
        # Function to create a campaign via API
        def create_campaign(i: int) -> Dict[str, Any]:
            campaign_data = {
                "name": f"Parallel Stress Test Campaign {i}",
                "description": f"Description for parallel campaign {i}",
                "industry": "Technology",
                "target_audience": "CTOs and IT Directors",
                "is_active": True
            }
            response = client.post(
                f"{settings.API_V1_STR}/campaigns",
                json=campaign_data,
                headers=auth_headers
            )
            return response.json()
        
        # Execute requests in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_campaign = {executor.submit(create_campaign, i): i for i in range(num_campaigns)}
            
            responses = []
            for future in concurrent.futures.as_completed(future_to_campaign):
                campaign_id = future_to_campaign[future]
                try:
                    data = future.result()
                    responses.append(data)
                except Exception as exc:
                    print(f"Campaign {campaign_id} generated an exception: {exc}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert all campaigns were created successfully
        assert len(responses) == num_campaigns
        
        # Log performance metrics
        campaigns_per_second = num_campaigns / duration
        print(f"\nParallel Campaign Creation Performance:")
        print(f"Created {num_campaigns} campaigns in {duration:.2f} seconds with {max_workers} workers")
        print(f"Rate: {campaigns_per_second:.2f} campaigns per second")
        
        # Check that all responses have the expected format
        for response in responses:
            assert "id" in response
            assert "name" in response
            assert "description" in response
    
    def test_create_campaign_with_varying_data(self, db: Session, test_user: models.User):
        """Test creating campaigns with varying data complexity."""
        num_campaigns = 10
        
        # Create campaigns with increasing complexity
        varying_complexity_times = []
        
        for i in range(num_campaigns):
            # Create campaign with increasing complexity
            campaign_data = schemas.CampaignCreate(
                name=f"Complex Campaign {i}",
                description="Lorem ipsum " * (i + 1),  # Increasing description length
                industry="Technology",
                target_audience="CTOs and IT Directors",
                is_active=True,
                # Add more variation based on index
                ab_test_active=i % 2 == 0,
                max_follow_ups=i
            )
            
            # Measure creation time
            start_time = time.time()
            campaign = campaign_service.create_campaign(db, campaign_data, test_user.id)
            end_time = time.time()
            
            varying_complexity_times.append(end_time - start_time)
        
        # Calculate statistics
        avg_time = sum(varying_complexity_times) / len(varying_complexity_times)
        max_time = max(varying_complexity_times)
        min_time = min(varying_complexity_times)
        
        print(f"\nCampaign Creation with Varying Complexity:")
        print(f"Average creation time: {avg_time:.6f} seconds")
        print(f"Maximum creation time: {max_time:.6f} seconds")
        print(f"Minimum creation time: {min_time:.6f} seconds")
        
        # Assert performance is within acceptable bounds
        assert max_time < 1.0, "Campaign creation is too slow for complex data"
    
    def test_bulk_campaign_creation(self, db: Session, test_user: models.User):
        """Test bulk creation of campaigns and measure database performance."""
        num_campaigns = 50
        
        # Prepare bulk data
        campaign_data_list = [
            self.random_campaign_data() for _ in range(num_campaigns)
        ]
        
        # Convert to schema objects
        campaign_schemas = [
            schemas.CampaignCreate(**data) for data in campaign_data_list
        ]
        
        # Function to perform bulk creation
        def bulk_create_campaigns():
            campaigns = []
            for campaign_schema in campaign_schemas:
                campaign = models.EmailCampaign(
                    **campaign_schema.dict(),
                    user_id=test_user.id
                )
                db.add(campaign)
                campaigns.append(campaign)
            db.commit()
            return campaigns
        
        # Measure bulk creation time
        start_time = time.time()
        created_campaigns = bulk_create_campaigns()
        end_time = time.time()
        duration = end_time - start_time
        
        # Assert all campaigns were created
        assert len(created_campaigns) == num_campaigns
        
        # Log performance metrics
        campaigns_per_second = num_campaigns / duration
        print(f"\nBulk Campaign Creation Performance:")
        print(f"Bulk created {num_campaigns} campaigns in {duration:.2f} seconds")
        print(f"Rate: {campaigns_per_second:.2f} campaigns per second")
        
        # Verify each campaign exists in the database
        campaign_ids = [campaign.id for campaign in created_campaigns]
        db_campaigns = db.query(models.EmailCampaign).filter(
            models.EmailCampaign.id.in_(campaign_ids)
        ).all()
        assert len(db_campaigns) == num_campaigns
    
    def test_campaign_read_performance(self, db: Session, test_user: models.User):
        """Test reading campaigns with filtering and pagination performance."""
        # Create a large number of campaigns for testing
        num_campaigns = 100
        
        # Create test campaigns with different properties
        for i in range(num_campaigns):
            is_active = i % 2 == 0
            industry = f"Industry{i % 5}"
            
            campaign = models.EmailCampaign(
                name=f"Performance Test Campaign {i}",
                description=f"Description for performance test {i}",
                industry=industry,
                is_active=is_active,
                user_id=test_user.id
            )
            db.add(campaign)
        
        db.commit()
        
        # Test various read operations
        # 1. Get all campaigns with pagination
        start_time = time.time()
        all_campaigns = campaign_service.get_campaigns(db, test_user.id, skip=0, limit=100)
        pagination_time = time.time() - start_time
        
        # 2. Get active campaigns
        start_time = time.time()
        active_campaigns = campaign_service.get_active_campaigns(db, test_user.id)
        active_filter_time = time.time() - start_time
        
        # 3. Filter by industry
        start_time = time.time()
        industry_campaigns = db.query(models.EmailCampaign).filter(
            models.EmailCampaign.user_id == test_user.id,
            models.EmailCampaign.industry == "Industry1"
        ).all()
        industry_filter_time = time.time() - start_time
        
        # Log performance metrics
        print(f"\nCampaign Read Performance:")
        print(f"Read {len(all_campaigns)} campaigns with pagination: {pagination_time:.6f} seconds")
        print(f"Read {len(active_campaigns)} active campaigns: {active_filter_time:.6f} seconds")
        print(f"Read {len(industry_campaigns)} campaigns by industry: {industry_filter_time:.6f} seconds")
        
        # Assert performance is within acceptable bounds
        assert pagination_time < 0.5, "Pagination is too slow"
        assert active_filter_time < 0.5, "Filtering active campaigns is too slow"
        assert industry_filter_time < 0.5, "Filtering by industry is too slow" 