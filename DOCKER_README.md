# Docker Setup for ReplyRocket.io

This document provides instructions for running the ReplyRocket.io backend using Docker and Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Configuration

### Environment Variables

The application requires certain environment variables to be set. For local development, these can be set in the `docker-compose.yml` file or in a `.env` file in the project root.

Required variables:
- `OPENAI_API_KEY`: Your OpenAI API key for email generation

Optional variables (defaults are provided in docker-compose.yml):
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Secret key for JWT token generation
- `BACKEND_CORS_ORIGINS`: List of allowed CORS origins

Example `.env` file:
```
OPENAI_API_KEY=your-openai-api-key
```

## Development Setup

For local development, we use `docker-compose.yml` with `Dockerfile.dev`, which provides hot-reloading and development tools.

### Starting the Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/replyRocket.io.git
   cd replyRocket.io
   ```

2. Create a `.env` file with your configuration (see above).

3. Start the development services:
   ```bash
   docker-compose up -d
   ```

This will start:
- FastAPI application on http://localhost:8000
- PostgreSQL database on localhost:5432
- pgAdmin on http://localhost:5050 (login with admin@replyrocket.io / admin)

The API documentation will be available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Running Tests in Docker

To run tests using the development container:

```bash
docker-compose exec api pytest
```

To generate a coverage report:

```bash
docker-compose exec api pytest --cov=app --cov-report=term-missing
```

## Production Setup

For production deployment, we use the multi-stage `Dockerfile` which creates a minimal image.

### Building the Production Image

```bash
docker build -t replyrocket-api:latest .
```

### Running in Production

Create a Docker Compose file for production (docker-compose.prod.yml):

```yaml
version: '3.8'

services:
  api:
    image: replyrocket-api:latest
    restart: always
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/replyrocket
      - SECRET_KEY=secure-production-key
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - BACKEND_CORS_ORIGINS=["https://replyrocket.io"]
    depends_on:
      - db

  db:
    image: postgres:14-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data/
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=replyrocket
    restart: always

volumes:
  postgres_data:
```

Start the production services:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Docker Image Structure

The Docker setup includes:

1. **Production Dockerfile (`Dockerfile`)**:
   - Multi-stage build to minimize image size
   - Uses Python 3.10 slim base image
   - Runs as a non-root user for security
   - Uses Gunicorn with Uvicorn workers for production performance

2. **Development Dockerfile (`Dockerfile.dev`)**:
   - Single-stage build optimized for development
   - Includes development and testing tools
   - Uses hot-reloading for faster development

3. **Docker Compose Configuration**:
   - Sets up FastAPI, PostgreSQL, and pgAdmin services
   - Mounts source code as volumes for development
   - Configures environment variables

## Troubleshooting

### Database Connection Issues

If the API can't connect to the database:
1. Ensure the PostgreSQL container is running: `docker-compose ps`
2. Check PostgreSQL logs: `docker-compose logs db`
3. Verify the `DATABASE_URL` environment variable is correct

### Permission Issues

If you encounter permission issues with mounted volumes:
1. Ensure the host directories exist
2. Check file ownership and permissions
3. You may need to run `sudo chown -R $(id -u):$(id -g) .` in the project directory

### API Not Starting

If the API container is not starting properly:
1. Check the API logs: `docker-compose logs api`
2. Verify all required environment variables are set
3. Ensure the `main.py` file exists in the project root 