import secrets
import os
from typing import Any, Dict, List, Optional, Union

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Adding test environment variables for debugging purposes
    TEST_VAR_ONE: str = "default_value_one"  # Will be overridden if TEST_VAR_ONE exists in .env
    TEST_VAR_TWO: str = "default_value_two"  # Will be overridden if TEST_VAR_TWO exists in .env
    
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    
    # Application version and environment
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"  # Options: development, staging, production
    
    # CORS Configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Project info
    PROJECT_NAME: str = "ReplyRocket.io"
    
    # Database configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "replyrocket"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    @field_validator("SQLALCHEMY_DATABASE_URI", mode="before")
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        """
        Validates and builds the database URI.
        - If a string is provided directly, it's returned as is
        - Otherwise, build a PostgresDsn from components and convert to string
        
        The str() conversion is critical because SQLAlchemy expects a string or URL object,
        not a Pydantic PostgresDsn object.
        """
        if isinstance(v, str):
            return v
            
        # Build the PostgresDsn from components
        postgres_dsn = PostgresDsn.build(
            scheme="postgresql",
            username=values.data.get("POSTGRES_USER"),
            password=values.data.get("POSTGRES_PASSWORD"),
            host=values.data.get("POSTGRES_SERVER"),
            path=f"{values.data.get('POSTGRES_DB') or ''}",
        )
        
        # Convert to string to ensure SQLAlchemy compatibility
        return str(postgres_dsn)

    # OpenAI configuration
    OPENAI_API_KEY: str = ""
    
    # Email service configuration
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Stripe API key
    STRIPE_API_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Explicit configuration for .env file loading
    # - env_file: Path to .env file
    # - env_file_encoding: Encoding of .env file (utf-8 is standard)
    # - case_sensitive: Whether variable names are case-sensitive
    # - extra: How to handle extra variables (ignore, forbid, allow)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Instantiate settings
settings = Settings()

# DEBUG: Print environment variable values for debugging
if settings.ENVIRONMENT == "development":
    print("\n" + "="*50)
    print("ENVIRONMENT VARIABLE DEBUGGING")
    print("="*50)
    print(f"ENVIRONMENT: '{settings.ENVIRONMENT}'")
    print(f"VERSION: '{settings.VERSION}'")
    print(f"TEST_VAR_ONE: '{settings.TEST_VAR_ONE}' (default is 'default_value_one')")
    print(f"TEST_VAR_TWO: '{settings.TEST_VAR_TWO}' (default is 'default_value_two')")
    print(f"SQLALCHEMY_DATABASE_URI: '{settings.SQLALCHEMY_DATABASE_URI}'")
    print(f".env file location: {os.path.abspath('.env') if os.path.exists('.env') else '.env NOT FOUND!'}")
    print("="*50 + "\n") 