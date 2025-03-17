# API Testing Guide

This guide explains how to use the API testing script to verify ReplyRocket.io's API functionality.

## Overview

The test script (`api_test_script.py`) provides a comprehensive way to validate the API endpoints of the ReplyRocket.io application. It tests user registration, authentication, campaign management, email generation, and other core features.

## Requirements

Install the required dependencies:

```bash
pip install -r api_test_requirements.txt
```

The script requires:
- httpx
- python-dotenv
- colorama
- pytest (optional, for future integration)

## Configuration

Create a `.env.test` file with the following variables:

```
TEST_API_BASE_URL=http://localhost:8000
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=StrongPassword123!
```

## Running the Tests

Execute the test script:

```bash
python api_test_script.py
```

### Test Flow

The script follows this sequence:
1. Register a new test user (or login if already exists)
2. Create a test campaign
3. Generate an email using AI
4. Send test emails
5. Test email tracking
6. Test campaign statistics
7. Clean up (delete test campaign)

## Test Output

The script provides detailed logging of each test step with color-coded output:
- Green: Successful tests
- Red: Failed tests
- Yellow: Warnings or informational messages

## Extending the Tests

To add new tests:
1. Add a new test function to the script
2. Follow the existing pattern for request making and response validation
3. Add your new test to the `run_all_tests()` function

## Troubleshooting

Common issues:
- **Connection errors**: Ensure the API server is running
- **Authentication failures**: Check that your test credentials are valid
- **Rate limiting**: Add delays between tests if needed

## Continuous Integration

The test script can be integrated into CI pipelines by:
1. Setting environment variables in your CI system
2. Running the script as part of deployment verification
3. Using the exit code (0 for success, non-zero for failure) to determine build status 
