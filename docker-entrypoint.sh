#!/bin/bash
set -eo pipefail

# Function to check if Postgres is ready
check_postgres() {
    echo "Checking if Postgres is ready..."
    
    host="$(echo $POSTGRES_SERVER)"
    port="${POSTGRES_PORT:-5432}"
    user="${POSTGRES_USER}"
    db="${POSTGRES_DB}"
    
    until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -p "$port" -U "$user" -d "$db" -c '\q'; do
        echo "Postgres is unavailable - sleeping"
        sleep 2
    done
    
    echo "Postgres is up - continuing"
}

# Function to validate required environment variables
validate_env() {
    echo "Validating environment variables..."
    
    required_vars=(
        "ENVIRONMENT"
        "SECRET_KEY"
        "POSTGRES_SERVER"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
    )
    
    if [ "$ENVIRONMENT" = "production" ]; then
        # In production we also require:
        required_vars+=(
            "OPENAI_API_KEY"
        )
    fi
    
    missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "ERROR: Missing required environment variables:"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        exit 1
    fi
    
    echo "Environment validation passed"
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    alembic upgrade head
    echo "Migrations complete"
}

# Function to create initial superuser if specified
create_superuser() {
    if [ -n "$FIRST_SUPERUSER_EMAIL" ] && [ -n "$FIRST_SUPERUSER_PASSWORD" ]; then
        echo "Creating initial superuser..."
        python -m app.initial_data
        echo "Superuser created"
    fi
}

# Main entrypoint logic
main() {
    # Validate environment
    validate_env
    
    # Check if this is a command or service
    if [ "$1" = "uvicorn" ] || [ "$1" = "gunicorn" ]; then
        # This is the app service - run startup checks
        check_postgres
        run_migrations
        create_superuser
        
        # Check environment-specific setup
        if [ "$ENVIRONMENT" = "production" ]; then
            echo "Starting application in PRODUCTION mode"
        elif [ "$ENVIRONMENT" = "staging" ]; then
            echo "Starting application in STAGING mode"
        else
            echo "Starting application in DEVELOPMENT mode"
        fi
    fi
    
    # Execute the command
    exec "$@"
}

# Run the main function passing all arguments
main "$@" 