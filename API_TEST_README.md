# ReplyRocket.io API Testing Script

This Python script allows you to test all the API endpoints in the ReplyRocket.io FastAPI backend. The script uses `httpx` for making HTTP requests and provides a comprehensive test suite covering authentication, email generation, campaign management, and more.

## Features

- Tests all major API endpoints
- Provides detailed reporting on test results
- Uses async functionality for better performance
- Configurable through command-line options
- Beautiful console output with color coding

## Installation

1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r api_test_requirements.txt
   ```

## Usage

Run the script with default settings:

```bash
python api_test_script.py test
```

### Command-line Options

- `--base-url` / `-b`: API base URL (default: http://localhost:8000/api/v1)
- `--email` / `-e`: User email for authentication (default: test@example.com)
- `--password` / `-p`: User password for authentication (default: password123)
- `--timeout` / `-t`: Request timeout in seconds (default: 30)
- `--log-level` / `-l`: Logging level (default: INFO)

Example with custom parameters:

```bash
python api_test_script.py test --base-url https://api.replyrocket.io/api/v1 --email admin@example.com --password securepassword --log-level DEBUG
```

## Test Categories

The script tests the following API endpoint categories:

1. **Authentication**
   - User registration
   - Login and token retrieval

2. **User Management**
   - Get current user info
   - Update user profile
   - Configure SMTP settings

3. **Campaign Management**
   - Create campaigns
   - List all/active campaigns
   - Get campaign details
   - Update campaigns
   - Configure A/B testing

4. **Email Functionality**
   - Generate email content
   - Send emails

5. **Follow-ups**
   - Generate follow-up emails

6. **Statistics**
   - User statistics
   - Campaign performance metrics

## Interpreting Results

The script produces a summary table showing:
- Total number of tests
- Pass/fail statistics
- Detailed results for each endpoint
- Error messages for failed tests

## Customization

You can extend the script by adding more test methods to the `APITester` class. Follow the existing pattern for implementing new endpoint tests. 