# ReplyRocket API Test Suite

This directory contains the test suite for the ReplyRocket API, implemented using pytest.

## Test Structure

- `conftest.py`: Contains pytest fixtures shared across test files
- `test_auth.py`: Tests for authentication endpoints
- `test_emails.py`: Tests for email generation and sending endpoints
- `test_campaigns.py`: Tests for campaign management endpoints

## Running Tests

To run the full test suite:

```bash
pytest
```

To run tests with verbose output:

```bash
pytest -v
```

To run a specific test file:

```bash
pytest tests/test_auth.py
```

To run a specific test:

```bash
pytest tests/test_auth.py::TestAuth::test_register_user
```

## Test Database

Tests use an in-memory SQLite database that is created and destroyed for each test session. This ensures tests don't interfere with your actual database.

## Mock Services

External services like the AI email generation and SMTP email sending are mocked during tests to avoid making actual API calls or sending real emails.

## Test Coverage

To run tests with coverage reporting:

```bash
pytest --cov=app
```

To generate an HTML coverage report:

```bash
pytest --cov=app --cov-report=html
```

This will create a `htmlcov` directory with the coverage report, which you can view in a browser. 