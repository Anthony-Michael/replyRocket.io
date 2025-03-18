# ReplyRocket.io

AI-powered email reply generation for busy professionals. 

## Features

- Generate personalized email responses with AI
- Manage email campaigns
- Track email engagement
- Smart response templates
- Seamless CRM integrations

## Table of Contents

- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Security Considerations](#security-considerations)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Docker & Docker Compose (optional)

### Local Setup

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

4. Copy the environment example file and configure it:

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Run database migrations:

```bash
alembic upgrade head
```

6. Start the development server:

```bash
uvicorn app.main:app --reload
```

### Docker Setup

1. Build and start the containers:

```bash
docker-compose up -d
```

2. Run initial migrations:

```bash
docker-compose exec app alembic upgrade head
```

## Environment Setup

ReplyRocket.io uses environment-specific configurations for development, staging, and production environments.

### Required Environment Variables

Copy the `.env.example` file to `.env` for your environment and set the following variables:

```
# Environment
ENVIRONMENT=development  # Options: development, staging, production

# Security
SECRET_KEY=  # Generate with: openssl rand -hex 32

# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_DB=replyrocket

# API Keys
OPENAI_API_KEY=  # Required for AI email generation
```

### Environment-Specific Configuration

The application loads configuration based on the `ENVIRONMENT` variable:

- **Development**: Relaxed security, debug logs, development database
- **Staging**: Stricter security, required env variables, staging database
- **Production**: Strict security, all critical variables required, optimized for performance

### Generating Secure Keys

Generate a strong secret key:

```bash
# Option 1: Using Python
python -c "import secrets; print(secrets.token_hex(32))"

# Option 2: Using OpenSSL
openssl rand -hex 32
```

## Development

### Code Structure

```
app/
├── api/              # API endpoints
├── core/             # Core configuration
├── crud/             # Database CRUD operations
├── db/               # Database setup
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # Business logic
└── utils/            # Utility functions
tests/                # Test files
alembic/              # Database migrations
```

### Running the Development Server

```bash
uvicorn app.main:app --reload
```

### Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:

```bash
alembic upgrade head
```

## Testing

Run tests with pytest:

```bash
pytest
```

Generate test coverage report:

```bash
pytest --cov=app tests/
```

## Deployment

See the [deploy.md](deploy.md) file for detailed deployment instructions.

### Quick Production Deployment

1. Configure production environment:

```bash
cp .env.example .env.production
# Edit .env.production with production values
```

2. Deploy with Docker Compose:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Security Considerations

### Environment Variables

- **Never commit** `.env` files to version control
- **Never hardcode** sensitive information in code
- Use **strong, unique** keys for production
- Rotate secrets regularly

### Database Security

- Use strong passwords
- Limit database user permissions
- Configure database connection pooling properly
- Back up your database regularly

### API Security

- Use HTTPS in production
- Implement rate limiting
- Validate all inputs
- Use proper authentication and authorization

## API Documentation

When the server is running, access the interactive API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 