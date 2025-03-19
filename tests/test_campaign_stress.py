"""
Stress testing for campaign creation API endpoints.

This module contains tests that verify the performance and stability
of campaign-related API endpoints under high load.
"""

import pytest
import time
import asyncio
import random
from typing import List, Dict, Any
import uuid
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.tests.utils.utils import random_email, random_lower_string
from app.tests.utils.user import create_random_user
from app.db.session import SessionLocal


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def superuser_token_headers():
    """Create a superuser and return headers with token."""
    db = SessionLocal()
    try:
        user = create_random_user(db, is_superuser=True)
        access_token = create_access_token(
            subject=str(user.id),
            expires_delta=60 * 24 * 8
        )
        return {"Authorization": f"Bearer {access_token}"}
    finally:
        db.close()


def create_sample_campaign(client: TestClient, token_headers: Dict[str, str]) -> Dict[str, Any]:
    """Helper function to create a sample campaign."""
    data = {
        "name": f"Stress Test Campaign {random_lower_string()}",
        "description": "This is a campaign created during stress testing",
        "target_audience": "Technology managers",
        "status": "draft"
    }
    response = client.post("/api/v1/campaigns/", json=data, headers=token_headers)
    assert response.status_code == 201, f"Failed to create campaign: {response.text}"
    return response.json()


def create_multiple_campaigns(client: TestClient, token_headers: Dict[str, str], count: int = 10) -> List[Dict[str, Any]]:
    """Create multiple campaigns in sequence."""
    campaigns = []
    for i in range(count):
        campaign = create_sample_campaign(client, token_headers)
        campaigns.append(campaign)
    return campaigns


def test_sequential_campaign_creation(client: TestClient, superuser_token_headers: Dict[str, str]):
    """Test creating 20 campaigns sequentially, measuring time."""
    start_time = time.time()
    campaigns = create_multiple_campaigns(client, superuser_token_headers, count=20)
    end_time = time.time()
    
    # Verify all campaigns were created
    assert len(campaigns) == 20
    
    # Log the total time and average time per campaign
    total_time = end_time - start_time
    avg_time = total_time / 20
    print(f"\nSequential campaign creation: {total_time:.2f} seconds total, {avg_time:.2f} seconds per campaign")


def create_campaign_worker(token_headers: Dict[str, str], client: TestClient = None):
    """Worker function for creating a campaign in a thread."""
    if client is None:
        client = TestClient(app)
        
    try:
        campaign = create_sample_campaign(client, token_headers)
        return campaign
    except Exception as e:
        return {"error": str(e)}


def test_parallel_campaign_creation(client: TestClient, superuser_token_headers: Dict[str, str]):
    """Test creating 20 campaigns in parallel using threads."""
    num_campaigns = 20
    start_time = time.time()
    
    # Use a thread pool to create campaigns in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        # Submit tasks to the executor
        futures = [
            executor.submit(create_campaign_worker, superuser_token_headers, client)
            for _ in range(num_campaigns)
        ]
        
        # Get results as they complete
        campaigns = [future.result() for future in futures]
    
    end_time = time.time()
    
    # Verify all campaigns were created
    successful_campaigns = [c for c in campaigns if "error" not in c]
    failed_campaigns = [c for c in campaigns if "error" in c]
    
    assert len(successful_campaigns) == num_campaigns, f"Only {len(successful_campaigns)} campaigns created successfully, {len(failed_campaigns)} failed"
    
    # Log the total time and average time per campaign
    total_time = end_time - start_time
    avg_time = total_time / num_campaigns
    print(f"\nParallel campaign creation: {total_time:.2f} seconds total, {avg_time:.2f} seconds per campaign")


def test_campaign_retrieval_stress(client: TestClient, superuser_token_headers: Dict[str, str]):
    """Test creating campaigns and then retrieving them repeatedly."""
    # First create some campaigns
    campaigns = create_multiple_campaigns(client, superuser_token_headers, count=10)
    campaign_ids = [c["id"] for c in campaigns]
    
    # Now perform many random reads
    start_time = time.time()
    num_reads = 100
    
    for _ in range(num_reads):
        # Pick a random campaign ID
        campaign_id = random.choice(campaign_ids)
        
        # Retrieve the campaign
        response = client.get(f"/api/v1/campaigns/{campaign_id}", headers=superuser_token_headers)
        assert response.status_code == 200, f"Failed to retrieve campaign: {response.text}"
    
    end_time = time.time()
    
    # Log the total time and average time per read
    total_time = end_time - start_time
    avg_time = total_time / num_reads
    print(f"\nCampaign retrieval stress: {total_time:.2f} seconds total, {avg_time:.2f} seconds per read")


def test_campaign_update_stress(client: TestClient, superuser_token_headers: Dict[str, str]):
    """Test creating campaigns and then updating them repeatedly."""
    # First create some campaigns
    campaigns = create_multiple_campaigns(client, superuser_token_headers, count=5)
    
    # Now perform multiple updates on each campaign
    start_time = time.time()
    updates_per_campaign = 10
    total_updates = len(campaigns) * updates_per_campaign
    
    for campaign in campaigns:
        for i in range(updates_per_campaign):
            update_data = {
                "name": f"Updated Campaign {i} - {random_lower_string()}",
                "description": f"Update {i} during stress testing",
                "status": "active" if i % 2 == 0 else "draft"
            }
            
            response = client.put(
                f"/api/v1/campaigns/{campaign['id']}", 
                json=update_data, 
                headers=superuser_token_headers
            )
            assert response.status_code == 200, f"Failed to update campaign: {response.text}"
    
    end_time = time.time()
    
    # Log the total time and average time per update
    total_time = end_time - start_time
    avg_time = total_time / total_updates
    print(f"\nCampaign update stress: {total_time:.2f} seconds total, {avg_time:.2f} seconds per update")


def test_mixed_campaign_operations(client: TestClient, superuser_token_headers: Dict[str, str]):
    """Test a mix of campaign operations (create, read, update) to simulate real-world usage."""
    # Create some initial campaigns
    initial_campaigns = create_multiple_campaigns(client, superuser_token_headers, count=5)
    campaign_ids = [c["id"] for c in initial_campaigns]
    
    # Mix of operations
    start_time = time.time()
    num_operations = 50
    
    for i in range(num_operations):
        operation = random.choice(["create", "read", "update"])
        
        if operation == "create" or not campaign_ids:
            # Create a new campaign
            campaign = create_sample_campaign(client, superuser_token_headers)
            campaign_ids.append(campaign["id"])
        
        elif operation == "read":
            # Read a random campaign
            campaign_id = random.choice(campaign_ids)
            response = client.get(f"/api/v1/campaigns/{campaign_id}", headers=superuser_token_headers)
            assert response.status_code == 200, f"Failed to retrieve campaign: {response.text}"
        
        elif operation == "update":
            # Update a random campaign
            campaign_id = random.choice(campaign_ids)
            update_data = {
                "name": f"Mixed Ops Campaign {i}",
                "description": f"Update during mixed operations test",
                "status": "active" if i % 2 == 0 else "draft"
            }
            
            response = client.put(
                f"/api/v1/campaigns/{campaign_id}", 
                json=update_data, 
                headers=superuser_token_headers
            )
            assert response.status_code == 200, f"Failed to update campaign: {response.text}"
    
    end_time = time.time()
    
    # Log the total time and average time per operation
    total_time = end_time - start_time
    avg_time = total_time / num_operations
    print(f"\nMixed campaign operations: {total_time:.2f} seconds total, {avg_time:.2f} seconds per operation")


@pytest.mark.skip(reason="This test can be resource-intensive")
def test_high_load_campaign_creation(client: TestClient, superuser_token_headers: Dict[str, str]):
    """Test creating a large number of campaigns to test system limits."""
    num_campaigns = 100  # Adjust as needed for your system
    
    start_time = time.time()
    
    # Use a thread pool with more workers for higher load
    with ThreadPoolExecutor(max_workers=20) as executor:
        # Submit tasks to the executor
        futures = [
            executor.submit(create_campaign_worker, superuser_token_headers, client)
            for _ in range(num_campaigns)
        ]
        
        # Get results as they complete
        campaigns = [future.result() for future in futures]
    
    end_time = time.time()
    
    # Verify all campaigns were created
    successful_campaigns = [c for c in campaigns if "error" not in c]
    failed_campaigns = [c for c in campaigns if "error" in c]
    
    success_rate = len(successful_campaigns) / num_campaigns * 100
    
    print(f"\nHigh load campaign creation: {len(successful_campaigns)} out of {num_campaigns} successful ({success_rate:.1f}%)")
    print(f"Total time: {end_time - start_time:.2f} seconds")
    print(f"Average time per campaign: {(end_time - start_time) / num_campaigns:.4f} seconds")
    
    if failed_campaigns:
        print(f"Sample of errors: {failed_campaigns[:3]}")
    
    # We don't assert all succeeded, as this test is meant to find the limits
    assert success_rate > 50, f"Success rate too low: {success_rate:.1f}%" 