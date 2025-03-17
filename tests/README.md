# ReplyRocket.io Test Suite

This directory contains the comprehensive test suite for the ReplyRocket.io application. The tests are designed to cover both unit tests and integration tests for various components of the application.

## Test Organization

The test suite is organized into the following files:

- **`test_utils.py`**: Tests for common utility functions
- **`test_campaigns_validation.py`**: Tests for campaign validation and access control
- **`test_error_handling.py`**: Tests for error handling utilities
- **`test_auth.py`**: Tests for authentication-related functionality
- **`test_campaigns.py`**: Tests for campaign management
- **`test_emails.py`**: Tests for email generation and sending

## Test Fixtures

Common test fixtures are defined in `conftest.py` and include:

- **`db`**: SQLite in-memory test database
- **`client`**: FastAPI TestClient
- **`mock_current_user`**: Mock authenticated user
- **`mock_db_session`**: Mock database session
- **`mock_openai_response`**: Mock OpenAI API response
- **`auth_headers`**: Authentication headers for protected endpoints
- **`patch_dependencies`**: Fixture to patch external dependencies

## Running Tests

To run the test suite, make sure you have the development dependencies installed:

```bash
pip install -r requirements-dev.txt
```

Then, run the tests using pytest:

```bash
# Run all tests
pytest

# Run tests with output
pytest -v

# Run a specific test file
pytest tests/test_utils.py

# Run a specific test
pytest tests/test_utils.py::TestValidateCampaignAccess::test_campaign_exists_and_belongs_to_user

# Run tests with coverage
pytest --cov=app
```

## Writing New Tests

When adding new tests:

1. **Organize by component**: Add tests to existing files that match the component being tested, or create a new file if needed.
2. **Use fixtures**: Take advantage of fixtures in `conftest.py` to minimize setup code.
3. **Mock external dependencies**: Always mock external services and APIs to avoid making real API calls during tests.
4. **Follow AAA pattern**: Structure tests with Arrange, Act, Assert sections for clarity.
5. **Test both success and failure paths**: Ensure both successful operations and error handling are tested.

## Test Coverage

The test suite aims to cover:

- Utility functions
- Database operations with error handling
- API endpoints
- Authentication and authorization
- External service interactions

Run the coverage report to identify areas that need more testing:

```bash
pytest --cov=app --cov-report=html
``` 