"""
Configuration settings for ReplyRocket.io.

This module handles environment-specific configuration values and ensures
secrets are properly loaded from environment variables.
"""

import os
import secrets
import logging
import sys
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Literal

from pydantic import AnyHttpUrl, PostgresDsn, validator, Field, SecretStr
from pydantic_settings import BaseSettings


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class LogFormat(str, Enum):
    TEXT = "text"
    JSON = "json"


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class BaseAppSettings(BaseSettings):
    """Base application settings shared across all environments."""
    
    # Environment settings
    ENVIRONMENT: EnvironmentType = EnvironmentType.DEVELOPMENT
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "ReplyRocket.io API"
    VERSION: str = "0.1.0"
    
    # Derived values
    IS_DEVELOPMENT: bool = False
    IS_STAGING: bool = False
    IS_PRODUCTION: bool = False
    IS_TEST: bool = False
    
    # Logging settings
    LOG_LEVEL: LogLevel = LogLevel.INFO
    LOG_FORMAT: LogFormat = LogFormat.TEXT
    
    @validator("IS_DEVELOPMENT", "IS_STAGING", "IS_PRODUCTION", "IS_TEST", pre=True, always=True)
    def set_environment_flags(cls, v: bool, values: Dict[str, Any]) -> bool:
        if "ENVIRONMENT" not in values:
            return False
        env = values["ENVIRONMENT"]
        if v:  # If manually set to True, respect that
            return True
        return cls._check_environment_match(env, v)
    
    @classmethod
    def _check_environment_match(cls, env: EnvironmentType, flag_value: bool) -> bool:
        field_name = f"IS_{env.upper()}"
        return flag_value or field_name == f"IS_{env.upper()}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


class DevelopmentSettings(BaseAppSettings):
    """Settings for the development environment."""
    
    # Debug settings
    DEBUG: bool = True
    
    # Security settings - less strict for development
    SECRET_KEY: str = Field(
        default_factory=lambda: os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for easier development
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # 30 days for easier development
    SECURE_COOKIES: bool = False
    
    # CORS - more permissive for development
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database settings
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "replyrocket_dev"
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    # Database pool settings for development (smaller pool)
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # Logging
    LOG_LEVEL: LogLevel = LogLevel.DEBUG


class StagingSettings(BaseAppSettings):
    """Settings for the staging environment."""
    
    # Debug settings
    DEBUG: bool = False
    
    # Security settings - more strict for staging
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # Required from environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECURE_COOKIES: bool = True
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database settings
    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    # Database pool settings 
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800


class ProductionSettings(BaseAppSettings):
    """Settings for the production environment."""
    
    # Debug settings
    DEBUG: bool = False
    
    # Security settings - very strict for production
    SECRET_KEY: str = Field(..., env="SECRET_KEY")  # Required from environment
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Shorter token lifetime for security
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SECURE_COOKIES: bool = True
    
    # CORS - restrict to specific domains in production
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Database settings
    POSTGRES_SERVER: str = Field(..., env="POSTGRES_SERVER")
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None
    
    # Database pool settings - larger pool for production
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    
    # AI Service settings - required for production
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    AI_MODEL: str = Field(..., env="AI_MODEL")
    
    # Superuser - optional in production
    FIRST_SUPERUSER_EMAIL: Optional[str] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    
    # Email settings - required for production
    EMAIL_TEMPLATES_DIR: str = "app/email-templates/"


class TestSettings(BaseAppSettings):
    """Settings for the test environment."""
    
    # Debug settings
    DEBUG: bool = False
    
    # Security settings
    SECRET_KEY: str = "test-secret-key-not-used-in-real-environments"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 5
    REFRESH_TOKEN_EXPIRE_DAYS: int = 1
    SECURE_COOKIES: bool = False
    
    # Database settings - use SQLite for tests
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./test.db"
    
    # Testing flag
    TESTING: bool = True


# Common validation for all settings classes
@validator("SQLALCHEMY_DATABASE_URI", pre=True)
def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
    """Build the database URI from component parts if not provided directly."""
    if isinstance(v, str):
        return v
    
    # Get database components, ensuring they're all present
    required_keys = ["POSTGRES_SERVER", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]
    missing_keys = [key for key in required_keys if key not in values or not values[key]]
    
    if missing_keys and values.get("ENVIRONMENT") in [EnvironmentType.STAGING, EnvironmentType.PRODUCTION]:
        missing_env_vars = [f"{key}" for key in missing_keys]
        raise ValueError(f"Missing required environment variables: {', '.join(missing_env_vars)}")
    
    postgres_server = values.get("POSTGRES_SERVER", "localhost")
    postgres_user = values.get("POSTGRES_USER", "postgres")
    postgres_password = values.get("POSTGRES_PASSWORD", "postgres")
    postgres_db = values.get("POSTGRES_DB", "replyrocket")
    
    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}/{postgres_db}"


@validator("BACKEND_CORS_ORIGINS", pre=True)
def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
    """Parse CORS origins from string to list."""
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, (list, str)):
        return v
    raise ValueError(v)


# Load settings based on the environment
def get_settings() -> BaseAppSettings:
    """
    Get the appropriate settings based on the ENVIRONMENT variable.
    Falls back to development settings if not specified.
    """
    env = os.getenv("ENVIRONMENT", "development")
    settings_class = {
        EnvironmentType.DEVELOPMENT: DevelopmentSettings,
        EnvironmentType.STAGING: StagingSettings, 
        EnvironmentType.PRODUCTION: ProductionSettings,
        EnvironmentType.TEST: TestSettings,
    }.get(env, DevelopmentSettings)
    
    try:
        settings = settings_class()
        
        # Validate required settings for production environment
        if env == EnvironmentType.PRODUCTION:
            required_vars = ["SECRET_KEY", "POSTGRES_PASSWORD", "OPENAI_API_KEY"]
            missing_vars = [var for var in required_vars if not getattr(settings, var, None)]
            if missing_vars:
                logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
                logging.error("Production deployment requires all security-critical variables to be set!")
                sys.exit(1)
        
        return settings
    except Exception as e:
        logging.error(f"Failed to load settings: {str(e)}")
        if env == EnvironmentType.PRODUCTION:
            logging.error("Aborting startup due to missing critical configuration!")
            sys.exit(1)
        logging.warning(f"Falling back to development settings")
        return DevelopmentSettings()


# Instantiate the settings
settings = get_settings()

# Debug output for development environment
if settings.IS_DEVELOPMENT:
    print("\n" + "="*50)
    print("ENVIRONMENT VARIABLE DEBUGGING")
    print("="*50)
    print(f"ENVIRONMENT: '{settings.ENVIRONMENT}'")
    print(f"VERSION: '{settings.VERSION}'")
    print(f"SQLALCHEMY_DATABASE_URI: '{settings.SQLALCHEMY_DATABASE_URI}'")
    print(f".env file location: {os.path.abspath('.env') if os.path.exists('.env') else '.env NOT FOUND!'}")
    print("="*50 + "\n") 