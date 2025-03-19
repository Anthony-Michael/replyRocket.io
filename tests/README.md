# Testing Framework for ReplyRocket.io

This directory contains the testing infrastructure for the ReplyRocket.io application. It includes unit tests, integration tests, and tools for generating coverage reports.

## Testing Architecture

The testing framework follows these key principles:

1. **Isolation**: Tests should be isolated from each other and from external services
2. **Coverage**: Tests should aim to cover all critical business logic and edge cases
3. **Speed**: Tests should run quickly to enable frequent execution
4. **Maintainability**: Tests should be easy to understand and maintain

## Test Categories

The test suite is organized into several categories:

- **Unit Tests**: Testing individual functions and methods in isolation
  - Focus on business logic in service modules
  - Use mocks to isolate from dependencies
  
- **Integration Tests**: Testing interactions between components
  - API endpoint tests
  - Database interaction tests
  
- **Functional Tests**: Testing complete workflows
  - End-to-end tests for critical user journeys
  - Authentication flows

## Running Tests

### Using the Test Runner

The easiest way to run tests is using the test runner script:

```bash
# Run all tests
python -m tests.run_tests

# Run unit tests only
python -m tests.run_tests --unit

# Run integration tests only
python -m tests.run_tests --integration

# Run tests with verbose output
python -m tests.run_tests -v

# Run tests for specific modules
python -m tests.run_tests --modules services api

# Run tests matching a pattern
python -m tests.run_tests --pattern "TestCreateCampaign"

# Run tests with coverage report
python -m tests.run_tests --coverage
```

### Basic Test Execution

To run all tests using pytest directly:

```bash
pytest
```

To run a specific test file:

```bash
pytest tests/test_campaign_service.py
```

To run tests with a specific name pattern:

```bash
pytest -k "TestCreateCampaign"
```

### Test with Coverage

To run tests with coverage reporting:

```bash
python -m tests.generate_coverage_report
```

This will run all tests and generate a comprehensive coverage report.

#### Coverage Report Options

The coverage report tool supports several options:

```bash
python -m tests.generate_coverage_report --quiet  # Don't output test results to console
python -m tests.generate_coverage_report --tests tests/test_campaign_service.py  # Run specific tests
```

## Test Fixtures

Common test fixtures are defined in `conftest.py` and include:

- `db`: A fresh in-memory SQLite database for each test
- `client`: A FastAPI TestClient with dependency overrides
- `test_user`: A standard user for authentication tests
- `test_superuser`: A user with admin privileges
- `token_headers`: Authorization headers with JWT token for the test user
- `test_campaign`: A sample campaign for testing campaign operations
- `mock_openai_response`: Mocked responses for AI-related tests

## Mocking Strategy

The testing framework uses several mocking strategies:

1. **Database Mocking**:
   - Unit tests use `Mock` objects to simulate database interactions
   - Integration tests use an in-memory SQLite database

2. **External Service Mocking**:
   - OpenAI API calls are mocked to return predetermined responses
   - Email sending services are mocked to prevent actual emails

3. **Environment Variables**:
   - Test environment uses settings from `app/core/config.py` with `ENVIRONMENT=test`

## Best Practices for Writing Tests

When adding new tests to the ReplyRocket.io application, follow these guidelines:

1. **Arrange-Act-Assert**: Structure tests with clear sections for setup, execution, and verification
2. **One Assertion Per Test**: Each test should verify a single behavior
3. **Descriptive Test Names**: Names should clearly describe what is being tested
4. **Independent Tests**: Tests should not depend on other tests or their order of execution
5. **Mock External Dependencies**: Use mocks for external services, databases, etc.
6. **Test Edge Cases**: Include tests for error conditions and boundary scenarios
7. **Keep Tests Fast**: Optimize tests to run quickly

## Coverage Goals

The project aims for the following coverage targets:

- **Services**: 90%+ coverage of all business logic
- **API Endpoints**: 85%+ coverage of all endpoints
- **Core Modules**: 95%+ coverage of security and critical infrastructure
- **Overall**: 85%+ total coverage

## Continuous Integration

Tests are automatically run on:
- Pull requests to the main branch
- Daily scheduled runs
- Manual trigger via CI/CD pipeline

## Adding New Tests

When adding new features to the application, follow this process:

1. Write tests that cover the new functionality
2. Run tests to ensure they fail initially
3. Implement the feature until tests pass
4. Run the full test suite to ensure no regressions
5. Generate a coverage report to verify coverage targets are met

## Available Test Tools

The testing directory includes several helpful tools:

- **run_tests.py**: A script to run tests with various options
- **generate_coverage_report.py**: A script to generate coverage reports
- **conftest.py**: Common fixtures for tests

## Troubleshooting Tests

Common issues with tests:

- **Database State**: Ensure tests clean up after themselves
- **Async/Await**: Properly handle asynchronous code in tests
- **Mocking Errors**: Check mock setup for external services
- **Test Independence**: Ensure tests don't depend on each other

## Reference Documentation

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#session-external-transaction)

# ReplyRocket.io Testing Documentation

This document provides information about the testing structure, how to run tests, and guidelines for writing new tests for the ReplyRocket.io application.

## Table of Contents

1. [Test Structure](#test-structure)
2. [Running Tests](#running-tests)
3. [Coverage Reports](#coverage-reports)
4. [Test Types](#test-types)
5. [Guidelines for Writing Tests](#guidelines-for-writing-tests)
6. [Continuous Integration](#continuous-integration)

## Test Structure

The test suite is organized as follows:

- `tests/` - Root directory for all tests
  - `test_*.py` - Unit and integration tests for specific modules
  - `conftest.py` - Pytest fixtures shared across multiple test files
  - `run_coverage.py` - Script to run tests with coverage reporting
  - `utils/` - Helper utilities for tests
  - `integration/` - Integration tests that test multiple components together

## Running Tests

### Running All Tests

To run all tests, use:

```bash
python -m pytest
```

### Running Specific Tests

To run tests from a specific module:

```bash
python -m pytest tests/test_campaign_service.py
```

To run a specific test class:

```bash
python -m pytest tests/test_campaign_service.py::TestCreateCampaign
```

To run a specific test method:

```bash
python -m pytest tests/test_campaign_service.py::TestCreateCampaign::test_create_campaign_success
```

### Running with Coverage

We have a custom script to run tests with coverage reports:

```bash
python tests/run_coverage.py
```

Options:
- Run specific tests with coverage: `python tests/run_coverage.py tests/test_campaign_service.py`
- Disable HTML report: `python tests/run_coverage.py --no-html`
- Hide missing lines in report: `python tests/run_coverage.py --no-missing`

## Coverage Reports

After running tests with coverage, you can view:

1. **Terminal report**: Shows coverage statistics in the console
2. **HTML report**: More detailed, interactive report found in the `htmlcov/` directory
   - Open `htmlcov/index.html` in a web browser to view

## Test Types

### Unit Tests

Unit tests focus on testing individual functions and classes in isolation. Examples:
- `test_campaign_service.py` - Tests for the campaign service functions
- `test_email_service.py` - Tests for the email service functions
- `test_ai_email_generator_service.py` - Tests for the AI email generator

### Integration Tests

Integration tests verify that different components work together correctly. These are typically found in the `integration/` directory.

### Stress Tests

Stress tests evaluate system performance under high load:
- `test_campaign_stress.py` - Tests campaign operations under heavy load

These tests are marked with `@pytest.mark.stress` and can be run separately:

```bash
python -m pytest -m stress
```

## Guidelines for Writing Tests

### Unit Tests

1. **Mock external dependencies**: Use the `unittest.mock` module to isolate the function being tested.
2. **Follow the AAA pattern**:
   - **Arrange**: Set up test data, mocks, etc.
   - **Act**: Call the function being tested
   - **Assert**: Verify the expected outcomes

3. **Test error cases**: Ensure functions handle errors correctly
4. **Keep tests independent**: One test should not depend on another

### Example Unit Test Structure

```python
def test_function_name_scenario(self, fixtures):
    """Test description explaining what is being tested."""
    # Arrange
    # Set up test data, mocks, etc.
    
    # Act
    # Call the function being tested
    
    # Assert
    # Verify the result is as expected
```

## Continuous Integration

Our CI pipeline runs all tests automatically on:
- Pull requests
- Merges to main branch

The CI checks code coverage and will fail if coverage drops below the configured threshold.

## Test-Driven Development

We encourage TDD for new features:
1. Write tests first that define the expected behavior
2. Run the tests (they should fail)
3. Implement the feature until tests pass
4. Refactor while keeping tests green

## Troubleshooting

### Common Issues

1. **Database-related test failures**:
   - Ensure test database is configured correctly
   - Check that database migrations are up to date

2. **Mock-related issues**:
   - Verify that mocks are configured to return appropriate values
   - Ensure that patched functions/methods are in the correct module path

3. **Flaky tests**:
   - Mark known flaky tests with `@pytest.mark.flaky(reruns=3)`
   - Investigate and fix the underlying cause of flakiness 