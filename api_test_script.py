#!/usr/bin/env python3
"""
ReplyRocket.io API Testing Script

This script tests all API endpoints in the FastAPI backend using httpx.
It includes tests for authentication, email generation, campaigns, 
follow-ups and other key features of the application.

Author: Claude AI Assistant
"""

import asyncio
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import httpx
import typer
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, track
from rich.table import Table
from typing_extensions import Annotated

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("api_tester")

# Create console for rich output
console = Console()

# Initialize CLI app
app = typer.Typer(help="API Testing Script for ReplyRocket.io")

# Default configuration
DEFAULT_BASE_URL = "http://localhost:8000/api/v1"
DEFAULT_EMAIL = "test@example.com"
DEFAULT_PASSWORD = "password123"


class APITester:
    """Main class for API testing functionality"""
    
    def __init__(self, base_url: str, email: str, password: str, timeout: int = 30):
        """
        Initialize the API tester with configuration
        
        Args:
            base_url: Base URL for the API
            email: Email for authentication
            password: Password for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.email = email
        self.password = password
        self.timeout = timeout
        self.access_token = None
        self.client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        self.user_id = None
        self.test_results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "endpoint_results": {}
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        auth_required: bool = True,
        expected_status: int = 200,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data/payload
            auth_required: Whether authorization is required
            expected_status: Expected HTTP status code
            description: Description of the test
            
        Returns:
            Response data as dictionary
        """
        self.test_results["total"] += 1
        
        url = f"{self.base_url}{endpoint}"
        headers = {}
        
        # Add authentication if required and available
        if auth_required and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        
        # Prepare request kwargs
        kwargs = {"headers": headers}
        if data:
            kwargs["json"] = data
        
        # Execute request based on method
        try:
            if method.upper() == "GET":
                response = await self.client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await self.client.post(url, **kwargs)
            elif method.upper() == "PUT":
                response = await self.client.put(url, **kwargs)
            elif method.upper() == "DELETE":
                response = await self.client.delete(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Check status code
            if response.status_code != expected_status:
                log.error(f"Expected status {expected_status}, but got {response.status_code} for {endpoint}")
                log.error(f"Response: {response.text}")
                self.test_results["failed"] += 1
                self._record_result(endpoint, method, description, False, 
                                   f"Expected status {expected_status}, got {response.status_code}")
                return {"error": f"Unexpected status code: {response.status_code}"}
            
            # Try to parse response as JSON
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"text": response.text}
            
            # Record success
            self.test_results["passed"] += 1
            self._record_result(endpoint, method, description, True, "Success")
            return response_data
            
        except httpx.RequestError as e:
            log.error(f"Request error for {endpoint}: {str(e)}")
            self.test_results["failed"] += 1
            self._record_result(endpoint, method, description, False, str(e))
            return {"error": str(e)}
    
    def _record_result(self, endpoint: str, method: str, description: str, success: bool, message: str):
        """Record test result for reporting"""
        if endpoint not in self.test_results["endpoint_results"]:
            self.test_results["endpoint_results"][endpoint] = []
        
        self.test_results["endpoint_results"][endpoint].append({
            "method": method,
            "description": description,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def run_all_tests(self):
        """Run all API tests in sequence"""
        console.rule("[bold blue]Starting API Tests[/bold blue]")
        
        # Authentication tests must run first to get token
        await self.test_authentication()
        
        # Only continue if authentication succeeded
        if self.access_token:
            # Run all other tests
            await self.test_user_endpoints()
            await self.test_campaign_endpoints()
            await self.test_email_endpoints()
            await self.test_follow_up_endpoints()
            await self.test_stats_endpoints()
        else:
            log.error("Authentication failed, skipping remaining tests")
        
        # Close the client
        await self.close()
        
        # Print summary
        self.print_summary()
    
    async def test_authentication(self):
        """Test authentication endpoints"""
        log.info("Testing authentication endpoints...")
        
        # Test registration first if needed
        new_user_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        register_data = {
            "email": new_user_email,
            "password": self.password,
            "full_name": "Test User"
        }
        
        register_response = await self._make_request(
            "POST", 
            "/auth/register", 
            data=register_data,
            auth_required=False,
            expected_status=200,
            description="Register new user"
        )
        
        # Test login
        login_data = {
            "username": self.email,  # OAuth2 form uses username field for email
            "password": self.password
        }
        
        login_response = await self._make_request(
            "POST", 
            "/auth/login/access-token", 
            data=login_data,
            auth_required=False,
            expected_status=200,
            description="Login with credentials"
        )
        
        # Extract token if login successful
        if "access_token" in login_response:
            self.access_token = login_response["access_token"]
            log.info("Authentication successful, token received")
        else:
            log.error("Failed to get access token")
    
    async def test_user_endpoints(self):
        """Test user-related endpoints"""
        log.info("Testing user endpoints...")
        
        # Get current user
        me_response = await self._make_request(
            "GET", 
            "/users/me", 
            auth_required=True,
            expected_status=200,
            description="Get current user info"
        )
        
        if "id" in me_response:
            self.user_id = me_response["id"]
            log.info(f"User ID: {self.user_id}")
        
        # Update user
        if self.user_id:
            update_data = {
                "full_name": f"Updated Name {random.randint(1, 1000)}"
            }
            
            await self._make_request(
                "PUT", 
                "/users/me", 
                data=update_data,
                auth_required=True,
                expected_status=200,
                description="Update user profile"
            )
        
        # Test SMTP config
        smtp_config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "test@example.com",
            "smtp_password": "smtp_password",
            "smtp_use_tls": True
        }
        
        await self._make_request(
            "POST", 
            "/users/smtp-config", 
            data=smtp_config,
            auth_required=True,
            expected_status=200,
            description="Update SMTP configuration"
        )
    
    async def test_campaign_endpoints(self):
        """Test campaign-related endpoints"""
        log.info("Testing campaign endpoints...")
        
        # Create a campaign
        campaign_data = {
            "name": f"Test Campaign {uuid.uuid4().hex[:8]}",
            "description": "Campaign created by API test script",
            "industry": "Technology",
            "target_job_title": "Software Developer",
            "pain_points": "Time management, code quality",
            "follow_up_days": 3,
            "max_follow_ups": 2
        }
        
        campaign_response = await self._make_request(
            "POST", 
            "/campaigns", 
            data=campaign_data,
            auth_required=True,
            expected_status=200,
            description="Create new campaign"
        )
        
        # Store campaign ID for other tests
        campaign_id = None
        if "id" in campaign_response:
            campaign_id = campaign_response["id"]
            log.info(f"Created campaign with ID: {campaign_id}")
        
        # Get all campaigns
        await self._make_request(
            "GET", 
            "/campaigns", 
            auth_required=True,
            expected_status=200,
            description="Get all campaigns"
        )
        
        # Get active campaigns
        await self._make_request(
            "GET", 
            "/campaigns/active", 
            auth_required=True,
            expected_status=200,
            description="Get active campaigns"
        )
        
        # Get specific campaign
        if campaign_id:
            await self._make_request(
                "GET", 
                f"/campaigns/{campaign_id}", 
                auth_required=True,
                expected_status=200,
                description="Get specific campaign by ID"
            )
            
            # Update campaign
            update_data = {
                "name": f"Updated Campaign {uuid.uuid4().hex[:8]}",
                "description": "Updated by API test script"
            }
            
            await self._make_request(
                "PUT", 
                f"/campaigns/{campaign_id}", 
                data=update_data,
                auth_required=True,
                expected_status=200,
                description="Update campaign"
            )
            
            # Configure A/B testing
            ab_test_data = {
                "campaign_id": campaign_id,
                "enabled": True,
                "variant_a_percentage": 0.7,
                "variant_b_percentage": 0.3
            }
            
            await self._make_request(
                "POST", 
                "/campaigns/ab-test", 
                data=ab_test_data,
                auth_required=True,
                expected_status=200,
                description="Configure A/B testing"
            )
    
    async def test_email_endpoints(self):
        """Test email-related endpoints"""
        log.info("Testing email endpoints...")
        
        # Generate email
        email_gen_data = {
            "recipient_name": "John Doe",
            "recipient_email": "john.doe@example.com",
            "recipient_company": "ACME Inc.",
            "recipient_job_title": "CTO",
            "industry": "Technology",
            "pain_points": ["Efficiency", "Automation", "Cost"],
            "personalization_notes": "Met at TechCrunch conference"
        }
        
        email_response = await self._make_request(
            "POST", 
            "/emails/generate", 
            data=email_gen_data,
            auth_required=True,
            expected_status=200,
            description="Generate email content"
        )
        
        # Send email (this might fail in test environment without proper SMTP setup)
        if "subject" in email_response and "body_text" in email_response:
            email_send_data = {
                "recipient_email": "john.doe@example.com",
                "recipient_name": "John Doe",
                "subject": email_response["subject"],
                "body_text": email_response["body_text"],
                "body_html": email_response["body_html"]
            }
            
            # Note: This may fail without proper SMTP configuration
            await self._make_request(
                "POST", 
                "/emails/send", 
                data=email_send_data,
                auth_required=True,
                expected_status=200,
                description="Send email (expected to fail without SMTP)",
                # We don't expect this to pass in a test environment
            )
    
    async def test_follow_up_endpoints(self):
        """Test follow-up-related endpoints"""
        log.info("Testing follow-up endpoints...")
        
        # This requires an existing email ID, which we may not have
        # We'll simulate with a random UUID, which will likely fail
        # but demonstrates how to test these endpoints
        mock_email_id = str(uuid.uuid4())
        
        follow_up_data = {
            "original_email_id": mock_email_id,
            "new_approach": "More direct and actionable"
        }
        
        await self._make_request(
            "POST", 
            "/follow-ups/generate", 
            data=follow_up_data,
            auth_required=True,
            # Expect 404 as the email ID is fake
            expected_status=404,
            description="Generate follow-up (expected to fail with mock ID)"
        )
    
    async def test_stats_endpoints(self):
        """Test statistics endpoints"""
        log.info("Testing statistics endpoints...")
        
        # Get user stats
        await self._make_request(
            "GET", 
            "/stats/user", 
            auth_required=True,
            expected_status=200,
            description="Get user statistics"
        )
        
        # Campaign stats requires a campaign ID
        # If we have one from previous tests, use it
        if hasattr(self, 'campaign_id') and self.campaign_id:
            await self._make_request(
                "GET", 
                f"/stats/campaign/{self.campaign_id}", 
                auth_required=True,
                expected_status=200,
                description="Get campaign statistics"
            )
    
    def print_summary(self):
        """Print a summary of the test results"""
        console.rule("[bold blue]Test Results Summary[/bold blue]")
        
        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        
        console.print(f"Total tests: {total}")
        console.print(f"Passed: [green]{passed}[/green] ({passed/total*100:.1f}%)")
        console.print(f"Failed: [red]{failed}[/red] ({failed/total*100:.1f}%)")
        
        # Create a table for detailed results
        table = Table(title="Endpoint Test Results")
        table.add_column("Endpoint", style="cyan")
        table.add_column("Method", style="magenta")
        table.add_column("Description")
        table.add_column("Result", style="bold")
        table.add_column("Message")
        
        for endpoint, results in self.test_results["endpoint_results"].items():
            for result in results:
                result_text = "[green]PASS[/green]" if result["success"] else "[red]FAIL[/red]"
                table.add_row(
                    endpoint,
                    result["method"],
                    result["description"],
                    result_text,
                    result["message"]
                )
        
        console.print(table)


@app.command()
def test(
    base_url: Annotated[str, typer.Option("--base-url", "-b")] = DEFAULT_BASE_URL,
    email: Annotated[str, typer.Option("--email", "-e")] = DEFAULT_EMAIL,
    password: Annotated[str, typer.Option("--password", "-p")] = DEFAULT_PASSWORD,
    timeout: Annotated[int, typer.Option("--timeout", "-t")] = 30,
    log_level: Annotated[str, typer.Option("--log-level", "-l")] = "INFO",
):
    """Run API tests on the specified ReplyRocket.io backend"""
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        console.print(f"[red]Invalid log level: {log_level}[/red]")
        return
    
    logging.getLogger().setLevel(numeric_level)
    
    # Display test configuration
    console.print(f"Testing API at: [bold]{base_url}[/bold]")
    console.print(f"Using credentials: [bold]{email}[/bold]")
    console.print(f"Timeout: [bold]{timeout}s[/bold]")
    console.print(f"Log level: [bold]{log_level}[/bold]")
    
    # Create tester and run tests
    async def run_tests():
        tester = APITester(base_url, email, password, timeout)
        await tester.run_all_tests()
    
    # Run the async tests
    asyncio.run(run_tests())


if __name__ == "__main__":
    app() 