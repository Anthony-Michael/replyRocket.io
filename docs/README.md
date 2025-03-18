# ReplyRocket.io

ReplyRocket is an AI-powered email marketing platform that allows users to easily create, send and track personalized email campaigns.

## Features

- AI-powered email content generation
- A/B testing support for email campaigns
- Email tracking and analytics
- User authentication and profile management
- Campaign management

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- Docker (optional for containerized development)

### Installation

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and configure your environment variables
4. Run database migrations: `alembic upgrade head`
5. Start the application: `uvicorn main:app --reload`

## Repository Structure

- `/app` - Main application code
- `/docs` - Documentation files
- `/infrastructure` - Deployment and infrastructure configuration 
- `/tests` - Unit and integration tests
- `/alembic` - Database migration files

## Documentation

For detailed documentation, please see the following guides in the docs folder:

- [Project Structure and Architecture](docs/README.md)
- [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md)
- [Docker Setup and Usage](docs/DOCKER_README.md)
- [API Testing Guide](docs/API_TESTING.md)
- [Clean Code Refactoring](docs/CLEAN_CODE_REFACTORING.md)
- [Code Quality Guidelines](docs/code_quality_guidelines.md)

## Development

For local development:
```
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python run_tests.py
```

## Deployment

For production deployment, see the infrastructure directory which contains:

- Dockerfile for containerization
- Docker Compose configuration
- Caddy server configuration
- GitHub Actions workflow for CI/CD

For detailed instructions, refer to the [Production Deployment Guide](docs/PRODUCTION_DEPLOYMENT.md).

## License

This project is licensed under the MIT License - see the LICENSE file for details. 