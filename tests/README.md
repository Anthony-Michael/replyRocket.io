# ReplyRocket.io Test Suite

This directory contains comprehensive unit tests for the ReplyRocket.io FastAPI backend application.

## Overview

The test suite is designed to ensure the reliability and correctness of the API endpoints, covering:

- Authentication (registration, login)
- Campaign management (CRUD operations, A/B testing)
- Email generation (AI-powered content creation)
- Email sending and tracking

All tests use mocks for external dependencies (OpenAI API, SMTP servers) to ensure tests run quickly and without external dependencies.

## Test Structure

- `conftest.py` - Contains pytest fixtures used across test modules
- `test_auth.py` - Tests for authentication endpoints
- `test_campaigns.py` - Tests for campaign management endpoints
- `test_emails.py` - Tests for email generation and sending endpoints

## Running Tests

### Option 1: Using the test runner script

The easiest way to run all tests is using the provided script:

```bash
python run_tests.py
```

This will:
1. Run all tests with coverage reporting
2. Display results in the terminal
3. Generate an HTML coverage report
4. Open the coverage report in your browser

### Option 2: Using pytest directly

You can also run specific tests or test modules using pytest directly:

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_register_user

# Run tests by marker
pytest -m auth
pytest -m campaigns
pytest -m emails
```

## Coverage Reports

To generate coverage reports:

```bash
# Generate terminal report
pytest --cov=app tests/

# Generate terminal report with missing lines
pytest --cov=app --cov-report=term-missing tests/

# Generate HTML report
pytest --cov=app --cov-report=html tests/
```

The HTML report will be generated in the `htmlcov` directory.

## Test Markers

Tests are tagged with markers to allow running specific test categories:

- `@pytest.mark.auth` - Authentication tests
- `@pytest.mark.campaigns` - Campaign management tests
- `@pytest.mark.emails` - Email generation and sending tests

## Writing New Tests

When adding new tests, follow these guidelines:

1. Use the Arrange-Act-Assert pattern
2. Add detailed docstrings explaining the test purpose
3. Mock external dependencies
4. Use appropriate test markers
5. Ensure tests are isolated and don't depend on each other
6. Keep tests focused on a single functionality

### Example test structure:

```python
@pytest.mark.campaigns
def test_create_campaign(client, token_headers):
    """
    Test creating a new campaign.
    
    Arrange:
        - Prepare campaign data
        - Set up authentication
    
    Act:
        - Send POST request to create campaign
    
    Assert:
        - Verify response status is 201
        - Verify campaign data in response
    """
    # Arrange
    campaign_data = {...}
    
    # Act
    response = client.post("/api/v1/campaigns", json=campaign_data, headers=token_headers)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["name"] == campaign_data["name"]
``` 