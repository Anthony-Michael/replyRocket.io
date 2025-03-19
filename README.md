# ReplyRocket.io

ReplyRocket.io is a powerful email campaign automation platform designed to help you create personalized outreach campaigns that get results.

## Features

- 🚀 **AI-Powered Email Generation**: Create personalized cold emails using AI
- 📊 **Campaign Analytics**: Track opens, replies, and conversions
- 🧪 **A/B Testing**: Test different messaging approaches to see what works best
- 📅 **Automated Follow-ups**: Schedule follow-up sequences for non-responders
- 🔒 **Secure Authentication**: JWT-based authentication with refresh tokens

## Getting Started

### Prerequisites

- Python 3.10+
- PostgreSQL
- Node.js 16+ (for frontend)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/replyrocket.io.git
   cd replyrocket.io
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env file with your configuration
   ```

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
app/
├── api/                  # API endpoints
│   └── api_v1/
│       └── endpoints/    # Route handlers
├── core/                 # Core functionality (config, security)
├── crud/                 # Database operations
├── db/                   # Database setup and session management
├── models/               # Database models
├── schemas/              # Pydantic schemas for validation
├── services/             # Business logic layer
│   ├── user_service.py
│   ├── campaign_service.py
│   ├── email_service.py
│   └── ai_email_generator_service.py
└── main.py               # Application entry point

tests/                    # Test suite
├── test_*.py             # Unit and integration tests
└── utils/                # Testing utilities
```

## Architecture

ReplyRocket.io follows a layered architecture pattern:

1. **API Layer**: HTTP interface with request validation
2. **Service Layer**: Business logic implementation
3. **CRUD Layer**: Database operations
4. **Model Layer**: Database schema definitions

This architecture ensures separation of concerns and testability.

## Testing Strategy

Our testing strategy is comprehensive, covering all layers of the application:

### Unit Tests

Unit tests focus on testing individual components in isolation. We use pytest for our testing framework and unittest.mock for isolating components.

```bash
# Run all unit tests
python -m pytest

# Run specific test file
python -m pytest tests/test_campaign_service.py

# Run with coverage report
python tests/run_coverage.py
```

### Integration Tests

Integration tests ensure that different components work together correctly.

```bash
# Run integration tests
python -m pytest tests/integration/
```

### Stress Tests

Stress tests evaluate system performance under high load.

```bash
# Run stress tests
python -m pytest tests/test_campaign_stress.py
```

### Code Coverage

We aim for high test coverage to ensure code quality and reliability.

```bash
# Generate coverage report
python tests/run_coverage.py

# View HTML coverage report
# Open htmlcov/index.html in your browser
```

For more detailed information about our testing approach, see [tests/README.md](tests/README.md).

## API Documentation

When the application is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -am 'Add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Submit a pull request

Please ensure that all tests pass and code coverage is maintained before submitting a pull request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 