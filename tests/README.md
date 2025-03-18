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